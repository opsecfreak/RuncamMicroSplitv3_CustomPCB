# PROTOCOL.md

Doc v1, 2026-11-13. Phase 1 research. Covers the RunCam Device Protocol, the JC02-1 rangefinder protocol, CRSF input, and the PIO UART.
Status words: VERIFIED (from a primary source or source code), UNVERIFIED (not proven on Alex's hardware). Nothing in this file is proven on hardware yet.

## 1. RunCam Device Protocol

### 1.1 Sources and priority

1. Real hardware (probe v2 log). Not run yet.
2. `docs/reference/RunCam_Device_Protocol_youdao.md` (Alex's youdao doc as text).
3. Betaflight `src/main/io/rcdevice.c` and `rcdevice.h` (master, read 2026-11-13).
4. ArduPilot `libraries/AP_Camera/AP_RunCam.cpp` and `AP_RunCam.h` (master, read 2026-11-13).
5. RunCam support article "RunCam Device Protocol".

### 1.2 Framing

| Item | Value | Source |
|---|---|---|
| Header | `0xCC` on every request and every fixed-length reply | youdao, Betaflight, ArduPilot |
| CRC | CRC8 DVB-S2, poly 0xD5, init 0, no reflection | Betaflight `crc8_dvb_s2`, ArduPilot `crc8_dvb_s2` |
| CRC coverage, request | every byte before the CRC, header included | Betaflight `crc8_dvb_s2_sbuf_append` over the whole buffer |
| CRC coverage, reply | every byte before the CRC, header included. Betaflight runs the CRC over the whole reply and expects 0. | Betaflight `rcdeviceReceive` |
| Baud | 115200 8N1 | Betaflight `openSerialPort(..., 115200, ...)`. Not in the youdao doc. |
| Max packet | 64 bytes | Betaflight `RCDEVICE_PROTOCOL_MAX_PACKET_SIZE` |
| Boot delay | 7000 ms before the first request | ArduPilot `RCAM_BT_DELAY` default |

Note: firmware `crc.py` is checked against the full 256 entry CRC8 DVB-S2 table in the TBS CRSF spec (`tests/test_crc_jc02.py`). The polynomial is the same one CRSF uses.

### 1.3 Reply lengths

| Cmd | Reply | Source |
|---|---|---|
| 0x00 device info | 5 bytes: `CC ver feat_lo feat_hi crc`. Features are little-endian. | Betaflight and ArduPilot tables, both read `buf[2]` as low byte |
| 0x01 camera control | No reply. Neither Betaflight nor ArduPilot waits for one. | Gap in youdao doc, filled from source |
| 0x02 5-key press | 2 bytes: `CC crc` | youdao, Betaflight, ArduPilot |
| 0x03 5-key release | 2 bytes: `CC crc` | same |
| 0x04 5-key connection | 3 bytes: `CC (action<<4 | result) crc` | same |
| 0x10, 0x11 settings | Variable. The youdao tables do not show the `CC` header. Firmware accepts both layouts and checks the CRC. | UNVERIFIED |
| 0x13 write setting | youdao says 4 bytes but lists 3 fields | UNVERIFIED. Firmware blocks writes by default. |
| 0x20 to 0x24 display | No reply defined | youdao |

### 1.4 Feature bits

| Bit | Name | In youdao | In Betaflight | In ArduPilot |
|---|---|---|---|---|
| 0 | Power button | yes | yes | yes |
| 1 | Wi-Fi button | yes | yes | yes |
| 2 | Change mode | yes | yes | yes |
| 3 | 5-key OSD cable | yes | yes | yes |
| 4 | Settings access | yes | no | yes |
| 5 | DisplayPort | yes | no | yes |
| 6 | Start recording | yes | yes | yes |
| 7 | Stop recording | yes | yes | yes |
| 8 | CMS menu | no | yes | no |
| 9 | FC attitude (cmd 0x50) | no | yes | no |

ArduPilot `AP_RunCam.h` comment: "RunCam 2 4k and Split 3S micro reports 0x77 (POWER, WIFI, MODE, SETTING, DPORT, START)". 0x77 is bits 0, 1, 2, 4, 5, 6. Bit 7 (stop) is not set.
This is the Split 3S Micro, not the Split 3 Micro. It is the closest data point found. UNVERIFIED for Alex's camera.

ArduPilot treats a camera that reports Wi-Fi + power + change mode as a "2-key OSD" camera. It drives the camera menu with those three button actions, not with 5-key commands.

### 1.5 Recording

- No command reports recording state. Firmware tracks it (`runcam.RunCam.recording`).
- ArduPilot uses actions 0x03 / 0x04 (start / stop) for "SplitMicro" and "Split" types, and the power button (0x01) as a toggle for Split 4K, Hybrid and Run24k.
- Which style the Split 3 Micro needs is UNVERIFIED. Config: `RUNCAM_RECORD_METHOD`. Probe v2 does not test this because it would start a recording.
- ArduPilot doubles the mode delay when a menu change first needs a recording change. Some cameras block menu control while recording.

### 1.6 Legacy RCSplit protocol

Betaflight keeps an older protocol for RCSplit firmware 1.1.0 and older: `55 01 arg crc AA`, CRC8 poly 0x31, high bit first, over `55 01 arg AA`. Betaflight sends `arg = 0xFF` to detect it when `0xCC` gets no answer. Probe v2 does the same only if `0xCC` is silent. The Split 3 Micro is expected to use `0xCC`. UNVERIFIED.

### 1.7 Gaps still open after source review

1. Settings reply header byte present or not.
2. 0x13 reply layout.
3. Whether the Split 3 Micro implements 0x20 to 0x24 at all, and whether the text reaches the SD recording.
4. Setting 1 (columns) value and the OSD row count.
5. Whether the MENU pad is active-low.
6. Split TX idle voltage.

Probe v2 answers 1, 3 (analog side), 4. Items 5 and 6 need a meter.

## 2. JC02-1 rangefinder

Source: `JC02-1.pdf` in https://github.com/liancity2025/JC02-1-Laser-Ranging-Module (read 2026-11-13). The PDF text extract has garbled tables. Items marked UNVERIFIED come from those tables.

### 2.1 Electrical

| Item | Value |
|---|---|
| Supply | +3.3V to +3.8V. Manual: "strictly control the power supply voltage range within 3.3V~3.8V". |
| Power | 100mW at 3.3V (about 30 mA average). Peak current at laser fire not given. |
| UART | TTL, 9600 default, 115200 also listed, 8N1, no flow control |
| Measure time | 0.9 s max |
| Weight | about 10.5 g |
| Pins | 1 GND white, 2 VCC light blue, 3 NC green, 4 UART TX yellow, 5 UART RX black, 6 Power ON red |

The harness order in HANDOFF.md (red, black, yellow, green, blue, white, top to bottom) is pin 6 down to pin 1. It matches the manual. On the PCB connector, pin 1 is white GND.

### 2.2 Frame

`AE A7 LEN ADDR CMD DATA... CHK BC BE`

- LEN counts LEN, ADDR, CMD, DATA and CHK.
- ADDR factory default 0x00.
- CHK = (LEN + ADDR + CMD + DATA) & 0xFF. Confirmed against every command printed in the manual (`tests/test_crc_jc02.py`).

### 2.3 Commands

| Function | Host sends | Module replies |
|---|---|---|
| Power-on text | none | `init OK\r\n` (manual). Alex's module sends `init ok` lowercase. |
| Reset | `AE A7 05 00 0B 00 10 BC BE` | `AE A7 04 00 8B 8F BC BE` |
| Single measure | `AE A7 04 00 05 09 BC BE` | `AE A7 17 00 85 <19 bytes> CHK BC BE` |
| Continuous start | `AE A7 04 00 0E 12 BC BE` | ack `AE A7 04 00 8E 92 BC BE`, then 0x85 frames |
| Continuous stop | `AE A7 04 00 0F 13 BC BE` | `AE A7 04 00 8F 93 BC BE` |
| Measure failure | n/a | Manual text gives `AE A7 04 00 0E 12 BC BE`. UNVERIFIED. Firmware reads it as NR. |

### 2.4 Measurement data (19 bytes)

- Values are signed 16 bit, high byte first.
- Units: angle 0.1 degree, speed 0.1 km/h, distance 0.1 m (code 01), 0.1 yd (02), 0.1 ft (03).
- Field order in the table is garbled. Both readings put crow-fly distance at offset 2 and a 1 byte field last. Firmware reads distance at offset 2 and the unit code at offset 18. Both offsets are in `config.py`. UNVERIFIED. Check against `jc02_debug.py debug v2` when it is committed, or against a raw capture.
- "The device supports only one linear distance measurement." Other fields are expected to be zero.

## 3. CRSF from the CR8

Source: TBS CRSF spec, https://github.com/tbs-fpv/tbs-crsf-spec/blob/main/crsf.md (read 2026-11-13).

- Frame: `SYNC LEN TYPE PAYLOAD CRC`. SYNC 0xC8. LEN = TYPE + PAYLOAD + CRC. Max 64 bytes total.
- CRC: CRC8 DVB-S2 over TYPE and PAYLOAD.
- 0x16 RC channels: 16 channels, 11 bits each, 22 bytes. Center 992 = 1500 us. `us = (ticks - 992) * 5 / 8 + 1500` (C integer division).
- Failsafe: the receiver stops sending 0x16 frames. Spec: wait 1 s before acting. Firmware holds all states on failsafe and never toggles anything.
- Baud: the spec says 416666 for the receiver to FC link. ELRS uses 420000. A Betaflight PR thread reports 420000 with zero errors on ELRS. Firmware uses 420000. Change `CRSF_BAUD` if framing errors show.

MicroPython on RP2040 at 420000 baud:
- `machine.UART` on rp2 is interrupt driven. The IRQ drains the hardware FIFO into a RAM ring buffer (`ports/rp2/machine_uart.c`, default 256 bytes, set by `rxbuf=`). Firmware uses `rxbuf=1024`.
- Load is set by the ELRS packet rate, not the baud. At 500 Hz, 26 byte frames give about 13 kB/s. 1024 bytes holds about 78 ms of frames. The main loop runs every 1 to 2 ms. Drops are not expected. UNVERIFIED on hardware.
- A MicroPython forum report says rp2 UART code must run on core 0. Firmware is single threaded.
- A PIO RX at 420000 baud is the fallback layout. PIO is fast enough. The 4 word FIFO fills in under 100 us, so it needs the IRQ drain used in `pio_uart.py`. Not built.

## 4. PIO UART for the JC02 (V7 layout)

- Programs come from MicroPython `examples/rp2/pio_uart_rx.py` and `pio_uart_tx.py`. 8 PIO cycles per bit.
- Change in `firmware/pio_uart.py`: RX raises a PIO IRQ after each byte. A handler drains the FIFO into a RAM buffer.
- At 9600 a byte arrives every 1.04 ms. Without the drain, a 4 word FIFO overflows after about 4 ms of main loop stall.
- Baud detect re-creates the state machines at the new baud. UNVERIFIED on hardware.

## 5. Sources

- Betaflight rcdevice.c: https://github.com/betaflight/betaflight/blob/master/src/main/io/rcdevice.c
- Betaflight rcdevice.h: https://github.com/betaflight/betaflight/blob/master/src/main/io/rcdevice.h
- ArduPilot AP_RunCam.cpp: https://github.com/ArduPilot/ardupilot/blob/master/libraries/AP_Camera/AP_RunCam.cpp
- ArduPilot AP_RunCam.h: https://github.com/ArduPilot/ardupilot/blob/master/libraries/AP_Camera/AP_RunCam.h
- RunCam support article: https://support.runcam.com/hc/en-us/articles/360014537794-RunCam-Device-Protocol
- JC02-1 manual: https://github.com/liancity2025/JC02-1-Laser-Ranging-Module
- TBS CRSF spec: https://github.com/tbs-fpv/tbs-crsf-spec/blob/main/crsf.md
- Betaflight CRSF baud PR: https://github.com/betaflight/betaflight/pull/13614
- MicroPython rp2 UART: https://github.com/micropython/micropython/blob/master/ports/rp2/machine_uart.c
- MicroPython PIO UART examples: https://github.com/micropython/micropython/tree/master/examples/rp2
- MicroPython forum, rp2 UART on core 0: https://forum.micropython.org/viewtopic.php?p=57146
