#!/usr/bin/env python3
"""Update trace_ppt_sequence.py to add TEST_FREQ scenario."""

with open("trace_ppt_sequence.py", "r") as f:
    content = f.read()

# 1. Update NON_TRIP_NAMES
content = content.replace(
    'NON_TRIP_NAMES = {"SWR1_1P5"}',
    'NON_TRIP_NAMES = {"SWR1_1P5", "TEST_FREQ"}'
)

# 2. Add validate_test_freq function before block_reason
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
    
    # Should see at least 2 different band values (2MHz and 14MHz transitions)
    unique_bands = set(bands)
    if len(unique_bands) < 2:
        raise AssertionError(f"Frequency counter did not transition between bands: {unique_bands}")
    
    # Final band should be 4 (BAND_20M for 14MHz)
    if bands[-1] != 4:
        raise AssertionError(f"Final band selection should be 4 (BAND_20M), got {bands[-1]}")

'''
content = content.replace(
    "\ndef block_reason(state: dict)",
    validate_func + "\ndef block_reason(state: dict)"
)

# 3. Update scenario_names in --suite section
content = content.replace(
    'scenario_names = [None, "TEMPERATURE", "SWR1", "SWR2", "HWFAULT",\n                          "CURRENT", "OVERDRIVE", "DRAIN", "SWR1_1P5"]',
    'scenario_names = [None, "TEMPERATURE", "SWR1", "SWR2", "HWFAULT",\n                          "CURRENT", "OVERDRIVE", "DRAIN", "SWR1_1P5", "TEST_FREQ"]'
)

# 4. Update validation dispatch in --suite
content = content.replace(
    '            if scenario == "SWR1_1P5":\n                validate_swr1_1p5(scenario_samples)\n            else:\n                validate_trip(scenario_samples, scenario)',
    '''            if scenario == "SWR1_1P5":
                validate_swr1_1p5(scenario_samples)
            elif scenario == "TEST_FREQ":
                validate_test_freq(scenario_samples)
            else:
                validate_trip(scenario_samples, scenario)'''
)

with open("trace_ppt_sequence.py", "w") as f:
    f.write(content)

print("Updated trace_ppt_sequence.py successfully")
