#!/usr/bin/env python3
"""Add g_selected_band to STATE_VARS and TEST_FREQ to TRIP_ADC_PINS."""
import glob
import sys

files = glob.glob("trace_p*.py")
if not files:
    sys.exit("Error: trace_ppt_sequence.py not found")

fname = files[0]

with open(fname, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add g_selected_band to STATE_VARS
old_state_vars = '''STATE_VARS = [
    "g_startup_inhibit", "g_comparator_reset_active", "g_fault_latched", "g_trip_reason",
    "g_ptt_active", "g_sequence_stage", "g_state", "g_trip_shutdown_active",
    "g_ppt_complete_display_active", "g_transient_menu_display"
]'''

new_state_vars = '''STATE_VARS = [
    "g_startup_inhibit", "g_comparator_reset_active", "g_fault_latched", "g_trip_reason",
    "g_ppt_active", "g_sequence_stage", "g_state", "g_trip_shutdown_active",
    "g_ppt_complete_display_active", "g_transient_menu_display", "g_selected_band"
]'''

content = content.replace(old_state_vars, new_state_vars)

# 2. Add TEST_FREQ to TRIP_ADC_PINS
old_trip_adc = '''TRIP_ADC_PINS = {
    "SWR1": ["RA0", "RA1"], "SWR2": ["RA2", "RA3"],
    "SWR1_1P5": ["RA0", "RA1"],
    "TEMPERATURE": ["RA5"], "CURRENT": ["RB1"],
    "OVERDRIVE": ["RB2"], "DRAIN": ["RB3"], "HWFAULT": []
}'''

new_trip_adc = '''TRIP_ADC_PINS = {
    "SWR1": ["RA0", "RA1"], "SWR2": ["RA2", "RA3"],
    "SWR1_1P5": ["RA0", "RA1"],
    "TEMPERATURE": ["RA5"], "CURRENT": ["RB1"],
    "OVERDRIVE": ["RB2"], "DRAIN": ["RB3"], "HWFAULT": [], "TEST_FREQ": []
}'''

content = content.replace(old_trip_adc, new_trip_adc)

with open(fname, "w", encoding="utf-8") as f:
    f.write(content)

print("Successfully updated:")
print("1. Added g_selected_band to STATE_VARS")
print("2. Added TEST_FREQ to TRIP_ADC_PINS")
print("\nNow g_selected_band will be sampled during TEST_FREQ simulation")
