import unittest

import helpers  # noqa: F401
import config
import runcam
from crc import crc8_dvb_s2
from machine import UART


def with_crc(body):
    body = bytes(body)
    return body + bytes([crc8_dvb_s2(body)])


def string_detail(text, maxlen=32):
    return bytes([10]) + text.encode() + b"\x00" + bytes([maxlen])


class FakeCamera:
    """Answers RunCam Device Protocol requests like a camera would.
    header: include 0xCC in variable replies (layout is UNVERIFIED on real hardware)."""

    def __init__(self, uart, features=0x77, header=True, alive=True):
        self.uart = uart
        self.features = features
        self.header = header
        self.alive = alive
        self.rx = []
        self.details = {
            1: bytes([0, 30]),                      # UINT8 columns = 30
            2: bytes([9, 0]) + b"NTSC;PAL\x00",     # TEXT_SELECTION index 0
            3: string_detail("29.7G"),
            4: string_detail("02:10:05"),
            6: string_detail("2026-11-13 10:00"),
        }
        uart.on_write = self.on_write

    def var_reply(self, data, remaining=0):
        body = bytes([remaining, len(data)]) + data
        if self.header:
            body = b"\xCC" + body
        return with_crc(body)

    def on_write(self, pkt):
        self.rx.append(pkt)
        if not self.alive:
            return
        assert pkt[0] == 0xCC
        assert crc8_dvb_s2(pkt[:-1]) == pkt[-1], "bad CRC from host"
        cmd = pkt[1]
        if cmd == runcam.CMD_GET_DEVICE_INFO:
            self.uart.inject(with_crc([0xCC, 0x01, self.features & 0xFF, self.features >> 8]))
        elif cmd == runcam.CMD_READ_SETTING_DETAIL:
            sid = pkt[2]
            if sid in self.details:
                self.uart.inject(self.var_reply(self.details[sid]))
        elif cmd == runcam.CMD_GET_SETTINGS:
            data = b"\x01Video\x00\x00\x02TV-OUT\x00NTSC\x00"
            self.uart.inject(self.var_reply(data))
        elif cmd == runcam.CMD_5KEY_CONNECTION:
            self.uart.inject(with_crc([0xCC, (pkt[2] << 4) | 1]))
        elif cmd in (runcam.CMD_5KEY_PRESS, runcam.CMD_5KEY_RELEASE):
            self.uart.inject(with_crc([0xCC]))


def run(cam, t, ms, step=5):
    end = t + ms
    while t < end:
        cam.poll(t)
        t += step
    return t


def make(features=0x77, header=True, alive=True):
    u = UART(1, baudrate=115200)
    fake = FakeCamera(u, features, header, alive)
    cam = runcam.RunCam(u, config)
    return cam, fake


class TestPackets(unittest.TestCase):
    def test_packet_layout(self):
        p = runcam.packet(0x00)
        self.assertEqual(p[:2], b"\xCC\x00")
        self.assertEqual(p[2], crc8_dvb_s2(b"\xCC\x00"))
        p = runcam.packet(0x22, bytes([3, 1, 2]) + b"ABC")
        self.assertEqual(len(p), 2 + 3 + 3 + 1)

    def test_parse_variable_both_layouts(self):
        data = b"\x0Ahello\x00\x20"
        a = with_crc(b"\xCC" + bytes([0, len(data)]) + data)
        b = with_crc(bytes([0, len(data)]) + data)
        self.assertEqual(runcam.parse_variable(a), (0, data, True))
        self.assertEqual(runcam.parse_variable(b), (0, data, False))
        self.assertIsNone(runcam.parse_variable(a[:-1] + b"\x00"))

    def test_decode_detail(self):
        self.assertEqual(runcam.decode_detail(string_detail("29.7G"))["value"], "29.7G")
        d = runcam.decode_detail(bytes([9, 1]) + b"NTSC;PAL\x00")
        self.assertEqual(d["value"], "PAL")
        self.assertEqual(d["options"], ["NTSC", "PAL"])

    def test_settings_list(self):
        items = runcam.decode_settings_list(b"\x01Video\x00\x00\x02TV-OUT\x00NTSC\x00")
        self.assertEqual(items, [(1, "Video", ""), (2, "TV-OUT", "NTSC")])


