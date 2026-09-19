#!/usr/bin/env python3
"""
Schematic Watch & Render - Auto-regenerates SVG on changes

Run this in a terminal to watch for component changes and auto-render SVG:
  $ python tools/watch_and_render.py

The SVG will update in VS Code Insiders automatically.
"""

import json
import time
from pathlib import Path
from subprocess import run, PIPE
import sys


def get_file_hash(filepath: Path) -> str:
    """Get hash of file for change detection"""
    if not filepath.exists():
        return ""
    
    import hashlib
    with open(filepath, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()


def regenerate_svg():
    """Run the SVG renderer"""
    print("\n[RENDER] Regenerating SVG...", flush=True)
    result = run(
        [sys.executable, 'tools/svg_renderer.py'],
        cwd='.',
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print(result.stdout, flush=True)
        return True
    else:
        print(f"[ERROR] SVG generation failed:\n{result.stderr}", flush=True)
        return False


def regenerate_specs():
    """Run the EasyEDA Pro generator"""
    print("\n[GEN] Regenerating component specs...", flush=True)
    result = run(
        [sys.executable, 'tools/easyeda_pro_generator.py'],
        cwd='.',
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print(result.stdout, flush=True)
        regenerate_svg()
        return True
    else:
        print(f"[ERROR] Generator failed:\n{result.stderr}", flush=True)
        return False


def watch_and_render():
    """Watch for changes and render"""
    print("=" * 70)
    print("Schematic Watch & Render - Auto-updating SVG")
    print("=" * 70)
    print("\nMonitoring for changes...")
    print("  • tools/easyeda_pro_generator.py")
    print("  • out/picampcontrol_easyeda_agent.json")
    print("\nPress Ctrl+C to stop")
    print("\nSVG will auto-update in VS Code Insiders on changes")
    print("=" * 70 + "\n")
    
    # Track hashes
    generator_hash = get_file_hash(Path('tools/easyeda_pro_generator.py'))
    spec_hash = get_file_hash(Path('out/picampcontrol_easyeda_agent.json'))
    
    # Initial render
    regenerate_specs()
    
    try:
        while True:
            time.sleep(1)  # Check every 1 second
            
            # Check if generator changed
            new_gen_hash = get_file_hash(Path('tools/easyeda_pro_generator.py'))
            if new_gen_hash and new_gen_hash != generator_hash:
                print("\n[DETECT] tools/easyeda_pro_generator.py changed")
                if regenerate_specs():
                    generator_hash = new_gen_hash
                    spec_hash = get_file_hash(Path('out/picampcontrol_easyeda_agent.json'))
            
            # Check if specs changed
            new_spec_hash = get_file_hash(Path('out/picampcontrol_easyeda_agent.json'))
            if new_spec_hash and new_spec_hash != spec_hash:
                print("\n[DETECT] Component specs changed")
                if regenerate_svg():
                    spec_hash = new_spec_hash
    
    except KeyboardInterrupt:
        print("\n\n[STOP] Watch terminated by user")
        print("=" * 70)


if __name__ == '__main__':
    watch_and_render()
