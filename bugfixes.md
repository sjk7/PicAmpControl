# Bug Fixes Log

Tracks bugs found in this codebase (via code review, refactors, or testing) along with
the fix applied. Newest entries at the top. This file is maintained going forward as
part of normal development, not just during large refactors.

## 2026-09-21 — Docs still described the removed EasyEDA/KiCad schematic automation

Commit `90c7bf7` deleted the whole schematic-automation pipeline (generators, `.kicad_sch`
artifacts, `node_modules`, `package.json`, the KiCad MCP skill setup) but left the documents that
described it, so the repo advertised a workflow with no files behind it:

- `docs/hardware/SCHEMATIC_WORKFLOW.md` documented an EasyEDA pipeline (`easyeda_pro_generator.py`,
  `svg_renderer.py`, `visual_validator.py`, `watch_and_render.py`, `pic_amp_control_full.yaml`,
  `out/picampcontrol_easyeda_*.json`) whose scripts no longer exist, plus three EasyEDA integration
  routes (`easyeda-agent` CLI, the `easyeda-copilot` MCP server, a custom `.eext` extension) that
  were themselves the abandoned approach.
- Three other files still pointed at removed targets: `README.md` linked the workflow doc,
  `AI-HANDOFF.md` listed it as the schematic reference and told the next session to read
  `docs/hardware/schematic-workflow.md` and run `tools/setup_schematic_skill.ps1` (neither exists),
  and `project_schematic_package/README.md` referenced a `schematic-design` MCP skill,
  `mcp-server-kicad`, `.vscode/mcp.json`, a `generated/` tree and a `_SCHEMATIC_TEMPLATE.kicad_sch`
  that are all absent.

Fixed by deleting the workflow document and repointing the survivors: the schematic package is now
described as what it actually is - static design inputs (block diagram, connection table, component
list, wiring checklist) captured by hand, with no automated path to a schematic file.

## 2026-09-21 — Releasing PTT during sequencer stage 2 left TX_VCC asserted and unlocked the band

Found by the new first-dit proof (`tools/simulate/test_first_dit.py`) the first time it released
PTT while the sequencer was in stage 2: TX and TX_VCC up, bias still ramping.

`update_tx_sequence()` had a release branch for stage 3 (the normal path) plus a separate one for
stage 2 that jumped straight to stage 5:

```c
} else if (g_sequence_stage == 2) {
    set_tx_output(false);
    g_sequence_elapsed_ms = 0;
    g_sequence_stage = 5;
}
```

Stage 5 only removes the bias, so a release in that window never turned TX_VCC off: the drain
supply stayed asserted for the rest of the receive period, and stage 5's completion then unlocked
the band, letting the LPF relays follow live RF with TX_VCC still on. An operator releasing PTT
within ~20 ms of keying hits this, and the reachable window is exactly the `tx_bias_delay_ms`
setting (20 ms by default).

Fixed by unwinding stage 2 through the same ordered path as stage 3 (TX relay first, TX_VCC after
the VCC delay, then TX_BIAS), and by adding `release_band_if_cold()`, which releases the band only
once every TX output is confirmed inactive. The first-dit test asserts the release ends cold with
the band released, and the defect was re-introduced to confirm the test fails on it:
`clause (c): the stage-2 release left a TX output asserted`.

## 2026-09-21 — Simulator suite modelled RF backwards: silent while transmitting, present while receiving

`trace_ptt_sequence.py` injected the 40m Timer1 counts only in the pre-PTT preflight. Because the
firmware resets TMR1 every 10 ms tick, the measurement went stale the moment the preflight ended,
so `g_fc_status.frequency_khz` was already 0 when PTT was asserted.

The old firmware hid this: its assert-time `freq_counter_signal_valid()` check happened to land on
a tick that still held the injected value, and the scenario only passed because of that timing. It
is also physically inverted — a real radio is silent while receiving and transmits once PTT is
asserted — and under the first-dit model the stale measurement correctly leaves the amplifier in
bypass-snoop, so the baseline scenario never reached TX.

The harness now keeps the 40m snoop signal present for the whole keyed window. That models a real
transmission, and it means the baseline scenario now exercises the first-dit decode-and-engage path
instead of relying on pre-PTT RF leakage.

