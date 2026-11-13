# PCB_RESEARCH.md

Doc v1, 2026-11-13. Research for answer 5 before any layout. No layout is started.

## 1. Plain answer on recovery paths

1. The RP2040 boot ROM has two paths only: boot from QSPI flash, or USB boot (UF2 mass storage drive plus PICOBOOT). It has no UART boot.
2. The ROM picks USB boot when the flash chip select (the BOOTSEL button) reads low at reset.
3. UART pads give a MicroPython REPL at most, and only if the firmware puts the REPL on that UART. The rp2 port puts the REPL on USB by default. UART pads cannot recover an erased or broken flash.
4. Real recovery paths: USB D+ / D- pads (plus BOOTSEL and RUN), and SWD pads (SWCLK, SWDIO) with a debug probe and OpenOCD.

Evidence:
- RP2040 boot ROM source, `bootrom/bootrom_main.c`, function `main()`: it samples the QSPI CSn strap 9 times, calls `_flash_boot()` on a majority high, and otherwise calls `_usb_boot()`. There is no other path. https://github.com/raspberrypi/pico-bootrom-rp2040/blob/master/bootrom/bootrom_main.c
- UART boot is a new RP2350 feature, not in the RP2040: https://hackaday.com/2025/05/11/exploring-the-rp2350s-uart-bootloader and https://pfister.dev/blog/2025/rp2350-uart-bl.html
- The RP2040 datasheet section 2.8 (Boot Sequence) lists only the bootrom, USB mass storage and USB PICOBOOT. datasheets.raspberrypi.com was not reachable from this session. The table of contents was seen through a search result only.

## 2. Recovery features for the board

| Feature | Recovers from | Needed on module carrier | Needed on bare chip |
|---|---|---|---|
| USB-C port | normal flashing, REPL | Use the module's own USB-C at the board edge | Yes, on the board |
| USB D+ / D- solder pads | broken USB-C connector | Only if the module exposes D+ / D-. UNVERIFIED. | Yes |
| BOOTSEL pad or button | bad firmware that hangs USB | Module has a BOOT button. Add a pad if it is covered. | Yes |
| RUN (reset) pad | hang | Module has RESET. Add a pad if covered. | Yes |
| SWD pads (SWCLK, SWDIO, GND) | anything, including a bad flash | Only if the module exposes SWD. UNVERIFIED. | Yes |
| UART pads | REPL access only | Optional | Optional |
| Safe-boot strap (GPIO to GND at boot skips main.py) | main.py crash loop | Firmware feature, not built yet | same |

## 3. Module carrier versus bare RP2040

| Item | Carrier for RP2040-Zero | Bare RP2040 |
|---|---|---|
| RP2040 package | already soldered on the module | QFN-56, 7 x 7 mm, 0.4 mm pitch. Needs JLCPCB assembly. |
| Flash, crystal, 3V3 regulator, USB-C, buttons | on the module | must be designed in |
| Home-etch variant | possible. Edge pads are on a 2.54 mm grid. | not possible. Pitch too fine, needs vias under the chip. |
| MicroPython build | same board as today | needs the matching board definition |
| Recovery pads | limited to what the module exposes | all of them |
| Risk | low | high for a first board |

Recommendation: carrier for the RP2040-Zero for the first JLCPCB board and for home etch. Bare RP2040 as a later fab-only revision, after path A/B/C is settled. Decision is Alex's.

Note: the RP2040-Zero pad map must be confirmed against the silkscreen before the footprint is drawn. See `docs/OPEN_ITEMS.md` item 1.

## 4. 3V3 budget

- JC02: 100 mW at 3.3V, about 30 mA average (manual). Peak at laser fire not given. Supply range 3.3V to 3.8V.
- The RP2040-Zero regulator part and spare current are UNVERIFIED. Waveshare wiki was not reachable from this session.
- The brownout without the 470uF cap shows a large inrush or pulse load on the module's 3V3.
- Option for the carrier: a separate 3.3V LDO from the 5V BEC for the JC02, with its own bulk cap, plus the high-side P-MOSFET switch from the handoff. GP2 keeps the Power ON line. The 470uF cap stays on the RP2040 3V3 pad per the project rule. Part numbers: blank, Alex to choose.

## 5. Questions that block layout

1. Branding: name and logo on the silkscreen.
2. Module carrier or bare chip.
3. Pad map confirmation for GP8 and GP14, and bottom row order.
4. Does the RP2040-Zero expose USB D+/D- and SWD pads? Photo of the back side, or Waveshare wiki access for this session.
