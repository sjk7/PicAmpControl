#!/usr/bin/env python3
"""Run the merged simulator suite in its own process group.

The launcher is deliberately separate from the caller's terminal process group:
the PID file and group cleanup keep an interrupted VS Code terminal from leaving
MPLAB MDB running into the next test.

It also keeps a progress file moving: a second copy of this script is run with
`--heartbeat` as its own process, appending a timestamped line every few seconds
for the whole test, so the log a human is watching never goes quiet. See
`heartbeat_loop` for why that is a process and not a thread.

The platform differences (process groups, `ps` vs `taskkill`, `/tmp` vs `%TEMP%`)
are all in `platform_process.py`, so this file stays one code path for both OSes.
"""
import argparse
import datetime
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import platform_process as procutil  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
PID_FILE = procutil.temp_dir() / "picampcontrol_suite.pid"
DEFAULT_LOG = procutil.temp_dir() / "picampcontrol_suite_progress.log"
# The heartbeat must keep moving for the whole test. 5 s is frequent enough that a reader never
# wonders whether the run died, and rare enough that a 20-minute run stays readable.
HEARTBEAT_INTERVAL = 5.0
SUITE = [sys.executable, "-u", str(REPO_ROOT / "tools/simulate/trace_ptt_sequence.py"), "--suite"]
FIRST_DIT = [sys.executable, "-u", str(REPO_ROOT / "tools/simulate/test_first_dit.py")]

# Orphan signatures. The mdb entries have to match a leftover simulator without also
# matching an unrelated `java.exe`, of which this machine has several (the MPLAB X IDE's
# own JVM and a Java updater) and which must survive. Each run leaves two processes:
# a POSIX launcher (`.../mplab_platform/bin/mdb[.sh]`), or on Windows `cmd.exe` holding
# `mdb.bat` plus the JVM it starts:
#   java.exe -Dfile.encoding=UTF-8 -classpath "...;...\lib\mdb.jar"
#            com.microchip.mplab.mdb.debugcommands.Main <script>
# The JVM is matched on its main class rather than on `mdb.jar` in the classpath, because
# a bare `mdb.jar` is a path the IDE's own JVM could also carry - do not loosen this to
# `mplab_platform` either, which matches the IDE as well.
ORPHAN_PATTERNS = (
    "mplab_platform/bin/mdb",
    r"mplab_platform\bin\mdb.bat",
    "com.microchip.mplab.mdb",
    "run_suite_with_watchdog.py",
    "trace_ptt_sequence.py --suite",
    "test_first_dit.py",
)


def stamp():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def last_mdb_line(mdb_log: Path, offset: dict, limit: int = 70, tail_bytes: int = 65536) -> str:
    """The most recent non-empty MDB line, from where the caller last looked.

    Byte counts alone say whether the run is moving, not what it is doing, and the MDB text
    otherwise sits in a separate log. A *line* says what the simulator is doing, where a hex
    dump of raw bytes did not: it showed MDB's hex-dump column, so a reader could not tell a
    fresh write from bytes already counted (user report, 2026-09-22). The offset advances by
    what was actually read, so the next heartbeat cannot re-report the same bytes.

    Two bounds, both deliberate: only the last `tail_bytes` of new output are read (the newest
    line is at the end, and the MDB log grows without limit inside a test), and the newest line
    is preferred over the *last complete* line, because mid-write MDB output means an empty
    newest line and "did not print anything" beats "printed a line from 40 s ago".
    """
    try:
        size = mdb_log.stat().st_size if mdb_log.exists() else 0
    except OSError:
        return ""
    start = offset["value"]
    if size < start:          # the log was recreated under us
        start = 0
    if size <= start:
        return ""
    read_from = max(start, size - tail_bytes)
    try:
        with mdb_log.open("rb") as handle:
            handle.seek(read_from)
            chunk = handle.read(size - read_from)
    except OSError:
        return ""
    offset["value"] = size
    text = chunk.decode("utf-8", "replace")
    lines = text.splitlines()
    for line in lines[1:] if read_from != start else lines:
        collapsed = " ".join(line.split())
        if collapsed:
            return collapsed[-limit:]
    return ""


