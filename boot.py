"""ESP32 boot script for automatic WiFi connection.

This file is executed automatically on power-up by MicroPython.
It loads saved WiFi credentials from wifi_credentials.json and connects to the
first known network that is visible to the board.

If no saved network is available, the board stays offline until a network is
added via the REPL.
"""

import time

try:
    from board.wifi_manager import WifiManager
except ImportError:  # pragma: no cover - fallback for direct upload layout
    try:
        from wifi_manager import WifiManager
    except ImportError:
        WifiManager = None


if WifiManager is not None:
    wifi = WifiManager("wifi_credentials.json")
    print("Boot: attempting saved WiFi networks...")
    connected = wifi.connect_saved(timeout=30)
    if connected:
        print("Boot: connected to WiFi")
    else:
        print("Boot: no saved WiFi network available or no match found")
else:
    print("Boot: wifi_manager unavailable")
