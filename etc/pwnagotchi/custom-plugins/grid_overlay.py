"""
Pwnagotchi Grid Overlay Plugin
Zeigt ein Koordinaten-Rastergitter mit Punkt-Strich-Linien auf dem Display an.
Ursprung: oben links (0,0)
"""

import logging
from PIL import Image, ImageDraw
import pwnagotchi
import pwnagotchi.ui.fonts as fonts
from pwnagotchi.ui.view import BLACK, WHITE

log = logging.getLogger(__name__)


class GridOverlay(pwnagotchi.plugins.Plugin):
    """
    Plugin das ein Koordinaten-Rastergitter auf dem Display anzeigt.
    
    Config-Beispiel in /etc/pwnagotchi/config.toml:
    [grid_overlay]
    enabled = true
    grid_size = 20        # Pixel zwischen Gitterpunkten
    line_width = 1        # Linienstärke (max 1px)
    dash_size = 3         # Länge Punkt/Strich
    gap_size = 3          # Lücke zwischen Punkt/Strich
    """

    def __init__(self):
        self.grid_size = 20      # Standard Rastergröße in Pixel
        self.line_width = 1      # Linienstärke
        self.dash_size = 3       # Punkt/Strich Länge
        self.gap_size = 3        # Lücke Größe
        self.grid_image = None
        self.enabled = False

    def on_loaded(self):
        """Plugin wurde geladen"""
        log.info("[grid_overlay] Grid Overlay Plugin geladen")
        
        # Config laden falls vorhanden
        self.enabled = self.options.get('enabled', True)
        self.grid_size = self.options.get('grid_size', 20)
        self.line_width = self.options.get('line_width', 1)
        self.dash_size = self.options.get('dash_size', 3)
        self.gap_size = self.options.get('gap_size', 3)
        
        log.info(f"[grid_overlay] Config: grid_size={self.grid_size}, "
                f"line_width={self.line_width}, dash_size={self.dash_size}")

    def _draw_dashed_line(self, draw, x0, y0, x1, y1, color, dash_size=3, gap_size=3):
        """
        Zeichnet eine Strich-Punkt Linie mit PIL ImageDraw
        
        Args:
            draw: PIL ImageDraw Objekt
            x0, y0: Startpunkt
            x1, y1: Endpunkt
            color: Farbe
            dash_size: Länge des Striches/Punktes
            gap_size: Länge der Lücke
        """
        # Richtung bestimmen
        dx = x1 - x0
        dy = y1 - y0
        
        # Länge der Linie
        import math
        length = math.sqrt(dx*dx + dy*dy)
        
        if length == 0:
            return
        
        # Normalisieren
        dx /= length
        dy /= length
        
        # Alternierend Strich und Lücke zeichnen
        x, y = x0, y0
        dash_gap_size = dash_size + gap_size
        distance = 0
        
        while distance < length:
            # Nächsten Punkt berechnen (Strich-Ende)
            next_distance = min(distance + dash_size, length)
            x_next = x0 + dx * next_distance
            y_next = y0 + dy * next_distance
            
            # Linie zeichnen (Strich)
            draw.line(
                [(int(x), int(y)), (int(x_next), int(y_next))],
                fill=color,
                width=self.line_width
            )
            
            # Distanz aktualisieren (Strich + Lücke)
            distance = next_distance + gap_size
            x = x0 + dx * distance
            y = y0 + dy * distance

    def _generate_grid(self, width, height):
        """
        Generiert das Rastergitter-Bild
        
        Args:
            width: Breite des Display
            height: Höhe des Display
            
        Returns:
            PIL Image mit Rastergitter
        """
        # Transparentes Bild (RGBA)
        grid_img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(grid_img)
        
        # Vertikale Linien (Y-Achse verläuft von oben nach unten)
        x = 0
        while x <= width:
            self._draw_dashed_line(
                draw,
                x, 0,           # Start oben
                x, height,      # End unten
                BLACK,
                self.dash_size,
                self.gap_size
            )
            x += self.grid_size
        
        # Horizontale Linien (X-Achse verläuft von links nach rechts)
        y = 0
        while y <= height:
            self._draw_dashed_line(
                draw,
                0, y,           # Start links
                width, y,       # End rechts
                BLACK,
                self.dash_size,
                self.gap_size
            )
            y += self.grid_size
        
        log.debug(f"[grid_overlay] Grid generiert: {width}x{height}, "
                 f"Rastergröße: {self.grid_size}px")
        return grid_img

    def on_ui_setup(self, ui):
        """
        UI Setup - wird aufgerufen wenn UI initialisiert wird.
        Hier registrieren wir das Grid als Custom Element.
        """
        if not self.enabled:
            return
        
        try:
            # Grid für aktuelle Display-Größe generieren
            # Standard Pwnagotchi e-Paper: 250x122, Web-UI: 480x720
            width = ui.canvas.width
            height = ui.canvas.height
            
            self.grid_image = self._generate_grid(width, height)
            log.info(f"[grid_overlay] Grid UI Element registriert ({width}x{height})")
            
        except Exception as e:
            log.error(f"[grid_overlay] Fehler in on_ui_setup: {e}")

    def on_ui_update(self, ui):
        """
        Wird aufgerufen wenn UI aktualisiert wird.
        Hier zeichnen wir das Grid auf den Canvas.
        """
        if not self.enabled or self.grid_image is None:
            return
        
        try:
            # Grid über dem Canvas überlagern
            # Konvertiere RGBA zu RGB wenn nötig
            if self.grid_image.mode == 'RGBA':
                # Nur die Linien (schwarze Pixel) beibehalten
                grid_rgb = Image.new('RGB', self.grid_image.size, WHITE)
                grid_rgb.paste(self.grid_image, (0, 0), self.grid_image)
            else:
                grid_rgb = self.grid_image
            
            # Grid auf Canvas zeichnen (overlay)
            if hasattr(ui, 'canvas'):
                ui.canvas.paste(grid_rgb, (0, 0))
            
        except Exception as e:
            log.error(f"[grid_overlay] Fehler in on_ui_update: {e}")
