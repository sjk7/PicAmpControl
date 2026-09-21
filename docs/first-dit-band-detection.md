# First-Dit Band Detection (RF Snooping)

## Purpose

The band selector must detect **any band change** made at the transceiver, and it must do so
without ever letting the amplifier amplify through an unverified low-pass filter.

Background leakage from a transceiver can be too low to resolve into a clean square wave on
the snoop input, so instead of relying on continuous background RF the firmware treats the
first transmission after an idle period as a dedicated measurement cycle.

**Status:** approved specification. The firmware change is not implemented yet; the current
release still refuses PTT when the snoop signal is unusable
(see [Band selection and lockout](project-architecture.md#band-selection-and-lockout)).

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

## Safety invariant

The amplifier must **never amplify on an unverified band**. Bypass is always safe; `OUTPUT_TX`,
`OUTPUT_TX_VCC`, and `OUTPUT_TX_BIAS` stay inactive until the band has been decoded and the LPF
relays match it.

## Intended implementation design

### State and flags

- new `STATE_BYPASS_SNOOP` member of `system_state_t` (`firmware/src/main.c`)
- `g_band_cache_valid` — a remembered band is usable
- `g_band_cache_band` (`rf_band_t`) — the remembered band
- `g_snoop_active` — authoritative snoop indicator (see note below)
- `g_band_cache_idle_ms` — time since the last PTT assert
- `BAND_CACHE_IDLE_TIMEOUT_MS` — inactivity timeout before the cache is dropped
  (60 s is a first guess and must be confirmed on the bench)

`update_protection_state()` ends by setting `g_state = STATE_OPERATE`, so the **flag**
`g_snoop_active` — not `g_state` — is the authoritative snoop indicator; `STATE_BYPASS_SNOOP` is
re-asserted each tick while snooping.

### PTT assert (`handle_ptt_transition(ptt_asserted = true)`)

- cache valid → restore and lock the remembered band, clear `g_snoop_active`, set
  `g_ptt_active` → normal instant engage.
- cache invalid but `freq_counter_signal_valid()` → normal engage (band already decoded).
- otherwise → `g_ptt_active = true`, `g_snoop_active = true`, stage 0, all TX outputs inactive,
  `freq_counter_unlock_band()`, `g_state = STATE_BYPASS_SNOOP`. **The band is not locked.**

### Snooping (`update_tx_sequence()` while `g_snoop_active`)

- `freq_counter_signal_valid()` → store the band in the cache, lock the band, clear
  `g_snoop_active`, and fall through to the normal engage sequence.
- not yet valid → keep every TX output inactive and return.

### Cache lifetime

- the idle counter resets on each PTT assert
- the cache expires after `BAND_CACHE_IDLE_TIMEOUT_MS` with no PTT
- `apply_startup_inhibit()` invalidates the cache

### Frequency-counter API

`freq_counter_lock_band()` only freezes whatever `current_band` already holds, so restoring a
remembered band needs a new entry point — `freq_counter_restore_locked_band(rf_band_t)` in
[firmware/include/freq_counter.h](../firmware/include/freq_counter.h) and
[firmware/src/freq_counter.c](../firmware/src/freq_counter.c) — which sets `current_band`,
`locked_band`, and `candidate_band` and calls `update_band_outputs()`.

These are internal firmware interfaces; the external pin contract is unchanged
(see [docs/hardware/PIC16F18875_pin_map.md](hardware/PIC16F18875_pin_map.md)).

## Test coverage

The band-cache/branch behaviour is testable in simulation; the Timer1 external-clock path is
not. See [TESTING.md](../TESTING.md) for what the counter test can and cannot cover.

## Open questions

- `BAND_CACHE_IDLE_TIMEOUT_MS` value (60 s assumed) — confirm on the bench against typical
  operator band-change habits.
- How the operator should be told the amplifier is in bypass-snoop on a `MENU_PAGE_STATUS`-style
  screen.
