# Bug Fixes Log

Tracks bugs found in this codebase (via code review, refactors, or testing) along with
the fix applied. Newest entries at the top. This file is maintained going forward as
part of normal development, not just during large refactors.

## 2026-09-12 — Added ADC acquisition delay after channel switch

Per the timing-budget review in docs/hardware/bench-validation.md, the ADC ISR in
`firmware/src/main.c` switched `ADPCH` to the next channel and immediately set
`GO_nDONE = 1`, with no settling time for the sample-and-hold capacitor to charge to
the newly-selected channel's voltage - a real accuracy risk depending on each
detector's source impedance.
Fix: added `ADC_ACQUISITION_US` (5 us, a common conservative industry baseline -
bench-confirm against the datasheet's acquisition-time formula for the actual
detector source impedances) as an explicit `__delay_us()` between the `ADPCH` change
and `GO_nDONE = 1`, both in the round-robin ISR and the one-time kick-off in
`adc_init()`. The delay runs inside the ISR itself, so it briefly (5 us) delays
servicing of other pending interrupts - negligible next to the 1 ms Timer0 tick.
Per-channel time goes from ~11 us to ~16 us (round-robin staleness bound ~88 us ->
~128 us), still far below the LCD-queue-drain latency addressed in the entry below.

## 2026-09-12 — LCD writes made non-blocking (queued, drained a few bytes per loop pass)

