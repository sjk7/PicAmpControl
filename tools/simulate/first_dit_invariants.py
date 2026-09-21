#!/usr/bin/env python3
"""Shared band-selection safety invariants for the first-dit model.

Spec: docs/first-dit-band-detection.md

Imported by tools/simulate/test_first_dit.py (standalone proof) and by
tools/simulate/trace_ptt_sequence.py (the merged suite), so both enforce exactly the same
properties on their own transcripts instead of keeping two copies that can drift.

The invariants are about the LPF relay selection (RD2-RD7) versus the amplifier enable
outputs (RC5 OUTPUT_TX, RC6 TX_VCC, RC7 TX_BIAS, all active-low with default settings):

  I1  the relay selection never changes between two consecutive keyed samples
  I2  the amplifier is only ever keyed while the band is locked
  I3  the amplifier is never keyed while bypass-snooping
  I4  the relay selection always agrees with the firmware's current_band
  I5  every observed relay-selection change is seen with the amplifier cold
  I6  every T/R relay close follows a band relay selection that has already settled

These were verified to fail on real regressions (2026-09-21), by re-introducing each defect
and re-running tools/simulate/test_first_dit.py:

  * band not locked before keying    -> "I2: amplifier keyed with the band unlocked"
  * no BAND_SETTLE_MS after decoding -> "clause (b): only 1.0ms of bypass between the relay
                                        selection and keying"
  * releasing PTT during stage 2     -> "clause (c): the stage-2 release left a TX output
                                        asserted"

Sample-granularity limit: a sample can only show the state at one instant, so a relay move
and a keying that happen inside one sample interval cannot be separated. The first-dit decode
path therefore holds BAND_SETTLE_MS of bypass, and the harness samples the transitions it
checks at 1-5 ms, which is finer than that window.
"""

TX_PINS = ["RC5", "RC6", "RC7"]  # OUTPUT_TX (relays), TX_VCC, TX_BIAS - active-low
BAND_PINS = ["RD2", "RD3", "RD4", "RD5", "RD6", "RD7"]
# The T/R relay is the pin that puts the amplifier (and therefore its LPF bank) into the RF path.
T_R_RELAY_PIN = "RC5"
# The band relays and the T/R relay are both mechanical and both live in the TX train. The band
# relays must ALWAYS be switched first, with the T/R relay open, so the amplifier is never connected
# to the RF path while its filter is changing. This ordering - "never hot-switch the band relay" - is
# what the whole first-dit design exists to preserve, so it is checked (I6), not merely documented.
# Both relay groups are taken to operate in 20 ms, and the harness samples transitions at 1-5 ms, so
# anything below 10 ms is a violation rather than sampling slop.
BAND_SETTLE_MIN_MS = 10.0
BAND_PIN_FOR = {1: "RD2", 2: "RD3", 3: "RD4", 4: "RD5", 5: "RD6", 6: "RD7"}
BAND_NAME = {1: "160m", 2: "80m", 3: "40m", 4: "20m", 5: "15m", 6: "10m"}
BAND_OUT_OF_SPEC = 7
SECONDS_PER_INSTRUCTION = 4 / 32_000_000


def keyed(sample):
    """True when any amplifier enable output is at its active level (active-low)."""
    return any(sample[1][pin] == 0 for pin in TX_PINS)


def band_pattern(sample):
    return tuple(sample[1][pin] for pin in BAND_PINS)


def selected_band_pin(sample):
    high = [pin for pin in BAND_PINS if sample[1][pin] == 1]
    return high[0] if len(high) == 1 else None


def millis(sample):
    return sample[0] * SECONDS_PER_INSTRUCTION * 1000


def describe(sample, extra=()):
    _, pins, state, *_ = sample
    fields = (("ptt_active", "g_ptt_active"), ("stage", "g_sequence_stage"),
              ("state", "g_state"), ("snoop", "g_snoop_active"),
              ("cache", "g_band_cache_valid"), ("cache_band", "g_band_cache_band"),
              ("idle_ms", "g_band_cache_idle_ms"),
              ("cur_band", "g_fc_status.current_band"),
              ("locked", "g_fc_status.band_locked"),
              ("freq_khz", "g_fc_status.frequency_khz"))
    detail = " ".join(f"{label}={state.get(name, '?')}" for label, name in fields)
    for label, name in extra:
        detail += f" {label}={state.get(name, '?')}"
    return (f"t={millis(sample):7.1f}ms PTT={pins['RC0']} "
            f"TX/VCC/BIAS={pins['RC5']}{pins['RC6']}{pins['RC7']} "
            f"bandpins={''.join(str(pins[pin]) for pin in BAND_PINS)} {detail}")