def heartbeat_loop(log, mdb_log: Path, test_name: str, timeout: float, started_wall: float):
    """Write a progress line every HEARTBEAT_INTERVAL until this process is stopped.

    This runs as its **own process**, not a thread of the launcher. A thread shares the
    launcher's fate: whenever the launcher is blocked - waiting on the child, sweeping orphan
    processes, or wedged on a Windows handle - the file stops moving exactly when the reader
    needs it most (user report, 2026-09-22).

    Three writers share this one file - the launcher, the test's own stdout, and this heartbeat -
    and on Windows the append mode alone does not keep their records whole, so all three go
    through `procutil.AppendLog`, which serialises on a lock file.

    The ordering in the loop is the part that matters: the beat is **stamped and written first**,
    and the MDB log is only read afterwards. A beat must not be delayed by the work of describing
    the run - if reading the MDB tail is slow, the next line still lands one interval later.
    """
    offset = {"value": 0}
    previous_size = 0
    while True:
        now = time.time()
        mdb_size = 0
        try:
            if mdb_log.exists():
                mdb_size = mdb_log.stat().st_size
        except OSError:
            pass
        log.write(
            f"[{stamp()}] HEARTBEAT test={test_name} elapsed={now - started_wall:.1f} "
            f"timeout={timeout:.0f} mdb_bytes={mdb_size} delta={mdb_size - previous_size}"
        )
        latest = last_mdb_line(mdb_log, offset)
        if latest:
            log.write(f"[{stamp()}] MDB {latest}")
        previous_size = mdb_size
        # Self-limiting: if the launcher is killed outright this must not outlive the test
        # by much. A later launcher's orphan sweep also matches it (see ORPHAN_PATTERNS).
        if now - started_wall > timeout + 300:
            return
        time.sleep(HEARTBEAT_INTERVAL)


def kill_previous(log):
    if not PID_FILE.exists():
        return
    try:
        pid = int(PID_FILE.read_text().strip())
    except (FileNotFoundError, ValueError):
        PID_FILE.unlink(missing_ok=True)
        return
    if not procutil.pid_is_alive(pid):
        PID_FILE.unlink(missing_ok=True)
        return
    log.write(f"[{stamp()}] CLEANUP previous_pid={pid}\n")
    procutil.terminate_tree(pid)
    PID_FILE.unlink(missing_ok=True)


def kill_orphaned_processes(log):
    for pid, command in procutil.running_processes():
        if pid == os.getpid() or not any(pattern in command for pattern in ORPHAN_PATTERNS):
            continue
        if procutil.kill_tree(pid):
            log.write(f"[{stamp()}] CLEANUP orphan_pid={pid} command={command}\n")


