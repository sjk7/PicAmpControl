#!/usr/bin/env python3
"""Quick runner for just the TEST_FREQ scenario."""
import glob
import sys
import os

files = glob.glob("trace_p*.py")
if not files:
    sys.exit("Error: trace_ppt_sequence.py not found")
fname = files[0]

# Read and add g_selected_band to STATE_VARS if not present
with open(fname, "r", encoding="utf-8") as f:
    content = f.read()

# Add g_selected_band to STATE_VARS if missing
if 'g_selected_band' not in content[:2000]:  # Check in the first part where STATE_VARS is
    old_state_vars = '''STATE_VARS = [
    "g_startup_inhibit", "g_comparator_reset_active", "g_fault_latched", "g_trip_reason",
    "g_ptt_active", "g_sequence_stage", "g_state", "g_trip_shutdown_active",
    "g_ptt_complete_display_active", "g_transient_menu_display"
]'''
    
    new_state_vars = '''STATE_VARS = [
    "g_startup_inhibit", "g_comparator_reset_active", "g_fault_latched", "g_trip_reason",
    "g_ptt_active", "g_sequence_stage", "g_state", "g_trip_shutdown_active",
    "g_ptt_complete_display_active", "g_transient_menu_display", "g_selected_band"
]'''
    
    if old_state_vars in content:
        content = content.replace(old_state_vars, new_state_vars)
        with open(fname, "w", encoding="utf-8") as f:
            f.write(content)
        print("Added g_selected_band to STATE_VARS")

# Now run just the TEST_FREQ scenario
sys.path.insert(0, os.getcwd())
namespace = {"__name__": "__main__", "__file__": fname}
sys.argv = ["trace_ppt_sequence.py", "--trip", "TEST_FREQ"]

with open(fname, "r", encoding="utf-8") as f:
    exec(f.read(), namespace)
