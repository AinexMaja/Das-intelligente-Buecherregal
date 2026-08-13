"""Local hardware test for the board firmware.

This is intentionally not the production API. It is a simple local validation
script that can be uploaded to the ESP32-S2 and run on the device to check
whether the motor and LED drivers react correctly.

Usage:
    - Upload this file to the ESP32-S2.
    - Connect the board serial console.
    - Run: python local_hardware_test.py (MicroPython REPL)
"""

from machine import Pin
import time

# Adjust these pin assignments to match the real hardware.
DIR_PIN = 11
STEP_PIN = 12
ENABLE_PIN_1 = 9
ENABLE_PIN_2 = 7
LED_PIN = 16
LED_COUNT = 200

try:
    from board.drivers.stepper_motor import SharedStepperMotorController
    from board.drivers.led_strip import LedStripDriver
except ImportError:
    # Fallback for a more direct script layout in a single-file firmware project.
    from stepper_motor import SharedStepperMotorController
    from led_strip import LedStripDriver


motor_controller = None
led = None


def setup():
    global motor_controller, led
    motor_controller = SharedStepperMotorController(
        DIR_PIN,
        STEP_PIN,
        [ENABLE_PIN_1, ENABLE_PIN_2],
        step_delay_us=2000,
    )
    led = LedStripDriver(LED_PIN, LED_COUNT, brightness=0.2)


def test_leds():
    print("Testing LEDs...")
    led.clear()
    time.sleep_ms(200)
    led.flash_segment(0, 10, (255, 0, 0))
    time.sleep_ms(500)
    led.flash_segment(10, 10, (0, 255, 0))
    time.sleep_ms(500)
    led.flash_segment(20, 10, (0, 0, 255))
    time.sleep_ms(500)
    led.clear()
    print("LED test ok")


def test_motors():
    print("Testing motor 1...")
    motor_controller.run_motor(0, steps=200, direction="cw")
    time.sleep_ms(200)
    print("Testing motor 2...")
    motor_controller.run_motor(1, steps=200, direction="ccw")
    time.sleep_ms(200)
    print("Motor test ok")


def main():
    setup()
    print("Starting local hardware validation")
    test_leds()
    test_motors()
    print("Local hardware test complete")


if __name__ == "__main__":
    main()
