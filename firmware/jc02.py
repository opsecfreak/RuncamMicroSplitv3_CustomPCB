# jc02.py, firmware v7
# JC02-1 (L22A) laser rangefinder: frame codec, stream parser, driver.
#
# Frame (JC02-1 manual section 3.1):
#   AE A7 LEN ADDR CMD DATA... CHK BC BE
#   LEN counts LEN, ADDR, CMD, DATA and CHK.
#   CHK = (LEN + ADDR + CMD + sum(DATA)) & 0xFF
# Replies use CMD | 0x80. Measurement reply is CMD 0x85 with 19 data bytes.
#
# Driver is non-blocking. Call poll(now_ms) often. It never sleeps.
# Driver behavior re-implements the v6 feature list from HANDOFF.md
# (auto start, baud detect, silence recovery, power cycle recovery).
# v6 source is not in the repo yet, so this is NOT a port of v6. Diff it
# against legacy/main.py when that file is committed.

HDR = b"\xAE\xA7"
FTR = b"\xBC\xBE"
ADDR = 0x00

CMD_SINGLE = 0x05
CMD_RESET = 0x0B
CMD_CONT_START = 0x0E
CMD_CONT_STOP = 0x0F
REPLY_MEASURE = 0x85
REPLY_RESET_OK = 0x8B
REPLY_CONT_START_OK = 0x8E
REPLY_CONT_STOP_OK = 0x8F

MMSG_LEN = 19

UNIT_TO_FEET = {1: 3.28084, 2: 3.0, 3: 1.0}  # 0x01 m, 0x02 yd, 0x03 ft

# Status strings, same set as the v6 line format.
OK = "OK"          # good reading
NR = "NR"          # module answered, no return from target
NT = "NT"          # no traffic: module was found but went silent
NOMOD = "NOMOD"    # module not found at any baud after power cycles
OFF = "OFF"        # laser mode off


def checksum(body):
    return sum(body) & 0xFF


def build(cmd, data=b""):
    length = 4 + len(data)
    body = bytes([length, ADDR, cmd]) + bytes(data)
    return HDR + body + bytes([checksum(body)]) + FTR


def to_signed16(hi, lo):
    v = (hi << 8) | lo
    return v - 0x10000 if v & 0x8000 else v


def decode_measure(data, dist_offset=2, unit_offset=18):
    """Return (feet or None, unit_code). None means no valid distance."""
    if len(data) != MMSG_LEN:
        return None, None
    raw = to_signed16(data[dist_offset], data[dist_offset + 1])
    unit = data[unit_offset]
    factor = UNIT_TO_FEET.get(unit, UNIT_TO_FEET[1])
    if raw <= 0:
        return None, unit
    return raw * 0.1 * factor, unit


def _lower(buf):
    return bytes((c | 0x20) if 65 <= c <= 90 else c for c in buf)


class Parser:
    """Byte stream to events. Events: ("init",) or ("frame", cmd, data)."""

    MAX_BUF = 160

    def __init__(self):
        self.buf = bytearray()
        self.bad_frames = 0

    def feed(self, chunk):
        events = []
        if chunk:
            self.buf.extend(chunk)
        while True:
            low = _lower(self.buf)
            i_init = low.find(b"init ok")
            i_hdr = self.buf.find(HDR)
            if i_init >= 0 and (i_hdr < 0 or i_init < i_hdr):
                events.append(("init",))
                self.buf = self.buf[i_init + 7:]
                continue
            if i_hdr < 0:
                # Keep a short tail: a split header or a split "init ok".
                if len(self.buf) > 8:
                    self.buf = self.buf[-8:]
                break
            if i_hdr > 0:
                self.buf = self.buf[i_hdr:]
            if len(self.buf) < 3:
                break
            length = self.buf[2]
            if length < 4 or length > 40:
                self.bad_frames += 1
                self.buf = self.buf[2:]
                continue
            total = 2 + length + 2
            if len(self.buf) < total:
                break
            frame = bytes(self.buf[:total])
            body = frame[2:2 + length - 1]
            chk = frame[2 + length - 1]
            if frame[-2:] != FTR or checksum(body) != chk:
                self.bad_frames += 1
                self.buf = self.buf[2:]
                continue
            self.buf = self.buf[total:]
            events.append(("frame", body[2], bytes(body[3:])))
        if len(self.buf) > self.MAX_BUF:
            self.buf = self.buf[-self.MAX_BUF:]
        return events


