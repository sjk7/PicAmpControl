#!/usr/bin/env python3
"""Run any long command with its output streamed to a VS Code tab + a heartbeat.

Thin CLI over `run_logged.run_logged()`, which owns the folding and follow behaviour. Use this for
builds, spikes, ctest - anything longer than a few seconds that the user must be able to watch.

Usage:
    python tools/simulate/run_with_log.py --log PATH -- <command> [args...]
    python tools/simulate/run_with_log.py --log PATH -- cmake --build _build/... -j4
"""
import argparse
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))
import platform_process as procutil  # noqa: E402
import run_logged  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", type=Path, default=Path(procutil.temp_dir()) / "pac_run.log")
    ap.add_argument("--interval", type=float, default=2.0)
    ap.add_argument("--label", default="")
    ap.add_argument("--max-repeats", type=int, default=run_logged.DEFAULT_MAX_REPEATS)
    ap.add_argument("command", nargs=argparse.REMAINDER)
    args = ap.parse_args()

    command = [part for part in args.command if part != "--"]
    if not command:
        ap.error("no command given (use: run_with_log.py --log PATH -- <command> ...)")

    code = run_logged.run_logged(command, args.log, label=args.label,
                                 interval=args.interval, max_repeats=args.max_repeats)
    print(f"run_with_log: {' '.join(command[:2])}... exit={code} log={args.log}")
    return 0 if code == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
