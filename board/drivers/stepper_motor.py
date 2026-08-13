"""Stepper motor driver for a MicroPython-based ESP32-S2 controller.

This module intentionally avoids Raspberry Pi / desktop Python dependencies.
It uses machine.Pin and time.sleep_us, which are compatible with MicroPython.
"""

try:
    from machine import Pin
except ImportError:  # pragma: no cover - used for desktop syntax checking only
    class Pin:  # type: ignore[override]
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

import time


class StepperMotorDriver:
    """Small stepper driver abstraction for a single motor channel."""

    def __init__(
        self,
        dir_pin,
        step_pin,
        enable_pin,
        steps_per_rev=48,
        microsteps=8,
        step_delay_us=2000,
    ):
        self.dir_pin = Pin(dir_pin, Pin.OUT)
        self.step_pin = Pin(step_pin, Pin.OUT)
        self.enable_pin = Pin(enable_pin, Pin.OUT)

        self.steps_per_rev = steps_per_rev
        self.microsteps = microsteps
        self.step_delay_us = step_delay_us
        self.position_steps = 0

        self.disable()

    def enable(self):
        self.enable_pin.value(0)

    def disable(self):
        self.enable_pin.value(1)

    def set_direction(self, direction):
        if direction not in ("cw", "ccw"):
            raise ValueError("direction must be 'cw' or 'ccw'")
        self.dir_pin.value(1 if direction == "cw" else 0)

    def move_steps(self, steps, direction="cw", step_delay_us=None):
        """Move a given number of microsteps in the requested direction."""
        if steps == 0:
            return 0

        delay_us = self.step_delay_us if step_delay_us is None else step_delay_us
        self.enable()
        self.set_direction(direction)

        for _ in range(abs(int(steps))):
            self.step_pin.value(1)
            time.sleep_us(delay_us)
            self.step_pin.value(0)
            time.sleep_us(delay_us)

            if direction == "cw":
                self.position_steps += 1
            else:
                self.position_steps -= 1

        self.disable()
        return self.position_steps

    def move_to(self, target_steps, speed=1.0):
        """Move from current position to a target step count."""
        delta = target_steps - self.position_steps
        direction = "cw" if delta >= 0 else "ccw"
        steps = abs(delta)
        if steps == 0:
            return self.position_steps

        delay_us = max(500, int(self.step_delay_us / max(speed, 0.1)))
        self.move_steps(steps, direction=direction, step_delay_us=delay_us)
        return self.position_steps

    def home(self):
        """Placeholder for homing logic using limit switches."""
        return self.position_steps


class SharedStepperMotorController:
    """Controller for two motors sharing one step and direction pin.

    Only one motor is enabled at a time. The shared signal pins are reused by
    the active motor, and every motor is returned to disabled state after its
    movement is complete.
    """

    def __init__(self, dir_pin, step_pin, enable_pins, step_delay_us=2000):
        self.dir_pin = Pin(dir_pin, Pin.OUT)
        self.step_pin = Pin(step_pin, Pin.OUT)
        self.enable_pins = [Pin(pin, Pin.OUT) for pin in enable_pins]
        self.step_delay_us = step_delay_us
        self.disable_all()

    def disable_all(self):
        for pin in self.enable_pins:
            pin.value(1)

    def enable_motor(self, motor_index):
        if motor_index < 0 or motor_index >= len(self.enable_pins):
            raise ValueError("motor_index out of range")
        self.disable_all()
        self.enable_pins[motor_index].value(0)

    def run_motor(self, motor_index, steps, direction="cw", step_delay_us=None):
        if steps <= 0:
            return

        if motor_index < 0 or motor_index >= len(self.enable_pins):
            raise ValueError("motor_index out of range")

        delay_us = self.step_delay_us if step_delay_us is None else step_delay_us
        self.enable_motor(motor_index)
        self.dir_pin.value(1 if direction == "cw" else 0)

        for _ in range(int(steps)):
            self.step_pin.value(1)
            time.sleep_us(delay_us)
            self.step_pin.value(0)
            time.sleep_us(delay_us)

        self.disable_all()
        return True
