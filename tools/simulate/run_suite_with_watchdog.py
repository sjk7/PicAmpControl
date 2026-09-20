#!/usr/bin/env python3
"""Run the merged simulator suite in its own process group.

The launcher is deliberately separate from the caller's terminal process group:
the PID file and group cleanup keep an interrupted VS Code terminal from leaving
MPLAB MDB running into the next test.
"""
import argparse
import datetime
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PID_FILE = Path("/tmp/picampcontrol_suite.pid")
DEFAULT_LOG = Path("/tmp/picampcontrol_suite_progress.log")
SUITE = [sys.executable, "-u", str(REPO_ROOT / "tools/simulate/trace_ptt_sequence.py"), "--suite"]


def stamp():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def kill_previous(log):
    if not PID_FILE.exists():
        return
    try:
        pid = int(PID_FILE.read_text().strip())
        os.kill(pid, 0)
    except (FileNotFoundError, ValueError, ProcessLookupError, PermissionError):
        PID_FILE.unlink(missing_ok=True)
        return
    log.write(f"[{stamp()}] CLEANUP previous_pid={pid}\n")
    try:
        os.killpg(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    PID_FILE.unlink(missing_ok=True)


def kill_orphaned_processes(log):
    patterns = ("/mplab_platform/bin/mdb", "run_suite_with_watchdog.py", "trace_ptt_sequence.py --suite")
    try:
        process_lines = subprocess.check_output(
            ["ps", "-axo", "pid=,command="], text=True, stderr=subprocess.DEVNULL
        ).splitlines()
    except subprocess.CalledProcessError:
        return
    for line in process_lines:
        fields = line.strip().split(None, 1)
        if len(fields) != 2:
            continue
        pid = int(fields[0])
        command = fields[1]
        if pid == os.getpid() or not any(pattern in command for pattern in patterns):
            continue
        try:
            process_group = os.getpgid(pid)
            os.killpg(process_group, signal.SIGKILL)
            log.write(f"[{stamp()}] CLEANUP orphan_pid={pid} group={process_group} command={command}\n")
        except (ProcessLookupError, PermissionError):
            pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG)
    parser.add_argument("--quick-bands", action="store_true",
                        help="Run one valid 40m band plus the frequency-failure scenario")
    args = parser.parse_args()
    args.log.unlink(missing_ok=True)
    mdb_log = args.log.with_name("picampcontrol_mdb_progress.log")
    mdb_log.unlink(missing_ok=True)

    with args.log.open("w", buffering=1) as log:
        kill_orphaned_processes(log)
        kill_previous(log)
        command = SUITE + (["--quick-bands"] if args.quick_bands else [])
        log.write(f"[{stamp()}] START timeout={args.timeout}s command={' '.join(command)}\n")
        env = os.environ.copy()
        env.setdefault("PICAMP_MDB_DEBUG_LOG", str(mdb_log))
        proc = subprocess.Popen(
            command,
            cwd=REPO_ROOT,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        PID_FILE.write_text(str(proc.pid))
        log.write(f"[{stamp()}] CHILD pid={proc.pid}\n")
        try:
            code = proc.wait(timeout=args.timeout)
        except KeyboardInterrupt:
            log.write(f"[{stamp()}] INTERRUPTED cleanup_group={os.getpgid(proc.pid)}\n")
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            code = proc.wait()
        except subprocess.TimeoutExpired:
            log.write(f"[{stamp()}] TIMEOUT cleanup_group={os.getpgid(proc.pid)}\n")
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            code = proc.wait()
        finally:
            PID_FILE.unlink(missing_ok=True)
            log.write(f"[{stamp()}] END code={proc.returncode}\n")
    print(f"SUITE_EXIT:{code}")
    print(f"LOG:{args.log}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
