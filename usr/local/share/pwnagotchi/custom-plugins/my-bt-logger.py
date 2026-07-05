import logging
from pwnagotchi.plugins import Plugin


class MyBTLogger(Plugin):
    """Custom plugin that logs Bluetooth tether connections."""

    def on_bt_tether_connected(self, agent, event_data):
        """Handle bluetooth tether connection event."""
        ip = event_data.get("ip", "unknown")
        device = event_data.get("device", "unknown")
        logging.info(f"[my-bt-logger] BT Connected: {device} ({ip})")

    def on_bt_tether_disconnected(self, agent, event_data):
        """Handle bluetooth tether disconnection event."""
        device = event_data.get("device", "unknown")
        reason = event_data.get("reason", "unknown")
        logging.info(f"[my-bt-logger] BT Disconnected: {device} (reason: {reason})")
