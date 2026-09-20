#!/usr/bin/env python3
"""Inject debug output into validate_test_freq."""
import glob

files = glob.glob("trace_p*.py")
if not files:
    exit("Error: trace_ppt_sequence.py not found")
fname = files[0]

with open(fname, "r", encoding="utf-8") as f:
    content = f.read()

# Replace validate_test_freq with a debug version
old_validate = '''def validate_test_freq(samples) -> None:
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
    
    print(f"Frequency counter test passed: band transitions {unique_bands}, final BAND_20M (4)")'''

new_validate = '''def validate_test_freq(samples) -> None:
    """Verify frequency counter correctly selects bands for 2MHz and 14MHz stimuli."""
    bands = []
    for sample in samples:
        if "g_selected_band" in sample[2]:
            try:
                bands.append(int(sample[2]["g_selected_band"]))
            except:
                pass
    
    print(f"DEBUG: Total samples={len(samples)}, band values found={len(bands)}")
    if bands:
        print(f"DEBUG: First 30 band values: {bands[:30]}")
        print(f"DEBUG: Last 20 band values: {bands[-20:]}")
        print(f"DEBUG: Unique bands: {set(bands)}")
    
    if not bands:
        raise AssertionError("No frequency counter measurements found")
    
    unique_bands = set(bands)
    if len(unique_bands) < 2:
        raise AssertionError(f"Frequency counter did not transition between bands: {unique_bands}")
    
    if bands[-1] != 4:
        raise AssertionError(f"Final band selection should be 4 (BAND_20M), got {bands[-1]}")
    
    print(f"Frequency counter test passed: band transitions {unique_bands}, final BAND_20M (4)")'''

if old_validate in content:
    content = content.replace(old_validate, new_validate)
    with open(fname, "w", encoding="utf-8") as f:
        f.write(content)
    print("Added debug output to validate_test_freq")
else:
    print("Could not find validate_test_freq to modify")
