# Host-side stub of MicroPython neopixel for CPython tests.


class NeoPixel:
    def __init__(self, pin, n):
        self.pixels = [(0, 0, 0)] * n
        self.writes = 0

    def __setitem__(self, i, v):
        self.pixels[i] = v

    def __getitem__(self, i):
        return self.pixels[i]

    def write(self):
        self.writes += 1
