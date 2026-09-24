#!/usr/bin/env python3
"""Shared "run a long command and let the user watch it" machinery.

Standing user instruction (2026-09-22, restated many times): a long job's output goes to a log
file, that log is open in a VS Code tab for the whole run, and a heartbeat proves it is alive.
The user has also asked for two specific refinements after seeing the raw result:

  * **Collapse repeated lines.** MDB emits `W0223-ADC: ADC input voltage low.  ADC output
    underflow.` 8,638 times in a 20 s probe - 99% of the log was one line repeated. Repetition is
    noise; the fact of the warning is the signal. Consecutive identical lines are emitted
    `max_repeats` times, then summarised once as `... (N more repeats of the line above)`.
  * **Follow the tail.** The editor tab must auto-scroll as the file grows. That is the
    marketplace **Log Viewer** extension (`berublan.vscode-log-viewer`), which re-reads the file
    on an interval and follows tail by scroll position without pulling focus from the active tab
    or from another app.

Everything that runs a job writes through `run_logged()` so the behaviour cannot diverge between
entry points (it did: folding was added to one runner and not the other).
"""
import subprocess
import sys
import threading
import time
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))
import platform_process as procutil  # noqa: E402
import open_progress_log  # noqa: E402

# Collapse a run of identical consecutive lines after this many copies.
DEFAULT_MAX_REPEATS = 3


def run_logged(command, log, label="", interval=2.0, max_repeats=DEFAULT_MAX_REPEATS,
               env=None):
    """Run `command`, streaming collapsed output to `log`, and heartbeat it.

    Returns the child's exit code. The log is truncated at the START of the run only - a fresh,
    followable log per run - and NEVER truncated at the end: the finished run's tail stays put.
    """
    log = Path(log)
    log.write_text("", encoding="utf-8")  # truncate at START only, never when a run finishes

    appender = procutil.AppendLog(log)
    # Write a delimited header BEFORE opening the tab, so the log has a line to show immediately.
    appender.write(f"RUN_BEGIN {time.strftime('%Y-%m-%dT%H:%M:%S%z')} "
                   f"{label or command[0]} :: {' '.join(str(c) for c in command)}")
    # `open_in_editor` uses `code -r` (reuse window, no raise): it opens the tab for the user to
    # watch without stealing focus. The old logfollower extension was the focus thief, now removed.
    open_progress_log.open_in_editor([log])

    started = time.monotonic()

    proc = subprocess.Popen([str(c) for c in command],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            stdin=subprocess.DEVNULL, env=env,
                            **procutil.isolated_spawn_kwargs())

    def pump():
        last_line = None
        run_count = 0
        for raw in proc.stdout:
            line = raw.decode("utf-8", "replace").rstrip("\r\n")
            if line == last_line:
                run_count += 1
                if run_count <= max_repeats:
                    appender.write(line)
                continue
            if run_count > max_repeats:
                appender.write(f"... ({run_count - max_repeats} more repeats of the line above)")
            last_line = line
            run_count = 1
            appender.write(line)
        if run_count > max_repeats:
            appender.write(f"... ({run_count - max_repeats} more repeats of the line above)")

    def heartbeat():
        last = 0
        while True:
            time.sleep(interval)
            try:
                size = log.stat().st_size
            except OSError:
                size = 0
            delta = size - last
            last = size
            # Beat is stamped and written BEFORE anything else, so describing the run can never
            # delay the proof of life (see the skill's heartbeat rule).
            appender.write(f"HEARTBEAT elapsed={time.monotonic() - started:.1f} "
                           f"bytes={size} delta={delta}")
            if proc.poll() is not None:
                return

    threading.Thread(target=pump, daemon=True).start()
    threading.Thread(target=heartbeat, daemon=True).start()

    code = proc.wait()
    appender.write(f"PROBE_END exit={code}")
    return code
