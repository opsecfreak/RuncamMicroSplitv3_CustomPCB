# RuncamMicroSplitv3_CustomPCB

Custom PCB integration for the RunCam Split 3 Micro (orange), adding a custom OSD and remote control of the camera.
One Waveshare RP2040-Zero (MicroPython) runs a JC02-1 laser rangefinder, controls the Split over its UART, and takes commands from a CR8 ELRS receiver.

Project brief: `HANDOFF.md`. Research: `docs/`. Open items: `docs/OPEN_ITEMS.md`.

## Status

| Item | Version | State |
|---|---|---|
| `legacy/jc02_debug.py` | debug v2 | LAST KNOWN GOOD ON HARDWARE. Not in the repo yet. |
| `firmware/` | v7 | Host tests pass (41). Compiles with mpy-cross v1.29.0. UNVERIFIED on hardware. |
| `tools/runcam_probe_v2.py` | probe v2 | UNVERIFIED on hardware. Run this first. |
| `hardware/SCHEMATIC_DRAFT.md` | v0.1 | Netlist only. |

## Run the host tests

```bash
cd tests && python3 -m unittest discover -s . -p "test_*.py"
```

## Flash firmware v7 to the RP2040-Zero

1. Install mpremote on the PC.
```bash
pip install mpremote
```
2. Connect the RP2040-Zero by USB-C.
3. Copy the firmware files.
```bash
cd firmware && mpremote cp config.py crc.py jc02.py runcam.py crsf.py osd.py pio_uart.py status_led.py main.py :
```
4. Reset the board.
```bash
mpremote reset
```
5. Watch the output.
```bash
mpremote repl
```

Note: this overwrites the `main.py` on the board (v6 or debug v2). Rollback: copy the old file back with `mpremote cp <old main.py> :main.py`. Keep a copy of the current board files first:
```bash
mkdir -p board_backup && mpremote cp :main.py board_backup/main.py
```

Default `LAYOUT = "BENCH_V6"` uses the pins soldered today. No rewiring needed.

## Run probe v2

1. Measure the Split TX pad idle voltage to GND. Stop if it is above 3.3V.
2. Open `tools/runcam_probe_v2.py`. Set `SPLIT_TX_MEASURED_OK = True`.
3. Wire GP4 to Split RX, GP5 to Split TX, GND to GND. Power the Split from its own 5V BEC.
4. Run it.
```bash
mpremote run tools/runcam_probe_v2.py
```
5. Paste the full output into the chat.
6. For the OSD test, set `OSD_WRITE_TEST = True` and run again. Check the live feed and the SD file.

## Changelog

- firmware v7 (2026-11-13): modules split out (config, jc02, runcam, crsf, osd); RunCam Device Protocol driver, CRSF input, OSD screen model added. Untested on hardware. Last known good: debug v2.
- probe v2 (2026-11-13): read-only by default, hex log, settings read, OSD test behind a flag, refuses to run before the TX voltage check. Untested on hardware.
