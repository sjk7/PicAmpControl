# Plan: firmware TX self-test -> undefined/unkeyable state, with the reason on the LCD

Status: **not started** - written 2026-09-25 for the next session. Nothing in this plan has been
implemented.

## Goal

The firmware tests **itself** on every key-down (and continuously while keyed). When a self-check
fails it latches the UNDEFINED/UNKEYABLE state, opens the RF path, and reports the state **and its
reason** on the LCD. The harness then asserts the firmware's own verdict - the reason code and the
panel screen - instead of the simulator's aliased counter reading, which is the pacing sensitivity
that broke the FREQ_CTR check.

## Why

- **Protects the LDMOS.** A keyed amplifier must never keep transmitting on a band it can no longer
  vouch for.
- **Removes harness sensitivity.** The contract becomes a firmware reason code plus an LCD screen,
  not `g_fc_status.frequency_khz` in a model whose TMR1 is reset by every 10 ms gate.
- **Flash is ample.** The current image is 13886 B of 20000h bytes (~10.6%), so a few hundred bytes
  is not a budget problem.

## Foundations already in place (2026-09-25 session)

### `firmware/src/main.c`
- `trip_reason_t` enum, `TRIP_REASON_NAMES[]`, `trip_reason_name()` (~lines 130-165), priority ordered,
  names capped at `TRIP_REASON_NAME_MAX` (11) characters to fit one 16-column LCD line.
- `#define LOCK_LOSS_UNKEYABLE_MS 200U` (~199); `static volatile bool g_unkeyable` (~223);
  `static unsigned int g_lock_loss_ms`.
- Interlock block inside `update_tx_sequence()` under `if (g_ptt_active)` (~1508-1540): holds the
  interlock, then

  ```c
  g_unkeyable = true;
  apply_bypass();
  freq_counter_unlock_band();
  invalidate_established_band();
  g_sequence_stage = SEQ_IDLE;
  g_state = STATE_BYPASS_SNOOP;
  g_snoop_active = true;
  ```

- The interlock is cleared (`g_unkeyable = false; g_lock_loss_ms = 0;`) in the snoop-decode path and
  both verified-engage branches of `handle_ptt_transition()` (~1008, ~1047, ~1446).
- LCD precedence in the display function (~700-790):
  TRIP screen -> `g_unkeyable` (`STATE: LOCK LOST` / `UNKEYABLE`) -> PTT COMPLETE -> keyed stage screen
  -> status page -> home.
- Helpers available: `lcd_write_swr_value()` (~598), `lcd_write_unsigned()`, `sequence_stage_name()`,
  `band_name()`, `invalidate_established_band()` (~452).

### `firmware/src/freq_counter.c` / `firmware/include/freq_counter.h`
- `freq_counter_tick_10ms()`: samples TMR1, computes `frequency_khz`, classifies, tracks
  `candidate_band`/`stability_count`; returns early once `band_locked` (freezing `current_band` and the
  relay selection for the whole transmission).
- `freq_counter_measured_band()`: `BAND_OUT_OF_SPEC` when `stability_count < STABILITY_REQUIRED_TICKS`
  or the frequency is outside 1000-32000 kHz.
- `freq_counter_band_confirmed()`, `freq_counter_lock_band()`, `freq_counter_restore_locked_band()`,
  `freq_counter_unlock_band()`, `freq_counter_get_status()`.
- `freq_counter_status_t` already carries `raw_pulses` and `stability_count`, so the self-test needs no
  new accessor.

### Harness and tooling
- `tools/simulate/trace_ptt_sequence.py`: `STATE_VARS`, `truncate_at_unkeyable()`, `_scope_events()`
  (marks `UNKEYABLE flagged`), the suite loop (validates the whole scenario but renders the trace
  truncated at the flag), `validate_freq_ctr()` with the `locked_injection` check and the current
  unkeyable-contract assertion, `--only` / `--bands`.
