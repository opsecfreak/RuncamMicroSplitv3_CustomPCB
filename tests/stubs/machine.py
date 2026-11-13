# Host-side stub of MicroPython machine for CPython tests.


class Pin:
    IN = 0
    OUT = 1
    PULL_UP = 1
    PULL_DOWN = 2

    def __init__(self, pin_id, mode=None, pull=None, value=None):
        self.id = pin_id
        self.mode = mode
        self._v = 0 if value is None else value
        self.history = [self._v]

    def value(self, v=None):
        if v is None:
            return self._v
        self._v = 1 if v else 0
        self.history.append(self._v)
        return None

    def __call__(self, v=None):
        return self.value(v)


class UART:
    instances = {}

    def __init__(self, uart_id, baudrate=115200, tx=None, rx=None, rxbuf=256, **kw):
        self.id = uart_id
        self.baudrate = baudrate
        self.tx = tx
        self.rx = rx
        self.rxbuf = bytearray()
        self.written = bytearray()
        self.on_write = None    # callback(bytes) for fake devices
        UART.instances[uart_id] = self

    def any(self):
        return len(self.rxbuf)

    def read(self, n=None):
        if not self.rxbuf:
            return None
        if n is None:
            n = len(self.rxbuf)
        out = bytes(self.rxbuf[:n])
        del self.rxbuf[:n]
        return out

    def write(self, data):
        data = bytes(data)
        self.written.extend(data)
        if self.on_write:
            self.on_write(data)
        return len(data)

    # test helper
    def inject(self, data):
        self.rxbuf.extend(data)
