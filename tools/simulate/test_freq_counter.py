#!/usr/bin/env python3
"""Standalone frequency counter test for amateur band classification.
Tests that the frequency counter correctly classifies 40m, locks during TX,
and updates to 20m in RX after PTT release.

Usage:
    python tools/simulate/test_freq_counter.py
"""
import os
import re
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ELF_PATH = REPO_ROOT / "out" / "My_Pic_Project" / "default.elf"
DEVICE = "PIC16F18875"

STATE_VARS = [
    "g_startup_inhibit", "g_comparator_reset_active", "g_fault_latched", "g_trip_reason",
    "g_ptt_active", "g_sequence_stage", "g_state", "g_trip_shutdown_active",
    "g_ptt_complete_display_active", "g_transient_menu_display",
    "g_fc_status.current_band", "g_fc_status.band_locked", "g_fc_status.frequency_khz"
]
XTAL_FREQ = 32_000_000
SECONDS_PER_INSTRUCTION = 4 / XTAL_FREQ

STEP_SIZE = 2000
PHASES = [
    ("steady_coarse", "5v", 22, 180000),  # ~495ms
    ("steady_mid", "5v", 402, 20000),  # ~495ms -> ~1500ms, 2.5ms/sample
    ("asserted", "0v", 300, STEP_SIZE),  # PTT pressed
    ("released", "5v", 100, STEP_SIZE),  # PTT released
]
PINS = ["RC1", "RC0", "RC5", "RC6", "RC7"]
PIN_LABELS = {"RC1": "SETTLE", "RC0": "PTT", "RC5": "RELAYS", "RC6": "TX_VCC", "RC7": "TX_BIAS"}
ADC_PINS = ["RA0", "RA1", "RA2", "RA3", "RA5", "RB1", "RB2", "RB3"]

PRINT_RE = re.compile(r"^(R[A-Z]\d+)\s+\S+\s+(?:(HIGH|LOW)|([\d.]+)V)", re.MULTILINE)
STEPI_RE = re.compile(r"^Stepi\s+(\d+)")
VAR_NAME_RE = re.compile(r"^(g_[\w\.]+)=$")


def find_mdb() -> Path:
    print("[DEBUG] Searching for mdb...", flush=True)
    candidates = sorted(Path("C:/Program Files/Microchip/MPLABX").glob("*/mplab_platform/bin/mdb.bat"))
    if not candidates:
        print("[DEBUG] No Windows mdb found, checking macOS", flush=True)
        candidates = sorted(Path("/Applications/microchip/mplabx").glob("*/mplab_platform/bin/mdb.sh"))
    if not candidates:
        print("[DEBUG] No mdb found in standard locations", flush=True)
        sys.exit("error: mdb not found. Install MPLAB X IDE.")
    print(f"[DEBUG] Found {len(candidates)} mdb candidate(s), using latest", flush=True)
    return candidates[-1]


def build_script() -> str:
    """Build mdb script for frequency counter test."""
    lines = [f"device {DEVICE}", "hwtool sim", f"program {ELF_PATH}"]
    lines += [
        "write pin RA0 0v", "write pin RA1 0v", "write pin RA2 0v", "write pin RA3 0v",
        "write pin RA5 2.5v", "write pin RB1 0v", "write pin RB2 0v", "write pin RB3 0v", "write pin RB4 0v",
        "write pin RC2 5v", "write pin RB0 5v", "write pin RB6 5v"
    ]
    for phase_name, ptt_level, step_count, step_size in PHASES:
        if phase_name == "steady_coarse":
            lines.append(f"# {phase_name}: PTT={ptt_level}")
            lines.append(f"stepi {step_count * step_size}")
        elif phase_name == "steady_mid":
            lines.append(f"# {phase_name}: PTT={ptt_level}, inject 40m (6900kHz) on RD1")
            lines.append("write pin RD1 2.5v")
            for i in range(step_count):
                lines.extend([f"stepi {step_size}", f"print {' '.join(PINS)}", *[f"print {var}" for var in STATE_VARS]])
        elif phase_name == "asserted":
            lines.append(f"# {phase_name}: PTT={ptt_level}, then inject 20m (13993kHz) during TX stage 3")
            lines.append("write pin RC0 0v")
            for i in range(step_count):
                if i == 100:
                    lines.append("write pin RD1 5.0v")
                lines.extend([f"stepi {step_size}", f"print {' '.join(PINS)}", *[f"print {var}" for var in STATE_VARS]])
        elif phase_name == "released":
            lines.append(f"# {phase_name}: PTT={ptt_level}")
            lines.append("write pin RC0 5v")
            lines.append("write pin RD1 2.5v")
            for i in range(step_count):
                lines.extend([f"stepi {step_size}", f"print {' '.join(PINS)}", *[f"print {var}" for var in STATE_VARS]])
    lines.append("quit")
    return "\n".join(lines)