try:
    from time import ticks_diff as _diff
except ImportError:
    def _diff(a, b):
        return a - b


# Driver states
S_POWER_OFF = "power_off"
S_BOOT = "boot"
S_RUN = "run"
S_NOMOD_WAIT = "nomod_wait"
S_IDLE = "idle"


class JC02:
    NOMOD_RETRY_MS = 10000

    def __init__(self, open_uart, power_pin, cfg, log=None):
        """open_uart(baud) returns an object with any(), read(n), write(b).
        power_pin has value(v). cfg is the config module."""
        self.open_uart = open_uart
        self.power = power_pin
        self.cfg = cfg
        self.log = log or (lambda *a: None)
        self.parser = Parser()
        self.uart = None
        self.baud_idx = 0
        self.baud = None
        self.locked = False         # True once the module answered at self.baud
        self.mode = cfg.JC02_DEFAULT_MODE
        self.status = NOMOD
        self.feet = None
        self.unit = None
        self.seq = 0                # increments on every new status event
        self.last_rx_ms = None
        self.last_good_ms = None
        self.restarts = 0
        self.cycles = 0
        self.state = None
        self.t_state = 0
        self.t_single = 0
        self._started = False

    # -- helpers ---------------------------------------------------------
    def _set_power(self, on):
        level = 1 if on == self.cfg.JC02_POWER_ACTIVE_HIGH else 0
        self.power.value(level)

    def _open(self, now):
        self.baud = self.cfg.JC02_BAUDS[self.baud_idx]
        self.uart = self.open_uart(self.baud)
        self.parser = Parser()
        self.log("jc02 uart", self.baud)

    def _enter(self, state, now):
        self.state = state
        self.t_state = now

    def _send(self, cmd):
        if self.uart is not None:
            self.uart.write(build(cmd))

    def _send_start(self, now):
        if self.mode == "continuous":
            self._send(CMD_CONT_START)
        elif self.mode == "single":
            self._send(CMD_SINGLE)
            self.t_single = now

    def _event(self, status, now):
        self.status = status
        self.seq += 1

    # -- public ----------------------------------------------------------
    def start(self, now):
        self._started = True
        self.baud_idx = 0
        self.cycles = 0
        self.restarts = 0
        self._open(now)
        self._set_power(False)
        self._enter(S_POWER_OFF, now)

    def set_mode(self, mode, now):
        if mode == self.mode:
            return
        self.mode = mode
        self.log("jc02 mode", mode)
        if mode == "off":
            self._send(CMD_CONT_STOP)
            self._event(OFF, now)
            self._enter(S_IDLE, now)
            return
        if self.state in (S_RUN, S_IDLE):
            if mode == "single":
                self._send(CMD_CONT_STOP)
            self._send_start(now)
            self.last_rx_ms = now
            self.restarts = 0
            self._enter(S_RUN, now)

    def trigger_single(self, now):
        if self.state == S_RUN:
            self._send(CMD_SINGLE)
            self.t_single = now

    def poll(self, now):
        if not self._started:
            return
        if self.uart is not None and self.uart.any():
            chunk = self.uart.read(self.uart.any())
            for ev in self.parser.feed(chunk):
                self._handle(ev, now)

        st = self.state
        age = _diff(now, self.t_state)
        if st == S_POWER_OFF:
            if age >= self.cfg.JC02_POWER_OFF_MS:
                self._set_power(True)
                self._enter(S_BOOT, now)
        elif st == S_BOOT:
            if age >= self.cfg.JC02_BOOT_WAIT_MS:
                # No "init ok" seen. Module may already be up, try a start.
                self._go_run(now)
        elif st == S_RUN:
            if self.mode == "single" and _diff(now, self.t_single) >= self.cfg.JC02_SINGLE_PERIOD_MS:
                self._send(CMD_SINGLE)
                self.t_single = now
            ref = self.last_rx_ms if self.last_rx_ms is not None else self.t_state
            if _diff(now, ref) >= self.cfg.JC02_SILENCE_MS:
                self._silence(now)
        elif st == S_NOMOD_WAIT:
            if age >= self.NOMOD_RETRY_MS:
                self.baud_idx = 0
                self.cycles = 0
                self.restarts = 0
                self._open(now)
                self._set_power(False)
                self._enter(S_POWER_OFF, now)

    def _go_run(self, now):
        self.restarts = 0
        self.last_rx_ms = None
        self._enter(S_RUN, now)
        if self.mode == "off":
            self._enter(S_IDLE, now)
            self._event(OFF, now)
        else:
            self._send_start(now)

    def _silence(self, now):
        if self.restarts < self.cfg.JC02_RESTARTS_BEFORE_CYCLE:
            self.restarts += 1
            self.log("jc02 silent, resend start", self.restarts)
            self._send_start(now)
            self.last_rx_ms = now
            if self.locked and self.status != NT:
                self._event(NT, now)
            return
        # Power cycle.
        self.cycles += 1
        if self.cycles > self.cfg.JC02_CYCLES_BEFORE_NOMOD:
            self.cycles = 0
            if not self.locked:
                self.baud_idx += 1
            if self.baud_idx >= len(self.cfg.JC02_BAUDS):
                self.log("jc02 not found")
                self.baud_idx = 0
                self.locked = False
                self._event(NOMOD, now)
                self._set_power(False)
                self._enter(S_NOMOD_WAIT, now)
                return
            self._open(now)
        self.log("jc02 power cycle", self.cycles)
        self._set_power(False)
        self._enter(S_POWER_OFF, now)

    def _handle(self, ev, now):
        self.last_rx_ms = now
        if not self.locked:
            self.locked = True
            self.log("jc02 locked at", self.baud)
        self.restarts = 0
        self.cycles = 0
        if ev[0] == "init":
            self.log("jc02 init ok")
            if self.state in (S_BOOT, S_POWER_OFF):
                self._go_run(now)
            return
        cmd, data = ev[1], ev[2]
        if self.state == S_BOOT:
            self._go_run(now)
        if cmd == REPLY_MEASURE:
            feet, unit = decode_measure(data, self.cfg.JC02_DIST_OFFSET, self.cfg.JC02_UNIT_OFFSET)
            self.unit = unit
            if feet is None:
                self._event(NR, now)
            else:
                self.feet = feet
                self.last_good_ms = now
                self._event(OK, now)
        elif cmd == CMD_CONT_START:
            # Manual lists AE A7 04 00 0E 12 as a measurement failure reply.
            # UNVERIFIED. Treated as no return.
            self._event(NR, now)
        elif cmd in (REPLY_CONT_START_OK, REPLY_CONT_STOP_OK, REPLY_RESET_OK):
            self.log("jc02 ack %02X" % cmd)
        else:
            self.log("jc02 unknown cmd %02X len %d" % (cmd, len(data)))


def nmea_line(seq, ms, feet, status):
    """$JC02,<seq>,<ms>,<feet>,<status>*<XOR> as in v6."""
    f = "" if feet is None else "%.1f" % feet
    body = "JC02,%d,%d,%s,%s" % (seq, ms, f, status)
    x = 0
    for ch in body:
        x ^= ord(ch)
    return "$%s*%02X" % (body, x)
