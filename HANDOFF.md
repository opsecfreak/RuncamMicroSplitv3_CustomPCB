# HANDOFF: RP2040-Zero companion for JC02 rangefinder + RunCam Split 3 Micro

Handoff v4, 2026-11-13. Written for Claude Code running on Opus.
Changelog v4: protocol section now uses the youdao doc text as primary reference, with the diff against the RunCam support article written in. Changelog v3: read the JC02 wiring from the board photos, confirmed the v6 layout is what is soldered, and re-anchored the pad map to the photographed side. Changelog v2: added the text pinout reference (pad map, v6 and v7 connection tables, board photo notes) so the pinout images are no longer required. Pad positions of GP8 and GP14 are unverified.
Repo: https://github.com/opsecfreak/RuncamMicroSplitv3_CustomPCB

Start Claude Code in the cloned repo and select Opus (`/model opus`), then say: "Read HANDOFF.md and start at Phase 0."

---

## 1. Goal

One Waveshare RP2040-Zero running MicroPython is the only processor. No Pi, no flight controller. It must:

1. Run the JC02-1-10 laser rangefinder (sold as L22A): power control, auto start at boot, parse distance, self-recover.
2. Control the RunCam Split 3 Micro (orange version, stacked board with SD card) over its UART using the RunCam Device Protocol: record start/stop, camera/menu control, read SD capacity and remaining record time.
3. Get the distance onto the video. Preferred: write a custom OSD through the Split's UART. Fallback: RP2040 drives its own OSD chip inline on the analog video.
4. Take in-flight commands from a CR8 ELRS receiver (CRSF) bound to Alex's C8 transmitter.
5. End up on a custom carrier PCB, so the repo also needs schematics.

Deliverable order: MicroPython firmware for both devices first, then OSD, then schematics/PCB.

## 2. Hardware

| Part | Notes |
|---|---|
| Waveshare RP2040-Zero | MicroPython v1.29.0 confirmed running. GP16 is the onboard RGB LED. All GPIO 3.3V only. |
| JC02-1-10 rangefinder | 905nm ToF, UART 9600 8N1 (115200 fallback seen in docs), binary frames, header `AE A7`, footer `BC BE`. |
| RunCam Split 3 Micro (orange) | Pads: TX, RX, GND, MENU, D+, D-. UART 115200 8N1. Needs its own 5V supply, 1A or more (manual lists 650mA at 5V). Do not power from the VTX or the RP2040. |
| Black Mamba 5.8 GHz analog VTX | Takes the Split's analog video out. |
| CR8 ELRS nano receiver | CRSF out at 420000 baud. RP2040 only listens. |
| 470uF 16V electrolytic | Across 3V3 and GND at the RP2040-Zero. Required. Without it the board resets when the JC02 powers up. Must be on the schematic. |

### JC02 harness (top to bottom on the connector)

| Wire | Function | Goes to |
|---|---|---|
| Red | Power ON (enable) | GP2 |
| Black | Module RX | RP2040 TX |
| Yellow | Module TX | RP2040 RX |
| Green | Not connected | none |
| Blue | VCC | 3V3 |
| White | GND | GND |

### Pin plan

Currently wired and proven on the bench (firmware v6 layout):

- UART0 GP0 TX / GP1 RX: JC02
- GP2: JC02 Power ON
- UART1 GP4 TX / GP5 RX: was the output to a second board, now reassigned to the Split

Target layout for v7 (decided, not yet built):

- UART0 RX (GP1): CR8 CRSF in, 420000 baud. Hardware UART because it is the fastest link.
- UART1 GP4 TX to Split RX, GP5 RX from Split TX, 115200.
- PIO UART GP6 TX / GP7 RX: JC02 at 9600.
- GP2: JC02 Power ON.
- GP16: status LED (blue searching, green good reading, yellow no return, red module not found).
- Free: GP3, GP8 to GP15, GP26 to GP29.

Keep every pin in one config block. If the PIO UART misbehaves, the fallback is JC02 back on UART0 and CRSF on PIO.

### Pinout reference (text version, replaces the pinout images)

RP2040-Zero pad map. 23 edge pads: 9 on the power edge, 9 on the GPIO edge, 5 on the bottom. Listed with USB-C at the top.

