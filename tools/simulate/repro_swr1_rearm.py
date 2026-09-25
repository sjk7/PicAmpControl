#!/usr/bin/env python3
"""Minimal repro: an SWR1 trip must CLEAR on a PTT re-arm and re-enter TX (stage 3).

Fails exactly like the merged suite's SWR1 scenario does on Windows:

    AssertionError: SWR1 did not clear and re-enter TX after a PTT re-arm

The merged suite only reaches this after nine other scenarios, which makes it useless as a
debugging instrument. This harness drives ONLY the SWR1 sequence: boot, settle, lock 40m, key,
trip on the SWR1 bridge, return the bridge to a safe reading, release PTT, re-key, and check that
the latch cleared and the TX sequence ran back up to stage 3 (`BIAS-ON`).

The sample it writes is the evidence, not the verdict: every sample carries the raw `RC0` pin
level beside the firmware's `g_ptt_active`, so "was the release edge even seen" is answered from
the file rather than inferred. RC0 is active-low - `write pin RC0 0v` is KEYED, `5v` is released.

Run it through the watchdog like every other simulator run:
    python tools/simulate/run_suite_with_watchdog.py --test repro-swr1-rearm --log <log>
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import trace_ptt_sequence as harness  # noqa: E402
import scope_trace  # noqa: E402

# How long the harness holds PTT released before re-keying. The firmware polls PTT once per main
# loop, and that pass can span a long LCD refresh, so the release edge is not seen instantly.
# MEASURED 2026-09-25: 54.0 ms of harness time at this point in the run. The suite's window used to
# be 50 ms - LESS than the latency - so the release was never seen, `handle_ptt_transition(true)`
# was never called, the latch was never cleared, and the scenario failed with "did not clear and
# re-enter TX" while the fault condition had already gone. 200 ms gives the poll ~4x margin.
RELEASE_MS = 200
# `--release-ms` and PICAMP_RELEASE_MS both override it: the watchdog builds a fixed command line,
# so the env var is the way to run the failing variant through the sanctioned wrapper rather than
# invoking this file directly (which is the cheat the build-test skill forbids).
ENV_RELEASE_MS = "PICAMP_RELEASE_MS"

# 40m, the band the preflight locks, so the amplifier is free to leave bypass when keyed.
BAND_KHZ = 7000
SAFE_ADC = [
    "write pin RA2 0v", "write pin RA3 0v", "write pin RA5 2.5v",
    "write pin RB1 0v", "write pin RB2 0v", "write pin RB3 0v", "write pin RB4 0v",
]


def write_tmr1_count(lines, freq_khz):
    """Inject the Timer1 count for `freq_khz`.

    TMR1H FIRST, then TMR1L: RD16 is set (T1CON 0x27), so a TMR1H write is buffered until TMR1L
    is written and the L-then-H order silently drops the high byte (7000 kHz -> 37 kHz). Bracketed
    with T1CON stop/start so the firmware's 10 ms gate cannot read a torn pair.
    """
    counts = int(round((freq_khz * 1000.0) / 400.0))
    lines.append("write T1CON 0x26")
    lines.append(f"write TMR1H 0x{(counts >> 8) & 0xFF:02X}")
    lines.append(f"write TMR1L 0x{counts & 0xFF:02X}")
    lines.append("write T1CON 0x27")


def build_script(release_ms=RELEASE_MS):
    lines = [f"device {harness.DEVICE}", "hwtool sim", f"program {harness.ELF_PATH}"]
    lines += ["write pin RA0 0v", "write pin RA1 0v"] + SAFE_ADC
    lines += ["write pin RC2 5v", "write pin RB0 5v", "write pin RB6 5v"]
    lines.append("write pin RC0 5v")  # released

    def sample():
        for pin in harness.PINS + harness.ADC_PINS:
            lines.append(f"print pin {pin}")
        for var in harness.STATE_VARS:
            lines.append(f"print {var}")

    # Settle: the startup inhibit ignores PTT for its whole 1000 ms, and a key-down inside it is
    # silently lost. The suite also asserts PTT during the inhibit and releases it again - a
    # no-op for the firmware, but it shifts every later edge in the run, and the failure this
    # repro exists to show is phase-sensitive. Mirror it so the phase matches the suite.
    lines.append("write pin RC0 0v")
    for _ in range(5):
        lines.append(harness.stepi(10))
        sample()
    lines.append("write pin RC0 5v")
    for _ in range(105):
        lines.append(harness.stepi(10))
        sample()
    # Lock 40m before keying: with no usable measurement the firmware is DESIGNED to hold bypass,
    # so a key-down without RF can never reach stage 3 and the re-arm check would be vacuous.
    for _ in range(16):
        write_tmr1_count(lines, BAND_KHZ)
        lines.append(harness.stepi(5))
        sample()
    # Key and hold until the sequence is transmitting (stage 3), mirroring the suite's keyed
    # window (12 x 1 ms + 40 x 5 ms + 100 x 5 ms = ~712 ms).
    lines.append("write pin RC0 0v")
    for _ in range(12):
        write_tmr1_count(lines, BAND_KHZ)
        lines.append(harness.stepi(1))
        sample()
    for _ in range(140):
        write_tmr1_count(lines, BAND_KHZ)
        lines.append(harness.stepi(5))
        sample()
    # Trip on SWR1 (2.5 V fwd / 0.75 V ref is well past the 2:1 threshold), the suite's cadence:
    # 40 x 1 ms to observe it, then 10 x 5 ms of latched state.
    lines.append("write pin RA0 2.500v")
    lines.append("write pin RA1 0.750v")
    for _ in range(40):
        write_tmr1_count(lines, BAND_KHZ)
        lines.append(harness.stepi(1))
        sample()
    for _ in range(10):
        write_tmr1_count(lines, BAND_KHZ)
        lines.append(harness.stepi(5))
        sample()
    # Bridge back to a safe reading, then release and re-key - the suite's exact tail, which is
    # what this repro exists to fail.
    lines.append("write pin RA0 0.000v")
    lines.append("write pin RA1 0.000v")
    lines.append("write pin RC0 5v")
    for _ in range(release_ms):  # release, sampled every 1 ms so the poll latency is measurable
        write_tmr1_count(lines, BAND_KHZ)
        lines.append(harness.stepi(1))
        sample()
    lines.append("write pin RC0 0v")
    for _ in range(400):  # 400 ms keyed: decode + settle + 3 stages + unwind
        write_tmr1_count(lines, BAND_KHZ)
        lines.append(harness.stepi(1))
        sample()
    lines.append("quit")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-ms", type=int,
                        default=int(os.environ.get(ENV_RELEASE_MS, RELEASE_MS)),
                        help="How long to hold PTT released before re-keying (default: %(default)s)")
    args = parser.parse_args()
    if not harness.ELF_PATH.exists():
        sys.exit(f"error: {harness.ELF_PATH} not found - build firmware first")
    output = harness.run_mdb(harness.find_mdb(), build_script(args.release_ms))
    samples = harness.parse_trace(output)
    if not samples:
        sys.exit("error: no samples parsed from mdb output - dumping raw output:\n" + output[-4000:])

    csv_path = (harness.REPO_ROOT / "_build" / "My_Pic_Project" / "sim" / "csv"
                / "repro_swr1_rearm.csv")
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with open(csv_path, "w") as f:
        f.write("time_ms,RC0_pin,g_ptt_active,g_fault_latched,g_trip_reason,g_sequence_stage,"
                "RC5_RELAYS,RC6_TX_VCC,RC7_TX_BIAS\n")
        for instr_count, vals, state, _adc in samples:
            f.write(f"{instr_count * harness.SECONDS_PER_INSTRUCTION * 1000:.3f},"
                    f"{vals['RC0']},{state['g_ptt_active']},{state['g_fault_latched']},"
                    f"{state['g_trip_reason']},{state['g_sequence_stage']},"
                    f"{vals['RC5']},{vals['RC6']},{vals['RC7']}\n")
    print(f"Wrote {csv_path} ({len(samples)} samples)")

    tripped = next((s for s in samples if s[2]["g_fault_latched"] == "true"), None)
    if tripped is None:
        raise AssertionError("SWR1 never tripped - the stimulus or the preflight is wrong")
    # Everything from the moment the bridge went safe: this is the window under test.
    window = [s for s in samples if s[0] > tripped[0]]
    for instr_count, vals, state, _adc in window:
        print(f"t={instr_count * harness.SECONDS_PER_INSTRUCTION * 1000:8.2f}ms "
              f"RC0_pin={vals['RC0']} ptt={state['g_ptt_active']} "
              f"latched={state['g_fault_latched']} reason={state['g_trip_reason']} "
              f"stage={harness.stage_name(state['g_sequence_stage'])} "
              f"tx=({vals['RC5']},{vals['RC6']},{vals['RC7']})")
    released = [s for s in window if s[1]["RC0"] == 1]
    print(f"release window: {len(released)} samples with RC0 HIGH; "
          f"firmware saw ptt_active=false in "
          f"{sum(1 for s in released if s[2]['g_ptt_active'] == 'false')} of them")
    if released:
        seen = next((s for s in released if s[2]["g_ptt_active"] == "false"), None)
        latency = ((seen[0] - released[0][0]) * harness.SECONDS_PER_INSTRUCTION * 1000
                   if seen is not None else None)
        print(f"release poll latency: {latency:.1f} ms" if latency is not None
              else "release poll latency: NEVER - the firmware never saw the release edge")
    recovered = next((s for s in window if s[2]["g_fault_latched"] == "false"
                      and s[2]["g_sequence_stage"] == "3"), None)
    if recovered is None:
        scope_trace.on_failure(samples, "repro_swr1_rearm",
                               harness.REPO_ROOT / "_build" / "My_Pic_Project" / "sim" / "graphs",
                               "FAILED: SWR1 did not clear and re-enter TX after a PTT re-arm",
                               events=failure_events(samples, tripped),
                               check=("An SWR1 trip must latch with the amplifier shut down, and a "
                                      "PTT re-arm must clear that latch and run the sequence back "
                                      "up to stage 3 (BIAS-ON) on a settled, locked band."),
                               observed=(f"the fault stayed latched for every sample of the re-arm "
                                         f"window ({len(window)} samples); {len(released)} "
                                         f"samples had PTT released and the firmware acknowledged "
                                         f"the release in "
                                         f"{sum(1 for s in released if s[2]['g_ptt_active'] == 'false')} "
                                         f"of them, so the re-key that followed may not have been "
                                         f"an edge at all"),
                               why="the trip never cleared, so the transmit sequence could not "
                                   "re-enter stage 3")
        raise AssertionError("SWR1 did not clear and re-enter TX after a PTT re-arm")
    print("SWR1 cleared by PTT re-arm; TX sequence resumed")


def failure_events(samples, tripped):
    """`(time_ms, label)` for the moments the SWR1 re-arm failure is about."""
    ms = harness.SECONDS_PER_INSTRUCTION * 1000
    events = [(tripped[0] * ms, "SWR1 trip")]
    index = samples.index(tripped)
    after = samples[index:]
    released = next((s for s in after if s[1]["RC0"] == 1), None)
    if released is not None:
        events.append((released[0] * ms, "PTT released"))
        rekey = next((s for s in samples[samples.index(released):] if s[1]["RC0"] == 0), None)
        if rekey is not None:
            events.append((rekey[0] * ms, "PTT re-arm"))
    return events


if __name__ == "__main__":
    main()
