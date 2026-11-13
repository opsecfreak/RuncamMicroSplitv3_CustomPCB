# SCHEMATIC_DRAFT.md

Schematic draft v0.1, 2026-11-13. Netlist only. No KiCad file and no layout yet.
Assumes the RP2040-Zero module carrier (recommendation, not decided). Matches `firmware/config.py` LAYOUT "V7".
Part numbers, values not stated below, and prices: blank on purpose. Alex picks them.
Blocked before KiCad: branding, module versus bare chip, pad map confirmation (`docs/OPEN_ITEMS.md`).

## Connectors

| Ref | Connector | Pins (pin 1 first) |
|---|---|---|
| J1 | 5V input from BEC | 1 +5V, 2 GND |
| J2 | JC02 harness, 6 pin, harness order | 1 GND (white), 2 VCC (blue), 3 NC (green), 4 JC02 TX (yellow), 5 JC02 RX (black), 6 Power ON (red) |
| J3 | Split UART | 1 GND, 2 Split TX, 3 Split RX, 4 MENU (optional) |
| J4 | Split power out | 1 +5V, 2 GND. 1A or more. Split must not take power from the RP2040. |
| J5 | CR8 receiver | 1 +5V, 2 GND, 3 CRSF (CR8 TX) |
| J6 | Recovery pads | GND, SWCLK, SWDIO, USB D+, USB D-, BOOTSEL, RUN. Each only if the module exposes it (UNVERIFIED). |
| J7 | Spare GPIO pads | GP3, GP8 to GP15, GP26 to GP29 for the OSD chip SPI or microSD later |

## Nets

| Net | Connects |
|---|---|
| +5V | J1.1, J4.1, J5.1, U1 5V pad |
| GND | J1.2, J2.1, J3.1, J4.2, J5.2, U1 GND pad, C1 -, C2 - |
| +3V3 | U1 3V3 pad, C1 +, J2.2 (or U2 output if the separate JC02 LDO is used) |
| JC02_PWR_ON | U1 GP2, J2.6 |
| JC02_TX_TO_MCU | J2.4, U1 GP7 (PIO RX) |
| MCU_TO_JC02_RX | U1 GP6 (PIO TX), J2.5 |
| SPLIT_TX_TO_MCU | J3.2, R1, U1 GP5 (UART1 RX). R1/R2 divider only if Split TX idles near 5V. |
| MCU_TO_SPLIT_RX | U1 GP4 (UART1 TX), J3.3 |
| SPLIT_MENU | J3.4, U1 spare GPIO through a jumper. Active level UNVERIFIED. Leave open by default. |
| CRSF_IN | J5.3, U1 GP1 (UART0 RX) |

## Parts

| Ref | Part | Value | Note |
|---|---|---|---|
| U1 | Waveshare RP2040-Zero | module | Castellated footprint. Pad map must be confirmed. USB-C at board edge. |
| C1 | Electrolytic | 470uF 16V | 3V3 to GND, close to the U1 3V3 pad. Required (brownout). |
| C2 | Electrolytic | blank | Bulk cap on +5V input |
| R1, R2 | 1/4W resistors | blank | Split TX divider. Fit only if the measurement needs it. Values from the measurement. |
| U2 | 3.3V LDO for the JC02 | blank | Option. See `docs/PCB_RESEARCH.md` section 4. |
| Q1 | P-MOSFET high-side switch | blank | Option, if Power ON does not cut the JC02 current fully. |
| D1 | Schottky (1N58xx on hand) | blank | Option: reverse polarity on J1. Drops voltage on +5V. Alex to decide. |

## Path B add-on (only after the bench proof in docs/OSD_OPTIONS.md section 3.3)

AT7456E with its crystal and video in/out parts, on SPI pins chosen from J7. Not drawn.