Per the reaction-time budget in docs/hardware/bench-validation.md, the bit-banged LCD
write was the dominant source of protection-loop latency: a full page redraw was
~13 ms of blocking bit-banging, during which `update_protection_state()` could not
run, so a fault occurring mid-redraw wasn't acted on until the LCD transaction
finished.
Fix: `lcd_write_byte()` in `firmware/src/lcd_i2c.c` now enqueues into a 56-entry ring
buffer (sized for the worst case: the TRIP screen with every fault reason set at
once, 49 bytes) instead of transmitting immediately. The main loop drains it via the
new `lcd_service(2)` (2 bytes/pass) after `update_protection_state()` has already run
that pass. The actual I2C bit-banging moved to `lcd_write_byte_now()`, used directly
by `lcd_init()`'s one-time startup sequence and by the "Clear Display" command on a
real page/state transition (both have their own real timing requirements and stay
synchronous; the queue is flushed first so ordering can't be disturbed). Rendering
code (`lcd_write_text`, `lcd_write_unsigned`, etc.) is unchanged - only *when* each
byte physically goes out changed, not what gets displayed. Worst-case gap between
consecutive `update_protection_state()` calls due to the LCD dropped from ~13 ms to
~0.8 ms (2 queued bytes), or ~2 ms including an occasional page-transition clear.

## 2026-09-12 — TRIP state/display cleared before the PTT re-arm, not only on it

`update_protection_state()` in [firmware/src/main.c](firmware/src/main.c) recomputed
`any_trip_fault` from live sensor readings every loop and unconditionally set
`g_state = STATE_OPERATE` the instant that reading looked clear - with no check of
`g_fault_latched`. Only `handle_ptt_transition()`'s PTT key-down path actually clears
`g_fault_latched`/`g_trip_reason`. Net effect: the TRIP screen (and `g_state`) could
silently revert to a normal STATUS screen as soon as the offending condition itself
cleared (e.g. forward power decays after unkeying), well before any new PTT keydown,
even though the fault was still latched underneath. TX sequencing itself was never
unsafe - `update_tx_sequence()` independently gates on `g_fault_latched`, not
`g_state` - but the operator-facing display didn't reflect the real latched state.
Fix: when the live condition clears but `g_fault_latched` is still true,
`update_protection_state()` now keeps `g_state = STATE_TRIP` (and the trip output
active) until the next PTT re-arm edge actually clears the latch via
`clear_fault_latches()`, matching the documented "latched until conditions are safe
and the system is re-armed" rule.

## 2026-09-12 — Remaining LCD flicker: config pages still cleared on every rapid-adjust redraw

The earlier flicker fix only skipped the LCD clear for STATUS/POWER_TEMPERATURE/TRIP.
Every other menu/config page still cleared on every redraw, and holding the ADJUST
button auto-repeats a value change (and a redraw) roughly every 100 ms - so a held
adjustment flickered exactly like the original bug did. Several of those pages also
printed numeric fields with no fixed width (`SWR full-scale`, `overdrive`, `temp
trip`, `drain trip`, `current trip`, both delay pages, `PEP decay`, and the `HIGH`/
`LOW` boolean fields), so simply skipping their clear would have left stale digits
behind when a value shrank (e.g. "100" -> "9" leaving a trailing stale "0").
Fix: the clear now only fires on an actual screen (page/state) change, for every
page, not just the three live ones; added `lcd_write_unsigned_padded()` and applied
fixed-width formatting to every previously-unpadded field so an in-place redraw is
always safe. `"LOW"` is now written as `"LOW "` (trailing space) to match `"HIGH"`'s
width.

## 2026-09-12 — STATUS page: live SWR readout, bar now tracks the selected power mode

Two follow-ups to the STATUS page requested after the PEP/RMS-label fix below:

1. The power bar on row 1 always used the PEP value (`g_post_fwd_pep_w`) even when
   RMS mode was selected, so the bar and the number above it could disagree. Fixed:
   the bar now uses the same `power_w` (PEP or RMS, per `power_display_pep`) as the
   numeric reading.
2. Added a live SWR reading, right-justified on row 0 (`lcd_write_swr_right()`).
   `compute_swr_tenths()` derives it from the post-filter forward/reflected ADC
   samples using the standard power-based relation
   `SWR = (1 + sqrt(Pr/Pf)) / (1 - sqrt(Pr/Pf))`, via a fixed-point integer square
   root (`isqrt32()`) since this part has no FPU. Display-only - trip logic still
   uses the existing threshold comparison in `swr_trip()`, unchanged.

Row 0 layout is now `P=nnnnW` or `R=nnnnW` (mode is now a single-letter prefix
instead of a trailing `" PEP"`/`" RMS"`) followed by right-justified `SWR=X.X`,
filling all 16 columns.

## 2026-09-12 — Dead "SWR=" label on the STATUS page (found in review)

The STATUS page in `show_menu_page()` printed `"P=<power>W SWR="` on row 0, but no
SWR value was ever written after the label - it was leftover/incomplete text with no
basis in the documented design (docs/project-architecture.md only specifies power +
a PEP bar for this page). Computing a live SWR ratio from raw ADC counts needs a
square-root approximation with no FPU on this part, which is new numeric code in a
safety-relevant display path and out of scope for a text-label cleanup.
Fix: replaced the dead label with `" PEP"`/`" RMS"`, reusing the already-available
`power_display_pep` flag so the row now tells the operator which reading mode they're
looking at instead of showing an unfulfilled promise of a value. (Superseded by the
entry above, which adds the actual SWR value.)

## 2026-09-12 — LCD full-clear on every refresh caused flicker (found in review)

`show_menu_page()` in [firmware/src/main.c](firmware/src/main.c) unconditionally sent
the HD44780 "Clear Display" command (`0x01`) plus a 2 ms delay on every call. The
STATUS and POWER/TEMPERATURE pages are redrawn every 100 ms during normal operation,
and the TRIP screen was redrawn identically every 100 ms while latched, so the
display blanked and repainted at ~10 Hz - a visible flicker on real hardware, worst on
the continuously-updating PEP bar.
Fix: track the last-drawn (menu page, state, trip reason) and only send the clear
command when that identity actually changes. Live pages now update their
fixed-width fields in place each refresh; the temperature field on the
POWER/TEMPERATURE page was also space-padded to a fixed 3 digits so no stale digit
can be left behind now that the clear is skipped between refreshes. Config/setting
pages keep the previous clear-per-change behavior since they only redraw on an
actual button press, not a timer.

Also added, as related usability fixes:
- an 8 s menu-inactivity timeout that returns the display to STATUS from any config
  page (`MENU_IDLE_TIMEOUT_MS` in `poll_menu_inputs()`), and
- forcing the display back to STATUS the instant PTT is asserted
  (`handle_ptt_transition()`), so an operator can't key up onto a frozen config page.

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
