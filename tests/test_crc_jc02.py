import unittest

import helpers  # noqa: F401  sets sys.path
from crc8_dvb_s2_table import CRC8_DVB_S2_TABLE
import config
import crc
import jc02
from helpers import FakeJC02, FakePowerPin


class TestCrc(unittest.TestCase):
    def test_matches_crsf_spec_table(self):
        # Table entry i is the CRC of the single byte i with init 0.
        for i in range(256):
            self.assertEqual(crc.crc8_dvb_s2_byte(0, i), CRC8_DVB_S2_TABLE[i], i)

    def test_table_driven_equals_bitwise(self):
        data = bytes(range(0, 250, 7)) + b"RunCam"
        t = 0
        for b in data:
            t = CRC8_DVB_S2_TABLE[t ^ b]
        self.assertEqual(crc.crc8_dvb_s2(data), t)

    def test_not_poly_07(self):
        # Poly 0x07 would give 0x07 for byte 0x01. DVB-S2 gives 0xD5.
        self.assertEqual(crc.crc8_dvb_s2(b"\x01"), 0xD5)


class TestJc02Codec(unittest.TestCase):
    def test_commands_match_manual(self):
        h = lambda s: bytes.fromhex(s)
        self.assertEqual(jc02.build(jc02.CMD_SINGLE), h("AEA704000509BCBE"))
        self.assertEqual(jc02.build(jc02.CMD_CONT_START), h("AEA704000E12BCBE"))
        self.assertEqual(jc02.build(jc02.CMD_CONT_STOP), h("AEA704000F13BCBE"))
        self.assertEqual(jc02.build(jc02.CMD_RESET, b"\x00"), h("AEA705000B0010BCBE"))
        # Replies printed in the manual parse as valid frames.
        for s, cmd in (("AEA704008B8FBCBE", 0x8B), ("AEA704008E92BCBE", 0x8E), ("AEA704008F93BCBE", 0x8F)):
            ev = jc02.Parser().feed(h(s))
            self.assertEqual(ev, [("frame", cmd, b"")])

    def test_init_ok_any_case_and_split(self):
        p = jc02.Parser()
        self.assertEqual(p.feed(b"in"), [])
        self.assertEqual(p.feed(b"it ok\r\n"), [("init",)])
        self.assertEqual(jc02.Parser().feed(b"init OK\r\n"), [("init",)])
        self.assertEqual(jc02.Parser().feed(b"INIT OK"), [("init",)])

    def test_measure_frame_in_noise_and_chunks(self):
        data = bytearray(19)
        data[2], data[3], data[18] = 0x04, 0xD2, 3   # 1234 -> 123.4 ft
        frame = jc02.build(jc02.REPLY_MEASURE, data)
        self.assertEqual(frame[2], 0x17)
        stream = b"\x00\xFF\xAE" + frame + b"junk" + frame
        p = jc02.Parser()
        events = []
        for i in range(0, len(stream), 5):
            events += p.feed(stream[i:i + 5])
        self.assertEqual(len(events), 2)
        feet, unit = jc02.decode_measure(events[0][2])
        self.assertAlmostEqual(feet, 123.4, places=3)
        self.assertEqual(unit, 3)

    def test_bad_checksum_dropped(self):
        f = bytearray(jc02.build(jc02.REPLY_CONT_START_OK))
        f[-3] ^= 0xFF
        p = jc02.Parser()
        self.assertEqual(p.feed(bytes(f)), [])
        self.assertEqual(p.bad_frames, 1)

    def test_units(self):
        d = bytearray(19)
        d[3] = 100   # 10.0 units
        d[18] = 1
        self.assertAlmostEqual(jc02.decode_measure(d)[0], 32.8084, places=3)
        d[18] = 2
        self.assertAlmostEqual(jc02.decode_measure(d)[0], 30.0, places=3)
        d[3] = 0
        self.assertIsNone(jc02.decode_measure(d)[0])

    def test_nmea_line(self):
        line = jc02.nmea_line(5, 1000, 123.44, "OK")
        self.assertTrue(line.startswith("$JC02,5,1000,123.4,OK*"))
        body = line[1:line.index("*")]
        x = 0
        for c in body:
            x ^= ord(c)
        self.assertEqual(line[-2:], "%02X" % x)
        self.assertIn(",,NOMOD*", jc02.nmea_line(1, 2, None, "NOMOD"))


def run_sim(mod, ms, start=0, drv=None):
    if drv is None:
        pwr = FakePowerPin(mod)
        drv = jc02.JC02(mod.open_uart, pwr, config)
        drv.start(start)
    t = start
    while t < start + ms:
        drv.poll(t)
        if t % 100 == 0:
            mod.tick()
        t += 10
    return drv, t


class TestJc02Driver(unittest.TestCase):
    def test_boot_and_continuous(self):
        mod = FakeJC02()
        drv, _ = run_sim(mod, 3000)
        self.assertTrue(drv.locked)
        self.assertEqual(drv.baud, 9600)
        self.assertEqual(drv.status, jc02.OK)
        self.assertAlmostEqual(drv.feet, 123.4, places=3)
        self.assertIn(jc02.CMD_CONT_START, mod.cmds)

    def test_no_init_text_still_starts(self):
        mod = FakeJC02(init_text=b"")
        drv, _ = run_sim(mod, 4000)
        self.assertEqual(drv.status, jc02.OK)

    def test_baud_detect_115200(self):
        mod = FakeJC02(baud=115200)
        drv, _ = run_sim(mod, 40000)
        self.assertEqual(drv.baud, 115200)
        self.assertEqual(drv.status, jc02.OK)

    def test_no_module_goes_nomod(self):
        mod = FakeJC02(alive=False)
        drv, _ = run_sim(mod, 60000)
        self.assertEqual(drv.status, jc02.NOMOD)
        self.assertFalse(drv.locked)

    def test_silence_recovery_with_power_cycle(self):
        mod = FakeJC02()
        drv, t = run_sim(mod, 3000)
        self.assertEqual(drv.status, jc02.OK)
        mod.alive = False
        cycles_before = drv.power.history.count(0)
        drv, t = run_sim(mod, 6500, start=t, drv=drv)
        self.assertEqual(drv.status, jc02.NT)
        self.assertEqual(drv.power.history.count(0), cycles_before)   # resends first
        drv, t = run_sim(mod, 4000, start=t, drv=drv)
        self.assertGreater(drv.power.history.count(0), cycles_before)  # then a power cycle
        mod.alive = True
        drv, t = run_sim(mod, 8000, start=t, drv=drv)
        self.assertEqual(drv.status, jc02.OK)

    def test_no_return(self):
        mod = FakeJC02()
        mod.no_return = True
        drv, _ = run_sim(mod, 3000)
        self.assertEqual(drv.status, jc02.NR)
        self.assertIsNone(drv.feet)

    def test_modes(self):
        mod = FakeJC02()
        drv, t = run_sim(mod, 3000)
        drv.set_mode("off", t)
        self.assertEqual(drv.status, jc02.OFF)
        self.assertFalse(mod.continuous)
        drv, t = run_sim(mod, 5000, start=t, drv=drv)
        self.assertEqual(drv.status, jc02.OFF)   # no silence recovery while off
        drv.set_mode("single", t)
        n = mod.cmds.count(jc02.CMD_SINGLE)
        drv, t = run_sim(mod, 3000, start=t, drv=drv)
        self.assertGreaterEqual(mod.cmds.count(jc02.CMD_SINGLE) - n, 2)
        self.assertEqual(drv.status, jc02.OK)


if __name__ == "__main__":
    unittest.main()