- `tools/simulate/scope_trace.py`: `lcd_screen()` (mirrors the firmware precedence),
  `failure_lcd_state()`, `failure_prose()`, `add_top_time_axis()` (ms), `draw_stimulus()` shading and
  key, `_draw_failure_notes()`.
- `tools/simulate/run_suite_with_watchdog.py` is the only way a simulator run may be started; verdicts
  come from files, never from terminal output.
- Docs: `docs/tx-sequencer.md`, `TESTING.md`, `Ai-Notes.md`, `.github/skills/build-test/SKILL.md`.

## Steps

### Phase 1 - self-test core (`firmware/src/main.c`)
1. Add a `tx_selftest_reason_t` enum beside `trip_reason_t`, plus `TX_SELFTEST_NAMES[]` (each <= 11
   characters) and `tx_selftest_reason_name()` in the same style as `trip_reason_name()`, with the same
   "never blank on the panel" rule (unknown code -> `UNKNOWN`). Codes:
   - `OK`
   - `LOCK_LOST` - lock held, but no usable measurement backs it
   - `BAND_UNKNOWN` - measurement present but out of spec / outside 1000-32000 kHz
   - `BAND_CHANGED` - measured band differs from the locked band while keyed
   - `NO_RF` - raw count zero for the whole hold window
   - `NOT_LOCKED` - keyed with no band lock held
2. Add `static volatile bool g_selftest_failed;` and `static volatile unsigned char g_selftest_reason;`
   (volatile so the harness reads them directly), plus the per-check hold counters.
3. Add `static void tx_selftest_run(void)`, called from `update_tx_sequence()` right after
   `freq_counter_get_status(&lock_status)` while `g_ptt_active && g_sequence_stage >= SEQ_TX_ON`. It
   evaluates the checks every 10 ms tick, increments a consecutive-failure counter for the failing
   check, and latches `g_selftest_failed` plus that check's code on the first check to reach
   `LOCK_LOSS_UNKEYABLE_MS`.
4. Keep **one** timer: the existing 200 ms window *is* the self-test hold, so the interlock action stays
   a single code path.
5. A check that passes resets its own counter. `g_unkeyable` / `g_selftest_failed` are cleared only on a
   fresh **confirmed** decode or a verified engage - never on one good sample.

### Phase 2 - the undefined/unkeyable action and the LCD
6. Replace the ad-hoc condition in the interlock block with `tx_selftest_run()` and, when it flags, run
   the existing action (bypass, unlock, invalidate, `SEQ_IDLE`, `STATE_BYPASS_SNOOP`, snoop active) with
   `g_unkeyable = true`.
7. LCD: on the `g_unkeyable` branch print line 0 `STATE: UNDEFINED` and line 1
   `tx_selftest_reason_name(g_selftest_reason)`, replacing `STATE: LOCK LOST` / `UNKEYABLE`, keeping the
   same shape as the trip screen so the bench reads both the same way.
8. Clear `g_selftest_failed` / `g_selftest_reason` in the same three places that clear the interlock
   today: the snoop-decode path and both verified-engage branches of `handle_ptt_transition()`.

### Phase 3 - harness asserts the firmware's own verdict
9. `tools/simulate/trace_ptt_sequence.py`: add `g_selftest_failed` and `g_selftest_reason` to
   `STATE_VARS` (so they reach the CSVs and the failure notes), and replace the remaining
   pacing-sensitive keyed-reading conditions in `validate_freq_ctr()` with the real contract: for every
   band, either the keyed window holds a verified lock, or the firmware flagged the undefined state with
   a reason code and the sequence left TX.
10. `tools/simulate/check_freq_ctr_bands.py` and `tools/simulate/repro_swr1_rearm.py`: mirror the same
    wording, so a band slice and the full suite agree (a slice that passes while the suite fails is a
    check, not a repro).
11. Keep the stop rule: `truncate_at_unkeyable()` triggers on `g_selftest_failed` as well as
    `g_unkeyable`, so the test and its trace end right after the flag.

