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
import open_progress_log  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
PID_FILE = procutil.temp_dir() / "picampcontrol_suite.pid"
DEFAULT_LOG = procutil.temp_dir() / "picampcontrol_suite_progress.log"
# The heartbeat must keep moving for the whole test. 5 s is frequent enough that a reader never
# wonders whether the run died, and rare enough that a 20-minute run stays readable.
HEARTBEAT_INTERVAL = 5.0
SUITE = [sys.executable, "-u", str(REPO_ROOT / "tools/simulate/trace_ptt_sequence.py"), "--suite"]
FIRST_DIT = [sys.executable, "-u", str(REPO_ROOT / "tools/simulate/test_first_dit.py")]
REPRO_20M = [sys.executable, "-u", str(REPO_ROOT / "tools/simulate/repro_first_dit_20m.py")]
REPRO_RELEASE = [sys.executable, "-u", str(REPO_ROOT / "tools/simulate/repro_release_stage4.py")]
REPRO_RELEASE_FINE = REPRO_RELEASE + ["--fine"]
REPRO_SWR1_REARM = [sys.executable, "-u", str(REPO_ROOT / "tools/simulate/repro_swr1_rearm.py")]
REPRO_FREQ_CTR = [sys.executable, "-u", str(REPO_ROOT / "tools/simulate/check_freq_ctr_bands.py")]

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


# The test writes its own instrumentation into the same log the heartbeat reads
# (`MDB_OUTPUT stream=... bytes=...`, `MDB_OUTPUT_END`, `MDB_START`, `MDB_STDERR_*`,
# `MDB_TIMEOUT`). Those are bookkeeping, not simulator output, and reporting them made the
# heartbeat say `MDB ... MDB_OUTPUT stream=stdout bytes=1641680` - a byte counter, and often
# no line at all, where the user wanted the simulator's actual output (user report,
# 2026-09-22: "I still do not see bytes (string) outputs since the last tick"). Skip them.
MDB_NOISE_PREFIXES = ("MDB_OUTPUT", "MDB_OUTPUT_END", "MDB_START", "MDB_STDERR",
                      "MDB_TIMEOUT")
# Benign simulator warnings that fire once per `program`/reset, or once per reading, and say nothing
# about the firmware. They are not instrumentation and not simulator output worth showing: the
# heartbeat reports "the most recent line of the simulator's OWN output", and a per-reset or per-pin
# warning is not that.
#   * `W0106-SIM` - no clock-source mux for TMR1/TMR3/TMR5.
#   * `W9602-COMP` - the model cannot route the on-chip DAC into a comparator (nothing here uses it).
#   * `W0223-ADC` - "ADC input voltage low. ADC output underflow". The harness deliberately drives
#     SWR/current/overdrive pins to 0.0 V between phases, so this fires routinely and means "a pin is
#     at 0 V", which is exactly what the test asked for (user instruction, 2026-09-25: *"If MDB W0223
#     ... is not important, then do not show it in the watched log."*).
MDB_NOISE_TOKENS = ("W0106-SIM", "W9602-COMP", "W0223-ADC")


def _is_mdb_noise(line: str) -> bool:
    """True for lines the heartbeat must not report as progress.

    Two kinds: the test's own instrumentation (`MDB_OUTPUT ...`), and the benign per-reset simulator
    warnings in MDB_NOISE_TOKENS. The test stamps the former as `[2026-09-22T11:49:20+0100] MDB_OUTPUT
    ...`, so a prefix test alone misses them; the marker can sit after one `] ` group.
    """
    body = line
    if body.startswith("["):
        close = body.find("]")
        if close != -1:
            body = body[close + 1:].lstrip()
    if any(token in body for token in MDB_NOISE_TOKENS):
        return True
    return body.startswith(MDB_NOISE_PREFIXES)


