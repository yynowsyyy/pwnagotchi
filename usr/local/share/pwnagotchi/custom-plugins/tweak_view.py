import logging
import os
import time
import sys
import html
import json
from flask import render_template_string, request, jsonify

import pwnagotchi.plugins as plugins
from pwnagotchi.ui.components import *

class TweakView(plugins.WebPlugin):
    __author__ = 'Sniffleupagus & Community'
    __version__ = '2.0.0'
    __license__ = 'GPL3'
    __description__ = 'Erweitertes Tweak-View mit Echtzeit-Schiebereglern und 3s Render-Delay.'

    def __init__(self):
        super(TweakView, self).__init__()
        self.ready = False
        self.view = None

    def on_loaded(self):
        logging.info("[TweakView] Geladen mit Schieberegler-Modifikation.")

    def on_ui_setup(self, view):
        self.view = view
        self.ready = True

    def on_webhook(self, path, request):
        if not self.ready or not self.view:
            return "UI-System ist noch nicht bereit. Bitte kurz warten."

        # Neuer API-Endpunkt für den Schieberegler-AJAX-Call
        if request.method == 'POST' and path == 'slider_update':
            try:
                data = request.get_json()
                key = data.get('key')
                x = int(data.get('x'))
                y = int(data.get('y'))

                if key in self.view._state._state:
                    element = self.view._state._state[key]
                    
                    # Setze die Koordinaten im Pwnagotchi-Element
                    if hasattr(element, 'xy'):
                        element.xy = (x, y)
                    elif hasattr(element, 'position'):
                        element.position = (x, y)

                    # Erzwinge ressourcenschonendes Neuzeichnen im RAM (und Display)
                    self.view.update(force=True)
                    
                    logging.info(f"[TweakView] {key} verschoben auf: ({x}, {y})")
                    return jsonify({"status": "success", "message": f"{key} aktualisiert"})
                else:
                    return jsonify({"status": "error", "message": "Element nicht gefunden"}), 404
            except Exception as e:
                return jsonify({"status": "error", "message": str(e)}), 500

        # Die Hauptseite des Tweak-View Plugins
        if request.method == 'GET' and (path == '' or path == '/'):
            elements_data = []
            display_width = self.view.width()
            display_height = self.view.height()

            # Extrahiere alle veränderbaren UI-Komponenten aus der View
            for key, element in self.view._state._state.items():
                pos = (0, 0)
                if hasattr(element, 'xy'):
                    pos = element.xy
                elif hasattr(element, 'position'):
                    pos = element.position
                
                if isinstance(pos, (list, tuple)) and len(pos) >= 2:
                    elements_data.append({
                        "key": key,
                        "x": pos[0],
                        "y": pos[1],
                        "type": element.__class__.__name__
                    })

            return render_template_string(TEMPLATE, elements=elements_data, width=display_width, height=display_height)

        return "404 Not Found", 404

