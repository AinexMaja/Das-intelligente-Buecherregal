"""Mock robot API server for validating the ESP32-S2 protocol contract.

This script implements the same JSON-over-TCP API that the board driver layer is
expected to use. It intentionally behaves like a real backend service while
keeping the implementation lightweight enough to run locally on a laptop.

Example payloads:
    {"type": "command", "command": "move_steps", "args": {"steps": 50, "direction": "cw"}}
    {"type": "command", "command": "set_led", "args": {"start": 0, "width": 10, "color": [255,0,0]}}
    {"type": "command", "command": "home", "args": {}}
"""

import json
import socket
import threading
import time

HOST = "192.168.178.69"
PORT = 9000
BOARD_HOST = "192.168.178.70"
BOARD_PORT = 9001


class MockRobot:
    """Simple in-memory robot state for API contract validation."""

    def __init__(self):
        self.state = "idle"
        self.position_steps = 0
        self.led_segments = []

    def status_event(self):
        return {
            "type": "event",
            "event": "status",
            "command": "status",
            "status": "ok",
            "state": self.state,
            "position_steps": self.position_steps,
            "led_segments": list(self.led_segments),
        }

    def build_error(self, message):
        return {
            "type": "event",
            "event": "error",
            "status": "error",
            "payload": {"error": message},
        }

    def handle_command(self, message):
        if not isinstance(message, dict):
            return self.build_error("message must be a JSON object")

        command = message.get("command")
        args = message.get("args", {})

        if command in ("status", "get_status"):
            return self.status_event()

        if command == "move_to":
            target = int(args.get("target_steps", self.position_steps))
            speed = float(args.get("speed", 1.0))
            self.state = "moving"
            self.position_steps = target
            return {
                "type": "event",
                "event": "done",
                "command": command,
                "status": "ok",
                "payload": {
                    "target_steps": target,
                    "speed": speed,
                    "position_steps": self.position_steps,
                },
            }

        if command == "move_steps":
            steps = int(args.get("steps", 0))
            direction = str(args.get("direction", "cw")).lower()
            if direction not in {"cw", "ccw"}:
                return self.build_error("direction must be 'cw' or 'ccw'")

            self.state = "moving"
            if direction == "cw":
                self.position_steps += steps
            else:
                self.position_steps -= steps

            return {
                "type": "event",
                "event": "done",
                "command": command,
                "status": "ok",
                "payload": {
                    "steps": steps,
                    "direction": direction,
                    "position_steps": self.position_steps,
                },
            }

        if command == "set_led":
            start = int(args.get("start", 0))
            width = int(args.get("width", 1))
            color = args.get("color", [255, 0, 0])
            if not isinstance(color, list) or len(color) != 3:
                return self.build_error("color must be a list of [r, g, b]")

            self.state = "idle"
            self.led_segments.append({"start": start, "width": width, "color": [int(v) for v in color]})
            return {
                "type": "event",
                "event": "done",
                "command": command,
                "status": "ok",
                "payload": {
                    "start": start,
                    "width": width,
                    "color": [int(v) for v in color],
                    "led_segments": list(self.led_segments),
                },
            }

        if command == "clear_leds":
            self.led_segments = []
            return {
                "type": "event",
                "event": "done",
                "command": command,
                "status": "ok",
                "payload": {"led_segments": []},
            }

        if command == "home":
            self.state = "calibrating"
            self.position_steps = 0
            self.state = "idle"
            return {
                "type": "event",
                "event": "done",
                "command": command,
                "status": "ok",
                "payload": {"position_steps": self.position_steps},
            }

        return self.build_error(f"unknown command: {command}")


robot = MockRobot()


def build_response(command, status="ok", payload=None, event="done"):
    response = {
        "type": "event",
        "event": event,
        "command": command,
        "status": status,
    }
    if payload is not None:
        response["payload"] = payload
    return response


def handle_client(conn, addr):
    print(f"Client connected: {addr}")
    try:
        while True:
            data = conn.recv(4096)
            if not data:
                break

            message = data.decode("utf-8").strip()
            print(f"Received from {addr}: {message}")

            try:
                payload = json.loads(message)
            except ValueError:
                response = build_response("unknown", status="error", payload={"error": "invalid json"}, event="error")
                conn.sendall((json.dumps(response) + "\n").encode("utf-8"))
                continue

            response = robot.handle_command(payload)
            conn.sendall((json.dumps(response) + "\n").encode("utf-8"))
    finally:
        conn.close()
        print(f"Client disconnected: {addr}")


def run_api_self_test():
    """Exercise the mock API as a quick end-to-end smoke test."""
    tests = [
        ({"type": "command", "command": "move_steps", "args": {"steps": 50, "direction": "cw"}}, "ok"),
        ({"type": "command", "command": "set_led", "args": {"start": 0, "width": 10, "color": [255, 0, 0]}}, "ok"),
        ({"type": "command", "command": "home", "args": {}}, "ok"),
        ({"type": "command", "command": "status", "args": {}}, "ok"),
    ]

    for payload, expected_status in tests:
        response = robot.handle_command(payload)
        if response.get("status") != expected_status:
            raise AssertionError(f"API self-test failed for {payload}: {response}")
        print(f"SELF_TEST_OK {payload['command']} -> {response}")

    return True


def send_command_to_board(command, args=None, host=BOARD_HOST, port=BOARD_PORT):
    payload = {
        "type": "command",
        "command": command,
        "args": args or {},
    }
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5)
    s.connect((host, port))
    s.sendall((json.dumps(payload) + "\n").encode("utf-8"))
    response = s.recv(4096)
    s.close()
    decoded = response.decode("utf-8")
    print(f"Board response for {command}: {decoded}")
    return json.loads(decoded)


def run_server_first_api_test(board_host=BOARD_HOST, board_port=BOARD_PORT):
    """Simulate the server pushing commands to a listening board."""
    board_ready = threading.Event()

    def board_listener():
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("127.0.0.1", board_port))
        server.listen(5)
        board_ready.set()
        conn, addr = server.accept()
        try:
            data = conn.recv(4096)
            print(f"BOARD_RECEIVED {data.decode('utf-8').strip()}")
            response = {
                "type": "event",
                "event": "done",
                "command": "move_steps",
                "status": "ok",
                "payload": {"position_steps": 50},
            }
            conn.sendall((json.dumps(response) + "\n").encode("utf-8"))
        finally:
            conn.close()
            server.close()

    thread = threading.Thread(target=board_listener, daemon=True)
    thread.start()
    board_ready.wait(2)
    time.sleep(0.2)

    response = send_command_to_board("move_steps", {"steps": 50, "direction": "cw"}, host="127.0.0.1", port=board_port)
    if response.get("status") != "ok":
        raise AssertionError(f"server-first API test failed: {response}")
    print("SERVER_FIRST_API_TEST_OK")


def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(5)
    print(f"Mock robot API server listening on {HOST}:{PORT}")

    try:
        while True:
            conn, addr = server.accept()
            thread = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            thread.start()
    except KeyboardInterrupt:
        print("Stopping mock robot API server")
    finally:
        server.close()


if __name__ == "__main__":
    if "--self-test" in __import__("sys").argv:
        run_api_self_test()
    elif "--server-first" in __import__("sys").argv:
        run_server_first_api_test()
    else:
        main()
