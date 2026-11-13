# runcam_probe_v2.py, probe v2
# Stand-alone probe for the RunCam Split 3 Micro over the RunCam Device Protocol.
# Copy this one file to the RP2040-Zero and run it from Thonny or mpremote.
# It does not need the firmware/ modules.
#
# Changelog probe v2: read-only by default; logs every TX and RX byte in hex;
#   reads device info, reserved settings 0 to 6 (0x11) and the root settings
#   list (0x10); legacy RCSplit (0x55) detect if 0xCC gets no reply;
#   OSD write test only when OSD_WRITE_TEST = True; refuses to run until
#   SPLIT_TX_MEASURED_OK = True.
# Untested on hardware. probe v1 never ran on hardware.
# Last known good on hardware: legacy jc02_debug.py debug v2.
#
# What this probe NEVER sends: camera control 0x01 (no record start or stop,
# no button presses), 5-key 0x02 to 0x04, setting write 0x13.
#
# Wiring (UART1):
#   GP4 (RP2040 TX) -> Split RX pad
#   GP5 (RP2040 RX) <- Split TX pad   Only after the idle voltage is measured.
#   GND             -- Split GND
#   Split 5V from its own BEC, 1A or more. Not from the RP2040.

import time
from machine import Pin, UART

# --- Flags. Edit these, then run. -------------------------------------------
SPLIT_TX_MEASURED_OK = False  # Set True only after Split TX idle measured at 3.3V or less.
OSD_WRITE_TEST = False        # True: write test text with 0x22 if feature bit 5 is set.
TRY_LEGACY_RCSPLIT = True     # Send the Betaflight legacy detect packet if 0xCC is silent.
BOOT_WAIT_S = 8               # Split boot time. ArduPilot default is 7 s.
UART_ID = 1
PIN_TX = 4
PIN_RX = 5
BAUD = 115200
# ---------------------------------------------------------------------------

FEATURES = ("POWER_BUTTON", "WIFI_BUTTON", "CHANGE_MODE", "5KEY_OSD", "SETTINGS_ACCESS",
            "DISPLAYPORT", "START_RECORDING", "STOP_RECORDING", "CMS_MENU(bf)", "FC_ATTITUDE(bf)")
SETTING_NAMES = ("CHARSET", "COLUMNS", "TV_MODE", "SD_CAPACITY", "REMAIN_REC_TIME",
                 "RESOLUTION", "CAMERA_TIME")
TYPES = {0: "UINT8", 1: "INT8", 2: "UINT16", 3: "INT16", 8: "FLOAT", 9: "TEXT_SELECTION",
         10: "STRING", 11: "FOLDER", 12: "INFO"}


def crc8_dvb_s2(data, crc=0):
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = ((crc << 1) ^ 0xD5) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc


def crc8_high_first_31(data):
    crc = 0
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = ((crc << 1) ^ 0x31) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc


def hexs(b):
    return " ".join("%02X" % x for x in b) if b else "(none)"


def txt(b):
    return "".join(chr(c) if 32 <= c < 127 else "." for c in b)


def packet(cmd, params=b""):
    body = bytes([0xCC, cmd]) + bytes(params)
    return body + bytes([crc8_dvb_s2(body)])


def say(*a):
    print("PROBE", *a)


class Link:
    def __init__(self):
        self.u = UART(UART_ID, baudrate=BAUD, tx=Pin(PIN_TX), rx=Pin(PIN_RX), rxbuf=1024)

    def flush(self):
        n = self.u.any()
        if n:
            junk = self.u.read(n)
            say("flushed", len(junk), "bytes:", hexs(junk))

    def xfer(self, pkt, wait_ms=500, quiet_ms=60):
        """Send pkt, collect bytes until wait_ms passes, or quiet_ms after the last byte."""
        self.flush()
        say("TX", hexs(pkt))
        self.u.write(pkt)
        got = bytearray()
        t0 = time.ticks_ms()
        t_last = None
        while True:
            n = self.u.any()
            if n:
                got.extend(self.u.read(n))
                t_last = time.ticks_ms()
            now = time.ticks_ms()
            if t_last is not None and time.ticks_diff(now, t_last) >= quiet_ms:
                break
            if time.ticks_diff(now, t0) >= wait_ms:
                break
            time.sleep_ms(1)
        say("RX", hexs(got), "|", txt(got))
        return bytes(got)


def check_crc_all(raw):
    return len(raw) >= 2 and crc8_dvb_s2(raw[:-1]) == raw[-1]


def device_info(link, tries=5):
    for i in range(tries):
        raw = link.xfer(packet(0x00), wait_ms=1000)
        j = raw.find(b"\xCC")
        if j >= 0 and len(raw) >= j + 5:
            r = raw[j:j + 5]
            ok = check_crc_all(r)
            say("device info frame", hexs(r), "crc", "OK" if ok else "BAD")
            if ok:
                ver = r[1]
                feat = r[2] | (r[3] << 8)
                say("protocol version", ver)
                say("features 0x%04X" % feat)
                for bit, name in enumerate(FEATURES):
                    say("  bit %d %-16s %s" % (bit, name, "YES" if feat & (1 << bit) else "no"))
                return ver, feat
        say("device info try", i + 1, "no valid reply")
    return None, None


