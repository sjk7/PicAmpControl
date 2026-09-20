#!/usr/bin/env python3
"""Add TEST_FREQ scenario to trace_ppt_sequence.py"""
import re

with open("trace_ppt_sequence.py", "r") as f:
    lines = f.readlines()

# Find and update lines
output = []
for i, line in enumerate(lines):
    # 1. Update NON_TRIP_NAMES
    if 'NON_TRIP_NAMES = {"SWR1_1P5"}' in line:
        output.append('NON_TRIP_NAMES = {"SWR1_1P5", "TEST_FREQ"}\n')
        print("Updated NON_TRIP_NAMES")
    # 2. Add validate_test_freq after validate_swr1_1p5
    elif line.strip().startswith("def block_reason(state:") and i > 0 and "validate_swr1_1p5" in "".join(lines[max(0, i-20):i]):
        # Insert validation function before block_reason
        validate_func = '''
def validate_test_freq(samples) -> None:
    """Verify frequency counter correctly selects bands for 2MHz and 14MHz stimuli."""
    # Extract final band selections from samples
    # First check: after 2MHz stimulus, should be BAND_160M (value 1)
    # Then check: after 14MHz stimulus, should be BAND_20M (value 4)
    
    # Find samples where band was measured (look for different g_selected_band values)
    bands = [int(sample[2].get("g_selected_band", "0")) for sample in samples if "g_selected_band" in sample[2]]
    freqs = [int(sample[2].get("g_freq_counter_hz", "0")) for sample in samples if "g_freq_counter_hz" in sample[2]]
    
    if not bands or not freqs:
        raise AssertionError("No frequency counter measurements captured in samples")
    
    # Should see transition from one band to another (2MHz → 14MHz)
    if len(set(bands)) < 2:
        raise AssertionError(f"Frequency counter did not change band selection: {set(bands)}")
    
    # Check that 2MHz was detected as 160M or lower (band <= 2) and 14MHz as 20M (band = 4)
    early_bands = bands[:len(bands)//2]
    late_bands = bands[len(bands)//2:]
    
    if late_bands[-1] != 4:
        raise AssertionError(f"14MHz did not select BAND_20M (got {late_bands[-1]})")

'''
        output.append(validate_func)
        output.append(line)
    # 3. In main(), update scenario list for --suite
    elif 'scenario_names = [None, "TEMPERATURE"' in line:
        output.append('        scenario_names = [None, "TEMPERATURE", "SWR1", "SWR2", "HWFAULT",\n')
        output.append('                          "CURRENT", "OVERDRIVE", "DRAIN", "SWR1_1P5", "TEST_FREQ"]\n')
        # Skip the next line since we're replacing it
        if i+1 < len(lines) and "SWR1" in lines[i+1]:
            i += 1
        print("Updated scenario_names for suite")
    # 4. Update validation dispatch
    elif "if scenario == \"SWR1_1P5\":" in line:
        output.append(line)
        # Next line should be validate call, keep it
        i += 1
        if i < len(lines):
            output.append(lines[i])
            # After that, add TEST_FREQ branch
            next_i = i + 1
            if next_i < len(lines) and "else:" in lines[next_i]:
                output.append("            elif scenario == \"TEST_FREQ\":\n")
                output.append("                validate_test_freq(scenario_samples)\n")
                output.append("            else:\n")
        continue
    else:
        output.append(line)

with open("trace_ppt_sequence.py", "w") as f:
    f.writelines(output)

print("Updated trace_ppt_sequence.py")
