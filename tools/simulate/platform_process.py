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
import time
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


# `O_BINARY` keeps the CRLF we write from being doubled by text-mode translation; it
# does not exist on POSIX, where the byte stream is already exact.
_BINARY = getattr(os, "O_BINARY", 0)
_APPEND_FLAGS = os.O_WRONLY | os.O_CREAT | os.O_APPEND | _BINARY


class AppendLog:
    """One serialised, line-atomic appender per log file.

    Three writers share the harness's progress file - the launcher, the test's own stdout, and
    the sibling heartbeat process (or, on a Ctrl-C, the test's Python atexit writer, which
    closes the same inherited handle). Frayed records only happen while two writers reach the
    file at the same instant, and that is what a heartbeat line reading `ed=50.3 ...` - no
    timestamp, no `HEARTBEAT`, just the tail of a line - was.

    Measured on Windows, 2026-09-22, three writers, 113-byte records, ~160 k records per run,
    repeatable across runs (throwaway probes, since deleted - the numbers are the point):

    ==================  ==========  =========
    writer shape        records     frayed
    ==================  ==========  =========
    one write per line  42 k        ~50
    lock, one per line  25 k        0
    ==================  ==========  =========

    So the rule this class encodes is **one `os.write` per record, with the writers serialised
    on an `O_CREAT|O_EXCL` lock file**, and no other write to the progress file. An earlier
    measurement that looked like "the lock alone fixes it" was confounded: that probe wrote a
    23 KB burst per lock acquisition, and a single large write is whole by itself.

    Acquire is retried on a stale lock because a writer killed mid-record must not wedge a run.
    """

    def __init__(self, path: Path):
        self.path = Path(path)
        self.lock_path = self.path.with_name(self.path.name + ".lock")

    def _acquire(self):
        while True:
            try:
                return os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                # A writer killed mid-record must not wedge the run; the lock file is only
                # advisory, so a stale one is replaced rather than waited on.
                try:
                    self.lock_path.unlink(missing_ok=True)
                except OSError:
                    pass
                time.sleep(0.002)
            except OSError:
                return None

    def _release(self, lock_fd):
        if lock_fd is not None:
            os.close(lock_fd)
            try:
                self.lock_path.unlink(missing_ok=True)
            except OSError:
                pass

    def write(self, text: str):
        """Append one line, whole or not at all."""
        data = text.encode("utf-8", "replace")
        if not data.endswith(b"\n"):
            data += b"\n"
        lock_fd = self._acquire()
        try:
            fd = os.open(self.path, _APPEND_FLAGS)
            try:
                view = memoryview(data)
                while view:
                    try:
                        written = os.write(fd, view)
                    except InterruptedError:      # pragma: no cover - signal-dependent
                        continue
                    view = view[written:] if written < len(view) else memoryview(b"")
            finally:
                os.close(fd)
        except OSError:
            pass
        finally:
            self._release(lock_fd)

    def open_for_child(self):
        """`(path, file_object)` for handing a log to a child as its stdout.

        The child gets its own append handle rather than the launcher's, because the
        launcher's is only open for the duration of a write.
        """
        return self.path, open(self.path, "a", buffering=1)


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
