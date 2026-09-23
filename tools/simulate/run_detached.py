#!/usr/bin/env python3
"""Start a simulator watchdog run DETACHED from this shell, then return immediately.

Why this exists
---------------
On 2026-09-23 a suite run launched synchronously through the agent's terminal was SIGTERMed twice
mid-run: MDB writes megabytes to the run's log, and when any of that reaches the terminal the
harness reacts to the flood and kills the process group. The damage is invisible in the obvious
place - the run's own log looks healthy and simply stops, and the wrapper records
`SUITE_EXIT=143` (SIGTERM), which reads like a test failure and is not one. Roughly 105 s of a
healthy Windows-green suite was thrown away each time.

So a long run is started in its OWN SESSION (`start_new_session=True`, the POSIX equivalent of
`setsid`) with stdout and stderr redirected into files, and this script exits at once. Nothing
about the run depends on the shell that started it, and the verdict is read from the files exactly
as the standing rule requires - the log, the appended exit-code line, and the heartbeat progress
log. The heartbeat keeps the log tab in VS Code moving while the run is live.

Usage
-----
    python tools/simulate/run_detached.py                    # merged suite, default paths
    python tools/simulate/run_detached.py --test first-dit   # the other simulator test
    python tools/simulate/run_detached.py --out /tmp/run.log --log /tmp/run_ctest.log

Defaults put `--out` in the temp dir as `picampcontrol_detached_run.log`. Watch that file - it
carries the launcher's own output plus `SUITE_EXIT=<code>` as its last line. `--quick-bands` is
passed straight through to the launcher.
"""
import argparse
import shlex
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
LAUNCHER = Path(__file__).resolve().parent / "run_suite_with_watchdog.py"

sys.path.insert(0, str(Path(__file__).resolve().parent))
import platform_process as procutil  # noqa: E402  (path set above)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default=str(procutil.temp_dir() / "picampcontrol_detached_run.log"),
                        help="file the launcher's stdout/stderr (and the exit-code line) go to")
    parser.add_argument("--log", default=None,
                        help="log passed to the launcher's --log; the heartbeat appends into it")
    parser.add_argument("--test", choices=("suite", "first-dit"), default="suite")
    parser.add_argument("--timeout", type=float, default=1200.0)
    parser.add_argument("--quick-bands", action="store_true")
    args = parser.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    log_path = Path(args.log) if args.log else procutil.temp_dir() / "picampcontrol_detached_ctest.log"

    # Truncate (never delete) both files before launching: the launcher appends, and a watcher
    # holding a deleted file open would go blind.
    out_path.write_text("", encoding="utf-8")
    log_path.write_text("", encoding="utf-8")

    launcher_args = [
        sys.executable, "-u", str(LAUNCHER),
        "--test", args.test,
        "--timeout", str(args.timeout),
        "--log", str(log_path),
    ]
    if args.quick_bands:
        launcher_args.append("--quick-bands")

    # One shell, so the exit code of the launcher lands in the same file as its output. The run
    # gets its own session, so nothing that happens to this shell (or to the terminal it ran in)
    # can signal it.
    command = (f"{' '.join(shlex.quote(a) for a in launcher_args)} >> {shlex.quote(str(out_path))} 2>&1; "
               f"echo \"SUITE_EXIT=$?\" >> {shlex.quote(str(out_path))}")
    child = subprocess.Popen(
        ["/bin/sh", "-c", command],
        cwd=str(REPO_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )

    print(f"detached pid  = {child.pid}")
    print(f"run log       = {out_path}")
    print(f"heartbeat log = {log_path}")
    print("read the verdict from the run log's last line (SUITE_EXIT=...), not from the terminal")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
