"""Robot controller layer.

This module keeps the hardware drivers separate from the API contract.
A server or socket client will send commands in JSON format, and this layer
will translate them into driver calls.
"""


class RobotController:
    """High-level robot operations for the ESP32-S2 board."""

    def __init__(self, motor_driver, led_driver):
        self.motor_driver = motor_driver
        self.led_driver = led_driver

    def handle_command(self, message):
        """Process one command object from the server or a local test harness."""
        if not isinstance(message, dict):
            return {"ok": False, "error": "Message must be a dict"}

        command = message.get("command")
        args = message.get("args", {})

        if command == "move_to":
            target = args.get("target_steps", 0)
            speed = args.get("speed", 1.0)
            position = self.motor_driver.move_to(target, speed=speed)
            return {"ok": True, "position_steps": position}

        if command == "move_steps":
            steps = int(args.get("steps", 0))
            direction = args.get("direction", "cw")
            position = self.motor_driver.move_steps(steps, direction=direction)
            return {"ok": True, "position_steps": position}

        if command == "set_led":
            start = int(args.get("start", 0))
            width = int(args.get("width", 1))
            color = tuple(args.get("color", (255, 0, 0)))
            self.led_driver.flash_segment(start, width, color)
            return {"ok": True, "segment": [start, width, color]}

        if command == "clear_leds":
            self.led_driver.clear()
            return {"ok": True}

        if command == "home":
            position = self.motor_driver.home()
            return {"ok": True, "position_steps": position}

        return {"ok": False, "error": f"Unknown command: {command}"}
