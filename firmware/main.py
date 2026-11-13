# main.py, firmware v7
# RP2040-Zero companion: JC02 rangefinder + RunCam Split 3 Micro + CRSF input.
#
# Changelog v7: split into modules (config, jc02, runcam, crsf, osd);
#   added RunCam Device Protocol driver, CRSF input and OSD screen model;
#   default LAYOUT "BENCH_V6" keeps the JC02 on the pins soldered today.
# Untested on hardware. Host simulation tests pass (tests/).
# Last known good on hardware: legacy jc02_debug.py debug v2.
#
# Non-blocking main loop. Nothing in the loop sleeps longer than 1 ms.

import time
from machine import Pin, UART

import config as cfg
from jc02 import JC02, nmea_line, OK, NOMOD
from runcam import RunCam, SETTING_COLUMNS, SETTING_TV_MODE, SETTING_SD_CAPACITY, \
    SETTING_REMAIN_REC_TIME, SETTING_CAMERA_TIME
from crsf import CRSF, Button, three_pos
from osd import OSD, NullBackend, RunCamBackend, MENU_ITEMS, LASER_MODES
from status_led import StatusLed


def log(*a):
    print("#", *a)


def make_jc02_uart_factory():
    if cfg.JC02_BACKEND == "uart":
        def open_uart(baud):
            return UART(cfg.JC02_UART_ID, baudrate=baud, tx=Pin(cfg.PIN_JC02_TX),
                        rx=Pin(cfg.PIN_JC02_RX), rxbuf=256)
        return open_uart
    from pio_uart import PioUart
    holder = [None]

    def open_pio(baud):
        if holder[0] is not None:
            holder[0].deinit()
        holder[0] = PioUart(cfg.PIN_JC02_TX, cfg.PIN_JC02_RX, baud)
        return holder[0]
    return open_pio