def main():
    parser = argparse.ArgumentParser()
    # The default is sized for the slowest supported host: MDB is ~2.8x slower on
    # Windows than macOS (measured 2026-09-22 - first-dit 55 s vs 20 s), and the merged
    # suite ran past 280 s on Windows while still progressing normally. Keep this above
    # the suite's real duration with margin rather than assuming macOS timings; the
    # CTest registration in user.cmake passes the same figure explicitly.
    parser.add_argument("--timeout", type=float, default=1200.0)
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG)
    parser.add_argument("--test", choices=("suite", "first-dit"), default="suite",
                        help="Which simulator test this watchdog wraps")
    parser.add_argument("--quick-bands", action="store_true",
                        help="Run one valid 40m band plus the frequency-failure scenario")
    parser.add_argument("--heartbeat", action="store_true",
                        help="Internal: run only the progress heartbeat (own process)")
    parser.add_argument("--label", default=None,
                        help="Internal: display name to stamp on heartbeat lines")
    parser.add_argument("--mdb-log", type=Path, default=None,
                        help="Internal: mdb trace log to summarise in heartbeats")
    parser.add_argument("--started", type=float, default=None,
                        help="Internal: epoch seconds the wrapped test started")
    args = parser.parse_args()

    if args.heartbeat:
        heartbeat_loop(procutil.AppendLog(args.log), args.mdb_log, args.label or args.test,
                       args.timeout, args.started if args.started is not None else time.time())
        return 0
    mdb_log = args.log.with_name("picampcontrol_mdb_progress.log")
    mdb_log.unlink(missing_ok=True)

    if args.test == "suite":
        test_name = "PTT_SequencerAndTripSuite"
        command = SUITE + (["--quick-bands"] if args.quick_bands else [])
    else:
        test_name = "FirstDit_BandDetectionAndHotSwitchGuards"
        command = FIRST_DIT

    # Appended, never recreated. One progress file therefore carries *every* test in a ctest
    # run - the suite finishing and the first-dit proof starting both appear in it, bracketed by
    # TEST_BEGIN/TEST_END so a reader can always tell which test is running. Deleting the file
    # per test used to leave a watcher's tab reading a dead handle (and the reader with no way
    # to see the transition). Delete it once, before the ctest run, for a fresh view.
    #
    # Every write goes through AppendLog: the launcher, the child's inherited stdout, and the
    # heartbeat process are three independent writers on this one file, and on Windows the
    # append mode alone does not keep their records whole (see AppendLog).
    log = procutil.AppendLog(args.log)
    kill_orphaned_processes(log)
    kill_previous(log)
    log.write(f"[{stamp()}] TEST_BEGIN name={test_name} timeout={args.timeout:.0f}s "
              f"command={' '.join(command)}")
    _, child_log = log.open_for_child()
    env = os.environ.copy()
    env.setdefault("PICAMP_MDB_DEBUG_LOG", str(mdb_log))
    proc = subprocess.Popen(
        command,
        cwd=REPO_ROOT,
        env=env,
        stdout=child_log,
        stderr=subprocess.STDOUT,
        **procutil.isolated_spawn_kwargs(),
    )
    child_log.close()
    PID_FILE.write_text(str(proc.pid))
    log.write(f"[{stamp()}] CHILD pid={proc.pid}")

    # Separate process, started *before* the first wait, so the progress file already carries
    # a fresh line while the launcher is still only blocking on the child (see
    # heartbeat_loop for why this is not a thread). Its stderr goes to a file rather than
    # DEVNULL: a wrong argument here once killed the writer silently, and a progress log that
    # quietly stops for a reason nobody can see is worse than no progress log.
    heartbeat_err = args.log.with_name("picampcontrol_heartbeat_err.log")
    heartbeat_proc = subprocess.Popen(
        [sys.executable, "-u", str(Path(__file__).resolve()), "--heartbeat",
         "--log", str(args.log), "--mdb-log", str(mdb_log), "--label", test_name,
         "--timeout", str(args.timeout), "--started", str(time.time())],
        cwd=REPO_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=heartbeat_err.open("a"),
    )
    log.write(f"[{stamp()}] HEARTBEAT_WRITER pid={heartbeat_proc.pid}")
    try:
        code = proc.wait(timeout=args.timeout)
    except KeyboardInterrupt:
        log.write(f"[{stamp()}] INTERRUPTED cleanup_pid={proc.pid}")
        procutil.terminate_tree(proc.pid)
        code = proc.wait()
    except subprocess.TimeoutExpired:
        log.write(f"[{stamp()}] TIMEOUT cleanup_pid={proc.pid}")
        procutil.kill_tree(proc.pid)
        code = proc.wait()
    finally:
        # The heartbeat is stopped last, so the file keeps moving through the whole of the
        # child's exit path, including anything slow this launcher does during cleanup.
        if heartbeat_proc.poll() is None:
            procutil.terminate_tree(heartbeat_proc.pid)
        PID_FILE.unlink(missing_ok=True)
        log.write(f"[{stamp()}] TEST_END name={test_name} code={proc.returncode}")
    print(f"SUITE_EXIT:{code}")
    print(f"LOG:{args.log}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
