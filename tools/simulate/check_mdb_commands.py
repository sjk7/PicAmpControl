#!/usr/bin/env python3
"""Check what MDB commands are actually being sent."""
import glob

files = glob.glob("trace_p*.py")
if not files:
    exit("Error: trace_ppt_sequence.py not found")
fname = files[0]

with open(fname, "r", encoding="utf-8") as f:
    content = f.read()

# Find run_mdb function and add debug output
old_run_mdb = '''def run_mdb(mdb_path: Path, script: str) -> str:
    """Invoke mdb.bat with the script, return the output."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".mdb", delete=False) as tmp:
        tmp.write(script)
        tmp_path = tmp.name
    try:
        output = subprocess.check_output([str(mdb_path), tmp_path], text=True, stderr=subprocess.STDOUT)
    finally:
        Path(tmp_path).unlink()
    return output'''

new_run_mdb = '''def run_mdb(mdb_path: Path, script: str) -> str:
    """Invoke mdb.bat with the script, return the output."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".mdb", delete=False) as tmp:
        tmp.write(script)
        tmp_path = tmp.name
    try:
        # DEBUG: Print first few lines of script
        lines = script.split("\\n")
        write_lines = [l for l in lines if "write" in l.lower()]
        if write_lines:
            print(f"DEBUG MDB write commands: {write_lines[:10]}")
        
        output = subprocess.check_output([str(mdb_path), tmp_path], text=True, stderr=subprocess.STDOUT)
    finally:
        Path(tmp_path).unlink()
    return output'''

if old_run_mdb in content:
    content = content.replace(old_run_mdb, new_run_mdb)
    with open(fname, "w", encoding="utf-8") as f:
        f.write(content)
    print("Added MDB script debug output")
else:
    print("Could not find run_mdb to modify")
