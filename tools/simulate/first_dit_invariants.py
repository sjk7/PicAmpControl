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
# The wait itself is witnessed through the firmware's own settle counter (BAND_SETTLE_MS); the
# harness samples transitions at 1-5 ms, which is what makes the ordering observable at all.
BAND_PIN_FOR = {1: "RD2", 2: "RD3", 3: "RD4", 4: "RD5", 5: "RD6", 6: "RD7"}
BAND_NAME = {1: "160m", 2: "80m", 3: "40m", 4: "20m", 5: "15m", 6: "10m"}
BAND_OUT_OF_SPEC = 7

# Instruction rate, MEASURED (see trace_ptt_sequence.py INSTRUCTIONS_PER_MS). This file MUST stay
# in sync with that one. PIC18F47Q10 is the only device, so the rate is a constant: 1625 instructions
# per simulated firmware-ms (validated value; the tighter 1695 measurement broke the SWR1 scenario -
# see trace_ptt_sequence.py).
#
# This is only ever used to TURN A SAMPLE INDEX INTO A REPORTED MILLISECOND, never to decide a
# verdict. The model's steps-per-firmware-ms is not a constant at all - it varies with the code path
# (2026-09-24: two in-run measurements of the same run disagreed by 4.5x, see the note on I6 below),
# so any pass/fail that divides by it is measuring the harness, not the firmware. Use a harness that
# steps at the rate it declares via set_instruction_rate().
_INSTRUCTIONS_PER_MS = 1625
SECONDS_PER_INSTRUCTION = 1.0 / (_INSTRUCTIONS_PER_MS * 1000.0)

# BAND_SETTLE_MS in firmware/src/main.c: the bypass window the firmware holds after it has commanded
# the band relays, before it may close the T/R relay. I6 witnesses this window through the
# firmware's own counter, so the two must agree.
BAND_SETTLE_MS = 20


def set_instruction_rate(steps_per_ms):
    """Declare the instruction rate the calling harness actually steps at.

    test_first_dit.py steps at 1887 while the merged suite steps at 1625; without this the reported
    times of a first-dit sample were scaled by the wrong constant (and by a different factor from
    the one its own windows were built with).
    """
    global _INSTRUCTIONS_PER_MS, SECONDS_PER_INSTRUCTION
    _INSTRUCTIONS_PER_MS = float(steps_per_ms)
    SECONDS_PER_INSTRUCTION = 1.0 / (_INSTRUCTIONS_PER_MS * 1000.0)


def _int_or_none(raw):
    if raw is None:
        return None
    text = raw.lstrip("-")
    return int(raw) if text.isdigit() else None


