#!/usr/bin/env python3
"""Smallest failing repro: key down, inject 14000 kHz, expect current_band == 4 (20m).

Isolates the FirstDit clause (b) failure ("the 20m first burst was never classified") with no
phases, no clauses and no invariants - just boot, PTT low, inject one frequency, and read the
classifier. Run:

    python3 tools/simulate/repro_first_dit_20m.py

Exit 0 when the band classified 20m; exit 1 when it did not (the current failure).
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("PICAMP_DEVICE", "PIC18F47Q10")

import trace_ptt_sequence as t  # noqa: E402
import platform_process as procutil  # noqa: E402

FREQ_KHZ = 14000          # 20m
EXPECTED_BAND = "4"       # BAND_20M
COUNTS = FREQ_KHZ * 1000 // 400   # inverse of the firmware's pulses*2/5 scaling

# Fewer prints per sample than the full harness: ADC pins are stimulus-only, so drop them.
t.ADC_PINS = []


def sample_lines() -> str:
    return "\n".join([f"print pin {p}" for p in t.PINS] +
                     [f"print {v}" for v in t.STATE_VARS])


def inject_atomic() -> str:
    """Halt Timer1, write both bytes, restart - the merged suite's write_tmr1_count pattern."""
    return "\n".join([
        "write T1CON 0x26",
        f"write TMR1L 0x{COUNTS & 0xFF:02X}",
        f"write TMR1H 0x{(COUNTS >> 8) & 0xFF:02X}",
        "write T1CON 0x27",
    ])


def main() -> int:
    script = "\n".join([
        f"device {t.DEVICE}", "hwtool sim", f"program {t.ELF_PATH}",
        # Safe idle stimulus (no SWR, mid-scale NTC, no current/overdrive/drain, encoder released).
        "write pin RA0 0v", "write pin RA1 0v", "write pin RA2 0v", "write pin RA3 0v",
        "write pin RA5 2.5v", "write pin RB1 0v", "write pin RB2 0v", "write pin RB3 0v",
        "write pin RB4 0v", "write pin RC2 5v", "write pin RB0 5v", "write pin RB6 5v",
        # Wait out the 1000 ms startup inhibit (PTT is ignored until it clears).
        t.stepi(1200), sample_lines(),
        "write pin RC0 0v",          # PTT asserted (active low)
        t.stepi(100), sample_lines(),   # let the main loop latch PTT (and clear the comp reset)
        # Hold the injected 20m across the firmware's 10 ms gate, sampling after each gate.
        f"{inject_atomic()}\n{t.stepi(10)}\n{sample_lines()}",
        f"{inject_atomic()}\n{t.stepi(10)}\n{sample_lines()}",
        f"{inject_atomic()}\n{t.stepi(10)}\n{sample_lines()}",
        f"{inject_atomic()}\n{t.stepi(10)}\n{sample_lines()}",
        "quit",
    ])

    raw = t.run_mdb(t.find_mdb(), script)
    samples = t.parse_trace(raw)
    if not samples:
        dump = Path(procutil.temp_dir()) / "repro_first_dit_20m_raw.txt"
        dump.write_text(raw, encoding="utf-8", errors="replace")
        print(f"repro: no samples parsed; raw transcript ({len(raw)} bytes) -> {dump}")
        print("repro: raw tail follows")
        print(raw[-1500:])
        return 2

    last = samples[-1]
    band = last[2].get("g_fc_status.current_band")
    freq = last[2].get("g_fc_status.frequency_khz")
    locked = last[2].get("g_fc_status.band_locked")
    ptt = last[2].get("g_ptt_active")
    seen = sorted({s[2].get("g_fc_status.frequency_khz") for s in samples
                   if s[2].get("g_ptt_active") == "true"})
    print(f"repro_first_dit_20m: injected {FREQ_KHZ} kHz -> freq_khz={freq} "
          f"current_band={band} locked={locked} ptt_active={ptt} (expected band {EXPECTED_BAND})")
    print(f"repro: frequencies seen while PTT active: {seen}")
    if ptt != "true":
        print("repro: PTT did not latch - the repro is not exercising the classifier")
        return 2
    if band == EXPECTED_BAND:
        print("repro: PASS - 20m classified")
        return 0
    print(f"repro: FAIL - the {FREQ_KHZ} kHz burst did not classify as 20m")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