Orientation, from Alex's board photos of 2026-11-13: looking at the side with the RP2040 chip and crystal, USB-C up, the GPIO edge (GP0 at the top) is on the LEFT and the power edge (5V at the top) is on the RIGHT. This was worked out from the JC02 wire colors and the cap position, not from silkscreen, which is unreadable in the photos. Confirm against the silkscreen before drawing the PCB footprint, because a mirrored footprint kills the board.

| Power edge, top to bottom | GPIO edge, top to bottom | Bottom edge |
|---|---|---|
| 5V | GP0 | GP13 |
| GND | GP1 | GP12 |
| 3V3 | GP2 | GP11 |
| GP29 (ADC3) | GP3 | GP10 |
| GP28 (ADC2) | GP4 | GP9 |
| GP27 (ADC1) | GP5 | |
| GP26 (ADC0) | GP6 | |
| GP15 | GP7 | |
| GP14 | GP8 | |

- GP16: onboard WS2812 RGB LED. GP17 to GP25: back-side solder points only.
- UART0: GP0 TX, GP1 RX. UART1: GP4 TX, GP5 RX (GP8/GP9 are the same UART1 peripheral, not a third port).
- All GPIO 3.3V only, not 5V tolerant.
- Status of this map: the edge order above is supported by the photos for 5V, GND, 3V3 and GP0 to GP2. Two points stay UNVERIFIED: (1) whether GP8 and GP14 are the last pads of the side edges (9 / 9 / 5, used here, and the photos show 5 bottom pads) or sit on the bottom row (8 / 8 / 7, drawn in an earlier chat); (2) the left-to-right order of the bottom row.

Connection table, v6 layout (what is soldered now, confirmed against the 2026-11-13 board photos except where noted):

| From | Wire | To RP2040-Zero pad |
|---|---|---|
| JC02 Power ON | red | GP2 |
| JC02 RX | black | GP0 (UART0 TX) |
| JC02 TX | yellow | GP1 (UART0 RX) |
| JC02 NC | green | not connected |
| JC02 VCC | blue | 3V3 |
| JC02 GND | white | GND |
| 470uF 16V cap + | n/a | 3V3 |
| 470uF 16V cap - | n/a | GND |

Connection table, v7 target:

| From | To RP2040-Zero pad | Notes |
|---|---|---|
| CR8 TX (CRSF) | GP1 (UART0 RX) | 420000 baud, listen only |
| CR8 5V, GND | 5V rail, GND | |
| Split RX | GP4 (UART1 TX) | 115200 |
| Split TX | GP5 (UART1 RX) | Measure idle voltage first, must be 3.3V or less |
| Split GND | GND | |
| Split MENU | spare GPIO, optional | Fallback only. Active-low is UNVERIFIED. |
| Split D+, D- | not connected | USB only |
| JC02 RX (black) | GP6 (PIO TX) | 9600 |
| JC02 TX (yellow) | GP7 (PIO RX) | 9600 |
| JC02 Power ON (red) | GP2 | |
| JC02 VCC (blue), GND (white) | 3V3, GND | |
| 470uF 16V cap | 3V3 to GND | Keep close to the 3V3 pad |
| 5V BEC | Split power in, RP2040 5V pad, CR8 5V | 1A or more for the Split. Common ground everywhere. |

What the 2026-11-13 board photos show (two close-ups, chip side, USB-C up, soft focus). The JC02 is still wired in the v6 layout:

| Pad position in photo | Wire seen | Matches |
|---|---|---|
| Left edge, pad 1 (top) | black | GP0, JC02 RX |
| Left edge, pad 2 | yellow | GP1, JC02 TX |
| Left edge, pad 3 | red | GP2, JC02 Power ON |
| Left edge, pad 4 and down | empty | GP3 onward free |
| Right edge, pad 1 (top) | empty | 5V unused |
| Right edge, pad 2 | white, plus one cap lead | GND, JC02 GND |
| Right edge, pad 3 | dark wire (probably blue), plus other cap lead | 3V3, JC02 VCC. Wire color not certain in the photo. |
| Bottom edge | 5 pads, all empty | |

- The cap body is marked 470uF 16V and sits off the right (power) edge.
- The harness leaves toward the lower right in a black sleeve. Green is not connected.
- Nothing is on GP4 to GP7 yet, so the Split, the CR8 and the JC02 move to PIO are not wired.
- Confidence: wire color to pad position is clear for black, yellow, red and white. The 3V3 wire and the exact cap lead pads are probable, not certain. Pad names are inferred from the harness colors.

