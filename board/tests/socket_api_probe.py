"""Board-side socket probe for the robot API contract.

This module supports both communication patterns:

1. board-initiated requests to a laptop server
2. server-first commands sent from the laptop to the board

The board side is intentionally small and platform-friendly for MicroPython.
"""

import socket
import json
import time

SERVER_HOST = "192.168.178.69"  # change to your development machine IP
SERVER_PORT = 9000
BOARD_LISTEN_HOST = "0.0.0.0"
BOARD_LISTEN_PORT = 9001


def handle_command(command, args=None):
    args = args or {}

    if command == "status":
        return {
            "type": "event",
            "event": "status",
            "command": "status",
            "status": "ok",
            "state": "idle",
            "position_steps": 0,
        }

    if command == "move_steps":
        steps = int(args.get("steps", 0))
        direction = str(args.get("direction", "cw")).lower()
        return {
            "type": "event",
            "event": "done",
            "command": "move_steps",
            "status": "ok",
            "payload": {"steps": steps, "direction": direction, "position_steps": steps},
        }

    if command == "move_to":
        target_steps = int(args.get("target_steps", 0))
        speed = float(args.get("speed", 1.0))
        return {
            "type": "event",
            "event": "done",
            "command": "move_to",
            "status": "ok",
            "payload": {"target_steps": target_steps, "speed": speed},
        }

    if command == "set_led":
        start = int(args.get("start", 0))
        width = int(args.get("width", 1))
        color = args.get("color", [255, 0, 0])
        return {
            "type": "event",
            "event": "done",
            "command": "set_led",
            "status": "ok",
            "payload": {"start": start, "width": width, "color": color},
        }

    if command == "clear_leds":
        return {
            "type": "event",
            "event": "done",
            "command": "clear_leds",
            "status": "ok",
            "payload": {"cleared": True},
        }

    if command == "home":
        return {
            "type": "event",
            "event": "done",
            "command": "home",
            "status": "ok",
            "payload": {"position_steps": 0},
        }

    return {
        "type": "event",
        "event": "error",
        "command": command,
        "status": "error",
        "payload": {"error": f"unknown command: {command}"},
    }


def send_command(command, args=None):
    payload = {
        "type": "command",
        "command": command,
        "args": args or {},
    }
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5)
    s.connect((SERVER_HOST, SERVER_PORT))
    s.sendall(json.dumps(payload).encode("utf-8"))
    response = s.recv(4096)
    s.close()
    print("Response:", response.decode("utf-8"))
    return response


def listen_for_server_commands(host=None, port=None):
    host = host or BOARD_LISTEN_HOST
    port = port or BOARD_LISTEN_PORT

    print(f"Board listening for server commands on {host}:{port}")
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    server.listen(5)

    try:
        while True:
            conn, addr = server.accept()
            print("Server connected:", addr)
            try:
                data = conn.recv(4096)
                if not data:
                    continue
                message = data.decode("utf-8").strip()
                print("Received:", message)
                payload = json.loads(message)
                response = handle_command(payload.get("command"), payload.get("args", {}))
                conn.sendall((json.dumps(response) + "\n").encode("utf-8"))
                print("Sent response:", json.dumps(response))
            except Exception as exc:
                error = {
                    "type": "event",
                    "event": "error",
                    "command": "unknown",
                    "status": "error",
                    "payload": {"error": str(exc)},
                }
                conn.sendall((json.dumps(error) + "\n").encode("utf-8"))
            finally:
                conn.close()
    finally:
        server.close()


def main(host=None, port=None):
    global SERVER_HOST, SERVER_PORT
    if host:
        SERVER_HOST = host
    if port:
        SERVER_PORT = port

    print("Sending move_steps command...")
    send_command("move_steps", {"steps": 50, "direction": "cw"})
    time.sleep_ms(200)

    print("Sending set_led command...")
    send_command("set_led", {"start": 0, "width": 10, "color": [255, 0, 0]})
    time.sleep_ms(200)

    print("Sending home command...")
    send_command("home", {})


if __name__ == "__main__":
    main()
