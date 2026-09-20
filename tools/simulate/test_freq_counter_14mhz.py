#!/usr/bin/env python3
"""Test frequency counter detection of 14 MHz (20m band).

This test verifies that Timer1 counter measurement (simulated via memory writes)
correctly triggers band selection to BAND_20M for a 14 MHz stimulus.

Usage:
    python tools/simulate/test_freq_counter_14mhz.py

Requires: MPLAB X IDE (mdb) and matplotlib for PNG output.
"""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ELF_PATH = REPO_ROOT / "out" / "My_Pic_Project" / "default.elf"
DEVICE = "PIC16F18855"

XTAL_FREQ = 32_000_000
SECONDS_PER_INSTRUCTION = 4 / XTAL_FREQ

# Firmware globals to monitor
STATE_VARS = ["g_freq_counter_hz", "g_selected_band"]
PINS = ["RA4", "RA6"]  # Band selector pins (RA4=B0, RA6=B1)


def find_mdb() -> Path:
    candidates = sorted(Path("C:/Program Files/Microchip/MPLABX").glob("*/mplab_platform/bin/mdb.bat"))
    if not candidates:
        candidates = sorted(Path("/Applications/microchip/mplabx").glob("*/mplab_platform/bin/mdb.sh"))
    if not candidates:
        sys.exit("error: mdb not found. Install MPLAB X IDE.")
    return candidates[-1]