## 2026-09-21 — Band-selection invariants found the amplifier keying on the 160 m no-signal default

The new I1-I5 invariants (checked over every suite scenario) failed the TEMPERATURE scenario:
after the thermal trip cleared, the relay selection had followed live RF while unlocked, and with
no measurement present the classifier reported its no-signal default (160m). Stage 0 then locked
whatever `current_band` happened to hold, so the amplifier keyed on the 160 m filter while the
radio was on 40 m. Old firmware had the same hole (it refused PTT only when no band was known *at
the assertion*, which is not the recovery path).

Fixed by gating keying on an established band: `g_band_established` is set by a live confirmed
measurement, by the first-dit memory, or by the snoop decode, and is invalidated on PTT release,
at startup and on a trip recovery (which is the only mid-over path that frees the relay
selection). Stage 0 now enters bypass-snoop instead of keying when no band is established.

The harness had to model reality for this: the operator keeps the key down through a thermal
cycle, so `TEMPERATURE` now holds the 40m snoop signal present throughout (see the next entry for
why a single injection per long step was not enough).

## 2026-09-21 — Sampling aliased with the frequency-counter tick (FREQ_CTR passed standalone, failed in the suite)

`FREQ_CTR` passed on its own but failed inside the merged suite with `80m TX lock failed while
injecting 1800 kHz`. The firmware resets TMR1 on every 10 ms tick, and the harness sampled on
10 ms boundaries, so when the two aliased the samples *always* landed before the tick that
consumed the injected count - the injected reading was never observed, and the assertion failed
on a stimulus artefact. Standalone runs happened to start at a favourable phase; the suite did
not.

Fixed by sampling injected counts at 5 ms (every tick window then contains a post-tick sample) and
by adding `inject_step_hold()`, which re-injects before each 5 ms chunk inside long steps instead
of injecting once at the start of a 50 ms step.

## 2026-09-21 — Band/frequency-counter tests were weaker than their labels; Timer1 external clock is not modelled

Audited the band/frequency-counter tests in `tools/simulate/trace_ptt_sequence.py` against the
firmware. The core assertions were genuine (the injected counts invert the firmware's own
scaling, and the TX-lock check injects a different band while asserting the band did not
move), but four gaps meant they did not do exactly what they claimed.

- **The band-select outputs were never observed.** `PINS` sampled only RC0/RC1/RC5/RC6/RC7, so
  "each band stayed locked during TX" was verified only through the internal
  `g_fc_status.current_band` variable. A regression in `update_band_outputs()` would have
  passed. RD2-RD7 are now sampled and `validate_band_outputs()` asserts the relay selection
  matches `current_band` (and that nothing is driven when out of spec).
- **`--quick-bands` made the lock assertion vacuous.** It reduced `BAND_TESTS` to one entry, and
  the "inject the next band's frequency" scheme then injected the *same* frequency, which
  cannot detect a failure to freeze. Injection now always picks a frequency different from the
  band under test.
- **`FREQ_CTR_FAIL` never proved PTT was asserted.** It asserted `g_ptt_active` was never true
  but never that RC0 was driven low, so a silent pin-write failure would have passed. It now
  requires an observed RC0 low.
- **The 10m case was not a real 10m frequency.** It used 25000 kHz, outside the documented 10m
  range (28000-29700 kHz); it only passed because the classifier's accept window is wider. A
  true 10m frequency needs 70000-74250 Timer1 counts, beyond the single 16-bit `TMR1` write the
  harness performs, so the limitation is now documented instead of hidden.

End-to-end counter testing is impossible in simulation, and that is now verified rather than
assumed. MDB does provide a stimulus facility that was not being used — `stim <file>.scl`
(SCL, documented in the MPLAB X install under `docs/SCL_Users_Guide`) — and SCL processes do
run during `Stepi`. But the simulator does not implement Timer1's external clock:

```text
W0106-SIM: This device only has partial support for TMR1 peripheral.
Use internal oscillator as timer clock slection is not implemented
```

