#!/usr/bin/env python3
"""Update trace_ppt_sequence.py to add TEST_FREQ frequency counter scenario."""
import sys
import os
import glob

# Change to simulate directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Find the file using glob
files = glob.glob("trace_p*.py")
if not files:
    sys.exit("Error: trace_ppt_sequence.py not found")
fname = files[0]

# Read the file with explicit encoding
with open(fname, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update NON_TRIP_NAMES
print("Updating NON_TRIP_NAMES...")
content = content.replace(
    'NON_TRIP_NAMES = {"SWR1_1P5"}',
    'NON_TRIP_NAMES = {"SWR1_1P5", "TEST_FREQ"}'
)

# 2. Add validate_test_freq function before parse_trace
print("Adding validate_test_freq function...")
validate_func = '''

def validate_test_freq(samples) -> None:
    """Verify frequency counter correctly selects bands for 2MHz and 14MHz stimuli."""
    bands = []
    for sample in samples:
        if "g_selected_band" in sample[2]:
            try:
                bands.append(int(sample[2]["g_selected_band"]))
            except:
                pass
    
    if not bands:
        raise AssertionError("No frequency counter measurements found")
    
    unique_bands = set(bands)
    if len(unique_bands) < 2:
        raise AssertionError(f"Frequency counter did not transition between bands: {unique_bands}")
    
    if bands[-1] != 4:
        raise AssertionError(f"Final band selection should be 4 (BAND_20M), got {bands[-1]}")
    
    print(f"Frequency counter test passed: band transitions {unique_bands}, final BAND_20M (4)")
'''
content = content.replace(
    "\ndef parse_trace(output: str):",
    validate_func + "\ndef parse_trace(output: str):"
)

# 3. Update scenario_names in --suite  
print("Updating scenario_names list...")
content = content.replace(
    'scenario_names = [None, "TEMPERATURE", "SWR1", "SWR2", "HWFAULT",\n                          "CURRENT", "OVERDRIVE", "DRAIN", "SWR1_1P5"]',
    'scenario_names = [None, "TEMPERATURE", "SWR1", "SWR2", "HWFAULT",\n                          "CURRENT", "OVERDRIVE", "DRAIN", "SWR1_1P5", "TEST_FREQ"]'
)

# 4. Update validation dispatch in --suite
print("Updating suite validation dispatch...")
content = content.replace(
    '            if scenario == "SWR1_1P5":\n                validate_swr1_1p5(scenario_samples)\n            else:\n                validate_trip(scenario_samples, scenario)',
    '''            if scenario == "SWR1_1P5":
                validate_swr1_1p5(scenario_samples)
            elif scenario == "TEST_FREQ":
                validate_test_freq(scenario_samples)
            else:
                validate_trip(scenario_samples, scenario)'''
)

# 5. Update single-run validation dispatch
print("Updating single-run validation dispatch...")
content = content.replace(
    '    if trip_name:\n        if trip_name in TRIP_NAMES:\n            validate_trip(samples, trip_name)\n        else:\n            validate_swr1_1p5(samples)',
    '''    if trip_name:
        if trip_name in TRIP_NAMES:
            validate_trip(samples, trip_name)
        elif trip_name == "TEST_FREQ":
            validate_test_freq(samples)
        else:
            validate_swr1_1p5(samples)'''
)

# Write back
with open(fname, "w", encoding="utf-8") as f:
    f.write(content)

print(f"Successfully updated {fname}")
print("\nNow TEST_FREQ can be used with:")
print("  python trace_ppt_sequence.py --trip TEST_FREQ")
print("  or included automatically in: python trace_ppt_sequence.py --suite")
