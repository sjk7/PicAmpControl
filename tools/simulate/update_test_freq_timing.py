#!/usr/bin/env python3
"""Update TEST_FREQ scenario to capture frequency transitions (2MHz→14MHz)."""
import glob

files = glob.glob("trace_p*.py")
if not files:
    exit("Error: trace_ppt_sequence.py not found")
fname = files[0]

with open(fname, "r", encoding="utf-8") as f:
    content = f.read()

# Update the TEST_FREQ stimulus to run longer
old_stimulus = '''    if trip_name == "TEST_FREQ":
        # Frequency counter test: verify firmware is ready
        # NOTE: MDB simulator cannot write Timer1 registers (only supports pin writes).
        # Real frequency counter testing requires hardware with RF input on RA7.
        # This test just verifies startup completes and g_selected_band is initialized.
        
        for _ in range(110):  # ~1.1 seconds startup
            lines.append("Stepi 80000")
            sample()
        
        # Verify band is initialized (expect BAND_NONE = 0 since no Timer1 input)
        for _ in range(10):  # Capture a few more samples
            lines.append("Stepi 40000")
            sample()
        
        lines.append("quit")
        return "\\n".join(lines)'''

new_stimulus = '''    if trip_name == "TEST_FREQ":
        # Frequency counter test: verify band selection transitions
        # NOTE: Firmware SIMULATE_FREQUENCY_COUNTER mode injects test values into Timer1.
        # The test cycles: 2MHz for 1s (BAND_160M), then 14MHz for 1s (BAND_20M).
        # This simulates the firmware's frequency measurement + band detection logic.
        
        for _ in range(110):  # ~1.1 seconds startup
            lines.append("Stepi 80000")
            sample()
        
        # First frequency: 2 MHz (160m band) - capture for ~1 second
        for _ in range(100):  # 100 * 10ms = 1000ms
            lines.append("Stepi 80000")
            sample()
        
        # Second frequency: 14 MHz (20m band) - capture for ~1 second
        for _ in range(100):  # 100 * 10ms = 1000ms
            lines.append("Stepi 80000")
            sample()
        
        lines.append("quit")
        return "\\n".join(lines)'''

if old_stimulus in content:
    content = content.replace(old_stimulus, new_stimulus)
    with open(fname, "w", encoding="utf-8") as f:
        f.write(content)
    print("Updated TEST_FREQ scenario to capture frequency transitions")
else:
    print("Could not find TEST_FREQ stimulus to replace")
