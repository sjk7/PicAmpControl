#!/usr/bin/env python3
"""Cross-platform process plumbing shared by the MDB-driven simulator harnesses.

Every harness in this directory drives MPLAB's `mdb` as a child process and has to
be able to abandon a run that has hung inside its JVM. That teardown is the one
part of the harnesses that cannot be written once for both platforms:

* POSIX gives each run its own session/process group (`start_new_session=True`)
  and tears the tree down with `os.killpg` + `signal.SIGKILL`.
* Windows has no signalable process groups. The same isolation comes from
  `CREATE_NEW_PROCESS_GROUP` (so a Ctrl-C aimed at the parent's console is not
  forwarded into `mdb`) and the tree is torn down with `taskkill /T /F`.

This module is the single place that knows the difference, so the harnesses keep
one code path. It is deliberately dependency-free - no matplotlib, no invariant
imports - because `run_suite_with_watchdog.py` imports it while it is still a thin
launcher that must not drag the plotting stack in with it.

Two Windows traps are handled here rather than at each call site:

* **Never probe liveness with `os.kill(pid, 0)`.** Python's Windows `os.kill` maps
  every signal other than `CTRL_C_EVENT`/`CTRL_BREAK_EVENT` onto `TerminateProcess`,
  so "is this process still alive?" would answer by killing it. `pid_is_alive()`
  uses `OpenProcess`/`GetExitCodeProcess` instead.
* **`signal.SIGKILL` does not exist at all on Windows.** Any module-level or
  default-argument reference to it raises `AttributeError` before anything runs,
  so the signal constants are resolved inside the POSIX branches only.
"""
from __future__ import annotations

import glob
import os
import subprocess
import sys
import tempfile
from pathlib import Path

WINDOWS = sys.platform == "win32"

# `taskkill` is the only supported way to kill a whole tree on Windows. Without
# /F it posts WM_CLOSE, which the mdb JVM (a console app) ignores, so /T /F it is.


def temp_dir() -> Path:
    """Per-user temp directory.

    `/tmp` does not exist on Windows; `tempfile.gettempdir()` resolves to
    `%TEMP%` there and to `/tmp` (or `$TMPDIR`) on the POSIX side.
    """
    return Path(tempfile.gettempdir())


# MPLAB X installs one versioned directory per release. `sort -V` is used by
# tools/simulate/run_sim.sh for this; a plain lexicographic sort would order
# "v6.9" after "v6.35", so the version tuple is compared instead.
MPLAB_INSTALL_GLOBS = (
    "C:/Program Files/Microchip/MPLABX/*/mplab_platform/bin/mdb.bat",
    "C:/Program Files (x86)/Microchip/MPLABX/*/mplab_platform/bin/mdb.bat",
    "/Applications/microchip/mplabx/*/mplab_platform/bin/mdb.sh",
)


def find_mdb() -> Path:
    """Locate MPLAB X's headless `mdb` launcher, newest installation first.

    `MPLABX_MDB` overrides the search, which is the escape hatch for a non-standard
    install root (the same override XC8 gets from `XC8_BIN_DIR`). Exits with the
    install hint rather than returning None, because every caller needs it.
    """
    override = os.environ.get("MPLABX_MDB")
    if override:
        candidate = Path(override)
        if not candidate.exists():
            sys.exit(f"error: MPLABX_MDB points at {candidate}, which does not exist.")
        return candidate
    candidates = []
    for pattern in MPLAB_INSTALL_GLOBS:
        # glob.glob rather than Path.glob: these patterns are absolute, and pathlib
        # has rejected absolute patterns since Python 3.13.
        candidates.extend(Path(match) for match in glob.glob(pattern))
    if not candidates:
        sys.exit(
            "error: mdb not found. Install MPLAB X IDE "
            "(Windows: the MPLAB X IDE installer; macOS: brew install --cask mplabx-ide), "
            "or set MPLABX_MDB to the mdb.bat/mdb.sh path."
        )
    return max(candidates, key=lambda path: _version_key(path.parts[-4]))


