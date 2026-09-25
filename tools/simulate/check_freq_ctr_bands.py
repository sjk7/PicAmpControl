#!/usr/bin/env python3
"""Band-slice CHECK for the FREQ_CTR scenario: one scenario, one band, in isolation.

It is a CHECK, not a repro, and the evidence is why: it PASSES whether or not the suite does. The
suite's 80m failure needs the whole session's pacing (the classifier reads a hard 0 while keyed and
locked under the suite's tick/injection phase, and 68 of 93 UNKEYED samples of the same band read the
injected 3600 kHz), so a scenario that fails in the suite need not fail here - reported as
*"This looks like your repro fails to see the bug. It's not a repro then, is it?"*, which was right.
**The repro for a suite failure is `run_suite_with_watchdog.py --test suite --only <scenario>`**,
which runs that scenario through the suite's own code path.

    python tools/simulate/run_suite_with_watchdog.py --test check-freq-ctr --log <log>

`PICAMP_BANDS` chooses the bands to exercise (default `80m`, the band that failed); `--no-stop-bracket`
drops the T1CON stop/start around the Timer1 injection, which was tried as the cause of the zero
readings and RULED OUT (51 of 100 keyed+locked samples non-zero either way, in the suite too).
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import trace_ptt_sequence as harness  # noqa: E402
import scope_trace  # noqa: E402

ENV_BANDS = "PICAMP_BANDS"
DEFAULT_BANDS = "80m"


def select_bands(spec):
    """`BAND_TESTS` for the band names in `spec` (comma-separated), in table order."""
    wanted = [name.strip() for name in spec.split(",") if name.strip()]
    chosen = [entry for entry in harness.ALL_BAND_TESTS if entry[0] in wanted]
    missing = [name for name in wanted if name not in {entry[0] for entry in harness.ALL_BAND_TESTS}]
    if missing:
        sys.exit(f"error: unknown band(s) {missing}; known: "
                 + ", ".join(entry[0] for entry in harness.ALL_BAND_TESTS))
    return chosen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bands", default=os.environ.get(ENV_BANDS, DEFAULT_BANDS),
                        help="Comma-separated bands to exercise (default: %(default)s)")
    parser.add_argument("--no-stop-bracket", action="store_true",
                        help="Drop the T1CON stop/start around each Timer1 injection")
    args = parser.parse_args()
    harness.BAND_TESTS[:] = select_bands(args.bands)
    if args.no_stop_bracket:
        harness.TMR1_STOP_BRACKET = False

    if not harness.ELF_PATH.exists():
        sys.exit(f"error: {harness.ELF_PATH} not found - build firmware first")
    band_names = ", ".join(name for name, _khz, _band in harness.BAND_TESTS)
    print(f"FREQ_CTR repro: bands={band_names} stop_bracket={harness.TMR1_STOP_BRACKET}")
    script = harness.build_script(trip_name="FREQ_CTR")
    output = harness.run_mdb(harness.find_mdb(), script)
    harness.record_stimulus(script)
    samples = harness.parse_trace(output)
    if not samples:
        sys.exit("error: no samples parsed from mdb output - dumping raw output:\n" + output[-4000:])

    ms = harness.SECONDS_PER_INSTRUCTION * 1000
    for band_name, freq_khz, expected_band in harness.BAND_TESTS:
        keyed_locked = [
            s for s in samples
            if s[2].get("g_ptt_active") == "true"
            and s[2].get("g_sequence_stage") == "3"
            and s[2].get("g_fc_status.band_locked") == "true"
            and s[2].get("g_fc_status.current_band") == str(expected_band)
        ]
        nonzero = [s for s in keyed_locked
                   if s[2].get("g_fc_status.frequency_khz") not in ("0", "", None)]
        print(f"{band_name}: keyed+locked+stage-3 samples={len(keyed_locked)}, "
              f"of those with a non-zero frequency={len(nonzero)} (the simulator-pacing figure that "
              f"used to be asserted; the firmware's own verdict is the contract now)")
        if nonzero:
            first = nonzero[0]
            print(f"  first non-zero: t={first[0] * ms:.2f}ms "
                  f"freq={first[2].get('g_fc_status.frequency_khz')} "
                  f"band={first[2].get('g_fc_status.current_band')}")
        else:
            print(f"  no non-zero reading while locked and keyed "
                  f"(injected {freq_khz} kHz -> band {expected_band})")

    try:
        harness.validate_freq_ctr(samples, "FREQ_CTR")
    except AssertionError as exc:
        scope_trace.on_failure(samples, "repro_freq_ctr", harness.REPO_ROOT / "_build"
                               / "My_Pic_Project" / "sim" / "graphs", f"FAILED: {exc}",
                               events=_keyed_events(samples),
                               stimulus=harness.stimulus_spans(samples),
                               **_failure_context(samples, exc))
        raise
    print("FREQ_CTR repro passed: every band classified, outputs matched, each band either verified "
          "its keyed lock or was flagged by the firmware's own self-test")


def _failure_context(samples, exc):
    """`check` / `observed` / `why` for this repro's scope trace (see scope_trace)."""
    bands = ", ".join(name for name, _khz, _band in harness.BAND_TESTS)
    counts = []
    for band_name, _freq_khz, expected_band in harness.BAND_TESTS:
        locked = [s for s in samples
                  if s[2].get("g_ptt_active") == "true"
                  and s[2].get("g_sequence_stage") == "3"
                  and s[2].get("g_fc_status.band_locked") == "true"
                  and s[2].get("g_fc_status.current_band") == str(expected_band)]
        live = [s for s in locked
                if s[2].get("g_fc_status.frequency_khz") not in ("0", "", None)]
        counts.append(f"{band_name}: {len(locked)} keyed+locked+stage-3 samples, "
                      f"{len(live)} of them reporting a non-zero frequency")
    flagged = [s for s in samples if s[2].get("g_selftest_failed") == "true"]
    if flagged:
        counts.append(f"the firmware's own self-test flagged the undefined state as "
                      f"{harness.selftest_reason_text(flagged[0][2].get('g_selftest_reason'))} "
                      f"in {len(flagged)} samples")
    return {
        "check": (f"Bands {bands}, RF injected once per millisecond while held: the band must "
                  "classify, the band-select output must match current_band, and for each band the "
                  "amplifier must either verify its keyed band lock (keyed, stage 3, band_locked, "
                  "current_band == expected) or have been flagged by its OWN self-test, with a "
                  "named reason. No keyed frequency reading is asserted: the firmware resets TMR1 "
                  "on every 10 ms gate and nothing in the model clocks it, so that reading measures "
                  "the simulator's pacing, not the firmware."),
        "observed": "; ".join(counts) + (
            f"; last sample: stage={samples[-1][2].get('g_sequence_stage')} "
            f"locked={samples[-1][2].get('g_fc_status.band_locked')} "
            f"band={samples[-1][2].get('g_fc_status.current_band')} "
            f"freq={samples[-1][2].get('g_fc_status.frequency_khz')}kHz"
            if samples else "; no samples"),
        "why": str(exc),
    }


def _keyed_events(samples):
    """`(time_ms, label)` for each key-down in the transcript, so the phases are readable."""
    ms = harness.SECONDS_PER_INSTRUCTION * 1000
    events, previous = [], None
    for sample in samples:
        keyed = sample[2].get("g_ptt_active") == "true"
        if keyed and previous is not True:
            events.append((sample[0] * ms, "keyed"))
        elif not keyed and previous is True:
            events.append((sample[0] * ms, "released"))
        previous = keyed
    return events


if __name__ == "__main__":
    main()