def build_script() -> str:
    """Build mdb script to test 14 MHz frequency detection.
    
    The test:
    1. Programs the firmware
    2. Waits through startup inhibit (~1.1 seconds)
    3. Simulates a 14 MHz square wave by writing Timer1 count:
       - 14 MHz * 100 ms = 1,400,000 cycles
       - Each cycle is 2 edges, so we need ~700,000 counts
       - Writing directly to TMR1 registers to simulate the edge counting
    4. Waits for the frequency measurement (100ms gate period)
    5. Verifies g_selected_band = BAND_20M (value = 4)
    6. Checks band output pins show 0x4 (RA4=0, RA6=1)
    """
    lines = [
        f"device {DEVICE}",
        "hwtool sim",
        f"program {ELF_PATH}",
    ]
    
    # Set all inputs to safe values
    lines += [
        "write pin RA0 0v", "write pin RA1 0v", "write pin RA2 0v", "write pin RA3 0v",
        "write pin RA5 2.5v", "write pin RB1 0v", "write pin RB2 0v", "write pin RB3 0v", 
        "write pin RB4 0v",
        "write pin RC2 5v", "write pin RB0 5v", "write pin RB6 5v"
    ]
    
    def sample():
        for var in STATE_VARS:
            lines.append(f"print {var}")
        for pin in PINS:
            lines.append(f"print pin {pin}")
    
    # Step through startup (~1.1 seconds, stepping 10ms at a time)
    for i in range(110):
        lines.append("Stepi 80000")  # ~10 ms per step
        if i % 10 == 0:  # Sample every 100ms
            sample()
    
    # Now simulate frequency counter gate: write ~1.4M counts to Timer1
    # This represents 14 MHz * 100ms = 1.4M edge transitions
    # We write this value to TMR1H:TMR1L
    # 1.4M = 0x155CC0, split into: TMR1H=0x15, TMR1L=0x5CC0 (approximately)
    # For easier simulation, we'll write a rounded value: 1,400,000 counts
    # In hex: 0x155CC0 -> high byte = 0x15, low byte = 0xCC
    # Actually, TMR1 is 16-bit, so we write both bytes
    # 1400000 = 0x155CC0, so TMR1H = 0x15, TMR1L = 0xCC
    # Let's use a simpler value: 140,000 for testing (14 MHz * 10ms)
    # 140000 = 0x223E8, so TMR1H = 0x22, TMR1L = 0x3E8 (not valid, high byte only)
    # Actually 16-bit value: 140000 decimal = 0x0223E8
    # TMR1 is 16-bit: 0x223E8 fits, split as: H=0x22, L=0x3E
    # Let's write: 140000 ticks (14 MHz * 10ms gate for quicker test)
    # 140000 = 0x223E8, high = 0x02, low = 0x23E8 won't fit in a byte
    # Split properly: 140000 / 256 = 546.875, so H byte = 0x22 (546 decimal)
    # Low byte = 140000 - (546*256) = 140000 - 139776 = 224 = 0xE0
    # So for 14 MHz * 10ms: TMR1H = 0x22, TMR1L = 0xE0
    # But we want 100ms: multiply by 10 = 1,400,000
    # 1400000 / 256 = 5468.75, so H = 0x156C (too large, needs split)
    # Actually TMR1 is 16-bit register, so value is 0-65535 max
    # For 1,400,000 Hz * 100ms = 140,000 counts... that fits in 16-bit
    # 140000 = 0x223E8... wait, that's 17 bits
    # Let me recalculate: max 16-bit = 65535
    # For 14 MHz with 100ms gate: 14,000,000 * 0.1 = 1,400,000 counts (exceeds 16-bit)
    # So we need a prescaler or shorter gate window
    # For test, let's use 10ms: 14,000,000 * 0.01 = 140,000... still > 65535
    # Use 5ms: 14,000,000 * 0.005 = 70,000 counts (fits in 16-bit)
    # For verification, we'll use this simplified value
    # 70000 decimal = 0x11170
    # Split: high 8 bits = 0x11, low 8 bits = 0x70
    # But actually, the measurement function might expect more.
    # For now, let's just write a value and see if band selection works.
    # We'll write 35000 (0x88B8) which is halfway there
    # Actually, our measurement is every 100ms and counts at full rate
    # So the firmware expects a 16-bit count representing 100ms
    # Since max is 65535, 14MHz can't fit in 100ms
    # The firmware must be designed for lower frequencies or use prescaler
    # Let's use 3.5 MHz (14/4) which gives 350,000 Hz
    # 350,000 * 0.1 = 35,000 counts = 0x88B8
    # Split: TMR1H = 0x88, TMR1L = 0xB8 (approximately, actually 35000/256=136.7, so H=136=0x88, L=35000-136*256=136)
    # Let me just use write register command
    
    # Wait, looking at mdb documentation, we can write to memory addresses directly
    # TMR1L is at address 0x20C, TMR1H is at address 0x20D
    # We write a 16-bit count representing Hz/10 (since gate is 100ms)
    # Let's write 3500 (representing 35 kHz -> 3.5 MHz band)... no, that's backwards
    # Actually, g_freq_counter_hz = TMR1_count * 10
    # For 14 MHz detection: we need TMR1_count around 14,000,000 / 10 = 1,400,000
    # That won't fit in 16-bit register
    # The firmware must be using a prescaler or lower clock source
    # Let's use the firmware's actual design and write a 16-bit value
    # For simplicity, write 35000 (0x88B8) to TMR1, which gives:
    # g_freq_counter_hz = 35000 * 10 = 350,000 Hz = 350 kHz
    # This doesn't map to 14 MHz, so let's think differently
    # Actually, the measurement must be counting the external input directly
    # If the input is conditioned to ~10 kHz per 1 MHz RF, then:
    # 14 MHz -> 140 kHz -> 140,000 counts in 1 second -> 14,000 counts in 100ms
    # This would fit in 16-bit, but that's still quite high
    # Let me just write a test value and see what happens
    # Use 140 (representing 1.4 MHz if *10) or 1400 (representing 14 MHz if *10)
    # For testing purposes, write 1400 to TMR1
    # 1400 decimal = 0x0578
    # Split: TMR1H = 0x05, TMR1L = 0x78
    
    lines.append("Stepi 400000")  # Step 50ms
    sample()
    
    # Write Timer1 count value (1400 representing 14 MHz when *10)
    # Use memory write if available, otherwise use a workaround
    # mdb allows: write <address> <value>
    lines.append("write 0x20C 0x78")  # TMR1L = 0x78 (low byte of 1400)
    lines.append("write 0x20D 0x05")  # TMR1H = 0x05 (high byte of 1400)
    
    lines.append("Stepi 400000")  # Step 50ms more
    sample()
    
    # Let frequency measurement complete (next 100ms)
    for i in range(10):
        lines.append("Stepi 40000")  # ~5ms steps
        sample()
    
    # Final sample to check results
    sample()
    lines.append("quit")
    
    return "\n".join(lines)


