# runcam.py, firmware v7
# RunCam Device Protocol host side, for the RunCam Split 3 Micro.
#
# Primary reference: docs/reference/RunCam_Device_Protocol_youdao.md.
# Gaps filled from Betaflight src/main/io/rcdevice.c and ArduPilot
# libraries/AP_Camera/AP_RunCam.cpp. See docs/PROTOCOL.md section 1.
#
# Request:  CC CMD [PARAMS...] CRC     CRC8 DVB-S2 over every byte before it.
# Replies with a fixed length (Betaflight and ArduPilot tables):
#   0x00 device info   5 bytes: CC ver feat_lo feat_hi crc
#   0x02 5-key press   2 bytes: CC crc
#   0x03 5-key release 2 bytes: CC crc
#   0x04 5-key conn    3 bytes: CC (action<<4 | result) crc
#   0x01 camera control: no reply. Neither Betaflight nor ArduPilot waits.
#   0x20 to 0x24 display: no reply defined.
#   0x10, 0x11 settings: variable length. Header byte presence UNVERIFIED.
#
# Non-blocking. One request in flight at a time. Call poll(now_ms) often.

from crc import crc8_dvb_s2, hexs

try:
    from time import ticks_diff as _diff, ticks_add as _add
except ImportError:
    def _diff(a, b):
        return a - b

    def _add(a, b):
        return a + b

HEADER = 0xCC

CMD_GET_DEVICE_INFO = 0x00
CMD_CAMERA_CONTROL = 0x01
CMD_5KEY_PRESS = 0x02
CMD_5KEY_RELEASE = 0x03
CMD_5KEY_CONNECTION = 0x04
CMD_GET_SETTINGS = 0x10
CMD_READ_SETTING_DETAIL = 0x11
CMD_WRITE_SETTING = 0x13
CMD_DISP_FILL_REGION = 0x20
CMD_DISP_WRITE_CHAR = 0x21
CMD_DISP_WRITE_HORT_STRING = 0x22
CMD_DISP_WRITE_VERT_STRING = 0x23
CMD_DISP_WRITE_CHARS = 0x24

ACT_WIFI_BTN = 0x00
ACT_POWER_BTN = 0x01
ACT_CHANGE_MODE = 0x02
ACT_START_REC = 0x03
ACT_STOP_REC = 0x04

KEY_SET = 0x01
KEY_LEFT = 0x02
KEY_RIGHT = 0x03
KEY_UP = 0x04
KEY_DOWN = 0x05

CONN_OPEN = 0x01
CONN_CLOSE = 0x02

FEATURE_NAMES = (
    (0, "POWER_BUTTON"),
    (1, "WIFI_BUTTON"),
    (2, "CHANGE_MODE"),
    (3, "5KEY_OSD"),
    (4, "SETTINGS_ACCESS"),
    (5, "DISPLAYPORT"),
    (6, "START_RECORDING"),
    (7, "STOP_RECORDING"),
    (8, "CMS_MENU"),          # Betaflight only
    (9, "FC_ATTITUDE"),       # support article and Betaflight only
)
F_POWER, F_WIFI, F_MODE, F_5KEY, F_SETTINGS, F_DPORT, F_START, F_STOP = range(8)

SETTING_CHARSET = 0
SETTING_COLUMNS = 1
SETTING_TV_MODE = 2
SETTING_SD_CAPACITY = 3
SETTING_REMAIN_REC_TIME = 4
SETTING_RESOLUTION = 5
SETTING_CAMERA_TIME = 6

SETTING_TYPES = {0: "UINT8", 1: "INT8", 2: "UINT16", 3: "INT16", 8: "FLOAT",
                 9: "TEXT_SELECTION", 10: "STRING", 11: "FOLDER", 12: "INFO"}

FIXED_REPLY_LEN = {
    CMD_GET_DEVICE_INFO: 5,
    CMD_5KEY_PRESS: 2,
    CMD_5KEY_RELEASE: 2,
    CMD_5KEY_CONNECTION: 3,
}
VARIABLE = -1

