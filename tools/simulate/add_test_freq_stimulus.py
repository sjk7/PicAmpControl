#!/usr/bin/env python3
"""Add TEST_FREQ stimulus handling to build_script() in trace_ppt_sequence.py."""
import glob
import sys
import os

print(f"CWD: {os.getcwd()}")
print(f"Files: {os.listdir('.')[:5]}")

files = glob.glob("trace_p*.py")
print(f"Glob result: {files}")

if not files:
    sys.exit("Error: trace_ppt_sequence.py not found")
fname = files[0]
print(f"Using file: {fname}")

with open(fname, "r", encoding="utf-8") as f:
    content = f.read()

# Find and replace the location where TEST_FREQ handling should go
# It goes after the SWR1_1P5 handling, before the temperature_trip check
old_pattern = '''    if trip_name == "SWR1_1P5":
        lines[3:5] = ["write pin RA0 5.000v", "write pin RA1 0.200v"]
    if not temperature_trip:'''

new_pattern = '''    if trip_name == "SWR1_1P5":
        lines[3:5] = ["write pin RA0 5.000v", "write pin RA1 0.200v"]
    if trip_name == "TEST_FREQ":
        # Test frequency counter: first 2MHz (160m band), then 14MHz (20m band)
        # Measurement period: 100ms; calibration: *10000 to convert Timer1 counts to Hz
        # 2 MHz test: write 200 counts (200*10000 = 2MHz) to TMR1
        # 14 MHz test: write 1400 counts (1400*10000 = 14MHz) to TMR1
        
        # Initial setup done above
        for _ in range(110):  # ~1.1 seconds startup
            lines.append("Stepi 80000")
            sample()
        
        # First frequency test: 2 MHz (160m band)
        # Write 200 to Timer1 (0x00C8)
        lines.append("write 0x20C 0xC8")  # TMR1L = 0xC8 (low byte of 200)
        lines.append("write 0x20D 0x00")  # TMR1H = 0x00 (high byte of 200)
        
        for _ in range(5):  # 50ms to capture measurement
            lines.append("Stepi 40000")
            sample()
        
        # Verify first band (should be BAND_160M = 1)
        # Now switch to second frequency: 14 MHz (20m band)
        # Write 1400 to Timer1 (0x0578)
        lines.append("write 0x20C 0x78")  # TMR1L = 0x78 (low byte of 1400)
        lines.append("write 0x20D 0x05")  # TMR1H = 0x05 (high byte of 1400)
        
        for _ in range(5):  # 50ms to capture measurement
            lines.append("Stepi 40000")
            sample()
        
        # Verify second band (should be BAND_20M = 4)
        lines.append("quit")
        return "\\n".join(lines)
    if not temperature_trip:'''

content = content.replace(old_pattern, new_pattern)

with open(fname, "w", encoding="utf-8") as f:
    f.write(content)

print("Successfully added TEST_FREQ stimulus to build_script()")
print("\nThe TEST_FREQ scenario will:")
print("1. Wait through startup inhibit (~1.1 seconds)")
print("2. Simulate 2 MHz square wave input (160m band selection)")
print("3. Simulate 14 MHz square wave input (20m band selection)")
print("4. Validate band transitions occur correctly")