class App:
    SETTINGS_REFRESH_MS = 10000

    def __init__(self):
        self.led = StatusLed(cfg.PIN_STATUS_LED)
        self.led.show("SEARCH")
        power = Pin(cfg.PIN_JC02_POWER, Pin.OUT, value=0 if cfg.JC02_POWER_ACTIVE_HIGH else 1)
        self.jc02 = JC02(make_jc02_uart_factory(), power, cfg, log)

        self.cam = None
        if cfg.RUNCAM_ENABLED:
            u = UART(cfg.SPLIT_UART_ID, baudrate=cfg.SPLIT_BAUD, tx=Pin(cfg.PIN_SPLIT_TX),
                     rx=Pin(cfg.PIN_SPLIT_RX), rxbuf=512)
            self.cam = RunCam(u, cfg, log)

        self.rc = None
        if cfg.CRSF_ENABLED:
            u = UART(cfg.CRSF_UART_ID, baudrate=cfg.CRSF_BAUD, rx=Pin(cfg.PIN_CRSF_RX),
                     rxbuf=cfg.CRSF_RXBUF)
            self.rc = CRSF(u, cfg.CRSF_FAILSAFE_MS)
        self.button = Button(cfg.BUTTON_LONG_MS, cfg.BUTTON_VERY_LONG_MS, cfg.SW_HIGH_US)
        self.last_rec_sw = None
        self.last_laser_sw = None
        self.menu_stick_armed = True

        if cfg.OSD_BACKEND == "runcam" and self.cam is not None:
            backend = RunCamBackend(self.cam)
        else:
            backend = NullBackend()
        self.osd = OSD(backend, cfg.OSD_COLUMNS, cfg.OSD_ROWS)
        self.t_osd = 0
        self.t_settings = None
        self.last_seq = -1
        self.t_line = 0

    # -- CRSF controls -------------------------------------------------------
    def controls(self, now):
        rc = self.rc
        if rc is None:
            return
        rc.poll(now)
        st = self.osd.state
        st.link_lq = rc.lq
        st.failsafe = rc.failsafe(now)
        if st.failsafe:
            return  # hold everything as it is. No toggles on failsafe.

        rec = three_pos(rc.us(cfg.CH_RECORD), cfg.SW_LOW_US, cfg.SW_HIGH_US)
        if rec is not None and rec != self.last_rec_sw:
            if self.last_rec_sw is not None and self.cam is not None:
                if rec == 2:
                    self.cam.start_recording()
                elif rec == 0:
                    self.cam.stop_recording()
            self.last_rec_sw = rec

        laser = three_pos(rc.us(cfg.CH_LASER_MODE), cfg.SW_LOW_US, cfg.SW_HIGH_US)
        if laser is not None and laser != self.last_laser_sw:
            self.jc02.set_mode(LASER_MODES[laser], now)
            self.last_laser_sw = laser

        ev = self.button.update(rc.us(cfg.CH_BUTTON), now)
        if ev == "short":
            if st.menu_open:
                self.menu_select(now)
            else:
                st.marked_feet = self.jc02.feet
                log("MARK", self.jc02.seq, "%.1f" % self.jc02.feet if self.jc02.feet else "-")
                if self.jc02.mode == "single":
                    self.jc02.trigger_single(now)
        elif ev == "long" and not st.menu_open:
            self.osd.next_page()
        elif ev == "very_long":
            st.menu_open = not st.menu_open
            st.menu_index = 0

        if st.menu_open:
            y = rc.us(cfg.CH_MENU_Y)
            if y is not None:
                if self.menu_stick_armed and y > cfg.SW_HIGH_US:
                    st.menu_index = (st.menu_index - 1) % len(MENU_ITEMS)
                    self.menu_stick_armed = False
                elif self.menu_stick_armed and y < cfg.SW_LOW_US:
                    st.menu_index = (st.menu_index + 1) % len(MENU_ITEMS)
                    self.menu_stick_armed = False
                elif cfg.SW_LOW_US <= y <= cfg.SW_HIGH_US:
                    self.menu_stick_armed = True

    def menu_select(self, now):
        st = self.osd.state
        item = MENU_ITEMS[st.menu_index]
        if item == "LASER":
            i = (LASER_MODES.index(self.jc02.mode) + 1) % len(LASER_MODES)
            self.jc02.set_mode(LASER_MODES[i], now)
        elif item == "OSD PAGE":
            self.osd.next_page()
        elif item == "SPLIT MENU":
            # Passthrough to the Split's own menu. 5-key needs feature bit 3.
            # Split-type cameras usually report 2-key style instead. UNVERIFIED.
            log("split menu passthrough not enabled until probe v2 results are in")
        elif item == "EXIT":
            st.menu_open = False

    # -- camera settings refresh --------------------------------------------
    def refresh_settings(self, now):
        cam = self.cam
        if cam is None or not cam.ready() or cam.busy():
            return
        if self.t_settings is not None and time.ticks_diff(now, self.t_settings) < self.SETTINGS_REFRESH_MS:
            return
        self.t_settings = now
        for sid in (SETTING_COLUMNS, SETTING_TV_MODE, SETTING_SD_CAPACITY,
                    SETTING_REMAIN_REC_TIME, SETTING_CAMERA_TIME):
            cam.read_setting_detail(sid)

    def sync_osd_state(self):
        st = self.osd.state
        j = self.jc02
        st.feet = j.feet if j.status == OK else st.feet
        st.jc02_status = j.status
        st.laser_mode = j.mode
        if self.cam is not None:
            st.recording = self.cam.recording
            s = self.cam.settings

            def val(sid):
                d = s.get(sid)
                return None if not d else d.get("value")
            st.tv_mode = val(SETTING_TV_MODE)
            st.sd_capacity = val(SETTING_SD_CAPACITY)
            st.rec_remaining = val(SETTING_REMAIN_REC_TIME)
            st.cam_time = val(SETTING_CAMERA_TIME)
            cols = self.cam.columns
            if cols and 10 <= cols <= 60 and cols != self.osd.screen.cols:
                self.osd.resize(cols, self.osd.screen.rows)

    def step(self, now):
        self.jc02.poll(now)
        if self.cam is not None:
            self.cam.poll(now)
            self.refresh_settings(now)
        self.controls(now)

        j = self.jc02
        if j.seq != self.last_seq or time.ticks_diff(now, self.t_line) >= 1000:
            self.last_seq = j.seq
            self.t_line = now
            if cfg.PRINT_LINES:
                feet = j.feet if j.status == OK else None
                print(nmea_line(j.seq, now, feet, j.status))
            if j.status == NOMOD:
                self.led.show("NOMOD")
            elif not j.locked:
                self.led.show("SEARCH")
            else:
                self.led.show(j.status)

        if time.ticks_diff(now, self.t_osd) >= cfg.OSD_PERIOD_MS:
            self.t_osd = now
            self.sync_osd_state()
            self.osd.update()

    def run(self):
        log("fw", cfg.FW_VERSION, "layout", cfg.LAYOUT)
        self.jc02.start(time.ticks_ms())
        while True:
            self.step(time.ticks_ms())
            time.sleep_ms(1)


def main():
    App().run()


if __name__ == "__main__":
    main()
