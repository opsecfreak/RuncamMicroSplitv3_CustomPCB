# status_led.py, firmware v7
# Onboard WS2812 on GP16. Colors from HANDOFF.md section 2:
#   blue searching, green good reading, yellow no return, red module not found.
# Extra in v7: dim white when laser mode is off.

COLORS = {
    "SEARCH": (0, 0, 40),
    "OK": (0, 40, 0),
    "NR": (40, 30, 0),
    "NT": (0, 0, 40),
    "NOMOD": (40, 0, 0),
    "OFF": (8, 8, 8),
}


class StatusLed:
    def __init__(self, pin_no):
        self.np = None
        self.last = None
        try:
            from machine import Pin
            import neopixel
            self.np = neopixel.NeoPixel(Pin(pin_no), 1)
        except Exception:
            self.np = None

    def show(self, key):
        rgb = COLORS.get(key, COLORS["SEARCH"])
        if rgb == self.last or self.np is None:
            self.last = rgb
            return
        # RP2040-Zero LED is wired GRB in some batches. Order UNVERIFIED.
        self.np[0] = rgb
        self.np.write()
        self.last = rgb
