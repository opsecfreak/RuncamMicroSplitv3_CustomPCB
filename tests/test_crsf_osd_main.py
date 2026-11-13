import importlib
import io
import sys
import unittest
from contextlib import redirect_stdout

import helpers
from helpers import Clock, FakeJC02, fake_time_module
import config
import crsf
import osd
import runcam
from machine import UART


def rc_frame(us_list):
    ticks = [crsf.us_to_ticks(u) for u in us_list] + [992] * (16 - len(us_list))
    return crsf.build_frame(crsf.TYPE_RC_CHANNELS, crsf.pack_channels(ticks))


class TestCrsf(unittest.TestCase):
    def test_pack_unpack_roundtrip(self):
        ticks = [172, 992, 1811, 0, 2047] + list(range(100, 1100, 100)) + [5]
        payload = crsf.pack_channels(ticks)
        self.assertEqual(len(payload), 22)
        self.assertEqual(crsf.unpack_channels(payload), ticks)

    def test_tick_conversion(self):
        self.assertEqual(crsf.ticks_to_us(992), 1500)
        self.assertEqual(crsf.ticks_to_us(172), 988)
        self.assertEqual(crsf.ticks_to_us(1811), 2011)

    def test_parser_noise_chunks_crc(self):
        f = rc_frame([1000, 2000])
        bad = bytearray(f)
        bad[5] ^= 1
        stream = b"\x00\x11" + bytes(bad) + f + f[:7]
        p = crsf.Parser()
        out = p.feed(stream)
        out += p.feed(f[7:])
        self.assertEqual(len(out), 2)
        self.assertGreaterEqual(p.crc_errors, 1)
        self.assertEqual(crsf.ticks_to_us(crsf.unpack_channels(out[0][1])[1]), 2000)

    def test_failsafe(self):
        u = UART(0, baudrate=420000)
        rc = crsf.CRSF(u, 1000)
        self.assertTrue(rc.failsafe(0))
        u.inject(rc_frame([1500] * 8))
        rc.poll(100)
        self.assertFalse(rc.failsafe(1000))
        self.assertTrue(rc.failsafe(1200))

    def test_button(self):
        b = crsf.Button(1000, 3000, 1700)
        self.assertIsNone(b.update(2000, 0))
        self.assertEqual(b.update(1000, 200), "short")
        b.update(2000, 1000)
        self.assertEqual(b.update(1000, 2500), "long")
        b.update(2000, 5000)
        self.assertEqual(b.update(2000, 8100), "very_long")
        self.assertIsNone(b.update(1000, 9000))   # release after very long: nothing

    def test_three_pos(self):
        self.assertEqual(crsf.three_pos(1000, 1300, 1700), 0)
        self.assertEqual(crsf.three_pos(1500, 1300, 1700), 1)
        self.assertEqual(crsf.three_pos(2000, 1300, 1700), 2)


class TestOsd(unittest.TestCase):
    def test_main_page(self):
        o = osd.OSD(osd.NullBackend(), 30, 16)
        o.state.feet = 123.4
        o.state.jc02_status = "OK"
        o.state.recording = True
        o.state.rec_remaining = "02:10:05"
        o.update()
        self.assertEqual(o.screen.lines[8][15], "+")
        self.assertIn("123.4 FT", o.screen.row(14))
        self.assertTrue(o.screen.row(0).startswith(" REC"))
        self.assertIn("02:10:05", o.screen.row(0))
        for y in range(16):
            self.assertEqual(len(o.screen.row(y)), 30)

    def test_status_and_pages(self):
        o = osd.OSD(osd.NullBackend(), 30, 16)
        o.state.jc02_status = "NOMOD"
        o.update()
        self.assertIn("---- FT NOMOD", o.dump())
        o.next_page()
        o.state.failsafe = True
        o.update()
        self.assertIn("RC FS", o.dump())
        o.state.menu_open = True
        o.update()
        self.assertIn("> LASER", o.dump())

    def test_runcam_backend_sends_only_changes(self):
        u = UART(1, baudrate=115200)
        cam = runcam.RunCam(u, config)
        cam.state = runcam.ST_READY
        cam.features = 0x77
        o = osd.OSD(osd.RunCamBackend(cam), 30, 16)
        o.state.feet = 50.0
        o.state.jc02_status = "OK"
        o.update()
        n_first = len(cam.queue)
        self.assertGreater(n_first, 1)
        t = 0
        while cam.busy():
            cam.poll(t)
            t += 1
        o.state.feet = 51.0
        o.update()
        self.assertEqual(len(cam.queue), 1)     # only the distance row changed
        cmd = cam.queue[0]
        self.assertEqual(cmd.cmd, runcam.CMD_DISP_WRITE_HORT_STRING)
        self.assertEqual(cmd.params[2], 14)

    def test_runcam_backend_silent_without_bit5(self):
        u = UART(1, baudrate=115200)
        cam = runcam.RunCam(u, config)
        cam.state = runcam.ST_READY
        cam.features = 0x57
        o = osd.OSD(osd.RunCamBackend(cam), 30, 16)
        o.update()
        self.assertEqual(cam.queue, [])


class TestMain(unittest.TestCase):
    def test_bench_layout_loop(self):
        clock = Clock()
        mod = FakeJC02()
        main = importlib.import_module("main")
        main.time = fake_time_module(clock)
        main.make_jc02_uart_factory = lambda: mod.open_uart
        out = io.StringIO()
        with redirect_stdout(out):
            app = main.App()
            app.jc02.power = helpers.FakePowerPin(mod)
            app.jc02.start(0)
            for t in range(0, 4000, 10):
                clock.t = t
                app.step(t)
                if t % 100 == 0:
                    mod.tick()
        text = out.getvalue()
        self.assertEqual(config.LAYOUT, "BENCH_V6")
        self.assertIsNone(app.rc)
        self.assertIn(",123.4,OK*", text)
        self.assertEqual(app.osd.state.jc02_status, "OK")


class TestProbe(unittest.TestCase):
    def test_probe_refuses_without_measurement_and_crc(self):
        sys.path.insert(0, helpers.ROOT + "/tools")
        out = io.StringIO()
        with redirect_stdout(out):
            probe = importlib.import_module("runcam_probe_v2")
        self.assertIn("STOP. Measure Split TX", out.getvalue())
        self.assertEqual(probe.packet(0x00), runcam.packet(0x00))
        self.assertEqual(probe.packet(0x11, b"\x03\x00"), runcam.packet(0x11, b"\x03\x00"))
        self.assertFalse(probe.OSD_WRITE_TEST)
        data = b"\x0Ax\x00\x05"
        from crc import crc8_dvb_s2
        raw = b"\xCC\x00\x04" + data
        raw += bytes([crc8_dvb_s2(raw)])
        self.assertEqual(probe.parse_variable(raw)[2], data)


if __name__ == "__main__":
    unittest.main()