### Phase 4 - the scope trace mirrors the panel
12. `tools/simulate/scope_trace.py`: `lcd_screen()` shows `STATE: UNDEFINED` plus the reason name in the
    firmware's precedence slot, read from `g_selftest_reason` in the sample.
13. `failure_prose()` / `_draw_failure_notes()`: state the reason in plain prose ("the amplifier could
    not verify its band lock: <reason> after 200 ms") beside the existing LCD panel, fault code and
    stimulus key.

### Phase 5 - docs, skill, notes
14. `docs/tx-sequencer.md`: add the self-test section - what is checked, in what order, the hold window,
    the action taken, the LCD screen, and why it exists (LDMOS protection plus harness independence).
15. `Ai-Notes.md`: current-state entry for the self-test and the new reason codes.
16. `.github/skills/build-test/SKILL.md`: record the new contract (the harness asserts the firmware's
    reason code and LCD screen, never a keyed counter reading) and the trap that a single good sample
    must not clear the interlock.

## Files to modify

| File | Change |
| --- | --- |
| `firmware/src/main.c` | self-test enum/names/accessor, state vars, `tx_selftest_run()`, interlock block, LCD screen, clear paths |
| `firmware/include/freq_counter.h` | only if an accessor is needed; `freq_counter_status_t` already exposes `raw_pulses` and `stability_count` |
| `tools/simulate/trace_ptt_sequence.py` | `STATE_VARS`, `validate_freq_ctr()`, `truncate_at_unkeyable()` |
| `tools/simulate/scope_trace.py` | `lcd_screen()`, `failure_prose()`, `_draw_failure_notes()` |
| `tools/simulate/check_freq_ctr_bands.py`, `tools/simulate/repro_swr1_rearm.py` | contract wording |
| `docs/tx-sequencer.md`, `TESTING.md`, `Ai-Notes.md`, `.github/skills/build-test/SKILL.md` | docs, skill, notes |

## Verification

1. Build: `cmake --build _build/My_Pic_Project/sim` (and the default Debug task) - clean, and record the
   flash figure to confirm there is still room.
2. Band slice first:
   `python tools/simulate/run_suite_with_watchdog.py --test suite --only FREQ_CTR --bands 80m`, then
   `--only FREQ_CTR`. Verdict from `%TEMP%\picampcontrol_suite_progress.log` plus the appended `EXIT=`
   line only - never from the terminal.
3. Force the failure path deliberately (temporary build, or a probe that starves the counter) and
   confirm: `g_selftest_failed` latches, the trace stops at the flag, the graph's LCD panel reads
   `STATE: UNDEFINED` plus the reason, and `<name>_failure.txt` carries the reason in prose.
4. Full suite: `python tools/simulate/run_suite_with_watchdog.py --test suite --timeout 1500`, verdict
   from the log file, then inspect the regenerated graphs.
5. Bench: key an out-of-band signal, confirm the panel shows the undefined state and reason and that the
   RF path opens.
6. Commit verified increments with explicit paths (never `git add .`) and push to `origin/main`.

## Decisions

- A failed self-check produces the **UNDEFINED/UNKEYABLE** state, not a latched trip: it is recoverable
  by a fresh confirmed decode, and a latch would need an operator clear for a condition that may be
  transient.
- The self-test runs on the **10 ms tick**, matching the cadence the band lock is built on.
- The hold window stays `LOCK_LOSS_UNKEYABLE_MS` (200 ms): one timer, one code path.
- Out of scope: new hardware or monitoring, rewiring the existing trip latches, changing the `--only` /
  `--bands` interfaces.

## Further considerations

1. **Reason granularity.** The five codes above, or fewer coarser ones? The recommendation is the five
   listed, because each maps to a distinct bench action and each fits the 11-character LCD line.
2. **`BAND_CHANGED` while keyed.** A separate hot-switch guard, or folded into the existing fold-back?
   The recommendation is to fold it in - the relay must never move while the amplifier is keyed.
3. **Any direct keyed `g_fc_status` check left in the harness?** The recommendation is no: the firmware's
   reason code is the contract, and a simulator-pacing property is not a firmware property.