def last_mdb_line(mdb_log: Path, offset: dict, limit: int = 70, tail_bytes: int = 65536) -> str:
    """The most recent line of the simulator's own output, since the caller last looked.

    Byte counts alone say whether the run is moving, not what it is doing, and the MDB text
    otherwise sits in a separate log. A *line* says what the simulator is doing, where a hex
    dump of raw bytes did not: it showed MDB's hex-dump column, so a reader could not tell a
    fresh write from bytes already counted (user report, 2026-09-22). The offset advances by
    what was actually read, so the next heartbeat cannot re-report the same bytes.

    Only **complete** lines are eligible, and the newest complete one wins. Sampling an
    in-progress write is what produced the fragments the user reported as "strange output"
    (`MDB ault_latched` is the tail of `g_fault_latched`, `MDB ence_stage` of `g_sequence_stage`).
    Two things guarantee completeness:

      * the read stops at the last newline, so a half-written final line is never examined; and
      * the offset advances only to the end of the last complete line, so those unread bytes are
        picked up (and shown whole) on a later beat instead of being discarded.

    The tail read is bounded because the MDB log grows without limit inside a test. Losing the
    oldest bytes of a huge burst is acceptable - MDB output is repetitive pin dumps - but showing
    half a line is not, so a bound that leaves no complete line reports nothing and lets the next
    beat catch up. A line also has to carry a word: MDB's own progress traces are runs of dots.
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
    complete = chunk.rfind(b"\n")
    if complete == -1:
        # No newline in the window at all: either the write is mid-line or the producer writes
        # very long lines. Re-readable later; do not report a fragment now.
        return ""
    offset["value"] = read_from + complete + 1
    text = chunk[:complete].decode("utf-8", "replace")
    lines = text.splitlines()
    # The first line is a fragment whenever the read started mid-log; drop it.
    if read_from != start:
        lines = lines[1:]
    for index in range(len(lines) - 1, -1, -1):
        collapsed = " ".join(lines[index].split())
        if not collapsed or _is_mdb_noise(collapsed) or not any(c.isalnum() for c in collapsed):
            continue
        # MDB reports a symbol's value as TWO lines - `g_fc_status.current_band=` and then `1` - so
        # either half alone is useless to read, and a heartbeat that lands between them shows
        # `...current_band=`, which the operator quite reasonably asked about (2026-09-25: *"Why are
        # some outputs from MPLAB truncated?"*). Join them exactly as the transcript parser does: the
        # value goes with the name, whichever half is newer.
        following = (" ".join(lines[index + 1].split())
                     if index + 1 < len(lines) else "")
        if collapsed.endswith("=") and following and any(c.isalnum() for c in following) \
                and not _is_mdb_noise(following):
            return f"{collapsed}{following}"[-limit:]
        if collapsed.endswith("="):
            continue      # the value has not been written yet: show the previous complete line
        previous = " ".join(lines[index - 1].split()) if index > 0 else ""
        if previous.endswith("=") and not _is_mdb_noise(previous):
            return f"{previous}{collapsed}"[-limit:]
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
        # Always emit the line, even when there is nothing new: the user watches this file to
        # confirm the run is alive, and a visible "" reads as a stalled heartbeat whereas an
        # absent line reads as a heartbeat that skipped its MDB tail.
        log.write(f"[{stamp()}] MDB {'(no new output)' if not latest else latest}")
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


def tail_lines(path: Path, count: int = 25, max_bytes: int = 16384) -> list:
    """The last `count` lines of the file at `path`, reading at most `max_bytes` of it.

    Bounded on purpose: the run log can be tens of megabytes (every MDB line lands in it), and the
    only thing wanted is the tail that says how the run ended.
    """
    try:
        size = path.stat().st_size
        with path.open("rb") as handle:
            handle.seek(max(0, size - max_bytes))
            chunk = handle.read().decode("utf-8", "replace")
    except OSError:
        return []
    return chunk.splitlines()[-count:]


def append_run_summary(log, since: float, code: int, test_name: str, path: Path) -> None:
    """Append the run's verdict, in words, to the END of the log.

    The scope trace already writes its WHAT THIS TEST IS FOR / WHAT THE FIRMWARE ACTUALLY DID / WHY
    THAT IS A FAILURE block into this log when it renders the picture - but the heartbeat and the
    simulator keep writing after that, so by the time the run finishes the block sits thousands of
    lines above the end, where nobody finds it. The operator said so outright (2026-09-25: *"You are
    not writing that nice image failure description at the end of the log. Or if you do, I am not
    seeing it. You should append it."*). So the launcher re-appends it here, AFTER `TEST_END` and after
    the heartbeat writer has been stopped, which is the one place nothing else can land after. The
    words come from the `<scenario>_failure.txt` that `scope_trace.on_failure()` wrote, never a
    re-render, so the log and the picture can never disagree.

    A FAILED run with no failure text gets the run's OWN TAIL instead of a shrug (2026-09-25, user
    report: *"It failed with no trace? INCORRECT!!"*). A crash in the test - before any waveform can
    be rendered - is still a failure, and the traceback a few lines above `TEST_END` is what explains
    it; saying "no failure text was written" and stopping there told the operator nothing.

    A PASSING run gets a block too (user instruction, 2026-09-25: *"If the run was successful, then
    don't print nothing, print that it was successful in the log."*). A clean run otherwise ends on a
    heartbeat line, which reads exactly like a run that stopped for no reason - the same trap as a
    quiet log read as a dead one.
    """
    elapsed = time.time() - since
    # Read the tail BEFORE writing anything, so the summary cannot quote itself.
    tail = tail_lines(path) if code != 0 else []
    graphs = REPO_ROOT / "_build" / "My_Pic_Project" / "sim" / "graphs"
    newest = None
    if code != 0 and graphs.is_dir():
        try:
            candidates = [candidate for candidate in graphs.glob("*_failure.txt")
                          if candidate.stat().st_mtime >= since - 1.0]
        except OSError:
            candidates = []
        if candidates:
            newest = max(candidates, key=lambda candidate: candidate.stat().st_mtime)

    log.write("")
    if newest is None and code == 0:
        log.write(f"===== RUN PASSED name={test_name} elapsed={elapsed:.0f}s =====")
        log.write("Every check in this run passed; no failure text to report.")
        log.write("===== END RUN SUMMARY =====")
        return
    if newest is None:
        log.write(f"===== RUN FAILED code={code} name={test_name} elapsed={elapsed:.0f}s =====")
        log.write("No scope trace was produced: the test did not reach a waveform. Its last lines are "
                  "the reason, and they are repeated here so the end of the log explains itself.")
        for line in tail:
            if line.startswith("=====") or line.startswith("Scope trace:"):
                continue      # a summary from an earlier run in this same file, not this failure
            log.write(line)
        log.write("===== END RUN SUMMARY =====")
        return

    try:
        text = newest.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return
    log.write(f"===== RUN FAILED code={code} name={test_name} elapsed={elapsed:.0f}s "
              f"({newest.name}) =====")
    for line in text.splitlines():
        log.write(line)
    log.write(f"Scope trace: {graphs / newest.name.replace('_failure.txt', '_scope.png')}")
    log.write("===== END RUN SUMMARY =====")


def main():
    parser = argparse.ArgumentParser()
    # The default is sized for the slowest supported host: MDB is ~2.8x slower on
    # Windows than macOS (measured 2026-09-22 - first-dit 55 s vs 20 s), and the merged
    # suite ran past 280 s on Windows while still progressing normally. Keep this above
    # the suite's real duration with margin rather than assuming macOS timings; the
    # CTest registration in user.cmake passes the same figure explicitly.
    parser.add_argument("--timeout", type=float, default=1200.0)
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG)
    parser.add_argument("--test",
                        choices=("suite", "first-dit", "repro-20m", "repro-release",
                                 "repro-release-fine", "repro-swr1-rearm", "check-freq-ctr"),
                        default="suite",
                        help="Which simulator test this watchdog wraps")
    parser.add_argument("--quick-bands", action="store_true",
                        help="Run one valid 40m band plus the frequency-failure scenario")
    parser.add_argument("--only", default=None,
                        help="Suite scenarios to run, comma-separated (debugging shortcut: "
                             "`--only FREQ_CTR` runs just that scenario instead of all eleven)")
    parser.add_argument("--bands", default=None,
                        help="Restrict the run to bands, comma-separated (e.g. `--only FREQ_CTR "
                             "--bands 80m` boots and goes straight to that band's check)")
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
    # One MDB progress log PER RUN. Deriving it from the run log's own name matters: with a fixed
    # name in the temp directory, any second run collided with the first on this file and died in
    # `unlink` with `PermissionError: [WinError 32] ... used by another process` BEFORE it started
    # (2026-09-25 - the suite was still live and a repro run could not launch at all, which reads
    # as a broken launcher rather than as "a run is already going"). The heartbeat is handed the
    # same path via --mdb-log, so the two stay in step.
    mdb_log = args.log.with_name(args.log.name + ".mdb_progress.log")
    mdb_log.unlink(missing_ok=True)

    # A new run owns the log from line 1: start it fresh rather than appending to the previous
    # run's output. Appending across runs was the earlier design, and it left a watcher unable to
    # tell where the current run began - the user saw the old run's lines interleaved with the new
    # one's and said so twice (2026-09-22: "I still see all the last log's run as well as this
    # one"). One run, one log. Truncate, never delete: the file has to keep its identity in the
    # editor tab the user is watching, and a deleted-and-recreated path drops that tab's handle.
    # TEST_BEGIN/TEST_END still bracket each *test* inside the run, so a ctest run of two tests is
    # still readable; it is runs, not tests, that start a fresh file.
    args.log.parent.mkdir(parents=True, exist_ok=True)
    # Truncate at the START of a run only - never at the end. A fresh log per run, so a watcher
    # can always tell where the current run begins, and TEST_BEGIN/TEST_END bracket it. The
    # finished run's tail (including TEST_END and any warnings) is left intact after the run.
    try:
        with args.log.open("w", encoding="utf-8", newline="\n"):
            pass
    except OSError:
        pass
    # A lock left behind by a killed run would otherwise stall this one for its first write.
    args.log.with_name(args.log.name + ".lock").unlink(missing_ok=True)

    if args.test == "suite":
        test_name = "PTT_SequencerAndTripSuite"
        if args.only:
            test_name = f"PTT_SequencerAndTripSuite[{'/'.join(args.only.split(','))}]"
        command = SUITE + (["--quick-bands"] if args.quick_bands else [])
        if args.only:
            command += ["--only", args.only]
        if args.bands:
            command += ["--bands", args.bands]
    elif args.test == "repro-20m":
        test_name = "Repro_FirstDit_20m"
        command = REPRO_20M
    elif args.test == "repro-release":
        test_name = "Repro_ReleaseStage4"
        command = REPRO_RELEASE
    elif args.test == "repro-release-fine":
        test_name = "Repro_ReleaseStage4_Fine"
        command = REPRO_RELEASE_FINE
    elif args.test == "repro-swr1-rearm":
        test_name = "Repro_SWR1Rearm"
        command = REPRO_SWR1_REARM
    elif args.test == "check-freq-ctr":
        # A band-slice CHECK, not a repro: it drives one FREQ_CTR scenario in isolation and passes
        # whether or not the suite fails, so it can never be the verdict (the suite's failure needs
        # the full session's pacing). The repro for that scenario is `--test suite --only FREQ_CTR`.
        test_name = "Check_FreqCtrBands"
        command = REPRO_FREQ_CTR
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
    # Name the watched file in the log itself. On Windows the launcher deliberately does NOT open a
    # tab for it (that would move the operator's focus - see open_progress_log.open_in_editor), so
    # the path has to be discoverable without asking the agent or reading a temp directory listing.
    log.write(f"[{stamp()}] LOG_TO_WATCH {args.log}")
    # Also say it on stdout, at the START: the path has to be visible while the run is live, not only
    # in the summary at the end (the operator asked "I don't see a log for it even if it is!"
    # on 2026-09-25, having been handed a run whose log existed under a name he had not chosen).
    print(f"watch: {args.log}")
    # Open the progress log so the user can watch it - but WITHOUT moving their focus (macOS uses
    # `open -g`; on Windows nothing is opened, see open_in_editor). Best-effort: a headless host has
    # no editor and that must not fail the run.
    if os.environ.get("PICAMP_NO_EDITOR_OPEN") != "1":
        # Reset the helper's state at the start of each run, so an already-open log is re-shown and
        # re-followed rather than silently skipped because it happened to be on screen (2026-09-25:
        # "Reset the user interaction disable when each run starts so it follows properly.").
        try:
            open_progress_log.RECEIPT_FILE.unlink(missing_ok=True)
        except OSError:
            pass
        open_progress_log.open_in_editor([args.log], quiet=True)
    _, child_log = log.open_for_child()
    env = os.environ.copy()
    env.setdefault("PICAMP_MDB_DEBUG_LOG", str(mdb_log))
    run_started = time.time()
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
    # LAST, and after the heartbeat is gone, so it is the tail the reader sees (see
    # append_run_summary): the verdict in words - the failure prose, or an explicit pass.
    append_run_summary(log, run_started, code, test_name, args.log)
    print(f"SUITE_EXIT:{code}")
    print(f"LOG:{args.log}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
