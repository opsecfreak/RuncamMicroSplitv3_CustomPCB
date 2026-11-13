# pio_uart.py, firmware v7
# PIO UART with a machine.UART-like API: any(), read(n), write(b).
# Used for the JC02 at 9600 baud in the V7 layout.
# PIO programs are the MicroPython examples examples/rp2/pio_uart_rx.py and
# pio_uart_tx.py, with one change: the RX program raises a PIO IRQ after
# each byte so a handler drains the 4 word FIFO into a RAM buffer. Without
# that the main loop would have to read the FIFO at least every 4 ms at 9600.
# UNVERIFIED on hardware.

# ruff: noqa: F821

from machine import Pin
from rp2 import PIO, StateMachine, asm_pio


@asm_pio(sideset_init=PIO.OUT_HIGH, out_init=PIO.OUT_HIGH, out_shiftdir=PIO.SHIFT_RIGHT)
def _uart_tx():
    pull()
    set(x, 7).side(0)[7]
    label("bitloop")
    out(pins, 1)[6]
    jmp(x_dec, "bitloop")
    nop().side(1)[6]


@asm_pio(in_shiftdir=PIO.SHIFT_RIGHT)
def _uart_rx():
    label("start")
    wait(0, pin, 0)
    set(x, 7)[10]
    label("bitloop")
    in_(pins, 1)
    jmp(x_dec, "bitloop")[6]
    jmp(pin, "good_stop")
    # Framing error or break: wait for idle, drop the byte.
    wait(1, pin, 0)
    jmp("start")
    label("good_stop")
    push(block)
    irq(rel(0))


class PioUart:
    def __init__(self, tx_pin, rx_pin, baud, sm_rx=0, sm_tx=1, bufsize=256):
        self.buf = bytearray()
        self.bufsize = bufsize
        self.overflows = 0
        rx = Pin(rx_pin, Pin.IN, Pin.PULL_UP)
        self.sm_rx = StateMachine(sm_rx, _uart_rx, freq=8 * baud, in_base=rx, jmp_pin=rx)
        self.sm_rx.irq(self._drain)
        self.sm_tx = StateMachine(sm_tx, _uart_tx, freq=8 * baud,
                                  sideset_base=Pin(tx_pin), out_base=Pin(tx_pin))
        self.sm_rx.active(1)
        self.sm_tx.active(1)

    def _drain(self, sm=None):
        while self.sm_rx.rx_fifo():
            b = (self.sm_rx.get() >> 24) & 0xFF
            if len(self.buf) < self.bufsize:
                self.buf.append(b)
            else:
                self.overflows += 1

    def any(self):
        self._drain()
        return len(self.buf)

    def read(self, n=None):
        self._drain()
        if not self.buf:
            return None
        if n is None or n >= len(self.buf):
            out = bytes(self.buf)
            self.buf = bytearray()
        else:
            out = bytes(self.buf[:n])
            self.buf = self.buf[n:]
        return out

    def write(self, data):
        for b in data:
            self.sm_tx.put(b)
        return len(data)

    def deinit(self):
        self.sm_rx.active(0)
        self.sm_tx.active(0)
