"""WiFi manager for MicroPython ESP32 boards.

Features:
- stores known SSID/password pairs in a JSON file on the board
- scans available networks and prioritizes saved SSIDs
- allows adding/updating credentials from the REPL
- auto-connects on boot if a saved network is visible
"""

try:
    import json
    import network
    import os
    import time
except ImportError:  # pragma: no cover - desktop compatibility only
    json = None
    network = None
    os = None
    time = None


class WifiManager:
    """Manage a board's known WiFi credentials and connection strategy."""

    def __init__(self, config_path="wifi_credentials.json"):
        self.config_path = config_path
        self.credentials = self._load_credentials()

    def _load_credentials(self):
        if os is None or json is None:
            return {}

        try:
            with open(self.config_path, "r") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except OSError:
            return {}
        except ValueError:
            return {}
        return {}

    def _save_credentials(self):
        if os is None or json is None:
            return
        with open(self.config_path, "w") as f:
            json.dump(self.credentials, f)

    def add_network(self, ssid, password):
        """Add or update a saved network configuration."""
        if not ssid:
            raise ValueError("SSID must not be empty")
        self.credentials[str(ssid)] = str(password)
        self._save_credentials()
        return self.credentials

    def update_network(self, ssid, password):
        return self.add_network(ssid, password)

    def remove_network(self, ssid):
        if str(ssid) in self.credentials:
            del self.credentials[str(ssid)]
            self._save_credentials()
        return self.credentials

    def get_networks(self):
        return dict(self.credentials)

    def scan(self):
        """Return a list of visible AP names."""
        if network is None:
            return []

        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        try:
            return wlan.scan()
        except Exception:
            return []

    def _network_names_from_scan(self):
        visible = []
        for item in self.scan():
            if isinstance(item, tuple):
                try:
                    visible.append(item[0].decode("utf-8"))
                except Exception:
                    visible.append(str(item[0]))
            else:
                visible.append(str(item))
        return visible

    def connect(self, ssid=None, password=None, timeout=20):
        """Connect to a saved SSID or to a provided SSID/password pair."""
        if network is None:
            raise RuntimeError("network module is unavailable on this platform")

        sta = network.WLAN(network.STA_IF)
        sta.active(True)

        if ssid is None and password is None:
            visible = self._network_names_from_scan()
            for saved_ssid in self.credentials:
                if saved_ssid in visible:
                    sta.connect(saved_ssid, self.credentials[saved_ssid])
                    for _ in range(timeout):
                        if sta.isconnected():
                            return True
                        time.sleep_ms(500)
            return False

        if ssid is None:
            raise ValueError("ssid is required when password is provided")

        if password is None:
            password = self.credentials.get(str(ssid))
            if password is None:
                raise ValueError("No saved password for this SSID")

        sta.connect(str(ssid), str(password))
        for _ in range(timeout):
            if sta.isconnected():
                self.add_network(str(ssid), str(password))
                return True
            time.sleep_ms(500)
        return False

    def connect_saved(self, timeout=20):
        return self.connect(timeout=timeout)

    def connect_known(self, ssid, password, timeout=20):
        return self.connect(ssid, password, timeout=timeout)


if __name__ == "__main__":
    wifi = WifiManager()
    print("Known networks:", wifi.get_networks())
    print("Visible networks:", wifi._network_names_from_scan())
