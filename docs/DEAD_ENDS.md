# DEAD_ENDS.md

Approaches that failed or must not be retried, with the reason.

| Date | Approach | Why it is a dead end |
|---|---|---|
| before 2026-11-13 | Powering the JC02 through GP2 without the 470uF cap on 3V3 | RP2040-Zero browns out and resets when the module powers up. Cap is required. |
| before 2026-11-13 | CRC8 with polynomial 0x07 for RunCam packets | Wrong polynomial, seen in a community example. Use DVB-S2, 0xD5. |
| before 2026-11-13 | Plain fetch of the youdao protocol link | Page is JavaScript-rendered. Text copy is in `docs/reference/`. |
| 2026-11-13 | UART flashing or UART recovery of the RP2040 | Boot ROM has no UART boot (flash or USB only). UART pads give REPL access only. See `docs/PCB_RESEARCH.md`. |
| 2026-11-13 | Fetching datasheets.raspberrypi.com, waveshare.com, analog.com from the cloud session | Hosts blocked by the session network policy. Use GitHub sources or ask Alex to allow the hosts. |