## 3. Existing code and assets (Alex adds these to the repo first)

Alex will commit these into `legacy/` and `assets/` before you start. If they are missing, stop and ask. Do not rewrite them from this description.

| File | Version | Status |
|---|---|---|
| `jc02_debug.py` | debug v2 | LAST KNOWN GOOD ON HARDWARE |
| `main.py` | v6 | Auto start, baud detect, recovery, status LED, UART1 output. Simulation tested only. |
| `jc02_bench.py` | bench v1 | Power cycle, single shot and continuous tests. Simulation only. |
| `runcam_probe.py` | probe v1 | Reads Split feature flags and settings, test-writes OSD. Simulation only. Never run on hardware as far as the chat history shows. |
| Pinout PNGs | n/a | Optional. The text pinout reference in section 2 replaces them. If committed, treat section 2 as the reference and flag any difference. |
| Existing schematics / photos | n/a | Including the cap on the RP2040. |

Facts already established on hardware:

- Module replies `init ok` in lowercase. The manual says `init OK`. Match case-insensitive.
- Single measurement command: `AE A7 04 00 05 09 BC BE`. Continuous start: `AE A7 04 00 0E 12 BC BE`. Checksum appears to be the byte sum of length through command. Confirm against the manual.
- v6 output line format: `$JC02,<seq>,<ms>,<feet>,<status>*<XOR checksum>`, status one of OK, NR, NT, NOMOD, OFF.
- Readings under about 11 ft are unverified.
- Powering the module through GP2 without the 470uF cap browns out the board.

JC02 manual: https://github.com/liancity2025/JC02-1-Laser-Ranging-Module

Version numbering continues from here: firmware is `main.py v7` next, probe is `probe v2` next.

## 4. RunCam Device Protocol (starting reference, verify it)

Primary reference: `docs/reference/RunCam_Device_Protocol_youdao.md`. This is the text of Alex's youdao protocol doc, supplied by him on 2026-11-13 (original link: https://share.note.youdao.com/coshare/index.html?token=9AD3F89F0B92488E8241F58CAEDF7939&gid=29699666&_time=1794594300867). The table below has been diffed against it. Still cross-check Betaflight `rcdevice.c/.h` and ArduPilot `AP_RunCam` for the parts the doc leaves out. Real hardware wins over all documents.

Diff result, youdao doc versus the RunCam support article:
- Commands 0x00 to 0x04, 0x10, 0x11, 0x13 and 0x20 to 0x24 match byte for byte.
- The youdao doc lists feature bits 0 to 7 only. Bit 9 (attitude request) and command 0x50 appear only in the support article. Do not rely on them.
- The youdao doc gives the full setting type table, which was garbled in the support article: UINT8 0, INT8 1, UINT16 2, INT16 3, FLOAT 8, TEXT_SELECTION 9, STRING 10, FOLDER 11, INFO 12.
- Reserved setting types: 0 charset TEXT_SELECTION (read/write), 1 columns UINT8 (read only), 2 TV mode TEXT_SELECTION (read/write), 3 SD capacity STRING (read only), 4 remaining record time STRING (read only), 5 resolution TEXT_SELECTION (read/write), 6 camera time STRING (read/write), 7 to 19 reserved.
- Neither document states the baud rate, the CRC start value, or which bytes the CRC covers. The youdao doc does not name the CRC algorithm at all. CRC8 DVB-S2 comes from the support article and the open-source implementations.
- Gaps in the youdao doc to resolve from Betaflight/ArduPilot source and then on hardware: no response format for camera control (0x01); the 0x10 and 0x11 response tables do not list the 0xCC header byte; the 0x13 response says 4 bytes but lists 3 fields; the 0x11 table has min and max descriptions swapped; no responses are defined for the display commands 0x20 to 0x24; FOLDER text refers to "Get Detail Command(0x7)", which is not a defined command.

- Every packet starts with `0xCC`. Last byte is CRC8 DVB-S2, polynomial 0xD5, init 0, over all bytes before the CRC. Do not use polynomial 0x07 (bug found in a community example).
- Baud is not in the spec. 115200 8N1 is what Betaflight and ArduPilot use.

