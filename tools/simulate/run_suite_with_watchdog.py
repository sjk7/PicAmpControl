#!/usr/bin/env python3
"""Run the merged simulator suite in its own process group.

The launcher is deliberately separate from the caller's terminal process group:
the PID file and group cleanup keep an interrupted VS Code terminal from leaving
MPLAB MDB running into the next test.

The platform differences (process groups, `ps` vs `taskkill`, `/tmp` vs `%TEMP%`)
are all in `platform_process.py`, so this file stays one code path for both OSes.
"""
import argparse
import datetime
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import platform_process as procutil  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
PID_FILE = procutil.temp_dir() / "picampcontrol_suite.pid"
DEFAULT_LOG = procutil.temp_dir() / "picampcontrol_suite_progress.log"
SUITE = [sys.executable, "-u", str(REPO_ROOT / "tools/simulate/trace_ptt_sequence.py"), "--suite"]

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
)


def stamp():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


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
            **procutil.isolated_spawn_kwargs(),
        )
        PID_FILE.write_text(str(proc.pid))
        log.write(f"[{stamp()}] CHILD pid={proc.pid}\n")
        stop_heartbeat = threading.Event()

        mdb_read_pos = {"offset": 0}
        # MDB writes in 4096-byte chunks that need not end on a line boundary, so a partial
        # trailing line is carried over rather than printed half-finished.
        pending_mdb = {"text": ""}

        def mdb_since_last(limit_bytes: int = 1200) -> str:
            """The MDB output that arrived since the previous heartbeat, as raw text.

            Byte counts alone say whether the run is moving, not what it is doing, and the
            MDB text otherwise sits in a separate log. Putting it here makes the one log the
            user watches readable while the run is in progress (sticky user instruction,
            2026-09-22).

            Emitted verbatim, NOT as a repr: `{!r}` renders every newline as a literal "\\n"
            and every tab as "\\t", and MDB's pin dumps are tab-separated tables, so escaping
            them turns a readable dump into a wall of backslashes (user feedback, 2026-09-22).
            """
            try:
                size = mdb_log.stat().st_size if mdb_log.exists() else 0
            except OSError:
                return ""
            offset = mdb_read_pos["offset"]
            if size < offset:      # the log was recreated under us
                offset = 0
                pending_mdb["text"] = ""
            if size <= offset:
                return ""
            try:
                with mdb_log.open("rb") as handle:
                    handle.seek(offset)
                    chunk = handle.read(min(size - offset, limit_bytes))
            except OSError:
                return ""
            mdb_read_pos["offset"] = offset + len(chunk)
            text = pending_mdb["text"] + chunk.decode("utf-8", errors="replace")
            # Print whole lines only, so the live view never ends mid-line.
            cut = text.rfind("\n")
            if cut == -1:
                pending_mdb["text"] = text
                return ""
            pending_mdb["text"] = text[cut + 1:]
            return text[: cut + 1]

        def heartbeat():
            # `time.monotonic()` is uptime, not elapsed time, so it has to be taken
            # relative to the spawn. Printing it raw made a stalled run look like a
            # progressing one (and vice versa) at exactly the moment the number matters.
            started = time.monotonic()
            previous_mdb_size = 0
            while not stop_heartbeat.wait(10):
                mdb_size = mdb_log.stat().st_size if mdb_log.exists() else 0
                log.write(
                    f"[{stamp()}] HEARTBEAT elapsed={time.monotonic() - started:.1f} "
                    f"timeout={args.timeout:.0f} child_poll={proc.poll()} mdb_bytes={mdb_size} "
                    f"delta={mdb_size - previous_mdb_size}\n"
                )
                new_text = mdb_since_last()
                if new_text:
                    log.write(f"[{stamp()}] MDB_BEGIN\n{new_text}\n[{stamp()}] MDB_END\n")
                previous_mdb_size = mdb_size

        heartbeat_thread = threading.Thread(target=heartbeat, daemon=True)
        heartbeat_thread.start()
        try:
            code = proc.wait(timeout=args.timeout)
        except KeyboardInterrupt:
            log.write(f"[{stamp()}] INTERRUPTED cleanup_pid={proc.pid}\n")
            procutil.terminate_tree(proc.pid)
            code = proc.wait()
        except subprocess.TimeoutExpired:
            log.write(f"[{stamp()}] TIMEOUT cleanup_pid={proc.pid}\n")
            procutil.kill_tree(proc.pid)
            code = proc.wait()
        finally:
            stop_heartbeat.set()
            heartbeat_thread.join(timeout=2)
            PID_FILE.unlink(missing_ok=True)
            log.write(f"[{stamp()}] END code={proc.returncode}\n")
    print(f"SUITE_EXIT:{code}")
    print(f"LOG:{args.log}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
