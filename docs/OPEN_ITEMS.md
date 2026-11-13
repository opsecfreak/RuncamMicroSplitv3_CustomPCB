# OPEN_ITEMS.md

List v1, 2026-11-13. Items blocked on Alex or on hardware.

## Missing files

- `legacy/jc02_debug.py` (debug v2, last known good on hardware)
- `legacy/main.py` (v6)
- `legacy/jc02_bench.py` (bench v1)
- `legacy/runcam_probe.py` (probe v1)

Phase 0 (`docs/HARDWARE.md`) is skipped until these are in the repo. Firmware v7 re-implements the v6 behavior list from HANDOFF.md. It is not a port of v6. It must be diffed against `legacy/main.py` when that file arrives, mainly the JC02 distance offset and the baud detect logic.

## Hardware measurements

1. Split TX pad idle voltage to GND. Probe v2 refuses to run until `SPLIT_TX_MEASURED_OK = True`.
2. Split MENU pad idle level, to learn if it is active-low.
3. JC02 current at laser fire, if a meter with peak hold is available.

## Pad map

1. HANDOFF.md section 2 says: chip side up, USB-C up, GPIO edge on the left. This was read from wire colors in the photos, and the wiring works with debug v2. The Waveshare wiki was not reachable from this session, so it was not checked against the published pinout.
2. Before the PCB footprint: confirm with the silkscreen, both edges, and the bottom row order. A mirrored footprint kills the board.
3. GP8 and GP14 position (9 / 9 / 5 versus 8 / 8 / 7) still UNVERIFIED.

## Decisions for Alex

1. CRSF map in `docs/CRSF_MAP.md`.
2. PCB branding (name and logo).
3. Module carrier or bare RP2040 (`docs/PCB_RESEARCH.md`, recommendation: carrier).
4. OSD path after probe v2.
5. Log storage (`docs/OSD_OPTIONS.md` section 5.1, recommendation: internal flash at 1 Hz first).
6. Allow waveshare.com, datasheets.raspberrypi.com, analog.com, digikey.com in the session network settings if more datasheet checks are wanted.