| Cmd | Function | Request |
|---|---|---|
| 0x00 | Read camera info | `CC 00 crc`. Reply: `CC`, protocol version u8, features u16, crc |
| 0x01 | Camera control | `CC 01 action crc`. 00 Wi-Fi btn, 01 power btn, 02 change mode, 03 start rec, 04 stop rec |
| 0x02 | 5-key press | `CC 02 key crc`. 01 set, 02 left, 03 right, 04 up, 05 down |
| 0x03 | 5-key release | `CC 03 crc` |
| 0x04 | 5-key connection | `CC 04 action crc`. 01 open, 02 close. Reply `CC, (action<<4)+result, crc` |
| 0x10 | Get sub-settings | `CC 10 settingID chunk crc` |
| 0x11 | Read setting detail | `CC 11 settingID chunk crc` |
| 0x13 | Write setting | `CC 13 settingID value crc` |
| 0x20 | Fill region | `CC 20 x y w h char crc` |
| 0x21 | Write char | `CC 21 x y char crc` |
| 0x22 | Write horizontal string | `CC 22 len x y string crc`, max 60 |
| 0x23 | Write vertical string | `CC 23 len x y string crc`, max 60 |
| 0x24 | Write chars | `CC 24 len [x y char]... crc`, max 20 entries |

Feature bits: 0 power button, 1 Wi-Fi button, 2 change mode, 3 5-key OSD, 4 settings access, 5 DisplayPort (accepts OSD text), 6 start recording, 7 stop recording, 9 attitude request.

Setting IDs: 0 charset, 1 columns, 2 TV mode, 3 SD capacity, 4 remaining record time, 5 resolution, 6 camera time.

Known unknowns for the Split 3 Micro (all UNVERIFIED until the probe runs on hardware):

- Which feature bits it reports. Split-style cameras usually report the 2-button style, not 5-key.
- Whether it accepts DisplayPort writes (0x20 to 0x24) at all.
- If it does, whether the text lands in the SD recording or only on the analog out.
- Whether the protocol can report recording state. Community reports say it cannot, so track state in firmware.
- Whether the MENU pad is active-low and usable as a fallback from a GPIO.
- Whether Split TX idles at 3.3V. Alex must measure this before connecting. If near 5V, add a divider.
- OSD menu control is reported disabled while recording on some RunCam devices.

## 5. OSD decision gate

Run the probe on hardware, then pick a path. Do not build the full OSD before this.

- Path A, camera OSD: the Split reports bit 5 and the test text shows. RP2040 writes distance, crosshair, REC state, record time, SD capacity, TV mode over UART. No extra hardware.
- Path B, own OSD chip: AT7456E (MAX7456 compatible) on RP2040 SPI, inline between Split video out and the VTX. Same OSD content. Shows on the live feed only, not in the HD SD recording. This is also the answer to "can I use a MAVLink telemetry OSD board": a MinimOSD-type board is this same chip plus an ATmega that expects MAVLink. Driving the chip directly over SPI is simpler than emitting MAVLink to a second MCU, but research both and report.
- Path C, software overlay: RP2040 PIO plus LM1881 sync separator switching pixels on the composite line. Note for the BOM: the LM1881 has a last-time-buy date (seen as 1/28/2027 on DigiKey, re-check).
- For the HD recording in any path: log distance with timestamps and generate a matching `.srt`. The RP2040-Zero has no SD and little flash, so research storage (small SPI flash or microSD breakout) and report before adding it.

Planned OSD content: distance in feet, crosshair, REC status, record time remaining, SD capacity, camera time, NTSC/PAL, plus an RP2040-drawn settings menu.

CRSF control priorities: record start/stop, laser mode (off / continuous / single shot), OSD page cycle, momentary "mark" to freeze and log a reading, menu navigation, passthrough of keys to the Split's own menu. Channel mapping is not decided. Ask Alex.

## 6. Work plan

Phase 0, intake
- Read everything in `legacy/` and `assets/`. Write `docs/HARDWARE.md` from the files, not from this handoff. List conflicts between them and this handoff.

Phase 1, research (write `docs/PROTOCOL.md` and `docs/OSD_OPTIONS.md` with sources)
- RunCam Device Protocol: youdao doc, RunCam support article, Betaflight, ArduPilot. Note Split 3 Micro specifics.
- JC02 manual: full command set and frame layout.
- CRSF channel frame decode at 420000 baud in MicroPython, and whether MicroPython UART on RP2040 holds that rate without drops.
- MicroPython PIO UART RX at 9600.
- AT7456E SPI driver options for MicroPython, MinimOSD/MAVLink route, LM1881 route.

