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

### Two relay groups, and the order they must switch in

There are **two mechanical relay groups in the RF path**, and the ordering between them is what
makes the whole scheme safe:

- `OUTPUT_TX` (RC5) — the **T/R relays**, which put the amplifier (and therefore its LPF) into the
  path. The harness labels this pin `RELAYS`, and the release path comments it as the one that is
  "opened first".
- `K1–K6` (RD2–RD7) — the **LPF band relays**, which select the filter. The filters are on the TX
  train only, so RX does not pass through them, and they are disconnected from the rig while the
  T/R relay is open.

In a conventional amplifier this never bites, because the band relays are positioned from the rig's
**band data** before key-down: only the T/R relay moves on PTT, and the normal sequencer's wait
after it (`tx_vcc_delay_ms`, default 20 ms) covers its switching time. That is why the relays fire
first — they are the only genuinely slow element; the supply and bias that follow are electronic
and effectively immediate.

This design has no band data. The band is **measured**, so the band relays can only be positioned
once RF exists — which is the whole reason the T/R relay cannot simply fire on PTT-low, and the
reason first-dit bypass exists. The order is therefore always:

```
band relays to the decoded/remembered band   (T/R relay open: the rig is not connected to them)
wait BAND_SETTLE_MS                          (relay contacts settle)
T/R relays close                             (OUTPUT_TX)
wait tx_vcc_delay_ms                         (the T/R relay's own switching time)
HT on                                        (OUTPUT_TX_VCC)
wait tx_bias_delay_ms
bias on                                      (OUTPUT_TX_BIAS)
```

The decode path always did this. The warm path now does too: `freq_counter_restore_locked_band()`
returns whether the band-select outputs actually moved, and the engage only takes the
`BAND_SETTLE_MS` window when they did. A warm re-key on the same band moves nothing, so it stays
immediate.

### The relay selection does not follow silence

`freq_counter_tick_10ms()` updates `current_band`, and therefore drives the band-select outputs,
**only for a usable measurement**. An empty gate window classifies as the 160 m no-signal default
(`classify_frequency_khz(<1000)`), and following that would make the LPF relays chatter to 160 m
after every over and leave the selection disagreeing with `current_band` (invariant I4). Real 160 m
(1800–2000 kHz) is separable from silence by the frequency bound, so the relays simply hold their
last real selection through RX — which is also what keeps a warm re-key free of relay movement.

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
| I6 | Every T/R relay close follows a band relay selection that has already settled |

Firmware mechanisms behind them:

- `apply_bypass()` — every path that is about to let the band selection change (restoring a
  remembered band, entering bypass-snoop, a PTT re-assert, the comparator-reset window)
  forces all TX outputs inactive first.
- `release_band_if_cold()` — the band is only allowed to follow live RF once every TX output is
  inactive, so a released band can never let the relays move under a keyed amplifier.
- the band is locked in the same tick that TX is first enabled, and stays locked for the whole
  TX cycle including the ordered release.
- the **T/R relay only closes after the band relays have settled**. The decode path holds
  `BAND_SETTLE_MS` after commanding a new selection; the warm path does the same whenever
  `freq_counter_restore_locked_band()` reports that the selection actually moved. When the
  selection does not move, nothing needs to settle and the engage stays immediate.
- the **SWR trips are only armed while the TX path is engaged** (`g_sequence_stage` 1–3, i.e. the
  stages that hold `OUTPUT_TX` asserted). The bridges sit in the TX train, which the T/R relay
  only connects to the RF path while it is closed; during bypass any reading is meaningless and
  the band selection may legitimately be moving, so a bridge reading must not be able to latch a
  trip while the amplifier is cold. The hardware overcurrent, current, temperature, overdrive and
  drain trips stay ungated.

## Implementation

### State and flags

- `STATE_BYPASS_SNOOP` in `system_state_t` (`firmware/src/main.c`), appended last so the
  existing state numbering stays stable
- `g_band_cache_valid`, `g_band_cache_band`, `g_snoop_active`, `g_band_cache_idle_ms`
- `g_band_settle_active`, `g_band_settle_elapsed_ms`
- `g_band_verify_active`, `g_band_verify_mismatch_ms`
- `BAND_CACHE_IDLE_TIMEOUT_MS` (60 s), `BAND_SETTLE_MS` (20 ms) and `BAND_VERIFY_MS` (20 ms)

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

The confirmation test is `freq_counter_band_confirmed()`, which requires the stabilised band to
match the latest measurement. A weaker "is any frequency in range" test must not be used:
after silence the 10 ms tick has already classified an empty gate window as 160 m, and that
stale band must never be cached or locked.

