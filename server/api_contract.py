"""API contract specification for the server that controls the robot.

This file is intentionally a specification placeholder. It is not the live
server implementation and not a board firmware module.

The actual server project should implement these commands and events over a
WebSocket or raw TCP JSON socket connection.
"""

COMMANDS = {
    "move_to": {
        "description": "Move the rail to a target position.",
        "payload": {
            "target_steps": "int",
            "speed": "float (optional)"
        },
    },
    "move_steps": {
        "description": "Move a given number of steps in a direction.",
        "payload": {
            "steps": "int",
            "direction": "cw|ccw"
        },
    },
    "set_led": {
        "description": "Highlight a LED range.",
        "payload": {
            "start": "int",
            "width": "int",
            "color": "[r, g, b]"
        },
    },
    "clear_leds": {
        "description": "Clear the LED strip.",
        "payload": {},
    },
    "home": {
        "description": "Run the calibration / homing routine.",
        "payload": {},
    },
}

EVENTS = {
    "status": {
        "description": "Robot state update.",
        "fields": {
            "state": "idle|moving|calibrating|error",
            "position_steps": "int"
        },
    },
    "position": {
        "description": "Current motor position report.",
        "fields": {
            "position_steps": "int"
        },
    },
    "limit_hit": {
        "description": "A limit switch was reached.",
        "fields": {
            "side": "left|right|middle"
        },
    },
    "error": {
        "description": "Command failed or runtime error.",
        "fields": {
            "message": "str"
        },
    },
    "done": {
        "description": "Command completed successfully.",
        "fields": {
            "command": "str"
        },
    },
}

EXAMPLE_COMMAND = {
    "type": "command",
    "command": "move_to",
    "args": {"target_steps": 900, "speed": 1.0},
}

EXAMPLE_EVENT = {
    "type": "event",
    "event": "status",
    "state": "moving",
    "position_steps": 200,
}
