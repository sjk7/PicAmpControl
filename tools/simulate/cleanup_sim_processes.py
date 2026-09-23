#!/usr/bin/env python3
r"""Pre-flight for a build or simulator run: leftovers killed, Defender checked.

Run this before any build or simulator job (sticky user instruction, 2026-09-22): an
interrupted wrapper, or a VS Code terminal that was closed mid-run, leaves MDB and its
JVM behind, and those stale processes make the next run look hung, slow, or flaky.

The patterns come from `run_suite_with_watchdog.ORPHAN_PATTERNS` so there is one list,
not two that drift apart.

It also checks the Windows Defender exclusions, at session start, because without them
Defender real-time scanning of the simulator, XC8 and `_build` eats most of the CPU during a
run (user report: "Defender is killing my pc").

The exclusion *list* cannot be read without elevation on Windows - verified 2026-09-22:
`Get-MpPreference` and the `MSFT_MpPreference` CIM class both answer "N/A: Must be an
administrator", the `...\Windows Defender\Exclusions\Paths` registry key denies access, and
even `MpCmdRun.exe -CheckExclusion` returns 0x80070005. `Get-MpComputerStatus` *does* work
unelevated, so the check uses it for the only question that matters here:

  real-time protection OFF   -> exclusions are moot, nothing to do
  ON + our record present    -> nothing to do
  ON + no record             -> raise the elevated installer (idempotent, self-closing)

That keeps the common case free of UAC prompts while still fixing a machine that has never
had the exclusions applied. The elevated installer does the authoritative per-entry check.
"""
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
DEFENDER_REPORT = procutil.temp_dir() / "pac_defender_exclusions.log"
DEFENDER_REQUEST = procutil.temp_dir() / "pac_defender_request.stamp"
RATE_LIMIT_SECONDS = 600


def powershell(script, timeout=60):
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command", script],
                             capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def real_time_protection_enabled():
    """True/False, or None when it cannot be determined.

    `Get-MpComputerStatus` is readable unelevated; the exclusion arrays next to it are not.
    """
    out = powershell("(Get-MpComputerStatus).RealTimeProtectionEnabled")
    if out is None:
        return None
    return out.lower().startswith("true")


def record_present():
    """Has a SUCCESS run recorded the exclusions on this machine?

    The marker file is the primary record; the installer's report is accepted as well, so
    losing the marker does not force another UAC prompt.
    """
    if DEFENDER_MARKER.exists():
        return True
    try:
        text = DEFENDER_REPORT.read_text(errors="replace")
    except OSError:
        return False
    return "VERDICT SUCCESS" in text and "FAILED" not in text


def install_defender_exclusions(why):
    if DEFENDER_REQUEST.exists():
        age = time.time() - DEFENDER_REQUEST.stat().st_mtime
        if age < RATE_LIMIT_SECONDS:
            print(f"  (installer already requested {int(age)}s ago; not asking again)")
            return
    DEFENDER_REQUEST.write_text(str(time.time()))
    args = (f"'-NoProfile','-ExecutionPolicy','Bypass','-File','{INSTALLER}',"
            f"'-NoPause','-AutoCloseSeconds','20'")
    try:
        subprocess.Popen(["powershell", "-NoProfile", "-Command",
                          f"Start-Process -FilePath powershell -Verb RunAs "
                          f"-ArgumentList @({args})"])
    except OSError as exc:
        print(f"  could not raise the elevated installer: {exc}")
        return
    print(f"  {why} - raised the elevated installer; approve the UAC prompt and it will fix it.")


def check_defender() -> None:
    if os.name != "nt":
        return
    rtp = real_time_protection_enabled()
    if rtp is False:
        print("Defender exclusions: real-time protection is off, so exclusions are moot.")
        return
    if rtp is None:
        print("Defender exclusions: could not read the Defender status; trying the record only.")
    if record_present():
        print("Defender exclusions: recorded as applied on this machine.")
        return
    print("=" * 78)
    print("DEFENDER EXCLUSIONS NOT RECORDED ON THIS MACHINE")
    print("Defender real-time scanning of the simulator, XC8 and _build eats most of the")
    print("machine's CPU during a run. (The exclusion list itself is admin-only, so this")
    print("check cannot read it without elevation - it uses the installer's own record.)")
    print("=" * 78)
    install_defender_exclusions("no record of the exclusions")


def live_run_processes():
    """Processes that are alive NOW and match ORPHAN_PATTERNS.

    Cleanup exists to clear *leftovers* before a run. A blind sweep cannot tell a leftover from a
    run in progress, and killing a live one is worse than doing nothing: the verdict is lost and the
    wrapper records `SUITE_EXIT=143` / `CTEST_EXIT=143` (SIGTERM), which reads like a test failure
    and is not one. Measured 2026-09-23: the merged suite was clean-killed this way twice, once at
    ~105 s with the suite's own PASS line already written and once before the first test started.
    """
    live = []
    for pid, command in procutil.running_processes():
        if pid == os.getpid():
            continue
        if any(pattern in command for pattern in launcher.ORPHAN_PATTERNS):
            live.append((pid, command))
    return live


def main():
    live = live_run_processes()
    if live:
        print("REFUSING TO CLEAN UP: a run appears to be in progress.")
        for pid, command in live:
            print(f"  live pid={pid} :: {command[:160]}")
        print("Those match the orphan patterns, so a blind sweep would kill the running test and")
        print("destroy its verdict (it would read as SUITE_EXIT=143). Let the run finish, or stop")
        print("it deliberately, then run this again.")
        print("CLEANUP_KILLED=0")
        check_defender()
        return 0

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
