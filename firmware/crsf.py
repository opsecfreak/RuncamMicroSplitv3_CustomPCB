# crsf.py, firmware v7
# CRSF receiver input (CR8 ELRS). Listen only.
#
# Frame: SYNC LEN TYPE PAYLOAD... CRC
#   SYNC 0xC8 (receiver to flight controller address)
#   LEN  = bytes after LEN, so TYPE + PAYLOAD + CRC
#   CRC  = CRC8 DVB-S2 over TYPE and PAYLOAD
#   Max frame 64 bytes including SYNC and CRC.
# 0x16 RC channels: 16 channels x 11 bits, little-endian bit packing, 22 bytes.
# 0x14 link statistics: 10 bytes, decoded for uplink LQ and RSSI only.
# Source: TBS CRSF spec (github.com/tbs-fpv/tbs-crsf-spec, crsf.md).

from crc import crc8_dvb_s2

try:
    from time import ticks_diff as _diff
except ImportError:
    def _diff(a, b):
        return a - b

SYNC = 0xC8
SYNC_ALT = (0xC8, 0xEE, 0xEA)   # some devices use the module/handset address
TYPE_LINK_STATS = 0x14
TYPE_RC_CHANNELS = 0x16
MAX_FRAME = 64


def _cdiv(a, b):
    # C style integer division (truncates toward zero), as in the spec macros.
    q = abs(a) // b
    return -q if a < 0 else q


def ticks_to_us(t):
    return _cdiv((t - 992) * 5, 8) + 1500


def us_to_ticks(us):
    return _cdiv((us - 1500) * 8, 5) + 992


def unpack_channels(payload):
    """22 bytes to 16 tick values (172 to 1811 typical)."""
    out = []
    bits = 0
    nbits = 0
    for b in payload:
        bits |= b << nbits
        nbits += 8
        while nbits >= 11 and len(out) < 16:
            out.append(bits & 0x7FF)
            bits >>= 11
            nbits -= 11
    return out


def pack_channels(ticks):
    """Inverse of unpack_channels. Used by tests."""
    bits = 0
    nbits = 0
    out = bytearray()
    for t in ticks:
        bits |= (t & 0x7FF) << nbits
        nbits += 11
        while nbits >= 8:
            out.append(bits & 0xFF)
            bits >>= 8
            nbits -= 8
    if nbits:
        out.append(bits & 0xFF)
    return bytes(out)


def build_frame(ftype, payload, sync=SYNC):
    body = bytes([ftype]) + bytes(payload)
    return bytes([sync, len(body) + 1]) + body + bytes([crc8_dvb_s2(body)])


class Parser:
    def __init__(self):
        self.buf = bytearray()
        self.frames = 0
        self.crc_errors = 0

    def feed(self, chunk):
        """Returns a list of (type, payload)."""
        out = []
        if chunk:
            self.buf.extend(chunk)
        buf = self.buf
        i = 0
        n = len(buf)
        while i < n:
            if buf[i] not in SYNC_ALT:
                i += 1
                continue
            if i + 2 > n:
                break
            ln = buf[i + 1]
            if ln < 2 or ln > MAX_FRAME - 2:
                i += 1
                continue
            end = i + 2 + ln
            if end > n:
                break
            body = buf[i + 2:end - 1]
            if crc8_dvb_s2(body) == buf[end - 1]:
                out.append((body[0], bytes(body[1:])))
                self.frames += 1
                i = end
            else:
                self.crc_errors += 1
                i += 1
        self.buf = buf[i:]
        if len(self.buf) > 2 * MAX_FRAME:
            self.buf = self.buf[-MAX_FRAME:]
        return out


class CRSF:
    def __init__(self, uart, failsafe_ms=1000):
        self.uart = uart
        self.parser = Parser()
        self.failsafe_ms = failsafe_ms
        self.ticks = [992] * 16
        self.t_last_rc = None
        self.lq = None
        self.rssi_dbm = None
        self.rc_frames = 0

    def poll(self, now):
        if self.uart is None:
            return
        n = self.uart.any()
        if not n:
            return
        for ftype, payload in self.parser.feed(self.uart.read(n)):
            if ftype == TYPE_RC_CHANNELS and len(payload) == 22:
                self.ticks = unpack_channels(payload)
                self.t_last_rc = now
                self.rc_frames += 1
            elif ftype == TYPE_LINK_STATS and len(payload) >= 10:
                self.rssi_dbm = -payload[0]
                self.lq = payload[2]

    def failsafe(self, now):
        if self.t_last_rc is None:
            return True
        return _diff(now, self.t_last_rc) > self.failsafe_ms

    def us(self, ch):
        """Channel in microseconds, ch is 1 based. None if ch is None."""
        if ch is None:
            return None
        return ticks_to_us(self.ticks[ch - 1])


def three_pos(us, low, high):
    if us is None:
        return None
    if us < low:
        return 0
    if us > high:
        return 2
    return 1


class Button:
    """Momentary switch to events: 'short', 'long', 'very_long' on release,
    'very_long' fires once while held so a menu can open without releasing."""

    def __init__(self, long_ms, very_long_ms, high_us):
        self.long_ms = long_ms
        self.very_long_ms = very_long_ms
        self.high_us = high_us
        self.t_down = None
        self.fired_very_long = False

    def update(self, us, now):
        if us is None:
            return None
        down = us > self.high_us
        if down and self.t_down is None:
            self.t_down = now
            self.fired_very_long = False
            return None
        if down:
            if not self.fired_very_long and _diff(now, self.t_down) >= self.very_long_ms:
                self.fired_very_long = True
                return "very_long"
            return None
        if self.t_down is None:
            return None
        held = _diff(now, self.t_down)
        self.t_down = None
        if self.fired_very_long:
            return None
        if held >= self.long_ms:
            return "long"
        return "short"
