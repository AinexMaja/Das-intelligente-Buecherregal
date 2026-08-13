# Intelligent Bookshelf - ESP32-S2 rewrite plan

## Goal

This project originally ran as a Raspberry Pi + Flask app that directly controlled the motor and LED strip. For the next-generation design, the robot hardware should be separated cleanly from the server application.

The new architecture is:

- board firmware on the ESP32-S2 handles the real hardware
- a server handles user UI, database logic, and orchestration
- communication happens through a socket-based API, not Flask on the board

## Why the rewrite is needed

The current code uses desktop-oriented Python libraries and direct GPIO access that are designed for a Raspberry Pi. The ESP32-S2 is a microcontroller and does not run normal CPython in the same way.

Important differences:

- Raspberry Pi uses `RPi.GPIO` and standard Python runtime
- ESP32-S2 normally runs MicroPython or a C++/ESP-IDF firmware
- the board does not have a full desktop operating system
- memory, runtime behavior, and peripheral access differ significantly

Because of that, the board code must be rewritten into a microcontroller-safe structure.

## Architecture decisions

### 1. Python version and runtime

Recommended runtime:

- MicroPython for the ESP32-S2, because it is the fastest path for a Python-based motor/LED controller
- Alternative: native C++ with ESP-IDF if lower-level control and performance are required

Decision for this project:

- keep the logic Python-like and structured
- write the board layer in MicroPython-compatible code
- avoid desktop-only modules like `RPi.GPIO`, `flask`, and regular `sqlite3`

### 2. Hardware driver separation

The board code is split into these layers:

- `board/drivers/stepper_motor.py` - low-level stepper motor command layer
- `board/drivers/led_strip.py` - LED strip control layer
- `board/robot_controller.py` - translates high-level commands into hardware calls
- `board/tests/local_hardware_test.py` - local validation script for direct hardware testing

This keeps the real hardware access isolated and prevents the API layer from depending on GPIO details.

### 3. Server separation

The server side is not implemented yet, and it should be a separate project or service. It owns:

- user interface
- database access
- inventory management
- API and socket server
- command generation for the robot

The robot should not render HTML, access SQLite, or use Flask.

### 4. Communication protocol

The board and server communicate over a socket connection. Recommended protocol:

- WebSocket for full-duplex communication
- or raw TCP JSON messages if the server implementation is simpler

WebSocket is preferred because the robot needs to send status updates while also receiving commands.

## Planned API contract

The API is intentionally not yet tied to implementation details. This is the contract to define before building the server.

### Command message format

```json
{
  "type": "command",
  "command": "move_to",
  "args": {
    "target_steps": 900,
    "speed": 1.0
  }
}
```

### Event message format

```json
{
  "type": "event",
  "event": "status",
  "state": "moving",
  "position_steps": 200
}
```

### Supported commands

#### move_to

Moves the rail to a target position.

Request:

```json
{
  "type": "command",
  "command": "move_to",
  "args": {
    "target_steps": 900,
    "speed": 1.0
  }
}
```

Response:

```json
{
  "type": "event",
  "event": "done",
  "position_steps": 900
}
```

#### move_steps

Moves a given number of steps in a direction.

Request:

```json
{
  "type": "command",
  "command": "move_steps",
  "args": {
    "steps": 120,
    "direction": "cw"
  }
}
```

#### set_led

Sets a LED segment range.

Request:

```json
{
  "type": "command",
  "command": "set_led",
  "args": {
    "start": 10,
    "width": 12,
    "color": [255, 0, 0]
  }
}
```

#### clear_leds

Clears the LED strip.

Request:

```json
{
  "type": "command",
  "command": "clear_leds"
}
```

#### home

Runs the homing routine for calibration.

Request:

```json
{
  "type": "command",
  "command": "home"
}
```

### Status events the robot should send

- `status`: current robot state
- `position`: current motor position
- `limit_hit`: a limit switch was reached
- `error`: failure in a command
- `done`: command completed successfully

### Socket transport modes

The robot API supports two valid communication patterns.

1. Board-initiated requests
   - The board opens a TCP connection to the server.
   - The board sends a command payload such as `move_steps` or `set_led`.
   - The server replies with a JSON event.
   - This is the mode used by the board-side probe in `board/tests/socket_api_probe.py`.

2. Server-first commands
   - The server opens or maintains a connection to the board.
   - The server sends JSON commands such as `home`, `move_steps`, `set_led`, or `status`.
   - The board returns a matching event response.
   - This mode is implemented in the mock server flow for local validation and is the pattern to support for server-driven control.

Both modes share the same JSON command and response format. The board must always respond with a JSON event object, and the server should treat command messages in the same way regardless of who initiated the connection.

### Local mock API server

The file `test_loopback_server.py` is a local mock server used to validate the full contract without needing a production backend. It implements a realistic in-memory robot state and supports:

- `move_to`
- `move_steps`
- `set_led`
- `clear_leds`
- `home`
- `status`

It is intended for local end-to-end verification against the ESP32 board over Wi‑Fi.

## Local hardware test

The file `board/tests/local_hardware_test.py` exists to validate the motor and LEDs directly on the board without going through the server API.

This test is built to run locally on the device and is intended for:

- verifying wiring
- verifying step/dir control
- verifying LED indexing and color output
- checking the board can run the driver layer without the server

The test does the following:

1. clears the LED strip
2. lights several LED ranges in different colors
3. moves the stepper a short distance
4. reports success back to the serial console

This is a local hardware smoke test, not a production endpoint.

## Upload and run tutorial

### 1. Install the board toolchain

For MicroPython on ESP32-S2:

- install `esptool` for flashing
- install `ampy` or use the board's preferred MicroPython upload method
- ensure your board is detected by the OS

Example commands:

```bash
pip install esptool
pip install adafruit-ampy
```

### 2. Flash MicroPython firmware

Download the latest MicroPython firmware for ESP32-S2 and flash it.

Example:

```bash
esptool.py --chip esp32s2 --port /dev/ttyUSB0 erase_flash
esptool.py --chip esp32s2 --port /dev/ttyUSB0 write_flash -z 0x1000 firmware.bin
```

### 3. Upload the project files

Copy the board package to the device.

Example with ampy:

```bash
ampy --port /dev/ttyUSB0 mkdir /board
ampy --port /dev/ttyUSB0 put board /board
```

If your file transfer tool requires a different layout, copy the files into the board's main filesystem and keep the same package structure.

### 4. Run the test script

From the MicroPython REPL:

```python
import board.tests.local_hardware_test as test

test.main()
```

If the board is configured with a simpler layout, you can also run:

```python
import local_hardware_test
local_hardware_test.main()
```

### 5. Use serial output to inspect results

Watch the board serial monitor for output such as:

- `Testing LEDs...`
- `LED test ok`
- `Testing motor...`
- `Motor test ok`
- `Local hardware test complete`

## Important notes

- Do not use desktop Python assumptions on the board.
- Do not import Flask or SQLite into the board firmware.
- Keep all device access inside the driver layer.
- Treat the motor and LEDs as resources managed by the robot controller.
- Use the socket API as the only communication boundary between the board and server.

## Recommended next steps

1. define exact pin mapping for the actual S2 board hardware
2. decide whether the board should act as a socket client or server
3. implement the server-side skeleton with the same JSON command schema
4. connect the board to the real limit switches and LEDs
5. validate the test script on the physical device

This gives a clean, testable path from the current Raspberry Pi prototype to an ESP32-S2 based robot controller.