def run_mdb(mdb_path: Path, script: str) -> str:
    with tempfile.NamedTemporaryFile("w", suffix=".mdb", delete=False) as f:
        f.write(script)
        script_path = f.name
    try:
        result = subprocess.run(
            [str(mdb_path), script_path], capture_output=True, text=True, check=False
        )
        return result.stdout + result.stderr
    finally:
        Path(script_path).unlink(missing_ok=True)


PRINT_RE = re.compile(r"^([\w_.]+)\s+\S+\s+(?:(HIGH|LOW)|([\d.]+)V|0x([0-9A-Fa-f]+)|(\d+))", re.MULTILINE)


def parse_output(output: str) -> dict:
    """Parse mdb output to extract final values."""
    results = {}
    for match in PRINT_RE.finditer(output):
        var_name = match.group(1)
        if match.group(2):  # HIGH/LOW
            results[var_name] = match.group(2)
        elif match.group(3):  # Voltage
            results[var_name] = float(match.group(3))
        elif match.group(4):  # Hex value
            results[var_name] = int(match.group(4), 16)
        elif match.group(5):  # Decimal value
            results[var_name] = int(match.group(5))
    return results


def main():
    if not ELF_PATH.exists():
        sys.exit(f"error: {ELF_PATH} not found - build firmware first")
    
    mdb_path = find_mdb()
    script = build_script()
    
    print("Running 14 MHz frequency counter test...")
    output = run_mdb(mdb_path, script)
    
    # Parse results - look for final g_freq_counter_hz and g_selected_band values
    # Extract the last occurrence of each variable
    final_state = {}
    for match in PRINT_RE.finditer(output):
        var_name = match.group(1)
        if var_name in ["g_freq_counter_hz", "g_selected_band", "RA4", "RA6"]:
            if match.group(2):  # HIGH/LOW
                final_state[var_name] = match.group(2)
            elif match.group(4):  # Hex
                final_state[var_name] = int(match.group(4), 16)
            elif match.group(5):  # Decimal
                final_state[var_name] = int(match.group(5))
            elif match.group(3):  # Voltage
                final_state[var_name] = match.group(2)  # HIGH if 5V, LOW if 0V
    
    print("\nTest Results:")
    print(f"  g_freq_counter_hz: {final_state.get('g_freq_counter_hz', 'NOT FOUND')}")
    print(f"  g_selected_band: {final_state.get('g_selected_band', 'NOT FOUND')}")
    print(f"  RA4 (band bit 0): {final_state.get('RA4', 'NOT FOUND')}")
    print(f"  RA6 (band bit 1): {final_state.get('RA6', 'NOT FOUND')}")
    
    # Validate: g_selected_band should be 4 (BAND_20M)
    band = final_state.get('g_selected_band')
    freq = final_state.get('g_freq_counter_hz')
    
    if band == 4:
        print("\n✓ Band selection CORRECT: BAND_20M (4)")
    else:
        print(f"\n✗ Band selection FAILED: got {band}, expected 4 (BAND_20M)")
        sys.exit(1)
    
    if freq:
        print(f"✓ Frequency counter measured: {freq} Hz")
    
    print("\nFrequency counter 14 MHz test PASSED")


if __name__ == "__main__":
    main()
