# Firmware refactor & menu-driven self-test — plan

Date: 2026-09-26 · Status: in progress

Goals (from the operator, `scratch.txt` + this session):
1. Firmware self-tests runnable at any time from the menu.
2. Each firmware test in its own function, callable all-together or individually via the menu.
3. Split the tests (and anything else) out of `firmware/src/main.c`, which is 2404 lines.
4. No file longer than ~500 lines; preferably a lot less.
5. Avoid the word "fail" in test/scenario names that exercise a failure (a passing "FAIL" test reads
   as an error).
6. A passing run's log must describe what was tested / expected / what happened, not just
   "no failure text to report".
7. The run log tab opens on every run (done 2026-09-26, absolute-path fix in `open_progress_log.py`).

## Phase 1 — harness naming + pass prose (no firmware change)
- [x] Rename `SELF_TEST_DIAG_FAIL` → `SELF_TEST_DIAG_STUCK` (harness scenario, validator, checks,
      suite list, band-invariant skip).
- [x] Append a per-scenario "what was tested / expected / observed" block to the log on PASS.

## Phase 2 — diagnostic self-test: own file + per-check functions + menu
- [x] Move the diagnostic self-test out of `main.c` into `firmware/src/self_test.c` + `self_test.h`.
- [x] Split the four checks into their own functions: `diag_outputs_step()`,
      `diag_sequencer_step()`, `diag_lcd_check()`, `diag_eeprom_check()` — each returns its own
      pass/fail bit via `g_diag_result`.
- [x] A driver that runs all four, plus a way to run one by index — both driven from the menu
      (`diag_start()` + `diag_select_cycle()` / `diag_selected_name()`).
- [x] Menu: `MENU_PAGE_SELF_TEST` rotate cycles ALL → OUTPUT → SEQ → LCD → EEPROM, press runs the
      selection; result shown on the LCD.

## Phase 3 — split the rest of `main.c` into ≤500-line modules
- [x] `outputs.c/h` — `output_level`, `set_tx/vcc/bias/fan/trip_output`, `apply_bypass`,
      `release_band_if_cold`, `invalidate_established_band`, plus `clear_fault_latches`,
      `start_comparator_reset`.
- [x] `tx_selftest.c/h` — `tx_selftest_*` (reason text, reset, apply, run).
- [x] `labels.c/h` — `trip_reason_name`, `sequence_stage_name`, `band_name`, name tables.
- [x] `lcd_format.c/h` — `lcd_write_spaces/_unsigned_padded/_power_bar/_swr_right/_swr_value`.
- [x] `settings.c/h` — settings record load/save/checksum/dirty/service.
- [x] `menu.c/h` — `show_menu_page`, `show_boot_message`, encoder/page/step handlers,
      `poll_menu_inputs`, `is_live_menu_page`.
- [x] `protection.c/h` — SWR/measurement maths, `update_post_filter_power`, `update_peak_decay`,
      `update_protection_state`, `swr_trip`, `isqrt32`.
- [x] `sequencer.c/h` — `handle_ptt_transition`, `update_tx_sequence`.
- [x] `main.c` left as init + ISR + main loop + the `volatile` state globals, ≤500 lines.
- [x] `state.h` — the shared enums + `extern` state globals; definitions stay in `main.c`
      (one per symbol, names unchanged for the .sym-address harness contract).

## Phase 4 — verify + docs + commit
- [x] Build green (Release + sim).
- [x] Full suite green through the watchdog (16 scenarios incl. `SELF_TEST_DIAG_STUCK`).
- [ ] Update `docs/firmware-self-test-diagnostic.md`, `Ai-Notes.md`, `bugfixes.md` as needed.
- [ ] Commit + push each verified increment.