def run_mdb(mdb_path: Path, script: str) -> str:
    print(f"[DEBUG] Starting mdb: {mdb_path}", flush=True)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".mdb", delete=False) as f:
        f.write(script)
        script_path = f.name
    try:
        print(f"[DEBUG] Running mdb with script file {script_path} ({len(script)} bytes)", flush=True)
        # stdin=DEVNULL + start_new_session detach mdb from our controlling tty so a
        # killed/hung mdb/JVM can never leave the terminal in raw mode (see bugfixes.md).
        proc = subprocess.Popen(
            [str(mdb_path), script_path], stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            start_new_session=True,
        )
        try:
            stdout, stderr = proc.communicate(timeout=120)
        except subprocess.TimeoutExpired:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            stdout, stderr = proc.communicate()
            print("[DEBUG] mdb timed out after 120 seconds", flush=True)
            sys.exit("error: mdb timed out after 120 seconds")
        print(f"[DEBUG] mdb completed, got {len(stdout)} bytes stdout, {len(stderr)} bytes stderr", flush=True)
        return stdout + stderr
    finally:
        Path(script_path).unlink(missing_ok=True)


def parse_trace(output: str):
    samples = []
    instr_count = 0
    pending = {}
    state_pending = {}
    awaiting_var = None
    for raw_line in output.splitlines():
        line = raw_line.strip()
        m_stepi = STEPI_RE.match(line)
        if m_stepi:
            instr_count += int(m_stepi.group(1))
            continue
        if awaiting_var is not None:
            if line:
                state_pending[awaiting_var] = line
                awaiting_var = None
            continue
        m_var = VAR_NAME_RE.match(line)
        if m_var:
            awaiting_var = m_var.group(1)
            continue
        m = PRINT_RE.match(line)
        if m:
            pin = m.group(1)
            level, volts = m.group(2), m.group(3)
            pending[pin] = 1 if level == "HIGH" or (volts is not None and float(volts) >= 2.5) else 0
        if len(pending) == len(PINS) and len(state_pending) == len(STATE_VARS):
            samples.append((instr_count, dict(pending), dict(state_pending)))
            pending.clear()
            state_pending.clear()
    return samples


def validate_freq_ctr(samples) -> None:
    # Check 40m band classified (BAND_40M = 3)
    classified_40m = [s for s in samples if s[2].get("g_fc_status.current_band") == "3"]
    if not classified_40m:
        raise AssertionError("Frequency counter failed to classify 40m band")

    # Check band was locked when frequency shifted to 20m (BAND_20M = 4) during TX stage 3
    tx_20m_injection = [s for s in samples if s[2]["g_ptt_active"] == "true" and s[2]["g_sequence_stage"] == "3" and s[2].get("g_fc_status.frequency_khz") == "13993"]
    if not tx_20m_injection:
        raise AssertionError("Frequency counter test did not inject 20m frequency during TX stage 3")

    tx_locked = [s for s in tx_20m_injection if s[2].get("g_fc_status.band_locked") == "true" and s[2].get("g_fc_status.current_band") == "3"]
    if not tx_locked:
        raise AssertionError("Frequency counter failed to lock 40m band when 20m frequency was injected during TX stage 3")

    # Check 20m band classified after PTT release in RX mode
    rx_20m = [s for s in samples if s[2]["g_ptt_active"] == "false" and s[2].get("g_fc_status.current_band") == "4"]
    if not rx_20m:
        raise AssertionError("Frequency counter failed to update to 20m band in RX mode after PTT release")

    print("FREQ_CTR test passed: 40m classified, locked during 20m injection in TX, updated to 20m in RX after PTT release")


def main():
    print("[DEBUG] Starting frequency counter test", flush=True)
    if not ELF_PATH.exists():
        print(f"[DEBUG] ELF not found at {ELF_PATH}", flush=True)
        sys.exit(f"error: {ELF_PATH} not found - build firmware first")
    
    print(f"[DEBUG] ELF found at {ELF_PATH}", flush=True)
    mdb_path = find_mdb()
    print(f"[DEBUG] Found mdb at {mdb_path}", flush=True)
    
    print("[DEBUG] Building mdb script", flush=True)
    script = build_script()
    print(f"[DEBUG] Script built: {len(script)} bytes", flush=True)
    
    print("[DEBUG] Running mdb", flush=True)
    output = run_mdb(mdb_path, script)
    print(f"[DEBUG] mdb output received: {len(output)} bytes", flush=True)
    
    print("[DEBUG] Parsing trace", flush=True)
    samples = parse_trace(output)
    print(f"[DEBUG] Parsed {len(samples)} samples", flush=True)
    
    if not samples:
        print("[DEBUG] No samples parsed, dumping last 500 chars of output:", flush=True)
        print(output[-500:], flush=True)
        sys.exit("error: no samples parsed from mdb output")
    
    print("[DEBUG] Validating frequency counter", flush=True)
    validate_freq_ctr(samples)
    print("Frequency counter test completed successfully", flush=True)


if __name__ == "__main__":
    main()
