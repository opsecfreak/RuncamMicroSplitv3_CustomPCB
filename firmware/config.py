# config.py, firmware v7
# All pins, bauds, timings and channel maps live here. Nothing else in the
# firmware hard-codes a pin number.
#
# Last known good on hardware: legacy jc02_debug.py debug v2.
# Everything in this file is UNVERIFIED on hardware unless marked otherwise.

FW_VERSION = "v7"

# ---------------------------------------------------------------------------
# Pin layout
# ---------------------------------------------------------------------------
# "BENCH_V6": matches what is soldered now (2026-11-13 photos).
#   JC02 on UART0 GP0/GP1, power enable GP2. CRSF disabled.
#   Split on UART1 GP4/GP5 (not wired yet, firmware only polls it).
# "V7": target layout from HANDOFF.md section 2.
#   CRSF on UART0 RX GP1, JC02 on PIO UART GP6/GP7, Split on UART1 GP4/GP5.
#   Needs rewiring before use. Do not select it until the JC02 wires move.
LAYOUT = "BENCH_V6"

PIN_JC02_POWER = 2          # red wire. High = module on (v6 behavior).
JC02_POWER_ACTIVE_HIGH = True
PIN_STATUS_LED = 16         # onboard WS2812 on the RP2040-Zero

PIN_SPLIT_TX = 4            # RP2040 TX, goes to Split RX pad
PIN_SPLIT_RX = 5            # RP2040 RX, from Split TX pad. MEASURE FIRST.
SPLIT_UART_ID = 1
SPLIT_BAUD = 115200         # Betaflight and ArduPilot value, not in the spec

PIN_SPLIT_MENU = None       # optional GPIO to the MENU pad. Active level UNVERIFIED.

if LAYOUT == "BENCH_V6":
    JC02_BACKEND = "uart"   # hardware UART
    JC02_UART_ID = 0
    PIN_JC02_TX = 0         # to JC02 RX, black wire
    PIN_JC02_RX = 1         # from JC02 TX, yellow wire
    CRSF_ENABLED = False
    CRSF_BACKEND = None
    CRSF_UART_ID = None
    PIN_CRSF_RX = None
elif LAYOUT == "V7":
    JC02_BACKEND = "pio"    # PIO UART, state machines 0 (RX) and 1 (TX)
    JC02_UART_ID = None
    PIN_JC02_TX = 6
    PIN_JC02_RX = 7
    CRSF_ENABLED = True
    CRSF_BACKEND = "uart"
    CRSF_UART_ID = 0
    PIN_CRSF_RX = 1         # CR8 TX pad. RP2040 only listens.
else:
    raise ValueError("unknown LAYOUT")

# Fallback named in the handoff if the PIO UART misbehaves:
# JC02 back on UART0 (BENCH_V6 pins) and CRSF on a PIO RX pin.
# Not implemented as a layout yet. PIO RX at 420000 baud needs the FIFO to be
# drained from an IRQ, see docs/PROTOCOL.md section 3.

# ---------------------------------------------------------------------------
# JC02 rangefinder
# ---------------------------------------------------------------------------
JC02_BAUDS = (9600, 115200)     # manual: default 9600, 115200 also listed
JC02_BOOT_WAIT_MS = 1500        # wait for "init ok" after power on
JC02_SILENCE_MS = 3000          # no frame for this long: resend start
JC02_RESTARTS_BEFORE_CYCLE = 2  # resends before a power cycle
JC02_POWER_OFF_MS = 500         # time held off during a power cycle
JC02_CYCLES_BEFORE_NOMOD = 2    # power cycles per baud before NOMOD
# Offsets inside the 19 byte MMSG data field of a 0x85 reply.
# Manual table is garbled. Both readings of it put crow-fly distance at
# offset 2 (signed, high byte first, 0.1 unit) and a 1 byte unit code last.
# UNVERIFIED until checked against jc02_debug.py debug v2 or a raw capture.
JC02_DIST_OFFSET = 2
JC02_UNIT_OFFSET = 18
JC02_DEFAULT_MODE = "continuous"  # "off", "continuous", "single"
JC02_SINGLE_PERIOD_MS = 1000      # single shot repeat rate when mode is single

# ---------------------------------------------------------------------------
# RunCam Split 3 Micro
# ---------------------------------------------------------------------------
RUNCAM_ENABLED = True
RUNCAM_BOOT_DELAY_MS = 7000     # ArduPilot RCAM_BT_DELAY default
RUNCAM_REPLY_TIMEOUT_MS = 400   # Betaflight value for 5-key commands
RUNCAM_INFO_RETRY_MS = 1000     # ArduPilot init interval
RUNCAM_BUTTON_DELAY_MS = 300    # ArduPilot RCAM_BTN_DELY default
RUNCAM_MODE_DELAY_MS = 800      # ArduPilot RCAM_MDE_DELY default
# Safety: settings writes (0x13) can change camera config. Off until proven.
RUNCAM_ALLOW_SETTING_WRITE = False

# ---------------------------------------------------------------------------
# OSD
# ---------------------------------------------------------------------------
OSD_BACKEND = "none"    # "none" (console only), "runcam" (path A), "at7456" (path B, not built)
OSD_COLUMNS = 30        # replaced by setting 1 read from the camera when available
OSD_ROWS = 16           # NTSC 13, PAL 16 on MAX7456 class chips. UNVERIFIED for the Split.
OSD_PERIOD_MS = 200

# ---------------------------------------------------------------------------
# CRSF (CR8 ELRS receiver)
# ---------------------------------------------------------------------------
CRSF_BAUD = 420000          # ELRS default. Spec says 416666. Both reported to work.
CRSF_FAILSAFE_MS = 1000     # spec: wait 1 s without RC frames before failsafe
CRSF_RXBUF = 1024

# PROPOSED default channel map. NOT APPROVED BY ALEX. Channel numbers are 1 based.
# None = function disabled.
CH_RECORD = 6       # 2 position: high = recording, low = stopped
CH_LASER_MODE = 7   # 3 position: low off, mid continuous, high single shot
CH_BUTTON = 8       # momentary: short press mark, long press OSD page, very long menu
CH_MENU_X = 1       # roll stick, only read while the menu is open
CH_MENU_Y = 2       # pitch stick, only read while the menu is open

# Thresholds in microseconds
SW_LOW_US = 1300
SW_HIGH_US = 1700
BUTTON_LONG_MS = 1000
BUTTON_VERY_LONG_MS = 3000

# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------
PRINT_LINES = True      # $JC02 lines on the USB console

# Record command style. "start_stop" sends actions 0x03 / 0x04 (ArduPilot
# SplitMicro default). "power_toggle" sends the power button (ArduPilot uses
# it for Split 4K, Hybrid, Run24k). Which one the Split 3 Micro needs is
# UNVERIFIED. The probe does not test it because it would start a recording.
RUNCAM_RECORD_METHOD = "start_stop"
