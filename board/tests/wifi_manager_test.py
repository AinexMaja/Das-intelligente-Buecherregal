"""Local test for the board WiFi manager.

This script validates the JSON storage, saved-network prioritization, and
connect behaviour on the board.
"""

try:
    from board.wifi_manager import WifiManager
except ImportError:  # pragma: no cover
    from wifi_manager import WifiManager


def main():
    wifi = WifiManager("wifi_credentials.json")

    # Example REPL use:
    # wifi.add_network("MyHomeWiFi", "secret-password")
    # wifi.connect_saved()

    print("Saved networks:", wifi.get_networks())
    print("Visible networks:", wifi._network_names_from_scan())


if __name__ == "__main__":
    main()