def _version_key(version: str) -> tuple:
    """Order MPLAB install directories by release, not lexicographically."""
    return tuple(int(part) for part in version.lstrip("v").split(".") if part.isdigit())


def isolated_spawn_kwargs() -> dict:
    """`Popen` kwargs that detach a child from the caller's console.

    On POSIX this is `start_new_session=True`; on Windows that argument is accepted
    but silently ignored, so the equivalent flag has to be passed as a creation flag.
    """
    if WINDOWS:
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    return {"start_new_session": True}


def pid_is_alive(pid: int) -> bool:
    """True if `pid` names a live process we are allowed to ask about.

    Returns False for a pid that no longer exists, and True when the process exists
    but belongs to another user (access denied) - that is a live process either way.
    """
    if pid <= 0:
        return False
    if WINDOWS:
        return _windows_pid_is_alive(pid)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _windows_pid_is_alive(pid: int) -> bool:
    import ctypes
    from ctypes import wintypes

    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    ERROR_ACCESS_DENIED = 5
    STILL_ACTIVE = 259

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return ctypes.get_last_error() == ERROR_ACCESS_DENIED
    try:
        code = wintypes.DWORD()
        if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
            return True
        return code.value == STILL_ACTIVE
    finally:
        kernel32.CloseHandle(handle)


def terminate_tree(pid: int) -> bool:
    """Politely ask a process and everything below it to stop.

    On Windows there is no polite option that console applications honour, so this
    degrades to `taskkill /T /F`; POSIX gets a real `SIGTERM` to the process group.
    Returns True when a kill was attempted without the target already being gone.
    """
    if pid <= 0:
        return False
    if WINDOWS:
        return _windows_taskkill(pid)
    try:
        os.killpg(os.getpgid(pid), _sigterm())
    except (ProcessLookupError, PermissionError):
        return False
    return True


def kill_tree(pid: int) -> bool:
    """Forcefully kill a process and its descendants (POSIX `SIGKILL` / `taskkill /F`)."""
    if pid <= 0:
        return False
    if WINDOWS:
        return _windows_taskkill(pid)
    try:
        os.killpg(os.getpgid(pid), _sigkill())
    except (ProcessLookupError, PermissionError):
        return False
    return True


def _windows_taskkill(pid: int) -> bool:
    result = subprocess.run(
        ["taskkill", "/PID", str(pid), "/T", "/F"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    # Exit 128 means "process not found": already gone, which is a fine outcome.
    return result.returncode == 0


def _sigterm():
    import signal
    return signal.SIGTERM


def _sigkill():
    import signal
    # Windows defines no SIGKILL, so this is only ever reached on POSIX.
    return signal.SIGKILL


def running_processes() -> list[tuple[int, str]]:
    """Snapshot every process as `(pid, command_line)`.

    POSIX uses `ps -axo pid=,command=`. Windows has no equivalent `ps`, and `wmic` is
    deprecated and absent from current Windows builds, so the PowerShell CIM provider
    is used; its command lines are what `Win32_Process` recorded at creation.
    """
    if WINDOWS:
        return _windows_running_processes()
    try:
        output = subprocess.check_output(
            ["ps", "-axo", "pid=,command="], text=True, stderr=subprocess.DEVNULL
        )
    except (OSError, subprocess.CalledProcessError):
        return []
    processes = []
    for line in output.splitlines():
        fields = line.strip().split(None, 1)
        if len(fields) != 2 or not fields[0].isdigit():
            continue
        processes.append((int(fields[0]), fields[1]))
    return processes


def _windows_running_processes() -> list[tuple[int, str]]:
    command = (
        "Get-CimInstance Win32_Process | "
        "ForEach-Object { '{0}|{1}' -f $_.ProcessId, $_.CommandLine }"
    )
    try:
        output = subprocess.check_output(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
            text=True,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except (OSError, subprocess.CalledProcessError):
        return []
    processes = []
    for line in output.splitlines():
        pid_text, _, command_line = line.partition("|")
        pid_text = pid_text.strip()
        if not pid_text.isdigit():
            continue
        processes.append((int(pid_text), command_line))
    return processes
