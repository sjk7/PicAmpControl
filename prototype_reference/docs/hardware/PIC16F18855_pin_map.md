# PIC16F18855 – not used

This device is **not used by this project**, and this file deliberately no longer carries a
pin table.

It previously held a stale duplicate of the PIC16F18875 pin map (28-pin SPDIP, I2C LCD
backpack, LPF band-decoder bits on RA4/RA6/RA7). Duplicating the pin map is what let the
band-select, LCD, and comparator-reset assignments drift apart across the docs.

Single source of truth for MCU pin assignments:

- [PIC16F18875_pin_map.md](PIC16F18875_pin_map.md) — human-readable authoritative table
- [../../firmware/include/pin_map.h](../../firmware/include/pin_map.h) — the code that must agree with it

Historical context for superseded designs belongs in `prototype_reference/`, not in `docs/`.
