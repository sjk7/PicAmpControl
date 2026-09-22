#!/usr/bin/env python3
"""Pre-flight for a build or simulator run: leftovers killed, Defender checked.

Run this before any build or simulator job (sticky user instruction, 2026-09-22): an
interrupted wrapper, or a VS Code terminal that was closed mid-run, leaves MDB and its
JVM behind, and those stale processes make the next run look hung, slow, or flaky.

The patterns come from `run_suite_with_watchdog.ORPHAN_PATTERNS` so there is one list,
not two that drift apart.

It also reports whether the Windows Defender exclusions have been applied on this machine.
Those need administrator rights to install, and only an elevated shell can read them back,
so the installer leaves a marker file: no marker means "prompt the user to run
`tools/setup/windows-defender-exclusions.ps1` from an elevated PowerShell".
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import platform_process as procutil  # noqa: E402
import run_suite_with_watchdog as launcher  # noqa: E402

DEFENDER_MARKER = procutil.temp_dir() / "pac_defender_exclusions.txt"


def check_defender() -> None:
    if os.name != "nt":
        return
    if DEFENDER_MARKER.exists():
        return
    print("=" * 78)
    print("DEFENDER EXCLUSIONS NOT APPLIED ON THIS MACHINE")
    print("Defender real-time scanning of the simulator, XC8 and _build costs most of the")
    print("machine's CPU during a run. Fix it once, from an ELEVATED PowerShell:")
    print(r"    powershell -ExecutionPolicy Bypass -File tools\setup\windows-defender-exclusions.ps1")
    print("=" * 78)


def main():
    killed = 0
    for pid, command in procutil.running_processes():
        if pid == os.getpid():
            continue
        if any(pattern in command for pattern in launcher.ORPHAN_PATTERNS):
            if procutil.kill_tree(pid):
                print(f"killed pid={pid} :: {command[:160]}")
                killed += 1
    print(f"CLEANUP_KILLED={killed}")
    check_defender()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