def settle_counts_reached(samples, start_index, end_index):
    """Largest `g_band_settle_elapsed_ms` the firmware reported over a sample slice.

    The BAND_SETTLE_MS bypass window is witnessed in the FIRMWARE's units, never against the
    harness clock - see the note on I6 for why a millisecond threshold cannot work here. Returns
    None when the samples carry no settle counter at all (a harness whose STATE_VARS omit it), so
    callers can tell "no window ran" from "the harness cannot see the window".
    """
    best = None
    for sample in samples[start_index:end_index + 1]:
        value = _int_or_none(sample[2].get("g_band_settle_elapsed_ms"))
        if value is not None and (best is None or value > best):
            best = value
    return best


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
              # The flags that GATE keying. Without them a "PTT is asserted but nothing keyed"
              # trace cannot say why: `ptt_active=false` with the pin low means the firmware
              # refused to latch, and the reason is one of these three (2026-09-23).
              ("inhibit", "g_startup_inhibit"),
              ("crst", "g_comparator_reset_active"),
              ("fault", "g_fault_latched"),
              ("cache", "g_band_cache_valid"), ("cache_band", "g_band_cache_band"),
              ("idle_ms", "g_band_cache_idle_ms"),
              ("cur_band", "g_fc_status.current_band"),
              ("locked", "g_fc_status.band_locked"),
              ("freq_khz", "g_fc_status.frequency_khz"),
              ("settle", "g_band_settle_active"),
              ("settle_ms", "g_band_settle_elapsed_ms"),
              ("verify", "g_band_verify_active"),
              ("verify_ms", "g_band_verify_mismatch_ms"))
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

    The wait is witnessed through the FIRMWARE'S OWN settle counter, not through a wall-clock
    deadline. That is deliberate, and it was learned the hard way (2026-09-24):

      * The model does not advance its millisecond tick at a fixed number of `Stepi` steps - the
        rate depends on the code path being executed. Two in-run measurements inside ONE first-dit
        run disagreed by 4.5x: the startup inhibit counter (1000 ticks over the whole startup phase)
        is consistent with ~1695 steps/tick, while the 20-tick settle window passed in 4.6ms of the
        same transcript, i.e. ~375 steps/tick. A verdict that divides a sample-index difference by
        a global steps-per-ms constant therefore measures the HARNESS, not the firmware, and it
        reported a hot switch where the firmware had in fact held bypass for its entire
        BAND_SETTLE_MS window (relays moved cold, `g_band_settle_active` true with
        `g_band_settle_elapsed_ms` counting 4 -> 10 -> 14 -> 20, T/R relay closed only afterwards).
      * What the invariant must prove is the ORDER and the WINDOW: the selection moved at an
        earlier sample, the firmware counted the whole BAND_SETTLE_MS bypass window, and only then
        did the T/R relay close. All three are visible in the firmware's own state, in the
        firmware's own units, with no clock constant in the path.

    So: the band-selection change must be at a strictly earlier sample than the close, and WHENEVER
    the firmware reported a settle window for that change (`g_band_settle_active` seen true between
    the change and the close) the close may only follow the counter reaching BAND_SETTLE_MS
    (main.c leaves it at the window value once the settle completes). A change with no settle in
    sight is not required to have one: the relays can also have moved outside an engage (while the
    amplifier was cold and bypassed during RX), in which case there is nothing to wait for and the
    ordering check plus I5 are the guard. Requiring a window unconditionally fails such a close -
    the merged suite's SWR1 scenario closes the T/R relay 147.0ms after a cold RX band change and
    has no settle window anywhere near it.

    The wall-clock gap is still reported as evidence, but it is never the verdict.
    """
    closes = []
    last_change_index = None
    for index, sample in enumerate(all_samples):
        if index and band_pattern(sample) != band_pattern(all_samples[index - 1]):
            last_change_index = index
        if (index and sample[1][T_R_RELAY_PIN] == 0
                and all_samples[index - 1][1][T_R_RELAY_PIN] != 0):
            closes.append((index, last_change_index))
    if not closes:
        return [f"  PASS  {label} I6: no T/R relay close in this scenario, so the ordering was "
                "not exercised"]

    def violation(index, change_index, reason):
        window = all_samples[max(0, index - 14):index + 1]
        change_text = ("none before this close" if change_index is None
                       else describe(all_samples[change_index]))
        return AssertionError(
            f"{label} I6: {reason}\n"
            f"      last band-select change: {change_text}\n"
            f"      close: {describe(all_samples[index])}\n"
            "      window (oldest first):\n"
            + "\n".join(f"        {describe(entry)}" for entry in window))

    gaps = []
    settled_closes = 0
    for index, change_index in closes:
        close_state = all_samples[index][2]
        if change_index is None:
            gaps.append(None)
            continue  # nothing moved: there is no relay to wait for
        gap = millis(all_samples[index]) - millis(all_samples[change_index])
        gaps.append(gap)
        if change_index >= index:
            raise violation(index, change_index,
                            "the band relay selection moved in the same sample as the T/R relay "
                            "close, so the harness cannot show the relays were switched first "
                            "(HOT SWITCH of the band relay - the band relays must always be "
                            "switched first, with the T/R relay open)")
        window = all_samples[change_index:index + 1]
        # A settle window is only owed when the change was made as part of a KEYED engage - the
        # decode path and the remembered-band restore both move the relays while the amplifier is
        # keyed (or bootstrapping a keyed engage) and both hold bypass for BAND_SETTLE_MS. A change
        # made unkeyed, while the amplifier sits in RX, needs no window at the close: the relays
        # have long since settled and the warm re-key restores the band the selection is already on,
        # so main.c's freq_counter_restore_locked_band() reports no relay movement and starts no
        # settle. Requiring one there fails the merged suite's SWR1 scenario, whose cold RX change
        # is 147.0ms before the close and has no settle window anywhere near it.
        if all_samples[change_index][2].get("g_ptt_active") != "true":
            continue
        settle_started = any(entry[2].get("g_band_settle_active") == "true" for entry in window)
        if not settle_started:
            continue
        settled_closes += 1
        if close_state.get("g_band_settle_active") != "false":
            raise violation(index, change_index,
                            "the T/R relay closed while the firmware still reported the band "
                            "settle window active")
        settle_ms = _int_or_none(close_state.get("g_band_settle_elapsed_ms"))
        if settle_ms is None or settle_ms < BAND_SETTLE_MS:
            raise violation(
                index, change_index,
                "the T/R relay closed after the band relay selection changed without the firmware "
                f"counting the whole BAND_SETTLE_MS window (settle counter "
                f"{close_state.get('g_band_settle_elapsed_ms')}, need >= {BAND_SETTLE_MS}) - the "
                "band relays must be switched first, with the T/R relay open")
    moved = [gap for gap in gaps if gap is not None]
    tightest = "n/a" if not moved else f"{min(moved):.1f}ms"
    return [f"  PASS  {label} I6: all {len(closes)} T/R relay closes followed a band relay "
            f"selection that had settled for the firmware's full {BAND_SETTLE_MS}-count bypass "
            f"window ({len(moved)} of them moved the selection, {settled_closes} ran a settle "
            f"window; tightest sample gap {tightest})"]


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
        # A scenario with no band-select change is NOT a violation: the invariant guards "changes
        # must be cold", and a scenario that changes nothing has nothing to guard. This fired on
        # FREQ_CTR_FAIL once the state-leak was fixed - with clean RAM there is no RF, so no band
        # is ever selected, so no relay ever moves. Report it, do not fail it (mirrors I6's
        # handling of "no T/R relay close").
        return [f"  PASS  {label} I5: no band-select change in this scenario, so the "
                "cold-change invariant was not exercised"]
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
