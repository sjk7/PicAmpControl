#!/usr/bin/env python3
"""Pre-flight for a build or simulator run: leftovers killed, Defender checked.

Run this before any build or simulator job (sticky user instruction, 2026-09-22): an
interrupted wrapper, or a VS Code terminal that was closed mid-run, leaves MDB and its
JVM behind, and those stale processes make the next run look hung, slow, or flaky.

The patterns come from `run_suite_with_watchdog.ORPHAN_PATTERNS` so there is one list,
not two that drift apart.

It also checks the Windows Defender exclusions, at session start, because without them
Defender real-time scanning of the simulator, XC8 and `_build` eats most of the CPU during a
run (user report: "Defender is killing my pc").

Reading the exclusion list needs administrator rights, so the check tries three things in
order: read the real list (only possible when elevated), else trust the installer's success
marker, else run the installer elevated. Installing needs a UAC approval, so a request is
rate-limited to one per RATE_LIMIT_SECONDS and the elevated window closes itself a few seconds
after a SUCCESS run (it stays open on failure, showing why).
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import platform_process as procutil  # noqa: E402
import run_suite_with_watchdog as launcher  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
INSTALLER = REPO_ROOT / "tools/setup/windows-defender-exclusions.ps1"
DEFENDER_MARKER = procutil.temp_dir() / "pac_defender_exclusions.ok"
DEFENDER_REQUEST = procutil.temp_dir() / "pac_defender_request.stamp"
RATE_LIMIT_SECONDS = 600
EXPECTED_PATHS = (
    r"E:\hamcode\PicAmpControl",
    r"C:\Program Files\Microchip",
    r"C:\Python314",
    r"C:\Python313",
)
EXPECTED_PROCS = (
    "xc8-cc.exe", "xc8.exe", "xc8-ld.exe", "mdb.bat", "java.exe", "javaw.exe",
    "mplab_backend64.exe", "python.exe", "python3.13.exe", "pythonw.exe",
    "cmake.exe", "ctest.exe", "ninja.exe", "clangd.exe",
)


def read_defender_lists():
    """(paths, processes) as the machine reports them, or None if we cannot read them.

    A non-elevated Get-MpPreference does not fail: it returns placeholder strings saying an
    administrator is required. Those are reported as "unreadable" rather than as "no
    exclusions", because treating them as missing would mean installing on every single run.
    """
    script = ("$p=Get-MpPreference; @{paths=@($p.ExclusionPath);"
              "procs=@($p.ExclusionProcess)} | ConvertTo-Json -Compress")
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command", script],
                             capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0 or not out.stdout.strip():
        return None
    try:
        data = json.loads(out.stdout.strip())
    except json.JSONDecodeError:
        return None
    paths = [str(v) for v in (data.get("paths") or [])]
    procs = [str(v) for v in (data.get("procs") or [])]
    if any("administrator" in v.lower() for v in paths + procs):
        return None
    return paths, procs


def missing_exclusions(lists):
    if lists is None:
        return None
    paths, procs = lists
    lowered_paths = {p.rstrip("\\").lower() for p in paths}
    lowered_procs = {p.lower() for p in procs}
    missing = [p for p in EXPECTED_PATHS
               if Path(p).exists() and p.rstrip("\\").lower() not in lowered_paths]
    missing += [p for p in EXPECTED_PROCS if p.lower() not in lowered_procs]
    return missing


def install_defender_exclusions(missing):
    if DEFENDER_REQUEST.exists():
        age = time.time() - DEFENDER_REQUEST.stat().st_mtime
        if age < RATE_LIMIT_SECONDS:
            print(f"  (installer already requested {int(age)}s ago; not asking again)")
            return
    DEFENDER_REQUEST.write_text(str(time.time()))
    args = f"'-NoProfile','-ExecutionPolicy','Bypass','-File','{INSTALLER}'," \
           f"'-NoPause','-AutoCloseSeconds','20'"
    try:
        subprocess.Popen(["powershell", "-NoProfile", "-Command",
                          f"Start-Process -FilePath powershell -Verb RunAs "
                          f"-ArgumentList @({args})"])
    except OSError as exc:
        print(f"  could not raise the elevated installer: {exc}")
        return
    print("  Raised the elevated installer - approve the UAC prompt and it will fix this.")


def check_defender() -> None:
    if os.name != "nt":
        return
    lists = read_defender_lists()
    missing = missing_exclusions(lists)
    if missing is None:
        if DEFENDER_MARKER.exists():
            print("Defender exclusions: marker present (cannot read the list unelevated).")
            return
        print("=" * 78)
        print("DEFENDER EXCLUSIONS NOT VERIFIED ON THIS MACHINE")
        print("Defender real-time scanning of the simulator, XC8 and _build eats most of the")
        print("machine's CPU during a run. Asking for the elevated installer now.")
        print("=" * 78)
        install_defender_exclusions(missing)
        return
    if not missing:
        DEFENDER_MARKER.write_text(f"verified {time.strftime('%Y-%m-%dT%H:%M:%S')}")
        print("Defender exclusions: all present.")
        return
    print("=" * 78)
    print("DEFENDER EXCLUSIONS MISSING: " + ", ".join(missing[:6])
          + (" ..." if len(missing) > 6 else ""))
    print("=" * 78)
    install_defender_exclusions(missing)


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