MAX_DISP_STRING = 60
MAX_DISP_CHARS = 20


def packet(cmd, params=b""):
    body = bytes([HEADER, cmd]) + bytes(params)
    return body + bytes([crc8_dvb_s2(body)])


def check_fixed(raw):
    """True if raw starts with 0xCC and its last byte is the CRC of the rest."""
    return len(raw) >= 2 and raw[0] == HEADER and crc8_dvb_s2(raw[:-1]) == raw[-1]


def parse_variable(raw):
    """Settings reply. Returns (remaining_chunks, data, header_seen) or None.
    Tries the layout with a 0xCC header first, then the youdao table layout
    without it. CRC covers every byte before the CRC."""
    if len(raw) >= 4 and raw[0] == HEADER:
        ln = raw[2]
        end = 3 + ln
        if len(raw) > end and crc8_dvb_s2(raw[:end]) == raw[end]:
            return raw[1], bytes(raw[3:end]), True
    if len(raw) >= 3:
        ln = raw[1]
        end = 2 + ln
        if len(raw) > end and crc8_dvb_s2(raw[:end]) == raw[end]:
            return raw[0], bytes(raw[2:end]), False
    return None


def _txt(b):
    return "".join(chr(c) if 32 <= c < 127 else "?" for c in b)


def decode_settings_list(data):
    """0x10 payload: repeated [id u8][name\\0][value\\0]."""
    data = bytes(data)
    items = []
    i = 0
    n = len(data)
    while i < n:
        sid = data[i]
        i += 1
        j = data.find(b"\x00", i)
        if j < 0:
            break
        name = _txt(data[i:j])
        i = j + 1
        k = data.find(b"\x00", i)
        if k < 0:
            break
        value = _txt(data[i:k])
        i = k + 1
        items.append((sid, name, value))
    return items


def decode_detail(data):
    """0x11 payload for STRING and TEXT_SELECTION, the types the reserved
    settings use. Other types are returned raw."""
    if not data:
        return None
    stype = data[0]
    tname = SETTING_TYPES.get(stype, "TYPE_%d" % stype)
    rest = bytes(data[1:])
    if stype == 10:  # STRING: value\0 then max size u8
        z = rest.find(b"\x00")
        if z >= 0:
            val = _txt(rest[:z])
            maxlen = rest[z + 1] if len(rest) > z + 1 else None
            return {"type": tname, "value": val, "max_len": maxlen}
    if stype == 9:   # TEXT_SELECTION: index u8 then "a;b;c\0"
        if rest:
            idx = rest[0]
            z = rest.find(b"\x00", 1)
            txt = _txt(rest[1:z if z >= 0 else len(rest)])
            opts = txt.split(";") if txt else []
            val = opts[idx] if idx < len(opts) else None
            return {"type": tname, "index": idx, "options": opts, "value": val}
    if stype == 0 and rest:
        return {"type": tname, "value": rest[0], "raw": hexs(rest)}
    return {"type": tname, "raw": hexs(rest)}


class Request:
    def __init__(self, cmd, params, reply, timeout, retries, cb):
        self.cmd = cmd
        self.params = bytes(params)
        self.reply = reply          # 0 none, >0 fixed length, VARIABLE
        self.timeout = timeout
        self.retries = retries
        self.cb = cb                # cb(ok, raw_or_parsed)
        self.t_sent = None


# Device states
ST_BOOT_WAIT = "boot_wait"
ST_PROBING = "probing"
ST_READY = "ready"
ST_ABSENT = "absent"


