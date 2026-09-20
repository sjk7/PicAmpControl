#!/usr/bin/env python3
"""Run trace_ppt_sequence.py --suite by importing directly."""
import glob
import sys
import os

# Find the script
files = glob.glob("trace_p*.py")
if not files:
    print("Error: trace_ppt_sequence.py not found")
    sys.exit(1)

script_path = files[0]
print(f"Running {script_path} with --suite")

# Add current directory to path so imports work
sys.path.insert(0, os.getcwd())

# Load and execute the script
with open(script_path, "r", encoding="utf-8") as f:
    script_content = f.read()

# Create a module namespace
namespace = {"__name__": "__main__", "__file__": script_path}

# Set sys.argv for the script
sys.argv = ["trace_ppt_sequence.py", "--suite"]

# Execute
exec(script_content, namespace)
