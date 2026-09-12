# Bug Fixes Log

Tracks bugs found in this codebase (via code review, refactors, or testing) along with
the fix applied. Newest entries at the top. This file is maintained going forward as
part of normal development, not just during large refactors.

## 2026-09-12 — Found while removing the warning system (KISS refactor)

While rebuilding `g_menu_setting_offsets`/`g_menu_setting_types` in
[firmware/src/main.c](firmware/src/main.c) to drop the temperature/overdrive/drain
warning tiers, three pre-existing type-tag mismatches were discovered in the same
tables. These were latent bugs, unrelated to the warning-system removal itself, and
were fixed in the same commit since the tables had to be rewritten anyway.

1. **`current_trip_a` read/written as the wrong size.** The struct field was declared
   `unsigned char` but tagged `MENU_SETTING_U16` in the settings table, so the menu code
   read/wrote 2 bytes at a 1-byte field's offset — corrupting the low byte of the next
   struct field (`tx_vcc_delay_ms`) every time the CURRENT TRIP setting was adjusted.
   Fix: widened `current_trip_a` to `unsigned int` to match how it was actually accessed.

2. **`tx_bias_delay_ms` misclassified as `MENU_SETTING_BOOL`.** The struct field is
   `unsigned int` (a millisecond delay, 0-1000 ms), but its table entry was tagged BOOL.
   This meant pressing "increase" on the TX-BIAS DELAY menu page toggled the low byte
   of the delay value on/off instead of incrementing it — the intended 5 ms step logic
   further down in `adjust_selected_threshold()` was unreachable dead code for this page.
   Fix: retagged as `MENU_SETTING_U16`.

3. **`power_display_pep` misclassified as `MENU_SETTING_U8`.** The struct field is
   `bool`, but was tagged as a plain ranged 0-100 byte. Pressing "increase" repeatedly
   on the POWER DISPLAY menu page would count up past 1 instead of cleanly toggling
   PEP/RMS, requiring a long "decrease" hold to get back to RMS.
   Fix: retagged as `MENU_SETTING_BOOL`.

Also bumped `SETTINGS_VERSION` (4 -> 5) so EEPROM records saved by older firmware
(with the old struct layout) are rejected by the checksum/version check on next boot
and the new compiled defaults load cleanly, rather than misinterpreting old bytes
under the new field layout.