class RunCam:
    VAR_SILENCE_MS = 40     # end of a variable reply: no byte for this long
    INFO_FAST_TRIES = 10
    INFO_SLOW_MS = 5000

    def __init__(self, uart, cfg, log=None):
        self.uart = uart
        self.cfg = cfg
        self.log = log or (lambda *a: None)
        self.state = ST_BOOT_WAIT
        self.t0 = None
        self.protocol_version = None
        self.features = 0
        self.queue = []
        self.cur = None
        self.rx = bytearray()
        self.t_last_rx = 0
        self.info_tries = 0
        self.t_next_info = 0
        # Recording state is tracked here. The protocol cannot report it.
        self.recording = False
        self.settings = {}      # setting id -> decoded detail
        self.columns = None

    # -- feature helpers -------------------------------------------------
    def has(self, bit):
        return bool(self.features & (1 << bit))

    def feature_list(self):
        return [name for bit, name in FEATURE_NAMES if self.features & (1 << bit)]

    def ready(self):
        return self.state == ST_READY

    # -- queue -----------------------------------------------------------
    def _queue(self, cmd, params=b"", reply=0, timeout=None, retries=0, cb=None, front=False):
        r = Request(cmd, params, reply, timeout or self.cfg.RUNCAM_REPLY_TIMEOUT_MS, retries, cb)
        if front:
            self.queue.insert(0, r)
        else:
            self.queue.append(r)
        return True

    def busy(self):
        return self.cur is not None or bool(self.queue)

    # -- public commands -------------------------------------------------
    def camera_control(self, action):
        return self._queue(CMD_CAMERA_CONTROL, bytes([action]))

    def start_recording(self):
        if not self.ready():
            return False
        method = getattr(self.cfg, "RUNCAM_RECORD_METHOD", "start_stop")
        if method == "power_toggle":
            self.camera_control(ACT_POWER_BTN)
        else:
            self.camera_control(ACT_START_REC)
        self.recording = True
        return True

    def stop_recording(self):
        if not self.ready():
            return False
        method = getattr(self.cfg, "RUNCAM_RECORD_METHOD", "start_stop")
        if method == "power_toggle":
            self.camera_control(ACT_POWER_BTN)
        else:
            self.camera_control(ACT_STOP_REC)
        self.recording = False
        return True

    def key_connection(self, action, cb=None):
        return self._queue(CMD_5KEY_CONNECTION, bytes([action]), 3, retries=2, cb=cb)

    def key_press(self, key, cb=None):
        return self._queue(CMD_5KEY_PRESS, bytes([key]), 2, retries=2, cb=cb)

    def key_release(self, cb=None):
        return self._queue(CMD_5KEY_RELEASE, b"", 2, retries=2, cb=cb)

    def get_settings(self, parent_id, chunk=0, cb=None):
        if not self.has(F_SETTINGS):
            return False
        return self._queue(CMD_GET_SETTINGS, bytes([parent_id, chunk]), VARIABLE, retries=1, cb=cb)

    def read_setting_detail(self, setting_id, chunk=0, cb=None):
        if not self.has(F_SETTINGS):
            return False

        def done(ok, res, sid=setting_id):
            if ok:
                det = decode_detail(res[1])
                self.settings[sid] = det
                if sid == SETTING_COLUMNS and det and isinstance(det.get("value"), int):
                    self.columns = det["value"]
            if cb:
                cb(ok, res)
        return self._queue(CMD_READ_SETTING_DETAIL, bytes([setting_id, chunk]), VARIABLE, retries=1, cb=done)

    def write_setting(self, setting_id, value_bytes, cb=None):
        if not self.cfg.RUNCAM_ALLOW_SETTING_WRITE:
            self.log("runcam: setting write blocked by config")
            return False
        if not self.has(F_SETTINGS):
            return False
        return self._queue(CMD_WRITE_SETTING, bytes([setting_id]) + bytes(value_bytes), VARIABLE, retries=0, cb=cb)

    # DisplayPort, gated on feature bit 5.
    def disp_ok(self):
        return self.ready() and self.has(F_DPORT)

    def disp_fill(self, x, y, w, h, ch=0x20):
        if not self.disp_ok():
            return False
        return self._queue(CMD_DISP_FILL_REGION, bytes([x, y, w, h, ch]))

    def disp_char(self, x, y, ch):
        if not self.disp_ok():
            return False
        return self._queue(CMD_DISP_WRITE_CHAR, bytes([x, y, ch]))

    def disp_string(self, x, y, text, vertical=False):
        if not self.disp_ok():
            return False
        data = text.encode() if isinstance(text, str) else bytes(text)
        cmd = CMD_DISP_WRITE_VERT_STRING if vertical else CMD_DISP_WRITE_HORT_STRING
        while data:
            part = data[:MAX_DISP_STRING]
            data = data[MAX_DISP_STRING:]
            self._queue(cmd, bytes([len(part), x, y]) + part)
            if vertical:
                y += len(part)
            else:
                x += len(part)
        return True

    def disp_chars(self, triples):
        """triples: list of (x, y, ch). Sent in groups of 20."""
        if not self.disp_ok():
            return False
        for i in range(0, len(triples), MAX_DISP_CHARS):
            grp = triples[i:i + MAX_DISP_CHARS]
            data = bytearray()
            for x, y, ch in grp:
                data.extend(bytes([x, y, ch]))
            self._queue(CMD_DISP_WRITE_CHARS, bytes([len(data)]) + bytes(data))
        return True

    # -- engine ----------------------------------------------------------
    def _info_cb(self, ok, raw):
        if ok:
            self.protocol_version = raw[1]
            self.features = raw[2] | (raw[3] << 8)
            self.state = ST_READY
            self.log("runcam ready ver %d features 0x%04X %s" % (
                self.protocol_version, self.features, ",".join(self.feature_list())))
        else:
            self.info_tries += 1
            if self.info_tries >= self.INFO_FAST_TRIES and self.state != ST_ABSENT:
                self.state = ST_ABSENT
                self.log("runcam: no reply to device info")

    def _send(self, req, now):
        pkt = packet(req.cmd, req.params)
        self.rx = bytearray()
        # Drop stale bytes before a request that expects a reply (Betaflight does the same).
        if req.reply and self.uart.any():
            self.uart.read(self.uart.any())
        self.uart.write(pkt)
        req.t_sent = now

    def poll(self, now):
        if self.t0 is None:
            self.t0 = now
        if self.uart.any():
            self.rx.extend(self.uart.read(self.uart.any()))
            self.t_last_rx = now

        if self.state == ST_BOOT_WAIT:
            if _diff(now, self.t0) >= self.cfg.RUNCAM_BOOT_DELAY_MS:
                self.state = ST_PROBING
                self.t_next_info = now
            else:
                return
        if self.state in (ST_PROBING, ST_ABSENT) and self.cur is None and not self.queue:
            if _diff(now, self.t_next_info) >= 0:
                self._queue(CMD_GET_DEVICE_INFO, b"", 5, timeout=self.cfg.RUNCAM_INFO_RETRY_MS, cb=self._info_cb)
                gap = self.INFO_SLOW_MS if self.state == ST_ABSENT else 0
                self.t_next_info = _add(now, gap)

        if self.cur is None:
            if not self.queue:
                return
            self.cur = self.queue.pop(0)
            self._send(self.cur, now)
            if self.cur.reply == 0:
                cb = self.cur.cb
                self.cur = None
                if cb:
                    cb(True, None)
            return

        req = self.cur
        if req.reply > 0:
            # Fixed length: skip to the header, then wait for the full reply.
            i = self.rx.find(bytes([HEADER]))
            if i > 0:
                self.rx = self.rx[i:]
            elif i < 0:
                self.rx = bytearray()
            if len(self.rx) >= req.reply:
                raw = bytes(self.rx[:req.reply])
                self.rx = self.rx[req.reply:]
                if check_fixed(raw):
                    self.cur = None
                    if req.cb:
                        req.cb(True, raw)
                    return
                self.log("runcam bad crc", hexs(raw))
        elif req.reply == VARIABLE and self.rx:
            if _diff(now, self.t_last_rx) >= self.VAR_SILENCE_MS:
                res = parse_variable(self.rx)
                if res is not None:
                    self.cur = None
                    if req.cb:
                        req.cb(True, res)
                    return

        if _diff(now, req.t_sent) >= req.timeout:
            if req.retries > 0:
                req.retries -= 1
                self._send(req, now)
            else:
                self.cur = None
                raw = bytes(self.rx)
                self.rx = bytearray()
                if req.cb:
                    req.cb(False, raw)
