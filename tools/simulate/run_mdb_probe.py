#!/usr/bin/env python3
"""Run one MDB script, streaming (collapsed) output to a VS Code tab with a heartbeat.

Thin CLI over `run_logged.run_logged()`, so a probe log folds repeated MDB warnings and follows
the tail exactly like the build/test runners. Use `run_with_log.py` for a non-MDB command.

Usage:
    python tools/simulate/run_mdb_probe.py <script.mdb> [--log PATH] [--interval 2]
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
    ap.add_argument("script", type=Path)
    ap.add_argument("--log", type=Path,
                    default=Path(procutil.temp_dir()) / "pac_mdb_probe.log")
    ap.add_argument("--interval", type=float, default=2.0)
    ap.add_argument("--max-repeats", type=int, default=run_logged.DEFAULT_MAX_REPEATS)
    args = ap.parse_args()

    mdb = procutil.find_mdb()
    code = run_logged.run_logged([mdb, args.script], args.log,
                                 label=f"mdb {args.script.name}",
                                 interval=args.interval, max_repeats=args.max_repeats)
    print(f"run_mdb_probe: {args.script} exit={code} log={args.log}")
    return 0 if code == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