Measured with an SCL stimulus driving RD1 as fast as the simulator can represent: `print pin
RD1` reported `HIGH`/`Din` (the pin really was driven) and `T1CON` read `0x27` (CS=T1CKI,
CKPS=1:4), yet `TMR1L`/`TMR1H` and `g_tmr1_overflows` stayed `0`. Register injection is
therefore the only option. It covers the frequency maths, band classification, band-select
outputs and TX lock, but not the T1CKI pin, PPS routing, the 1:4 prescaler, or the Timer1
overflow path — those need bench validation.

Related gotcha recorded for future use: SCL pin/SFR assignment uses `<=` (`:=` is for user
variables). `RD1 = '1';` parses but derails the simulator with
`E0101-SIM: Failed to disassemble instruction`.

Verified: `ctest` passes 1/1 in 130 s with all 11 scenarios green, including the new
band-select and PTT-asserted assertions.

## 2026-09-21 — Pin/net assignments were duplicated across the docs and had drifted (single source of truth established)

The same pin and net assignments were restated in at least eight documents, and they no longer
agreed with each other or with `pin_map.h`. This is the underlying cause of the individual doc
bugs fixed earlier today.

- `docs/hardware/PIC16F18855_pin_map.md` was a **misnamed stale duplicate** of the 18875 pin
  map (28-pin SPDIP, I2C LCD backpack, LPF band-decoder bits on RA4/RA6/RA7), and nothing
  linked to it.
- `docs/hardware/wiring-checklist.md` duplicated the entire pin map and contradicted the
  firmware: it claimed a 3.3 V supply, listed RD1–RD7 and RB2/RB3 as "NC / reserved for future
  use", and proposed RA4/RA6/RA7 as future band-select pins — those are the parallel LCD lines.
- `project_schematic_package/connection_table.md` restated the netlist that already existed in
  `connection_table.csv`.
- README, `project-architecture.md`, `section_breakdown.md`, `block_diagram.md`, and the
  package `wiring_checklist.md` each restated pin assignments too.
- `AI-HANDOFF.md` claimed "RA4 and RA6 are available for future band selection" (wrong) and
  linked a `schematic-workflow.md` that does not exist.

Fix — single source of truth treatment:

- `docs/hardware/PIC16F18875_pin_map.md` is now explicitly the one authoritative pin table, and
  must agree with `firmware/include/pin_map.h`.
- `project_schematic_package/connection_table.csv` is the one authoritative netlist;
  `connection_table.md` became a short usage/conventions page instead of a second netlist.
- The misnamed duplicate was replaced with a short "not used" pointer, and
  `docs/hardware/wiring-checklist.md` was rewritten as wiring guidance that refers to signals
  rather than pins.
- README, architecture, block diagram, section breakdown, and both checklists now link to the
  pin map instead of restating it.
- Band selection and lockout are now documented in the block diagram, the architecture doc, and
  the README flow model, following the removal of the 74HC4514 decoder in favour of one
  dedicated output per band.

Rule recorded in `Ai-Notes.txt`: never restate pin numbers or pin tables outside the pin map.

## 2026-09-21 — `ctest` could not run the simulator suite (Python 2 binding + non-portable `timeout`)

`ctest` reported 0/1 passed (exit 8) on a clean checkout. `user.cmake` used
`find_program(PYTHON_EXECUTABLE NAMES python python3 REQUIRED)`, which resolved to
`/Library/Frameworks/Python.framework/Versions/2.7/bin/python`. The suite is Python 3
only, and that interpreter is an Intel-only binary on this Apple Silicon host, so the
test died before starting:

```text
timeout: failed to run command '.../Versions/2.7/bin/python': Bad CPU type in executable
```

The registration also wrapped the test in GNU `timeout`, which is not part of macOS.

Fix in `cmake/My_Pic_Project/default/user.cmake`:

- search `NAMES python3 python` and verify `sys.version_info[0] == 3` at configure time,
  so a Python 2 interpreter fails configuration with an actionable message instead of
  failing the test at run time;
- run the suite through `tools/simulate/run_suite_with_watchdog.py` (owns the MDB
  process group, cleans up stale runs, own timeout, progress logs) instead of invoking
  `trace_ptt_sequence.py --suite` under the external `timeout` binary.

`PYTHON_EXECUTABLE` is cached, so an existing build directory must be reconfigured with
`-U PYTHON_EXECUTABLE` to pick up the change.

