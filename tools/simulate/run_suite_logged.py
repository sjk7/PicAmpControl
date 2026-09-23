#!/usr/bin/env python3
"""Run the full simulator suite with its progress log open in VS Code.

Wraps `run_suite_with_watchdog.py` through `run_logged.run_logged()`, so the suite's own
heartbeat/progress output is:
  * written to a single log file,
  * folded so repeated MDB warnings do not bury the progress lines,
  * and opened in the user's editor, following the tail.

The launcher already clears its own temp progress log and heartbeat; this wrapper exists so the
*combined* run is watchable and so the elapsed time is measured (for sizing the next timeout).

Usage:
    python tools/simulate/run_suite_logged.py [--timeout 1200] [--log PATH]
"""
import argparse
import os
import sys
import time
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))
import platform_process as procutil  # noqa: E402
import run_logged  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--timeout", type=int, default=1200,
                    help="suite timeout in seconds, passed to the watchdog launcher")
    ap.add_argument("--log", type=Path,
                    default=Path(procutil.temp_dir()) / "pac_suite_run.log")
    args = ap.parse_args()

    # Device comes from the environment so the same wrapper serves the Q10 (default) and the 16F.
    device = os.environ.get("PICAMP_DEVICE") or "PIC18F47Q10"
    started = time.monotonic()
    code = run_logged.run_logged(
        [sys.executable, str(TOOLS_DIR / "run_suite_with_watchdog.py"),
         "--timeout", str(args.timeout)],
        args.log,
        label=f"suite {device} timeout={args.timeout}s",
        interval=5.0,
    )
    elapsed = time.monotonic() - started
    # Record the elapsed time in the log so the next run's timeout can be sized from it.
    with open(args.log, "a", encoding="utf-8") as handle:
        handle.write(f"SUITE_ELAPSED device={device} seconds={elapsed:.1f} "
                     f"timeout={args.timeout} exit={code}\n")
    print(f"run_suite_logged: device={device} exit={code} elapsed={elapsed:.1f}s log={args.log}")
    return 0 if code == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
