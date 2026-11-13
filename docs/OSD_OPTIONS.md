# OSD_OPTIONS.md

Doc v1, 2026-11-13. Phase 1 research for the OSD decision gate (HANDOFF.md section 5) and answers 6 and 7.
No OSD path is chosen. Probe v2 runs first.

## 1. Summary

| Path | Hardware added | Live feed | SD recording | Status |
|---|---|---|---|---|
| A, Split DisplayPort | none | yes, if the Split implements 0x20 to 0x24 | unknown | Backend written (`osd.RunCamBackend`). Waits for probe v2. |
| B, AT7456E / MAX7456 on SPI | OSD chip, inline video | yes | no | Bench proof needed first (answer 6) |
| B2, MinimOSD board via MAVLink | MinimOSD board | yes | no | Not recommended, see 3.4 |
| C, PIO + LM1881 overlay | LM1881 and a few parts | yes | no | Most work, LM1881 supply risk |

Only path A can put text into the SD file, and only if the Split mixes DisplayPort text into its recording. That is UNVERIFIED. ArduPilot reports that the Split 3S Micro sets bit 5 (DisplayPort). That is a different model.

## 2. Path A, Split DisplayPort

1. Run probe v2 with `OSD_WRITE_TEST = True`.
2. Check the analog feed for `PROBE V2 OSD` at column 2, row 2.
3. Check the SD recording for the same text.
4. Report both results.

Notes:
- Firmware sends only rows that changed. One 30 column row is one 0x22 packet of 36 bytes. At 115200 baud that takes about 3 ms.
- Characters are plain ASCII until setting 0 (charset) is read.
- Columns come from setting 1. Row count is not in the protocol. Firmware default is 16. UNVERIFIED.

## 3. Path B, AT7456E (MAX7456 compatible)

### 3.1 What the chip does

| Item | MAX7456 | AT7456E |
|---|---|---|
| Characters in NVM | 256 | 512 per the Chinese datasheet (andesource PDF). UNVERIFIED. |
| Character size | 12 x 18 pixels | 12 x 18 pixels |
| Pixel values | 2 bits: black, white, transparent | same (compatible) |
| Screen | 30 columns. 13 rows NTSC (390 chars), 16 rows PAL (480 chars). | same |
| Interface | SPI | SPI. Datasheet says software needs "some adjustments" against MAX7456. |
| Glyph upload | 54 bytes per glyph to shadow RAM, then write NVM. About 12 ms per glyph. | same flow |

Betaflight `drivers/max7456.c` confirms: 54 byte glyph, CMAH/CMAL/CMDI registers, then `CMM = 0xA0` to write NVM and wait for the busy bit.

### 3.2 What "custom OSD layer" can mean on this chip

1. Custom character set. You can draw any 12 x 18 glyph and store it. Examples: big distance digits made of 2 x 2 glyphs, a crosshair glyph, a REC dot, unit symbols. This is the normal use.
2. Free graphics. Not possible as pixels. The chip has no frame buffer. It shows a grid of character cells only. You can fake graphics by tiling custom glyphs, for example a 3 x 3 glyph crosshair. Each glyph must be in NVM before use.
3. Live changing graphics. Not practical. Every new shape needs an NVM write. NVM endurance is finite. Do not rewrite glyphs in flight.

Conclusion: path B gives a fixed custom font and a character grid. Content is the same as path A.

### 3.3 Bench proof before any PCB (answer 6)

1. Buy an off-the-shelf AT7456E or MAX7456 board. Part number and price: Alex picks. Do not use this doc as a source for either.
2. Feed it composite video from the Split. Feed its output to a monitor or the VTX.
3. Drive it from the RP2040 SPI (pins TBD in `config.py`, GP8 to GP15 are free).
4. Show distance text from the JC02 on the live feed.
5. Upload 2 or 3 custom glyphs and show them.
6. Pass condition: stable text on NTSC (or PAL), no flicker, glyphs survive power off.

Only after a pass: design the AT7456E section into the JLCPCB board.

### 3.4 MinimOSD route

A MinimOSD board is an ATmega328P plus a MAX7456-class chip. Its firmware (MinimOSD-Extra and forks) reads MAVLink telemetry.
To use it, the RP2040 must send MAVLink messages that the OSD firmware already draws, and the distance field must exist in that firmware. That needs a MAVLink encoder in MicroPython and a firmware check or change on the ATmega.
Driving the OSD chip directly over SPI removes the ATmega and the MAVLink layer. Recommendation: direct SPI. Reason: fewer parts, one firmware to maintain. MinimOSD firmware field list is UNVERIFIED (not checked this session).

## 4. Path C, PIO + LM1881

- LM1881 separates sync from composite video. RP2040 PIO times pixels from the sync and switches a pixel driver.
- Free graphics are possible (pixel level), but timing, analog levels and a video switch circuit all need design and test.
- LM1881 last-time-buy date was seen as 1/28/2027 on DigiKey. Not re-checked this session (DigiKey not reachable from this session). Re-check before any BOM.
- Recommendation: do not start path C unless A fails and B fails the bench test.

## 5. Distance in the SD recording (answer 7)

Option A, live overlay plus a log merged later:
- RP2040 logs `$JC02` lines with time since record start.
- A desktop script turns the log into an `.srt` file named like the video. Players show it as subtitles. Burn-in with ffmpeg is optional.
- Sync: firmware knows when it sent "start recording". Offset error is the camera start latency. UNVERIFIED, measure once with a clap test.

Option B, burned into the SD file: only if path A works and the Split records DisplayPort text. Probe v2 answers this.

### 5.1 Log storage options (report before adding hardware)

| Option | Hardware | Notes |
|---|---|---|
| RP2040-Zero flash, MicroPython filesystem | none | Flash size and free space UNVERIFIED (Waveshare wiki not reachable this session). A 40 byte line at 10 Hz is about 1.4 MB per hour. Too much at 10 Hz. At 1 Hz plus marks, about 150 KB per hour. Flash wear: write in blocks, not per line. |
| microSD breakout on SPI | SPI microSD board | `sdcard.py` driver exists in micropython-lib. FAT, easy to read on a PC. Best for long logs. |
| SPI NOR flash chip | 8-pin flash on the PCB | Needs a block driver and a filesystem. More firmware work than microSD. |
| No local log | none | Stream `$JC02` lines over USB to a laptop on the bench only. Not usable in flight. |

Recommendation: start with option 1 at 1 Hz plus marks (no hardware). Add a microSD breakout if longer logs are needed. Do not add hardware until Alex approves.

## 6. Sources

- Betaflight MAX7456 driver: https://github.com/betaflight/betaflight/blob/master/src/main/drivers/max7456.c
- Betaflight MAX7456 header (390 / 480 chars): https://github.com/betaflight/betaflight/blob/master/src/main/drivers/max7456.h
- AT7456E datasheet (Chinese): https://file01.andesource.com/dkpdf/AT7456E_001.pdf
- MAX7456 product page: https://www.analog.com/en/products/MAX7456.html (not reachable from this session)
- ArduPilot AP_RunCam.h (Split 3S Micro features 0x77): https://github.com/ArduPilot/ardupilot/blob/master/libraries/AP_Camera/AP_RunCam.h
