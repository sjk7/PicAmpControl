#!/usr/bin/env python3
"""Debug version that shows all g_selected_band values."""
import glob
import sys
import os

files = glob.glob("trace_p*.py")
if not files:
    sys.exit("Error: trace_ppt_sequence.py not found")
fname = files[0]

sys.path.insert(0, os.getcwd())
namespace = {"__name__": "__main__", "__file__": fname}
sys.argv = ["trace_ppt_sequence.py", "--trip", "TEST_FREQ"]

with open(fname, "r", encoding="utf-8") as f:
    script_content = f.read()

# Hook the validate_test_freq function to show details
inject_debug = '''
# DEBUG: Show all samples and band values
import sys
original_validate = validate_test_freq

def debug_validate_test_freq(samples):
    print(f"\\nDEBUG: Total samples: {len(samples)}")
    bands = []
    for i, sample in enumerate(samples):
        state = sample[2]
        if "g_selected_band" in state:
            try:
                band = int(state["g_selected_band"])
                bands.append(band)
                if i % 10 == 0 or band != bands[i-1] if i > 0 else False:
                    print(f"  Sample {i}: g_selected_band={band}")
            except:
                pass
    
    print(f"DEBUG: Unique bands: {set(bands)}")
    print(f"DEBUG: Band sequence: {bands[:20]}...")  # First 20 samples
    
    # Call original validation
    return original_validate(samples)

validate_test_freq = debug_validate_test_freq
'''

# Insert debug hook before the exec
script_content = inject_debug + script_content

exec(script_content, namespace)
