import os
import logging
import threading
from time import sleep
from datetime import datetime, timedelta
from pwnagotchi import plugins
from pwnagotchi.utils import StatusFile
from flask import render_template_string
from flask import jsonify

TEMPLATE = """
{% extends "base.html" %}
{% set active_page = "plugins" %}
{% block title %}
    Session stats
{% endblock %}

{% block styles %}
    {{ super() }}
    <style>
        div.chart {
            height: 400px;
            width: 100%;
            position: relative;
            margin-bottom: 2rem;
            padding: 1rem;
            background-color: var(--card-bg);
            border: 1px solid #333;
            border-radius: 8px;
        }
        #session {
            margin-bottom: 1rem;
            padding: 0.5rem;
            background-color: var(--card-bg);
            border: 1px solid #333;
            border-radius: 4px;
            color: var(--text-main);
        }
    </style>
{% endblock %}

{% block scripts %}
    {{ super() }}
    <script src="/js/plugins/chart.min.js"></script>
    <script src="/js/plugins/chartjs-adapter-date-fns.min.js"></script>
{% endblock %}

{% block script %}
    // Chart instances storage
    const charts = {};

    async function fetchData(url) {
        try {
            const response = await fetch(url);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const data = await response.json();
            console.log(`Fetched ${url}:`, data);
            return data;
        } catch (error) {
            console.error(`Failed to fetch ${url}:`, error);
            return { values: [], labels: [] };
        }
    }

    function createChart(elementId, title, data, fill = false) {
        const container = document.getElementById(elementId);
        if (!container) {
            console.warn(`Container ${elementId} not found`);
            return;
        }

        // Destroy existing chart if it exists
        if (charts[elementId]) {
            charts[elementId].destroy();
        }

        // Check if we have data
        if (!data.values || data.values.length === 0) {
            console.warn(`No data for ${elementId}`);
            container.innerHTML = '<p style="padding: 1rem; color: var(--text-muted);">No data available</p>';
            return;
        }

        // Prepare data for Chart.js with category labels (timestamps)
        const allLabels = new Set();
        data.values.forEach(values => {
            values.forEach(([ts]) => allLabels.add(ts));
        });
        const labels = Array.from(allLabels).sort();

        const datasets = data.values.map((values, index) => {
            const color = getChartColor(index);
            // Create a map of timestamp -> value for easy lookup
            const valueMap = Object.fromEntries(values);
            // Ensure all datasets have values for all timestamps (null for missing)
            const chartData = labels.map(ts => valueMap[ts] ?? null);
            
            return {
                label: data.labels[index],
                data: chartData,
                borderColor: color,
                backgroundColor: fill ? color + '33' : 'transparent',
                borderWidth: 2,
                fill: fill,
                tension: 0.1,
                pointRadius: 0,
                pointHoverRadius: 6
            };
        });

        const ctx = container.querySelector('canvas') || document.createElement('canvas');
        if (!container.querySelector('canvas')) {
            container.appendChild(ctx);
        }

        try {
            charts[elementId] = new Chart(ctx, {
                type: 'line',
                data: { 
                    labels: labels,
                    datasets: datasets
                },
                plugins: [bgPlugin],
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        title: {
                            display: true,
                            text: title,
                            font: { size: 16, family: 'var(--font-pixel)' },
                            color: 'var(--text-main)'
                        },
                        legend: {
                            display: true,
                            position: 'bottom',
                            labels: {
                                color: 'var(--text-main)',
                                font: { family: 'var(--font-main)' },
                                padding: 15
                            }
                        }
                    },
                    scales: {
                        x: {
                            type: 'category',
                            grid: { color: '#333' },
                            ticks: { 
                                color: 'var(--text-muted)', 
                                font: { family: 'var(--font-main)' },
                                maxRotation: 45,
                                minRotation: 0
                            }
                        },
                        y: {
                            grid: { color: '#333' },
                            ticks: { color: 'var(--text-muted)', font: { family: 'var(--font-main)' } }
                        }
                    }
                }
            });
            console.log(`Chart ${elementId} created successfully with ${labels.length} data points`);
        } catch (error) {
            console.error(`Failed to create chart ${elementId}:`, error);
        }
    }

    function getChartColor(index) {
        const colors = ['#4caf50', '#ff9800', '#2196f3', '#f44336', '#9c27b0', '#00bcd4'];
        return colors[index % colors.length];
    }

    // Plugin to set canvas background color
    const bgPlugin = {
        id: 'customCanvasBackgroundColor',
        beforeDraw(chart, args, options) {
            const { ctx } = chart;
            ctx.save();
            ctx.globalCompositeOperation = 'destination-over';
            ctx.fillStyle = '#1e1e1e';
            ctx.fillRect(0, 0, chart.width, chart.height);
            ctx.restore();
        }
    };

    async function loadSessionFiles() {
        try {
            const data = await fetchData('/plugins/session-stats/session');
            const select = document.getElementById("session");
            if (!select) {
                console.error('Session select element not found');
                return;
            }
            data.files.forEach(file => {
                const option = document.createElement("option");
                option.text = file;
                select.appendChild(option);
            });
            select.addEventListener('change', loadSessionData);
            console.log('Session files loaded:', data.files);
        } catch (error) {
            console.error('Failed to load session files:', error);
        }
    }

    async function loadSessionData() {
        try {
            const sessionSelect = document.getElementById("session");
            const session = sessionSelect.options[sessionSelect.selectedIndex].text;
            const params = session === 'Current' ? '' : '?session=' + encodeURIComponent(session);
            console.log('Loading session data for:', session);

            const chartConfigs = [
                { endpoint: 'os', id: 'chart_os', title: 'OS Stats', fill: false },
                { endpoint: 'temp', id: 'chart_temp', title: 'Temperature', fill: false },
                { endpoint: 'wifi', id: 'chart_wifi', title: 'WiFi Stats', fill: true },
                { endpoint: 'duration', id: 'chart_duration', title: 'Session Duration', fill: true },
                { endpoint: 'reward', id: 'chart_reward', title: 'Reward', fill: false },
                { endpoint: 'epoch', id: 'chart_epoch', title: 'Epochs', fill: false }
            ];

            for (const config of chartConfigs) {
                const data = await fetchData('/plugins/session-stats/' + config.endpoint + params);
                createChart(config.id, config.title, data, config.fill);
            }
        } catch (error) {
            console.error('Failed to load session data:', error);
        }
    }

    // Load on page ready
    document.addEventListener('DOMContentLoaded', () => {
        console.log('DOM loaded, starting session stats...');
        loadSessionFiles();
        loadSessionData();
        setInterval(loadSessionData, 60000);
    });
{% endblock %}

{% block content %}
    <select id="session">
        <option selected>Current</option>
    </select>
    <div id="chart_os" class="chart"><canvas></canvas></div>
    <div id="chart_temp" class="chart"><canvas></canvas></div>
    <div id="chart_wifi" class="chart"><canvas></canvas></div>
    <div id="chart_duration" class="chart"><canvas></canvas></div>
    <div id="chart_reward" class="chart"><canvas></canvas></div>
    <div id="chart_epoch" class="chart"><canvas></canvas></div>
{% endblock %}
"""