# --- DAS INTEGRATIVE FRONTEND (HTML / JS / CSS) ---
TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Pwnagotchi Tweak View - Sliders</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: 'Courier New', Courier, monospace; background-color: #121212; color: #e0e0e0; padding: 20px; }
        h1 { color: #ff9800; border-bottom: 2px solid #ff9800; padding-bottom: 10px; margin-bottom: 5px; }
        .subtitle { color: #888; font-size: 0.9em; margin-bottom: 20px; }
        .canvas-info { font-weight: bold; margin-bottom: 20px; color: #00ff00; background: #1a1a1a; padding: 10px; border-left: 5px solid #00ff00; }
        .element-card { background: #1e1e1e; border: 1px solid #333; padding: 15px; margin-bottom: 15px; border-radius: 6px; box-shadow: 0 2px 5px rgba(0,0,0,0.5); }
        .element-title { font-size: 1.2em; color: #00ffff; font-weight: bold; margin-bottom: 12px; }
        .control-group { margin: 8px 0; display: flex; align-items: center; }
        .control-group label { width: 90px; color: #aaa; }
        input[type=range] { flex-grow: 1; margin: 0 15px; accent-color: #ff9800; cursor: pointer; }
        .val-display { width: 45px; text-align: right; font-weight: bold; color: #fff; background: #2a2a2a; padding: 2px 6px; border-radius: 3px; }
        .status-badge { font-size: 0.85em; padding: 4px 10px; border-radius: 4px; background: #2a2a2a; float: right; color: #bbb; font-weight: bold; }
        .waiting { color: #ff9800 !important; background: rgba(255,152,0,0.1); border: 1px solid #ff9800; }
        .rendering { color: #00ffff !important; background: rgba(0,255,255,0.1); border: 1px solid #00ffff; }
        .saved { color: #00ff00 !important; background: rgba(0,255,0,0.1); border: 1px solid #00ff00; }
    </style>
</head>
<body>
    <h1>Tweak View 2.0</h1>
    <div class="subtitle">Live Layout Editor mit intelligentem 3s Render-Delay</div>
    
    <div class="canvas-info">Hardware-Auflösung: {{ width }}x{{ height }} Pixel</div>

    <div id="elements-container">
        {% for elem in elements %}
        <div class="element-card" id="card-{{ elem.key }}">
            <span class="status-badge" id="status-{{ elem.key }}">Inaktiv</span>
            <div class="element-title">{{ elem.key }} <span style="font-size:0.65em; color:#666; font-weight:normal;">[{{ elem.type }}]</span></div>
            
            <div class="control-group">
                <label>X (Breite):</label>
                <input type="range" min="0" max="{{ width }}" value="{{ elem.x }}" 
                       oninput="updateValue('{{ elem.key }}', 'x', this.value)">
                <span class="val-display" id="val-{{ elem.key }}-x">{{ elem.x }}</span>
            </div>

            <div class="control-group">
                <label>Y (Höhe):</label>
                <input type="range" min="0" max="{{ height }}" value="{{ elem.y }}" 
                       oninput="updateValue('{{ elem.key }}', 'y', this.value)">
                <span class="val-display" id="val-{{ elem.key }}-y">{{ elem.y }}</span>
            </div>
        </div>
        {% endfor %}
    </div>

    <script>
        const timers = {};

        // Verarbeitet das Ziehen am Regler (Sofortiges UI Feedback im Browser)
        function updateValue(key, axis, value) {
            document.getElementById(`val-${key}-${axis}`).innerText = value;
            
            const badge = document.getElementById(`status-${key}`);
            badge.innerText = "Warte (3s)";
            badge.className = "status-badge waiting";

            // Timer zurücksetzen, solange sich der Regler in Bewegung befindet (Debounce)
            if (timers[key]) {
                clearTimeout(timers[key]);
            }

            // Exakt 3000ms nach dem LETZTEN Stopp wird abgeschickt
            timers[key] = setTimeout(() => {
                sendCoordinates(key);
            }, 3000);
        }

        // Sendet die Koordinaten via AJAX ressourcenschonend an den Pi Zero
        function sendCoordinates(key) {
            const xVal = document.getElementById(`val-${key}-x`).innerText;
            const yVal = document.getElementById(`val-${key}-y`).innerText;
            const badge = document.getElementById(`status-${key}`);
            
            badge.innerText = "Rendere...";
            badge.className = "status-badge rendering";

            // Generiert die korrekte Sub-Route relativ zum aktuellen Plugin-Pfad
            const targetUrl = window.location.pathname.replace(/\/$/, "") + '/slider_update';

            fetch(targetUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    key: key,
                    x: parseInt(xVal),
                    y: parseInt(yVal)
                })
            })
            .then(response => response.json())
            .then(data => {
                if(data.status === "success") {
                    badge.innerText = "Gerendert!";
                    badge.className = "status-badge saved";
                    setTimeout(() => {
                        if(badge.innerText === "Gerendert!") {
                            badge.innerText = "Inaktiv";
                            badge.className = "status-badge";
                        }
                    }, 2000);
                } else {
                    badge.innerText = "Fehler";
                    alert("Pwnagotchi meldet Fehler: " + data.message);
                }
            })
            .catch((error) => {
                console.error('Error:', error);
                badge.innerText = "Verbindungsfehler";
            });
        }
    </script>
</body>
</html>
"""
