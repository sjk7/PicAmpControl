#!/usr/bin/env python3
"""Minimal repro for the FREQ_CTR I5 hot-switch (15m -> 10m), per the sticky rule:
test only the failing part.

Runs ONLY the 15m then 10m band sequence (skips 160m/80m/40m/20m), samples at 1ms around
the band re-key, and dumps the settle/verify state at every sample so the boundary is visible.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("PICAMP_DEVICE", "PIC18F47Q10")

import trace_ptt_sequence as t  # noqa: E402
import first_dit_invariants as invariants  # noqa: E402


def main():
    # Override BAND_TESTS. To isolate a single band, set the slice below.
    t.BAND_TESTS[:] = list(t.ALL_BAND_TESTS)

    script = t.build_script(trip_name="FREQ_CTR")
    mdb_path = t.find_mdb()
    raw = t.run_mdb(mdb_path, script)
    samples = t.parse_trace(raw)

    # Dump every sample around the 15m/10m boundary (cur_band 5->6) with full state.
    print("=== full sample dump (time, bandpins, cur_band, locked, stage, keyed, settle, verify) ===")
    prev_band = None
    for i, sample in enumerate(samples):
        pins, state = sample[1], sample[2]
        bp = "".join(str(pins[p]) for p in t.BAND_PINS)
        band = state.get("g_fc_status.current_band")
        locked = state.get("g_fc_status.band_locked")
        stage = state.get("g_sequence_stage")
        keyed = "K" if any(pins[p] == 0 for p in ("RC5", "RC6", "RC7")) else "-"
        settle = state.get("g_band_settle_active")
        settle_ms = state.get("g_band_settle_elapsed_ms")
        verify = state.get("g_band_verify_active")
        verify_ms = state.get("g_band_verify_mismatch_ms")
        ms = sample[0] * t.SECONDS_PER_INSTRUCTION * 1000
        # print a marker line on any band-change and on keying transitions
        mark = ""
        if prev_band is not None and band != prev_band:
            mark = "  <-- BAND CHANGE"
        print(f"t={ms:8.1f} band={band} bp={bp} locked={locked} stage={stage} keyed={keyed} "
              f"settle={settle} settle_ms={settle_ms} verify={verify} verify_ms={verify_ms} "
              f"freq={state.get('g_fc_status.frequency_khz')}{mark}")
        prev_band = band

    # Run the same invariants the suite runs, so we get the exact same verdict.
    fails = False
    for line in invariants.validate_band_changes_are_cold(samples, "REPRO"):
        print(line)
        if line.startswith("AssertionError") or "HOT SWITCH" in line:
            fails = True

    # Also run the FREQ_CTR lock check (the "TX lock failed" assertion).
    try:
        t.validate_freq_ctr(samples, "REPRO")
    except AssertionError as e:
        print(f"REPRO FREQ_CTR LOCK FAIL: {e}")
        fails = True

    if fails:
        print("REPRO: FAILURE reproduced")
    else:
        print("REPRO: I5 + lock both clean in isolation")


if __name__ == "__main__":
    main()
