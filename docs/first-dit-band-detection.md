# First-Dit Band Detection (RF Snooping)

## Purpose

The band selector must detect **any band change** made at the transceiver, and it must do so
without ever letting the amplifier amplify through an unverified low-pass filter.

Background leakage from a transceiver can be too low to resolve into a clean square wave on
the snoop input, so instead of relying on continuous background RF the firmware treats the
first transmission after an idle period as a dedicated measurement cycle.

**Status:** implemented (2026-09-21). See [Implementation](#implementation) for the code and
[Test coverage](#test-coverage) for the proof.

## How it works

When the PTT line goes low, the amplifier MCU keeps the main LDMOS bias turned off and keeps
the RF path in **Bypass** (straight-through) mode.

The radio then sends its first bit of RF — the first dit of CW, or the first syllable of SSB
speech. Because the amplifier is in bypass, this RF passes safely straight to the antenna. The
frequency counter catches this split-second burst, decodes the band, and immediately switches
the LPF relays to match.

For all subsequent transmissions on that band, the MCU remembers the setting and switches the
amplifier into active TX mode instantly on the next PTT drop. The amplifier only reverts to
Bypass-Snoop mode if it detects a long period of inactivity, which indicates the operator may
have changed bands.

## Required behaviour

1. PTT goes low → the MCU keeps the LDMOS bias OFF and holds the RF path in **Bypass**
   (straight-through).
2. The radio's first RF burst (first dit / first syllable) passes safely to the antenna through
   bypass. The frequency counter decodes the band and switches the LPF relays to match.
3. The MCU **remembers** that band. On subsequent PTT drops it engages active TX **instantly**.
4. It reverts to bypass-snoop only after a **long period of inactivity**, because the operator
   may have changed bands in the meantime.

## Safety invariants

The amplifier must **never amplify on an unverified band**, and the LPF relay selection must
**never move while the amplifier is keyed**. Bypass is always safe: the RF path is straight
through to the antenna and no LDMOS bias is applied.

These are enforced by construction in the firmware and checked independently by the tests:

| # | Invariant |
|---|---|
| I1 | The relay selection never changes between two consecutive keyed samples |
| I2 | The amplifier is only ever keyed while the band is locked |
| I3 | The amplifier is never keyed while bypass-snooping |
| I4 | The relay selection always agrees with the firmware's `current_band` |
| I5 | Every observed relay-selection change is seen with the amplifier cold |

Firmware mechanisms behind them:

- `apply_bypass()` — every path that is about to let the band selection change (restoring a
  remembered band, entering bypass-snoop, a PTT re-assert, the comparator-reset window)
  forces all TX outputs inactive first.
- `release_band_if_cold()` — the band is only allowed to follow live RF once every TX output is
  inactive, so a released band can never let the relays move under a keyed amplifier.
- the band is locked in the same tick that TX is first enabled, and stays locked for the whole
  TX cycle including the ordered release.

## Implementation

### State and flags

- `STATE_BYPASS_SNOOP` in `system_state_t` (`firmware/src/main.c`), appended last so the
  existing state numbering stays stable
- `g_band_cache_valid`, `g_band_cache_band`, `g_snoop_active`, `g_band_cache_idle_ms`
- `g_band_settle_active`, `g_band_settle_elapsed_ms`
- `BAND_CACHE_IDLE_TIMEOUT_MS` (60 s) and `BAND_SETTLE_MS` (20 ms)

`update_protection_state()` re-derives `g_state` every pass, so the **flag** `g_snoop_active`
is the authoritative snoop indicator, not the enumerated state.

### PTT assert (`handle_ptt_transition(ptt_asserted = true)`)

1. Latch PTT, reset the idle counter, and force bypass.
2. Live RF already confirmed a band → that measurement wins over the remembered band (it is
   fresher evidence: the operator may have changed bands and be transmitting on the new one
   right now). Remember it and engage normally.
3. Otherwise, a remembered band exists → restore and lock it; the relay selection settles while
   the amplifier stays in bypass, then the normal engage sequence runs.
4. Otherwise → `g_snoop_active = true`, stage 0, all TX outputs inactive,
   `freq_counter_unlock_band()`, `g_state = STATE_BYPASS_SNOOP`. **The band is not locked**, so
   the relay selection stays live and the first burst can be classified.

Priority matters: the cache is a *fallback for silence* (the radio has only just been keyed),
never an override of a live, confirmed measurement.

### Decoding the first burst (`update_tx_sequence()` while `g_snoop_active`)

- Not yet confirmed → keep every TX output inactive and return.
- Confirmed → cache the band, lock it, clear `g_snoop_active`, and hold bypass for
  `BAND_SETTLE_MS` so the amplifier is never keyed into a relay that is still moving. The
  normal engage sequence then starts on the decoded band.

The confirmation test is `freq_counter_band_confirmed()`, **not** `freq_counter_signal_valid()`:
after silence the 10 ms tick has already classified an empty gate window as 160 m, and that
stale band must never be cached or locked.

### Cache lifetime

- the idle counter resets on each PTT assert
- the cache expires after `BAND_CACHE_IDLE_TIMEOUT_MS` with no PTT
- `apply_startup_inhibit()` invalidates the cache, so power-up always requires a fresh first dit

### Frequency-counter API

`freq_counter_lock_band()` only freezes whatever `current_band` already holds, so two entry
points were added in [firmware/include/freq_counter.h](../firmware/include/freq_counter.h):

- `freq_counter_restore_locked_band(rf_band_t)` — sets `current_band`, `candidate_band` and
  `locked_band`, locks, and drives the band-select outputs, for the remembered band
- `freq_counter_band_confirmed(void)` — true only when the stabilised `current_band` agrees with
  the latest measurement

These are internal firmware interfaces; the external pin contract is unchanged
(see [docs/hardware/PIC16F18875_pin_map.md](hardware/PIC16F18875_pin_map.md)).

## Test coverage

Two CTest tests cover this model:

- `FirstDit_BandDetectionAndHotSwitchGuards` —
  [tools/simulate/test_first_dit.py](../tools/simulate/test_first_dit.py), its own MDB session
  (~18 s). Proves each item of [Required behaviour](#required-behaviour) in order: bypass with no
  band, decode of the first burst and engagement on the decoded band, an instant warm re-key with
  **no RF injected at all**, cache expiry after the inactivity timeout, re-detection of a band
  change, and a hot-switch fault injection that re-keys during the release ramp with a
  deliberately wrong cached band.
- `PTT_SequencerAndTripSuite` — enforces invariants I1-I5 over **every** scenario in the merged
  suite by post-processing the samples it already takes.

The invariant checks live in one module,
[tools/simulate/first_dit_invariants.py](../tools/simulate/first_dit_invariants.py), used by both.

They were verified to fail on real regressions rather than merely passing: re-introducing each
of these defects makes the first-dit test fail with the message shown.

| Re-introduced defect | Failure |
|---|---|
| Band not locked before keying | `I2: amplifier keyed with the band unlocked` |
| No `BAND_SETTLE_MS` after decoding | `clause (b): only 1.0ms of bypass between the relay selection and keying` |
| Releasing PTT during sequencer stage 2 | `clause (c): the stage-2 release left a TX output asserted` |

Two limits are worth stating:

- **Sample granularity.** A sample only shows one instant, so a relay move and a keying inside
  one sample interval cannot be separated. The decode path therefore holds `BAND_SETTLE_MS` of
  bypass and the harness samples those transitions at 1-5 ms, which is finer than that window.
- **The Timer1 external clock is not modelled**, so the first burst is injected by writing
  `TMR1H`/`TMR1L`. The T1CKI pin, PPS routing and prescaler are not covered — see
  [TESTING.md](../TESTING.md).

## Open questions

- `BAND_CACHE_IDLE_TIMEOUT_MS` (60 s) — confirm on the bench against typical operator
  band-change habits.
- `BAND_SETTLE_MS` (20 ms) — confirm against the fitted LPF relay's operate time.
- If the operator changes bands and keys again within the timeout **and the counter has no live
  measurement at that moment**, the first RF burst of that transmission is amplified through the
  previous band's filter. That is the accepted trade-off for an instant engage (clause 3), and the
  timeout is the mitigation. A live confirmed measurement always wins over the remembered band, so
  the exposure is limited to the case where the counter genuinely has nothing to say. The
  alternative, if the bench shows it matters, is to snoop every PTT and accept the bypass delay.
- How the operator should be told the amplifier is in bypass-snoop on a `MENU_PAGE_STATUS`-style
  screen.