## 2026-09-21 — README, TESTING.md, and the pin-map doc were out of sync with the current hardware and test scheme

Found while bringing `ctest` back to green.

- README described the superseded LCD and band-select scheme: a PCF8574 I2C backpack on
  RC3/RC4, and a band-decoder bus on RA4/RA6/RA7/RB6. `pin_map.h` actually drives a 4-bit
  **parallel** LCD (RS=RA4, E=RA6, D4=RA7, D5=RC3, D6=RC4, D7=RD0) and one dedicated
  active-high band-select output per band on RD2-RD7. README also linked
  `firmware/src/lcd_i2c.c`, `docs/hardware/lpf-band-select-netlist.md`,
  `docs/hardware/lpf_band_decoder.kicad_sch`, and `docs/hardware/schematic-workflow.md` —
  none of which exist.
- README claimed a self-hosted Windows x64 runner and manual-only releases.
  `firmware-build.yml` runs on `ubuntu-latest` and installs XC8/DFP itself, and
  `auto-release.yml` tags and publishes a release automatically after a successful `main`
  build.
- TESTING.md listed a non-existent `PTT_FrequencyCounter_BandLock` test, said the suite
  builds the firmware itself, documented trace PNG filenames that are never produced, and
  claimed the simulator tests run in CI on a runner with MPLAB X installed via apt. They do
  not run in CI at all.
- `docs/hardware/PIC16F18875_pin_map.md` described `OUTPUT_COMP_RESET` as an active-high
  pulse. `main.c` idles it high and drives it low for the reset/settle window
  (`apply_startup_inhibit`, `start_comparator_reset`), so it is active-low.

Fix: README now defers to the canonical pin map instead of duplicating a stale copy that
had already drifted, the dead links were replaced with real ones, TESTING.md was rewritten
to the current CTest + watchdog scheme, and the pin-map polarity note was corrected.

## 2026-09-20 — Hardware pin-map doc and sim tests out of sync with actual pinout

`docs/hardware/PIC16F18875_pin_map.md` claimed RA4/RA6/RA7 and RB2/RB3 were free,
but `pin_map.h`/`lcd_parallel.c` actually use RA4/RA6/RA7/RC3/RC4/RD0 for the
parallel LCD and RB2/RB3 for ADC_OVERDRIVE/ADC_DRAIN_PEAK (ANSELB=0x0E). Also fixed
a stale comment in `lcd_parallel.c` (said D5/D6 were RB2/RB3) and in `main.c`'s
`adc_init()` (said RA4 was reserved for an LPF band-select bus it no longer drives).
Doc now lists the true free pins: RD2-RD7, RE0/RE2/RE3 (9 pins).

Separately, `tools/simulate/test_freq_counter.py` never worked: it stimulated the
Timer1 external clock input (RD1/T1CKI) with a static pin voltage, which produces
no clock edges, so frequency_khz stayed 0 and every band assertion failed. Fixed by
writing TMR1H/TMR1L directly (same technique as trace_ptt_sequence.py's FREQ_CTR
scenario) and extending the post-release window so the relay/VCC/bias shutdown
sequence has time to complete before the band unlocks and reclassifies.

Also: `run_mdb()` in both `trace_ptt_sequence.py` and `test_freq_counter.py`
inherited our controlling terminal as stdin, so a killed/hung mdb+JVM process
could leave the shell in raw mode (looked like the terminal was "broken", e.g.
`ls` producing no visible output). Fixed by using `stdin=DEVNULL` +
`start_new_session=True` and killing the whole process group on timeout.

## 2026-09-18 — Front-panel menu now uses a single EC11 rotary encoder

The two-switch menu model became awkward as the normal display pages and saved
settings grew. It also did not match the selected front-panel actuator. Fix: the
firmware now treats RC2/RB0/RB6 as EC11 encoder A/B/push inputs. Rotation selects
normal display pages or edits the active setting, short press enters/advances
settings, and long press exits settings or clears a trip latch. RB6 was freed by
reducing the LPF band decoder bus to the required 3 bits; OFF plus seven bands fit
in codes 0-7, so the external decoder's fourth address input is tied low.