Phase 2, firmware v7
- Layout: `firmware/config.py` (all pins and bauds), `jc02.py`, `runcam.py`, `crsf.py`, `osd.py`, `main.py`. Non-blocking main loop.
- Keep v6 behavior: auto start, baud detect, silence recovery, power cycle recovery, status LED.
- `runcam.py`: CRC, packet build, reply parse with timeouts, device info, camera control, 5-key, settings read, DisplayPort writes gated on feature bits.
- Host-side tests under CPython with stubbed `machine` and `time` (`tests/`). Known CRC vectors, synthetic JC02 frames, fake camera. Nothing ships to hardware without passing simulation.
- Ship `probe v2` first so Alex can run it and paste the log. Read-only mode default, OSD write test behind a flag.

Phase 3, hardware gate
- Alex runs the probe and bench scripts and pastes logs. Choose OSD path A, B or C. Then finish `osd.py` and the menu.

Phase 4, schematics and PCB
- KiCad project in `hardware/`. Schematic first, layout second.
- Must include: RP2040-Zero as a module footprint, 470uF cap on 3V3, JC02 6-pin connector in harness order, Split UART header (TX, RX, GND, MENU optional), CR8 header (5V, GND, signal), 5V input, optional AT7456E section with video in/out if path B.
- Check 3V3 budget: the RP2040-Zero regulator feeds the JC02. Spare current is unverified. Measure or research before finalizing. A high-side P-MOSFET on JC02 VCC is the option if the enable pin does not cut power fully.
- Alex etches boards at home on small single and double-sided copper clad blanks with a Cricut-cut mask, and also plans US-made fab boards. Ask which target and the blank size before layout. Home etch means wide traces, big clearances, minimal vias, through-hole friendly.
- Bench stock on hand: 1/4W resistor kit (10 ohm to 1M), electrolytics 1uF to 470uF, 1N4148, 1N58xx Schottky, 1N400x. Prefer these in the BOM.
- Never invent part numbers, prices or specs. Leave blanks and ask.

Phase 5, docs
- `README.md` with wiring table, flashing steps, changelog. Wiring diagram regenerated from `config.py` so it cannot drift.

## 7. Rules for this project

- Ask before guessing on anything that affects hardware. A wrong write can corrupt the SD card or damage pads.
- Label every iteration (v7, v8, probe v2). One to three line changelog each: what changed, what was fixed, what is untested.
- Never overwrite a working version. Keep `legacy/` untouched. State the last known good on hardware in every changelog. Right now that is `jc02_debug.py debug v2`.
- Before a change that could break working wiring or firmware, say so and give the rollback.
- Mark anything not proven on Alex's hardware as UNVERIFIED.
- Record dead ends in `docs/DEAD_ENDS.md` with the reason.
- Feet for all distances shown to the user. No em dashes in docs or comments.
- No Docker. No credentials or keys in the repo.
- Git: small commits with clear messages, tag firmware releases (`fw-v7`). Show Alex the exact commands for anything he must run himself.

## 8. Questions to ask Alex before Phase 2

1. Has `runcam_probe.py` been run on the Split yet? If yes, paste the log.
2. Split TX idle voltage measurement?
3. Confirm the 3V3 wire is the blue one and both cap leads sit on GND and 3V3 (photos show JC02 still on GP0/GP1/GP2).
4. CRSF channel assignments for record, laser mode, OSD page, mark, menu.
5. PCB target: home etch or fab, and board size limit.
6. Is an inline OSD chip acceptable if the Split refuses OSD writes?
7. Does the distance need to be in the SD recording, or is live feed plus an `.srt` log enough?

## 9. Sources

- RunCam Device Protocol (RunCam support): https://support.runcam.com/hc/en-us/articles/360014537794-RunCam-Device-Protocol
- Betaflight RunCam Device Protocol: https://betaflight.com/docs/wiki/guides/current/runcam-device-protocol
- ArduPilot RunCam support: https://ardupilot.org/plane/docs/common-camera-runcam.html
- RunCam Split 3 series manual: https://runcam.com/download/split-3-series/RC_Split_3_series_Manual_EN.pdf
- JC02-1 manual: https://github.com/liancity2025/JC02-1-Laser-Ranging-Module
