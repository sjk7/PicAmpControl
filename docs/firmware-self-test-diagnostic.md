# Firmware self-test diagnostic (session setup)

Date: 2026-09-26 · Status: IMPLEMENTED (verified in the simulator 2026-09-26)

This file is the launch point for the session that adds a **firmware-only diagnostic self-test**:
as much of the board as the PIC can verify on its own, with no simulator, no harness and no RF.

The diagnostic is now implemented and wired end-to-end: `diag_selftest_request()` / `diag_selftest_tick()`
in `firmware/src/main.c`, the `MENU_PAGE_SELF_TEST` live menu page (encoder short-press runs it, only
while cold), the `SELF_TEST_DIAG` suite scenario in `tools/simulate/trace_ptt_sequence.py` (which reads
the firmware's own `g_diag_result` verdict, never re-derives it), and the `g_diag_*` globals published
for the simulator. Verified 2026-09-26: `--test suite --only SELF_TEST_DIAG` passes — verdict `0x08`
(EEPROM bit, the one check the simulator cannot model), outputs/sequencer/LCD green, amplifier cold.

## Why this exists

The TX self-test (`tx_selftest_run()` in `firmware/src/main.c`) is a **runtime** check: it runs on
every keydown/unkey and verifies the band lock, the `SENSE_*` output read-backs and the stage
progress. It is already fully firmware-resident and needs no trigger.

What it cannot do is prove the board **before** or **without** a transmission, and it cannot drive
its own fault injection (a bad band or a stuck relay must come from the outside). The goal of this
piece of work is the part that CAN be self-driven:

- the TX / TX_VCC / TX_BIAS / band-relay / fan / trip outputs actually reach their commanded levels
  (the firmware already reads them back through `PORT` via `SENSE_*`, so it can assert-and-verify);
- the sequencer walks 0 -> 1 -> 2 -> 3 -> 0 in order and each stage's outputs are correct;
- the LCD is alive (write a known pattern the operator confirms, or exercise the data bus);
- the settings EEPROM record round-trips (write, read back, checksum — `firmware/src/nvm.c` already
  has a versioned, checksummed record).

Out of scope (still needs a bench jig): anything fed by the frequency counter or an external
fault — out-of-spec RF, a genuinely stuck relay, a shorted sensor. Those are stimulus, not firmware.

## Design decisions to make in-session

1. **Trigger.** Pick one (or both):
   - **Power-on self-test (POST):** run a short version once at boot, inside the existing 1000 ms
     startup inhibit (`g_startup_inhibit`). Must finish well inside 1000 ms and must not delay the
     tick being armed (see `docs/keying-and-band-selection.md` "Why the tick is armed before the LCD").
   - **Menu diagnostic:** a new `MENU_PAGE` (e.g. `MENU_PAGE_SELF_TEST`) reached from the existing
     menu, which runs the checks and reports PASS/FAIL per item on the LCD. This is the one the
     operator can run at will; prefer it if the POST budget is tight.
2. **Report.** Each check writes its result to a 16x2 LCD line pair and a bit-mask result global the
   simulator/debugger can read (same convention as `g_selftest_reason`). Name every check so a
   failure is readable on the bench with no harness attached — same rule as the trip and self-test
   screens.
3. **Safety.** The diagnostic toggles real outputs. It must only run when the amplifier is **cold**
   (`!g_ptt_active`, not keyed, startup inhibit still active or an explicit bypass state), and must
   force bypass before and after, so a diagnostic can never key the LDMOS. Reuse `apply_bypass()`.

## Where the code lives

- `firmware/src/main.c` — the diagnostic (or a new `firmware/src/self_test.c` + header if it grows),
  the menu page entry, the `MENU_PAGE` enum/table, the `show_menu_page()` result screen.
- `firmware/include/pin_map.h` — the `SENSE_*` macros already provide the read-back; verify each
  output has one (TX, TX_VCC, TX_BIAS do; check fan/trip/band relays).
- `firmware/src/nvm.c` — reuse the existing record read/write/checksum for the EEPROM round-trip.
- `tools/simulate/render_lcd_lifecycle_diagram.py` — its `SETTINGS_PANELS` is coupled to the menu
  labels; a new menu page means updating that list too.
- Harness: `tools/simulate/trace_ptt_sequence.py` — add a scenario (or a standalone probe) that
  drives the trigger and asserts the firmware's own PASS/FAIL mask, same "the firmware decides, the
  harness reads the verdict" contract as the TX self-test scenarios.

## Acceptance criteria

- ✅ Firmware-only: with just the PIC and the board, the operator can trigger the diagnostic and read
  each check's PASS/FAIL on the LCD. (Menu `SELF TEST` page → encoder short-press → `RUNNING...` →
  `PASS` or the `+`-joined failed check names.)
- ✅ A diagnostic can never leave an output asserted or key the amplifier when it finishes.
  (`diag_selftest_request()` forces bypass first and requires cold; `diag_selftest_tick()` re-forces
  bypass at the end.)
- ✅ The simulator proves it: build green, and `--test suite --only SELF_TEST_DIAG` passes through the
  watchdog wrapper (see `.github/skills/build-test/SKILL.md`).
- ✅ The output/`SENSE_*` loop and the sequencer walk prove a real defect fails them: the
  `SELF_TEST_DIAG_STUCK` scenario pins the TX output (RC5) to the wrong level, triggers the diagnostic,
  and asserts `g_diag_result & DIAG_OUTPUTS` — it reads back `0x0B` (`DIAG_OUTPUTS` | `DIAG_SEQUENCER`
  | `DIAG_EEPROM`), so a stuck output is flagged, not just a healthy board passing. The amplifier still
  ends cold. Run it via `--test suite --only SELF_TEST_DIAG_STUCK`. (Named without "fail": the
  diagnostic reporting a fault is the PASS condition here, not an error.)
- ✅ Docs updated: this file's status, `Ai-Notes.md`. (`docs/tx-sequencer.md` §9 is untouched — the
  runtime self-test did not change.)

## References

- Runtime TX self-test: `docs/tx-sequencer.md` §9, `docs/tx-self-test-plan.md`.
- Keying/timing and tick-before-LCD: `docs/keying-and-band-selection.md`.
- Output read-back rule (`SENSE_*` from `PORT`, writes via `LAT`):
  `.github/instructions/firmware.instructions.md`.
- Build/test method: `.github/skills/build-test/SKILL.md`.