def legacy_detect(link):
    # Betaflight runcamSplitSendCommand(0xFF): 55 01 FF crc AA, crc8 poly 0x31
    # high-bit-first over 55 01 FF AA. Expected 5 byte reply 55 01 FF crc AA.
    buf = bytes([0x55, 0x01, 0xFF, 0xAA])
    pkt = bytes([0x55, 0x01, 0xFF, crc8_high_first_31(buf), 0xAA])
    raw = link.xfer(pkt, wait_ms=1000)
    j = raw.find(b"\x55")
    if j >= 0 and len(raw) >= j + 5:
        r = raw[j:j + 5]
        calc = crc8_high_first_31(bytes([r[0], r[1], r[2], r[4]]))
        say("legacy reply", hexs(r), "crc", "OK" if calc == r[3] else "BAD")
        return calc == r[3]
    return False


def parse_variable(raw):
    """Try [CC][remaining][len][data][crc], then [remaining][len][data][crc]."""
    if len(raw) >= 4 and raw[0] == 0xCC:
        ln = raw[2]
        if len(raw) > 3 + ln and crc8_dvb_s2(raw[:3 + ln]) == raw[3 + ln]:
            return "with CC header", raw[1], raw[3:3 + ln]
    if len(raw) >= 3:
        ln = raw[1]
        if len(raw) > 2 + ln and crc8_dvb_s2(raw[:2 + ln]) == raw[2 + ln]:
            return "no header", raw[0], raw[2:2 + ln]
    return None


def read_details(link):
    for sid, name in enumerate(SETTING_NAMES):
        say("--- 0x11 read setting detail", sid, name)
        raw = link.xfer(packet(0x11, bytes([sid, 0])), wait_ms=800)
        res = parse_variable(raw)
        if res is None:
            say("  no parse. Raw bytes above are the record.")
            continue
        layout, remaining, data = res
        say("  layout", layout, "remaining chunks", remaining, "data", hexs(data))
        if data:
            t = data[0]
            say("  type", TYPES.get(t, "?%d" % t), "body text:", txt(data[1:]))


def read_settings_tree(link, parent=0):
    chunk = 0
    while chunk < 8:
        say("--- 0x10 get settings parent", parent, "chunk", chunk)
        raw = link.xfer(packet(0x10, bytes([parent, chunk])), wait_ms=800)
        res = parse_variable(raw)
        if res is None:
            say("  no parse")
            return
        layout, remaining, data = res
        say("  layout", layout, "remaining", remaining)
        i = 0
        data = bytes(data)
        while i < len(data):
            sid = data[i]
            a = data.find(b"\x00", i + 1)
            if a < 0:
                break
            b = data.find(b"\x00", a + 1)
            if b < 0:
                break
            say("  id %d name '%s' value '%s'" % (sid, txt(data[i + 1:a]), txt(data[a + 1:b])))
            i = b + 1
        if remaining == 0:
            return
        chunk += 1


def listen(link, ms):
    say("--- passive listen", ms, "ms")
    t0 = time.ticks_ms()
    got = bytearray()
    while time.ticks_diff(time.ticks_ms(), t0) < ms:
        n = link.u.any()
        if n:
            got.extend(link.u.read(n))
        time.sleep_ms(5)
    say("unsolicited", hexs(got))


def osd_test(link, feat):
    if not feat & (1 << 5):
        say("OSD test skipped: feature bit 5 (DISPLAYPORT) not reported")
        return
    text = b"PROBE V2 OSD"
    say("--- OSD write test. Look at the analog feed AND the SD recording.")
    link.xfer(packet(0x22, bytes([len(text), 2, 2]) + text), wait_ms=300)
    link.xfer(packet(0x21, bytes([15, 7, ord("+")])), wait_ms=300)
    say("text should show at column 2 row 2, '+' near center. Waiting 10 s.")
    time.sleep(10)
    link.xfer(packet(0x20, bytes([0, 0, 30, 16, 0x20])), wait_ms=300)
    say("fill region sent to clear it")


def main():
    say("runcam probe v2")
    if not SPLIT_TX_MEASURED_OK:
        say("STOP. Measure Split TX pad idle voltage to GND first.")
        say("If 3.3V or less, set SPLIT_TX_MEASURED_OK = True and run again.")
        say("If near 5V, add a divider before GP5. Do not connect it to GP5.")
        return
    say("UART%d TX GP%d RX GP%d %d 8N1" % (UART_ID, PIN_TX, PIN_RX, BAUD))
    say("waiting", BOOT_WAIT_S, "s for Split boot")
    time.sleep(BOOT_WAIT_S)
    link = Link()
    listen(link, 1000)
    ver, feat = device_info(link)
    if feat is None:
        say("no 0xCC reply")
        if TRY_LEGACY_RCSPLIT:
            say("legacy RCSplit detect:", "REPLIED" if legacy_detect(link) else "no reply")
        say("check TX/RX crossover, GND, 5V to Split, baud")
        return
    if feat & (1 << 4):
        read_details(link)
        read_settings_tree(link, 0)
    else:
        say("settings access (bit 4) not reported, skipping 0x10 and 0x11")
    listen(link, 1000)
    if OSD_WRITE_TEST:
        osd_test(link, feat)
    else:
        say("OSD write test off (OSD_WRITE_TEST = False)")
    say("done. Paste everything from 'runcam probe v2' to here.")


main()
