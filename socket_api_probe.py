"""Top-level import wrapper for the board socket API probe.

This makes the script importable as:
    import socket_api_probe
    socket_api_probe.main()

while the actual implementation lives under the board package.
"""

from board.tests.socket_api_probe import main

if __name__ == "__main__":
    main()
