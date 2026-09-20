#!/usr/bin/env python3
"""Fix TEST_FREQ stimulus with correct MDB syntax for Timer1 writes."""
import glob

files = glob.glob("trace_p*.py")
if not files:
    exit("Error: trace_ppt_sequence.py not found")
fname = files[0]

with open(fname, "r", encoding="utf-8") as f:
    content = f.read()

# Find and replace the Timer1 write commands with correct syntax
old_stimulus = '''    if trip_name == "TEST_FREQ":
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
        return "\\n".join(lines)'''

new_stimulus = '''    if trip_name == "TEST_FREQ":
        # Test frequency counter: first 2MHz (160m band), then 14MHz (20m band)
        # Measurement period: 100ms; calibration: *10000 to convert Timer1 counts to Hz
        # 2 MHz test: write 200 counts (200*10000 = 2MHz) to TMR1
        # 14 MHz test: write 1400 counts (1400*10000 = 14MHz) to TMR1
        
        # Initial setup done above
        for _ in range(110):  # ~1.1 seconds startup
            lines.append("Stepi 80000")
            sample()
        
        # First frequency test: 2 MHz (160m band)
        # Write 200 to Timer1: TMR1 = 0x00C8
        lines.append("write TMR1L 0xC8")  # Low byte of 200
        lines.append("write TMR1H 0x00")  # High byte of 200
        
        for _ in range(5):  # 50ms to capture measurement
            lines.append("Stepi 40000")
            sample()
        
        # Verify first band (should be BAND_160M = 1)
        # Now switch to second frequency: 14 MHz (20m band)
        # Write 1400 to Timer1: TMR1 = 0x0578
        lines.append("write TMR1L 0x78")  # Low byte of 1400
        lines.append("write TMR1H 0x05")  # High byte of 1400
        
        for _ in range(5):  # 50ms to capture measurement
            lines.append("Stepi 40000")
            sample()
        
        # Verify second band (should be BAND_20M = 4)
        lines.append("quit")
        return "\\n".join(lines)'''

if old_stimulus in content:
    content = content.replace(old_stimulus, new_stimulus)
    with open(fname, "w", encoding="utf-8") as f:
        f.write(content)
    print("Fixed Timer1 write syntax in TEST_FREQ stimulus")
else:
    print("Warning: Could not find old stimulus code to replace")