### Verifying a remembered band

Engaging from the memory is a blind decision: at keydown the radio has not started transmitting
yet, so there is nothing to measure. If the operator changes bands and keys straight away, the
remembered band is wrong, and the first RF of that transmission would otherwise be amplified
through the previous band's filter for the whole over.

The remembered band is therefore checked against the **first usable measurement of that
transmission**, using `freq_counter_measured_band()` (which reports the band being received
regardless of the lock). While `g_band_verify_active` is set:

- measured band matches the frozen one → the memory is confirmed, verification ends, and the band
  stays locked for the rest of the TX cycle
- the measurement is unusable → keep waiting: there is nothing to compare against yet
- the measured band differs for `BAND_VERIFY_MS` (20 ms) → **fold back**: force bypass, release the
  band and re-enter bypass-snoop. The snoop path then re-selects the measured band with the
  amplifier cold, waits for the relay to settle, and re-engages on it

The relay selection never moves while the amplifier is keyed, so a correction always goes through
bypass first (invariants I1/I5).

This applies **only** to engages that came from the memory. When the counter has already confirmed
a band from live RF at keydown, that measurement is used directly and the band is frozen for the
whole cycle - which is the behaviour the merged suite's per-band TX lock test exercises.

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
  (~21 s). Proves each item of [Required behaviour](#required-behaviour) in order: bypass with no
  band, decode of the first burst and engagement on the decoded band, an instant warm re-key with
  **no RF injected at all**, cache expiry after the inactivity timeout, re-detection of a band
  change, and a hot-switch fault injection that re-keys during the release ramp with a
  deliberately wrong cached band, then a blind cached-band engage that is corrected by the first
  measurement of the transmission. Three clauses guard the relay ordering and the SWR arming:
  (h) the relay selection **holds** through RX instead of following the 160m no-signal default,
  (i) a remembered-band engage that has to **move** the band relays holds bypass until they have
  settled before the T/R relay closes, and (j) a hard SWR fault injected while bypass-snooping
  latches **no** trip.
- `PTT_SequencerAndTripSuite` — enforces invariants I1-I6 over **every** scenario in the merged
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
| Relay selection follows silence in RX | `clause (c): the remembered 20m band was not restored` — an *earlier* clause trips first, because one phase of the session feeds the next. Clause (h) is the direct guard for this defect, but its own proof is still outstanding: the cascade masks it. |
| No relay settle on a remembered-band engage | `clause (i): only 6.0ms of bypass between the band-relay selection change and the T/R relay closing` — the focused proof, with (g) and (h) still passing. |
| SWR trips left ungated | `clause (j): an SWR fault injected while the amplifier was bypassed latched a trip`, with the failing sample showing `state=3` (TRIP) and `snoop=true`. Focused proof: (h) and (i) still passed. (The first attempt at this injection was masked by a layout-sensitivity in clause (d), which has since been fixed - see the snags section of [the build/test skill](../.github/skills/picampcontrol-build-test/SKILL.md).) |

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
- `BAND_SETTLE_MS` (20 ms) — confirm against the fitted LPF relay's operate time. Unlike the
  two sequencer delays, this one is a compile-time constant, not a settings-menu value:
  `tx_vcc_delay_ms` and `tx_bias_delay_ms` are adjustable from the menu (0–1000 ms in 5 ms steps,
  both defaulting to 20 ms), but `BAND_SETTLE_MS` and `BAND_VERIFY_MS` are `#define`s. If the
  bench shows the LPF relays need longer than the T/R relays, the two windows need to be
  separable, which means either promoting `BAND_SETTLE_MS` to a setting or accepting one
  conservative value for both. Record the fitted relay part numbers and operate times with the
  final values.
- If the operator changes bands and keys again within the timeout **and the keydown has no RF to
  measure**, the first RF of that transmission is amplified through the previous band's filter
  until the verification above corrects it: `BAND_VERIFY_MS` of measurement/stability plus the
  snoop confirmation and relay settle (measured ~23 ms to bypass in the simulator, e.g. a
  fraction of one CW dit at 20 wpm, and the rest of the over is correctly filtered). Confirm on
  the bench that the correction is not audible. The alternative, if it ever matters, is to snoop
  every PTT and accept a bypass window on every over instead of only after a band change.
- How the operator should be told the amplifier is in bypass-snoop on a `MENU_PAGE_STATUS`-style
  screen.