## 2026-09-18 — Peak displays now hold briefly, then decay smoothly

The PEP and current-meter pages are likely operator home pages, but the previous
peak behavior decayed by one display unit per configured interval with no explicit
hold. At the old 500 ms default this made PEP linger for minutes; at short intervals
it still looked mechanically linear. Fix: both peak displays now hold the captured
peak for the configured peak-hold interval, then decay by about 3% per configured
peak-decay interval with a minimum one-unit step. Both settings are stored in the
versioned EEPROM record. The default home page is now the PEP/temperature display;
factory defaults are 1.2 s hold and 100 ms decay interval.

## 2026-09-18 — Normal SWR displays use the available second decimal place

The STATUS and SWR meter pages had enough 16x2 LCD space for `SWR=1.02`, but the
display path rounded live SWR to tenths and left the top-right STATUS cell blank.
Fix: the display-only SWR calculation now carries hundredths, and the normal/trip
SWR render helper prints two fractional digits. Trip thresholds and trip decisions
remain in tenths and keep using the existing integer threshold comparison.

## 2026-09-18 — ADC trip sources now share the fastest bounded scan cadence

SWR/current/drain/temperature ADC faults were not all refreshed at the same rate:
the ADC scheduler gave overdrive an alternating priority slot while every other
trip channel waited on the slower round-robin path. That made non-overdrive trips
slower to observe than necessary once the expensive RF chain was already in TX.
Fix: the scheduler now advances through all eight ADC protection channels once per
1 ms tick, giving every ADC-based trip source the same ~8 ms maximum sample-age
bound. The trip logic still latches immediately once a trip-worthy sample is seen;
the change removes the unequal pre-trip sampling delay.

## 2026-09-15 — ADC ISR self-re-arm starved the main loop of CPU time

Found via MPLAB X simulation (see Ai-Notes.txt "Simulation" section): with PTT
asserted and no faults present, `update_tx_sequence()`/`update_protection_state()`
never ran even once after 30+ simulated seconds - the CPU was always caught inside
the interrupt vector on `Halt`, and the debug console was flooded with continuous
`W0223-ADC` underflow warnings. Root cause: `timer0_isr()`'s ADC branch (added in the
2026-09-12 entry below) immediately re-armed the next conversion
(`ADCON0bits.GO_nDONE = 1`) right after each conversion completed, with a blocking
`__delay_us(ADC_ACQUISITION_US)` in between - all from inside the ISR. This created a
back-to-back interrupt chain with no guaranteed idle time for the main loop between
conversions.
Fix: the ADC branch of `timer0_isr()` now only captures the completed sample and
selects the next channel; it no longer calls `__delay_us()` or re-arms the
conversion. Re-arming (`GO_nDONE = 1`) now happens only once per Timer0 tick
(~1 ms), gated by a new `tick` flag set from the `TMR0IF` branch. This paces the
8-channel scan to a full cycle every ~8 ms (still fast enough for this application)
and guarantees the main loop gets to run for the bulk of each 1 ms tick period
between conversions, regardless of how fast the ADC itself completes. Also removed
the now-redundant acquisition delay's dependency on the ISR: the ~1 ms natural gap
between ticks is vastly longer than the 5 us settle time it replaced, so no
functional accuracy regression versus the 2026-09-12 fix.
Verified via `tools/simulate/run_sim.ps1`: main-loop breakpoints (e.g.
`update_protection_state`) now hit normally and the PC advances through real code
between `Halt`s, instead of being stuck at the interrupt vector.

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
   The display-only SWR calculation derives it from the post-filter forward/reflected ADC
   samples using the standard power-based relation
   `SWR = (1 + sqrt(Pr/Pf)) / (1 - sqrt(Pr/Pf))`, via a fixed-point integer square
   root (`isqrt32()`) since this part has no FPU. Display-only - trip logic still
   uses the existing threshold comparison in `swr_trip()`, unchanged.

Row 0 layout is now `P=nnnnW` or `R=nnnnW` (mode is now a single-letter prefix
instead of a trailing `" PEP"`/`" RMS"`) followed by right-justified `SWR=X.XX`,
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
   further down in the setting-adjust path was unreachable dead code for this page.
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