class TestDevice(unittest.TestCase):
    def test_boot_wait_then_ready(self):
        cam, fake = make()
        t = run(cam, 0, config.RUNCAM_BOOT_DELAY_MS - 10)
        self.assertEqual(fake.rx, [])           # nothing sent during boot wait
        run(cam, t, 200)
        self.assertTrue(cam.ready())
        self.assertEqual(cam.features, 0x77)
        self.assertIn("DISPLAYPORT", cam.feature_list())
        self.assertNotIn("STOP_RECORDING", cam.feature_list())

    def test_absent_camera(self):
        cam, fake = make(alive=False)
        run(cam, 0, config.RUNCAM_BOOT_DELAY_MS + 15000, step=20)
        self.assertEqual(cam.state, runcam.ST_ABSENT)
        self.assertFalse(cam.ready())

    def test_settings_read_both_layouts(self):
        for header in (True, False):
            cam, fake = make(header=header)
            t = run(cam, 0, config.RUNCAM_BOOT_DELAY_MS + 100)
            for sid in (1, 2, 3, 4, 6):
                cam.read_setting_detail(sid)
            run(cam, t, 2000)
            self.assertEqual(cam.columns, 30)
            self.assertEqual(cam.settings[2]["value"], "NTSC")
            self.assertEqual(cam.settings[3]["value"], "29.7G")
            self.assertEqual(cam.settings[4]["value"], "02:10:05")

    def test_settings_gated_on_bit4(self):
        cam, fake = make(features=0x0047)   # no SETTINGS_ACCESS
        run(cam, 0, config.RUNCAM_BOOT_DELAY_MS + 100)
        self.assertFalse(cam.read_setting_detail(3))

    def test_displayport_gated_on_bit5(self):
        cam, fake = make(features=0x0057)   # Split 2S style, no DISPLAYPORT
        t = run(cam, 0, config.RUNCAM_BOOT_DELAY_MS + 100)
        self.assertFalse(cam.disp_string(1, 1, "X"))
        cam2, fake2 = make(features=0x77)
        t = run(cam2, 0, config.RUNCAM_BOOT_DELAY_MS + 100)
        self.assertTrue(cam2.disp_string(1, 1, "A" * 70))
        run(cam2, t, 100)
        sent = [p for p in fake2.rx if p[1] == runcam.CMD_DISP_WRITE_HORT_STRING]
        self.assertEqual([p[2] for p in sent], [60, 10])   # split at 60
        self.assertEqual(sent[1][3], 61)                    # second part x offset

    def test_setting_write_blocked(self):
        cam, fake = make()
        run(cam, 0, config.RUNCAM_BOOT_DELAY_MS + 100)
        self.assertFalse(cam.write_setting(2, b"\x01"))
        self.assertFalse(any(p[1] == runcam.CMD_WRITE_SETTING for p in fake.rx))

    def test_recording_commands(self):
        cam, fake = make()
        self.assertFalse(cam.start_recording())    # not ready yet
        t = run(cam, 0, config.RUNCAM_BOOT_DELAY_MS + 100)
        cam.start_recording()
        t = run(cam, t, 50)
        cam.stop_recording()
        run(cam, t, 50)
        ctrl = [p for p in fake.rx if p[1] == runcam.CMD_CAMERA_CONTROL]
        self.assertEqual([p[2] for p in ctrl], [runcam.ACT_START_REC, runcam.ACT_STOP_REC])
        self.assertFalse(cam.recording)

    def test_5key_replies(self):
        cam, fake = make(features=0x7F)
        t = run(cam, 0, config.RUNCAM_BOOT_DELAY_MS + 100)
        res = []
        cam.key_connection(runcam.CONN_OPEN, cb=lambda ok, raw: res.append((ok, raw)))
        cam.key_press(runcam.KEY_SET, cb=lambda ok, raw: res.append((ok, raw)))
        cam.key_release(cb=lambda ok, raw: res.append((ok, raw)))
        run(cam, t, 200)
        self.assertEqual([r[0] for r in res], [True, True, True])
        self.assertEqual(res[0][1][1], 0x11)

    def test_bad_crc_then_timeout(self):
        u = UART(1, baudrate=115200)
        cam = runcam.RunCam(u, config)
        cam.state = runcam.ST_READY
        cam.features = 0x7F
        res = []
        cam.key_press(runcam.KEY_UP, cb=lambda ok, raw: res.append(ok))
        cam.poll(0)
        u.inject(b"\xCC\x00")   # wrong CRC
        t = run(cam, 1, 2000)
        self.assertEqual(res, [False])
        self.assertEqual(sum(1 for i in range(len(u.written)) if u.written[i:i + 2] == b"\xCC\x02"), 3)


if __name__ == "__main__":
    unittest.main()
