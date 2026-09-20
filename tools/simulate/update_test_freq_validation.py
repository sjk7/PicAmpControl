#!/usr/bin/env python3
"""Update validate_test_freq to check for actual band transitions."""
import glob

files = glob.glob("trace_p*.py")
if not files:
    exit("Error: trace_ppt_sequence.py not found")
fname = files[0]

with open(fname, "r", encoding="utf-8") as f:
    content = f.read()

old_validate = '''def validate_test_freq(samples) -> None:
    """Verify frequency counter infrastructure is initialized (simulator-limited test).
    
    NOTE: MDB simulator cannot write Timer1 registers, so full band-selection testing
    requires real hardware with RF input on RA7. This test verifies the infrastructure
    is present and firmware startup completes without errors.
    """
    if not samples:
        raise AssertionError("No samples captured during TEST_FREQ scenario")
    
    # Check that g_selected_band is being sampled
    bands = []
    for sample in samples:
        if "g_selected_band" in sample[2]:
            try:
                bands.append(int(sample[2]["g_selected_band"]))
            except:
                pass
    
    if not bands:
        raise AssertionError("g_selected_band not sampled (frequency counter not integrated)")
    
    # In simulator without Timer1 input, band should stay at 0 (BAND_NONE)
    if set(bands) != {0}:
        raise AssertionError(f"Expected BAND_NONE (0) in simulator, got {set(bands)}")
    
    print(f"Frequency counter infrastructure test passed (simulator verification only; full test requires real hardware)")'''

new_validate = '''def validate_test_freq(samples) -> None:
    """Verify frequency counter band selection transitions (2MHz→160M, 14MHz→20M).
    
    Firmware SIMULATE_FREQUENCY_COUNTER mode (when enabled with #define) injects 
    test Timer1 values to simulate 2MHz for 1s, then 14MHz for 1s. This validates
    the frequency→band logic without requiring actual RF input on RA7.
    """
    if not samples:
        raise AssertionError("No samples captured during TEST_FREQ scenario")
    
    # Extract g_selected_band values from samples
    bands = []
    for sample in samples:
        if "g_selected_band" in sample[2]:
            try:
                bands.append(int(sample[2]["g_selected_band"]))
            except:
                pass
    
    if not bands:
        raise AssertionError("g_selected_band not sampled (frequency counter not integrated)")
    
    # Verify we see both band 1 (160M) and band 4 (20M)
    unique_bands = set(bands)
    if 1 not in unique_bands or 4 not in unique_bands:
        raise AssertionError(f"Expected bands {{1, 4}} for 2MHz→14MHz test, got {unique_bands}")
    
    # Verify band 4 appears at the end (after 14MHz injection)
    if bands[-1] != 4:
        raise AssertionError(f"Expected final band 4 (BAND_20M), got {bands[-1]}")
    
    # Count transitions for diagnostics
    transitions = sum(1 for i in range(1, len(bands)) if bands[i] != bands[i-1])
    print(f"Frequency counter test passed: bands {unique_bands}, {transitions} transitions detected")'''

if old_validate in content:
    content = content.replace(old_validate, new_validate)
    with open(fname, "w", encoding="utf-8") as f:
        f.write(content)
    print("Updated validate_test_freq to check for band transitions")
else:
    print("Could not find validate_test_freq to replace")
