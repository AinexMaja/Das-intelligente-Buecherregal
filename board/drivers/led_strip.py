"""LED strip driver for a MicroPython/ESP32-S2 board.

The code intentionally avoids desktop-only libraries. The board runtime should
use either MicroPython's neopixel module or CircuitPython's neopixel library.
"""

try:
    import neopixel
    from machine import Pin
except ImportError:  # pragma: no cover - used for desktop syntax checking only
    neopixel = None

    class Pin:  # type: ignore[override]
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs


class LedStripDriver:
    """Basic driver for a single RGB LED strip."""

    def __init__(self, pin_number, num_pixels, brightness=0.2, order="GRB"):
        if neopixel is None:
            raise RuntimeError(
                "neopixel library is required on the ESP32-S2 board runtime. "
                "This file is not intended to run under standard CPython."
            )

        self.pin = Pin(pin_number, Pin.OUT)
        self.num_pixels = num_pixels

        try:
            self.pixels = neopixel.NeoPixel(
                self.pin,
                num_pixels,
                brightness=brightness,
                pixel_order=order,
            )
        except TypeError:
            self.pixels = neopixel.NeoPixel(self.pin, num_pixels)
            try:
                self.pixels.brightness = brightness
            except AttributeError:
                pass

    def clear(self):
        self.pixels.fill((0, 0, 0))
        self.pixels.write()

    def set_pixel(self, index, color):
        self.pixels[index] = color
        self.pixels.write()

    def set_range(self, start, end, color):
        if start < 0:
            start = 0
        if end > self.num_pixels:
            end = self.num_pixels
        for i in range(start, end):
            self.pixels[i] = color
        self.pixels.write()

    def flash_segment(self, start, width, color):
        end = start + width
        self.set_range(start, end, color)

    def show_book_range(self, position_cm, width_cm, scale, color=(255, 0, 0)):
        """Map a logical book position to LED indexes.

        position_cm and width_cm are board-space numbers. The exact conversion is
        board-specific and should be adjusted according to the physical shelf.
        """
        start_index = int(position_cm * scale)
        end_index = int((position_cm + width_cm) * scale)
        self.set_range(start_index, end_index, color)