class GhettoClock:
    def __init__(self):
        self.lock = threading.Lock()
        self._track = datetime.now()
        self._counter_thread = threading.Thread(target=self.counter)
        self._counter_thread.daemon = True
        self._counter_thread.start()

    def counter(self):
        while True:
            with self.lock:
                self._track += timedelta(seconds=1)
            sleep(1)

    def now(self):
        with self.lock:
            return self._track


class SessionStats(plugins.Plugin):
    __author__ = "33197631+dadav@users.noreply.github.com"
    __version__ = "0.1.0"
    __license__ = "GPL3"
    __description__ = "This plugin displays stats of the current session."

    def __init__(self):
        self.lock = threading.Lock()
        self.options = dict()
        self.stats = dict()
        self.clock = GhettoClock()

    def on_loaded(self):
        """
        Gets called when the plugin gets loaded
        """
        # this has to happen in "loaded" because the options are not yet
        # available in the __init__
        os.makedirs(self.options["save_directory"], exist_ok=True)
        self.session_name = "stats_{}.json".format(
            self.clock.now().strftime("%Y_%m_%d_%H_%M")
        )
        self.session = StatusFile(
            os.path.join(self.options["save_directory"], self.session_name),
            data_format="json",
        )
        logging.info("Session-stats plugin loaded.")

    def on_epoch(self, agent, epoch, epoch_data):
        """
        Save the epoch_data to self.stats
        """
        with self.lock:
            self.stats[self.clock.now().strftime("%H:%M:%S")] = epoch_data
            self.session.update(data={"data": self.stats})

    @staticmethod
    def extract_key_values(data, subkeys):
        result = dict()
        result["values"] = list()
        result["labels"] = subkeys
        for plot_key in subkeys:
            v = [[ts, d[plot_key]] for ts, d in data.items()]
            result["values"].append(v)
        return result

    def on_webhook(self, path, request):
        if not path or path == "/":
            return render_template_string(TEMPLATE)

        session_param = request.args.get("session")

        if path == "os":
            extract_keys = [
                "cpu_load",
                "mem_usage",
            ]
        elif path == "temp":
            extract_keys = ["temperature"]
        elif path == "wifi":
            extract_keys = [
                "missed_interactions",
                "num_hops",
                "num_peers",
                "tot_bond",
                "avg_bond",
                "num_deauths",
                "num_associations",
                "num_handshakes",
            ]
        elif path == "duration":
            extract_keys = [
                "duration_secs",
                "slept_for_secs",
            ]
        elif path == "reward":
            extract_keys = [
                "reward",
            ]
        elif path == "epoch":
            extract_keys = [
                "active_for_epochs",
            ]
        elif path == "session":
            return jsonify({"files": os.listdir(self.options["save_directory"])})

        with self.lock:
            data = self.stats
            if session_param and session_param != "Current":
                file_stats = StatusFile(
                    os.path.join(self.options["save_directory"], session_param),
                    data_format="json",
                )
                data = file_stats.data_field_or("data", default=dict())
            return jsonify(SessionStats.extract_key_values(data, extract_keys))
