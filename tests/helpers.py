# Shared test setup: put stubs and firmware on sys.path, fake devices.

import os
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(HERE, "stubs"))
sys.path.insert(0, os.path.join(ROOT, "firmware"))

import jc02  # noqa: E402


class Clock:
    def __init__(self, t=0):
        self.t = t

    def ticks_ms(self):
        return self.t

    def ticks_diff(self, a, b):
        return a - b

    def ticks_add(self, a, b):
        return a + b

    def sleep_ms(self, ms):
        self.t += ms


def fake_time_module(clock):
    m = types.SimpleNamespace()
    m.ticks_ms = clock.ticks_ms
    m.ticks_diff = clock.ticks_diff
    m.ticks_add = clock.ticks_add
    m.sleep_ms = clock.sleep_ms
    return m


class Endpoint:
    """UART-like endpoint handed to the JC02 driver."""

    def __init__(self, module, baud):
        self.module = module
        self.baud = baud
        self.rx = bytearray()
        self.written = bytearray()

    def any(self):
        return len(self.rx)

    def read(self, n=None):
        n = len(self.rx) if n is None else n
        out = bytes(self.rx[:n])
        del self.rx[:n]
        return out or None

    def write(self, data):
        self.written.extend(data)
        self.module.on_cmd(self, bytes(data))
        return len(data)


class FakePowerPin:
    def __init__(self, module):
        self.module = module
        self.level = None
        self.history = []

    def value(self, v=None):
        if v is None:
            return self.level
        self.level = v
        self.history.append(v)
        self.module.set_power(bool(v))


class FakeJC02:
    """Simulated module. Talks only when the host baud matches self.baud."""

    def __init__(self, baud=9600, feet_tenths=1234, unit=3, alive=True, init_text=b"init ok\r\n"):
        self.baud = baud
        self.alive = alive
        self.powered = False
        self.ep = None
        self.continuous = False
        self.feet_tenths = feet_tenths
        self.unit = unit
        self.init_text = init_text
        self.no_return = False
        self.cmds = []

    def open_uart(self, baud):
        self.ep = Endpoint(self, baud)
        return self.ep

    def _match(self):
        return self.alive and self.powered and self.ep is not None and self.ep.baud == self.baud

    def set_power(self, on):
        was = self.powered
        self.powered = on
        if not on:
            self.continuous = False
        if on and not was and self._match():
            self.ep.rx.extend(self.init_text)

    def mmsg(self):
        data = bytearray(19)
        v = 0 if self.no_return else self.feet_tenths
        data[2] = (v >> 8) & 0xFF
        data[3] = v & 0xFF
        data[18] = self.unit
        return bytes(data)

    def on_cmd(self, ep, data):
        p = jc02.Parser()
        for ev in p.feed(data):
            if ev[0] != "frame":
                continue
            cmd = ev[1]
            self.cmds.append(cmd)
            if not self._match():
                continue
            if cmd == jc02.CMD_CONT_START:
                self.continuous = True
                ep.rx.extend(jc02.build(jc02.REPLY_CONT_START_OK))
            elif cmd == jc02.CMD_CONT_STOP:
                self.continuous = False
                ep.rx.extend(jc02.build(jc02.REPLY_CONT_STOP_OK))
            elif cmd == jc02.CMD_SINGLE:
                ep.rx.extend(jc02.build(jc02.REPLY_MEASURE, self.mmsg()))

    def tick(self):
        """Call every 100 ms of simulated time."""
        if self.continuous and self._match():
            self.ep.rx.extend(jc02.build(jc02.REPLY_MEASURE, self.mmsg()))
