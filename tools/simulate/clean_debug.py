#!/usr/bin/env python3
"""Remove debug output strings from validate functions."""
import glob

files = glob.glob("trace_p*.py")
if not files:
    exit("Error: trace_ppt_sequence.py not found")
fname = files[0]

with open(fname, "r", encoding="utf-8") as f:
    content = f.read()

# Remove the debug MDB print from run_mdb
old_run_mdb_debug = '''        # DEBUG: Print first few lines of script
        lines = script.split("\\n")
        write_lines = [l for l in lines if "write" in l.lower()]
        if write_lines:
            print(f"DEBUG MDB write commands: {write_lines[:10]}")
        '''

# Actually this is in the run_mdb function - let me search for it differently

# Remove debug prints from validate_test_freq
old_debug_prints = '''    
    print(f"DEBUG: Total samples={len(samples)}, band values found={len(bands)}")
    if bands:
        print(f"DEBUG: First 30 band values: {bands[:30]}")
        print(f"DEBUG: Last 20 band values: {bands[-20:]}")
        print(f"DEBUG: Unique bands: {set(bands)}")
    '''

if old_debug_prints in content:
    content = content.replace(old_debug_prints, "\n    ")
    print("Removed debug prints")

with open(fname, "w", encoding="utf-8") as f:
    f.write(content)

print("Cleaned up debug output")