def validate_keyed_band_invariants(all_samples, label):
    """I1-I4. Returns evidence strings; raises AssertionError on violation."""
    keyed_runs = []
    for index, sample in enumerate(all_samples):
        pins, state = sample[1], sample[2]
        band = state.get("g_fc_status.current_band")

        # I4: the relay selection and current_band must always agree. Skipped during the
        # startup inhibit, before freq_counter_init() has driven the band outputs.
        if state.get("g_startup_inhibit") == "false" and band != str(BAND_OUT_OF_SPEC):
            expected = BAND_PIN_FOR.get(int(band)) if band and band.isdigit() else None
            if selected_band_pin(sample) != expected:
                raise AssertionError(
                    f"{label} I4: band-select output for current_band={band} is "
                    f"{selected_band_pin(sample)}, expected {expected}\n      {describe(sample)}")

        if not keyed(sample):
            continue

        # I2: keyed implies a locked band, otherwise the relays may follow live RF.
        if state.get("g_fc_status.band_locked") != "true":
            raise AssertionError(
                f"{label} I2: amplifier keyed with the band unlocked\n      {describe(sample)}")

        # I3: snooping implies bypass.
        if state.get("g_snoop_active") == "true":
            raise AssertionError(
                f"{label} I3: amplifier keyed while bypass-snooping\n      {describe(sample)}")

        # I1: no relay-selection change between two consecutive keyed samples.
        if index == 0 or not keyed(all_samples[index - 1]):
            keyed_runs.append([sample])
        else:
            if band_pattern(sample) != band_pattern(all_samples[index - 1]):
                raise AssertionError(
                    f"{label} I1: band-select outputs changed while the amplifier stayed "
                    "keyed (HOT SWITCH)\n"
                    f"      prev: {describe(all_samples[index - 1])}\n"
                    f"      now:  {describe(sample)}")
            keyed_runs[-1].append(sample)
    evidence = [f"  PASS  {label} I1-I4 hold over {len(all_samples)} samples and "
                f"{len(keyed_runs)} keyed runs; every keyed run kept one fixed band "
                "selection and a locked band"]
    for run in keyed_runs:
        evidence.append(f"      keyed run {millis(run[0]):.0f}..{millis(run[-1]):.0f}ms "
                        f"band={BAND_NAME.get(int(run[0][2]['g_fc_status.current_band']), '?')} "
                        f"({len(run)} samples, selection {selected_band_pin(run[0])})")
    return evidence


def validate_t_r_closes_only_after_band_settle(all_samples, label):
    """I6. Returns evidence strings; raises AssertionError on violation.

    The band relays must always be switched first, with the T/R relay open, so the amplifier is
    never connected to the RF path while its low-pass filter is changing. This is the ordering the
    whole first-dit design exists to preserve: "never hot-switch the band relay". A scenario with no
    T/R relay close is reported rather than failed, so the check is never silently vacuous.
    """
    closes = []
    last_change_ms = None
    for index, sample in enumerate(all_samples):
        if index and band_pattern(sample) != band_pattern(all_samples[index - 1]):
            last_change_ms = millis(sample)
        if (index and sample[1][T_R_RELAY_PIN] == 0
                and all_samples[index - 1][1][T_R_RELAY_PIN] != 0):
            gap = None if last_change_ms is None else millis(sample) - last_change_ms
            closes.append((sample, gap))
    if not closes:
        return [f"  PASS  {label} I6: no T/R relay close in this scenario, so the ordering was "
                "not exercised"]
    for sample, gap in closes:
        if gap is not None and gap < BAND_SETTLE_MIN_MS:
            raise AssertionError(
                f"{label} I6: the T/R relay closed {gap:.1f}ms after the band relay selection "
                "changed (HOT SWITCH of the band relay - the band relays must always be switched "
                "first, with the T/R relay open)\n"
                f"      {describe(sample)}")
    worst = min((gap for _, gap in closes if gap is not None), default=None)
    tightest = "n/a" if worst is None else f"{worst:.1f}ms"
    return [f"  PASS  {label} I6: all {len(closes)} T/R relay closes followed a band relay "
            f"selection already settled for at least {BAND_SETTLE_MIN_MS:.0f}ms "
            f"(tightest {tightest})"]


def validate_band_changes_are_cold(all_samples, label):
    """I5. Returns evidence strings; raises AssertionError on violation."""
    changes = []
    for index in range(1, len(all_samples)):
        if band_pattern(all_samples[index]) == band_pattern(all_samples[index - 1]):
            continue
        if keyed(all_samples[index]):
            raise AssertionError(
                f"{label} I5: band-select outputs changed while the amplifier was keyed "
                "(HOT SWITCH)\n"
                f"      prev: {describe(all_samples[index - 1])}\n"
                f"      now:  {describe(all_samples[index])}")
        changes.append((all_samples[index - 1], all_samples[index]))
    if not changes:
        raise AssertionError(f"{label} I5: no band-select change was observed at all")
    evidence = [f"  PASS  {label} I5: all {len(changes)} observed band-select changes were "
                "seen with the amplifier cold (every TX output inactive)"]
    for previous, current in changes:
        evidence.append(
            f"      {selected_band_pin(previous)!s:>5} -> {selected_band_pin(current)!s:<5} "
            f"at t={millis(current):.0f}ms, TX/VCC/BIAS="
            f"{current[1]['RC5']}{current[1]['RC6']}{current[1]['RC7']}, "
            f"locked={current[2].get('g_fc_status.band_locked', '?')}, "
            f"keyed_before={keyed(previous)}")
    return evidence
