# CRSF_MAP.md

Map v1 (PROPOSED), 2026-11-13. NOT APPROVED. Values live in `firmware/config.py`.
Radio: C8 ELRS V3 transmitter, CR8 receiver, 8 channels. RP2040 only listens.

| Channel | Control | Function | Firmware behavior |
|---|---|---|---|
| CH1 | roll stick | menu left / right | read only while the menu is open. Not used yet. |
| CH2 | pitch stick | menu up / down | read only while the menu is open |
| CH3 | throttle | none | not read |
| CH4 | yaw | none | not read |
| CH5 | 2-pos switch | none (often arm) | not read. Kept free so record is not tied to arm. |
| CH6 | 2-pos switch | record | switch change to high: start recording. Change to low: stop. Nothing on boot. |
| CH7 | 3-pos switch | laser mode | low off, mid continuous, high single shot |
| CH8 | momentary button | multi | short: mark (freeze and log reading, or fire a single shot). Long (1 s): next OSD page. Very long (3 s): open or close the menu. In the menu, short = select. |

Rules in firmware:
- Record and laser act on a switch change only, never on the first frame after boot.
- On failsafe (no RC frame for 1 s) nothing changes state.
- Thresholds: low below 1300 us, high above 1700 us.

Questions for Alex:
1. Approve or change each row.
2. Is CH5 the arm switch on this radio? Does anything else listen to this receiver?
3. Which C8 switches are 2-position, 3-position, and momentary?
