---
name: picampcontrol-build-test
description: "Use when building, testing or debugging PicAmpControl firmware on macOS or Windows: Debug or Release builds, CMake configuration, ctest, run_tests.sh / run_tests.ps1, simulator/mdb runs, the VS Code Simulate debug session, breakpoints and symbol reads, PTT/frequency-counter tests, band-lock tests, first-dit band detection, remembered-band fold-back, band-change/hot-switch guards, or build/test failures."

# PicAmpControl Build, Test and Debug
**Hard rule: be maximally token-efficient at ALL times.** The user has flagged thinking/reasoning
output as wasteful more than once (2026-09-22). Keep every reply, every reasoning trace and every
tool-call preamble to the absolute minimum; no filler, no step-by-step narration, no restating what
was just done. Batch tool calls; filter command output; put detail in files, not the chat. This is a
standing, permanent constraint, not a one-off.
**Hard writing rule: never write "Hmm". Not in a reply, not in a reasoning trace, not as a preamble
or a hedge.** The user reads the reasoning as well as the final answer, and this was repeated three
times on 2026-09-22 *after* the rule already existed in `Ai-Notes.txt` - the third time the user
quoted the word straight back. A bullet buried in a long list did not stop it, so it lives here too.
State the finding, or the uncertainty, plainly, and move on.
**Hard rule: NEVER ASK A RUNNING TEST FOR ITS TERMINAL OUTPUT - IT BREAKS THE TERMINAL.** (user
instruction, restated 2026-09-23: *"we should not ask for terminal output when running tests --
this breaks the terminal. We are using a file-based approach instead."*) The verdict method is
file-based, always: launch the run with its output redirected into a log file, append the exit-code
line, then read the log, that line, and the watchdog progress log. Do not run a test in order to
watch it, do not `tail`/`grep` a log into the console, and do not ask the tool for captured terminal
output - MDB emits megabytes, the capture wedges the shell, and "the terminal showed nothing" says
nothing at all about the run. The terminal is for launching and for short bounded process checks
only.

**How a run is watched (STICKY user instruction, 2026-09-23): the user watches the log file - the
heartbeat file - in a VS Code tab while the tests run. Never in the terminal.** The user's words:
*"we watch files now during sim runs, and never output to terminal. The code user sees the log file
(heartbeat file) in VSCODE when the tests run."* So opening the log in a tab and keeping it fresh is
part of doing the job, not a courtesy: the user has complained repeatedly that long tasks (suite,
probe, build) run with no visible output in VS Code. The method:
1. Truncate the log FIRST (`Clear-Content <log>`, or `: > <log>` on macOS). The launcher appends, and
   deleting a file a watcher holds open kills the watcher.
2. Launch the run with its output redirected into that log. `run_suite_with_watchdog.py` /
   `run_logged.py` open it, write a `RUN_BEGIN` header, and append the exit-code line at the end.
3. Open that file in a VS Code tab so the user can watch it, and keep a heartbeat flowing into it
   while the run is live: `tools/simulate/open_progress_log.py` opens the tab, `AppendLog` in
   `tools/simulate/platform_process.py` is the heartbeat helper. Never just redirect to a temp file
   and report the tail.
4. Which file is the moving one depends on how you launched it: **when you pass `--log <file>`, the
   heartbeat appends INTO that file** (verified 2026-09-23: the heartbeat process is spawned with
   `--log` pointing at the same path), so that is the file to open in the tab. Only when `--log` is
   omitted does the heartbeat use `DEFAULT_LOG` =
   `platform_process.temp_dir()/picampcontrol_suite_progress.log`. Do not assume that is
   `/tmp/...` on macOS: `temp_dir()` resolves to `$TMPDIR`, i.e. under `/var/folders/...`, and an
   older file of the same name can be sitting in `/tmp` - which is exactly how a stale, empty-looking
   log got opened instead of the live one. Confirm liveness from the file's mtime or from the
   elapsed value in its latest `HEARTBEAT` line.
5. Watching a log for visibility is sanctioned; judging a run from terminal output is not. The
   verdict still comes from the run's own log plus its appended exit-code line.
6. The log is there to be watched, so keep it a plain growing text file, and delete it once its
   verdict has been read (standing rule: never accumulate run logs).
**Hard rule: keep token and CPU output down.** The chat transcript is re-rendered on every streamed
token, and this is not theoretical: a 2,041-line / 2.2 MB session drove the VS Code renderer to ~225%
of one core and the extension host to ~112% for the whole of each assistant turn (measured
2026-09-22; the transcript is at
`...\workspaceStorage\<hash>\GitHub.copilot-chat\transcripts\<session>.jsonl` if it needs checking).
Therefore, permanently:
- reply in as few words as the answer allows; never restate the context or re-list what was just done;
- never paste file contents, logs, tables of raw output or exit-code dumps into the chat unless asked;
  put findings in the run's log file, this skill, or a repo doc, and report one line plus the path;
- batch work into fewer, longer tool calls instead of many small ones;
- filter command output (`-Tail`, `-First`, `Select-String`); the terminal panel is rendered too, so a
  whole-file dump costs CPU as well as tokens;
- no code blocks unless the user asked for one. Durable knowledge goes in this skill, not the chat.
**Hard rule: EVERY durable finding goes into this skill in the same session it is found, and "it can
never happen again" is only true once it is written here.** Standing user instruction, 2026-09-22:
*"'so it can't happen again' needs to be: wrote to skill so it never happens again.' Don't forget to
feedback things like this to the skill, always. Sticky."*
A fix in code, a comment in a file, or a commit message is **not** a finding recorded. Only this
skill, `Ai-Notes.txt`, or a repo doc counts, because those are what a future session reads before it
starts work. Concretely, whenever any of these happens, write it to the skill before moving on:
- a trap that cost time (a wrong flag, a silent failure, an assumed value, a tool that lied);
- a *method* that worked (positive controls, staged probes, per-device build configuration);
- a measurement that replaces a guess (timings, memory figures, instruction rates);
- a mistake of mine that a reader should not repeat, including wrong verdicts I had to retract.
The test of whether it is recorded: could a fresh session hit the same problem and be stopped by
what is written here? If not, it is not written yet. Do not batch this "for later" - the session that
found it is the only one that still has the context.
**Hard rule: tighten the test to test only the failing part. Do that every time. Sticky**
(user instruction, 2026-09-22, repeated). When the full suite fails, do NOT re-run the whole suite
to diagnose. Build the smallest run that reproduces ONLY the failing check - the one scenario, band
transition, or assertion - iterate on it until understood, then re-run the full suite once as the
final verdict. The full suite confirms; it never debugs. The minimal repro is a single-scenario
`trace_ptt_sequence.py` run or a two-band slice, not `--suite`.

**Hard rule: the progress log is APPENDed, never replaced, least of all on failure.** User
correction 2026-09-22: "Do not replace my progress.log with `TEST_END ... code=1` when the test
fails. Append, not replace." The log's whole value is the failing run's history - the scenarios that
passed, the traceback, the hot-switch sample - so it must survive a failure intact. Truncate exactly
once, at the START of a run (`run_suite_with_watchdog.py` opens `"w"` before the child starts;
`run_logged.py` does `write_text("")` then a `RUN_BEGIN` header). NEVER truncate at the end and
NEVER truncate in a failure/error path. `TEST_END` / `PROBE_END` is appended at suite exit after
whatever the run wrote, so a finished log reads begin -> heartbeats -> scenario output -> failure
detail -> end marker. A failure must leave the full tail, not a one-line `code=1`.

**Hard rule: NEVER run a simulator test against an ELF you have not just rebuilt, and never trust
`cmake --build` alone to have rebuilt it.** Every harness loads a single fixed image
(`out/My_Pic_Project_<mcpu>/default.elf`), *not* the build tree it was configured in, so a test run
silently uses whatever ELF was written last - including a stale one from an older source revision or
a different `-D` set. This wasted a whole debugging cycle on 2026-09-22: an LCD-protocol test kept
reading the *previous* firmware's output because `cmake --build` printed only `ninja: no work to do`
(the build dir was cleaned after configure, so ninja had already built during the combined command
and main.c's edit had not been seen by a *fresh* configure). The failure looked like a firmware bug
and was pure staleness. Rules that prevent it:

1. Before running any simulator test, compare timestamps: `(Get-Item firmware/src/main.c).LastWriteTime`
   vs `(Get-Item out/My_Pic_Project_<mcpu>/default.elf).LastWriteTime`. The ELF must be **newer** than
   every source file you edited. If it is not, the build did nothing - fix that first.
2. Do not chain the reconfigure and the build in one shell command and then read only the tail; the
   `--build` output can be swallowed. Run `cmake --build <dir> --verbose` as its own command and
   grep it for the compile line of the file you changed (e.g. `main.c.p1`). "no work to do" means
   your change was not picked up.
3. When a test's behaviour does not change after an edit that should change it, suspect the ELF
   BEFORE suspecting the logic. A stale image is the most common cause of "my fix did nothing".
4. A `PICAMP_LCD_TEST` (or any other test-only `#ifdef`) build writes the SAME shared ELF path as
   the normal build. Rebuild the normal configuration afterwards, or the next suite run will load
   the test-only image.

**Finding (2026-09-22): FREQ_CTR I5 hot-switch root cause and fix.** The remembered-band rekey
engaged on the stale remembered band, then the band-verify mismatch folded the relay back to the
measured band *after* the amplifier was keyed, moving the band relay under a keyed amp (I5/I1
"HOT SWITCH"). Two firmware fixes in `main.c`:
1. `update_tx_sequence()` band-verify block: the `BAND_OUT_OF_SPEC` and mismatch-accumulating
   branches must `apply_bypass(); g_sequence_stage = 0; return;` - the original fell through to the
   PTT keying block and keyed on the unverified remembered band.
2. `handle_ptt_transition()` remembered-band branch: guard - if `freq_counter_measured_band()` is a
   real band that differs from the remembered band, the live RF wins (go to snoop), never restore the
   stale band. Without this the restore moves the relay to the wrong band and the fold-back creates
   an I4 transient (`current_band` disagrees with the relay output) and a keyed relay move.

**Open item (2026-09-22): "80m TX lock failed while injecting 1800 kHz".** After the two fixes the
80m band holds its lock correctly (`current_band=2`, `locked=true`, `stage=3` throughout the
injection window), but `validate_freq_ctr` asserts an EXACT `frequency_khz == "1800"` sample and the
Timer1 register-injection aliases with the firmware's 10 ms TMR1 reset, so the sampled value lands on
1740/1756/0 instead of exactly 1800. This is a harness sampling artifact, not a lock loss. Fix by
asserting the injected band is REJECTED (current_band stays the band under test) rather than requiring
an exact `frequency_khz` string match; or sample the injection window more finely.

**Harness note: sample settle/verify state when debugging band timing.** `STATE_VARS` in
`trace_ptt_sequence.py` now carries `g_band_settle_active`, `g_band_settle_elapsed_ms`,
`g_band_verify_active`, `g_band_verify_mismatch_ms`, and `first_dit_invariants.describe()` prints
them as `settle`/`settle_ms`/`verify`/`verify_ms`. Without these the settle/verify interaction is
invisible and only the symptom (the hot-switch sample) is seen. `tools/simulate/repro_i5_15m_10m.py`
is the minimal single-band repro (set `BAND_TESTS` to isolate a band); it runs
`validate_band_changes_are_cold` + `validate_freq_ctr` so the isolated verdict matches the suite.

**Finding (2026-09-23): the device strip, and the traps in it.** The project is PIC18F47Q10 ONLY;
the 16F port, its build option, its CI matrix leg and its docs are gone (`Ai-Notes.txt` carries the
standing rule). What that touched, and what it caught:

- `tools/simulate/run_sim.sh` and `run_sim.ps1` had `DEVICE="PIC16F18875"` / `$Device =
  "PIC16F18875"` hardcoded while everything else defaulted to the Q10. **Whenever a device default
  is changed, grep every launcher for the old name** - a launcher that disagrees with the build tree
  asks the simulator for one part and loads the other part's image, and that produces a wrong verdict
  with no error message.
- `tools/setup/parameterise_device.py` still *pattern-matches* MPLAB X's 16F tokens on purpose: those
  are the generator's tokens (MPLAB X regenerates `.generated/rule.cmake` from a 16F-created project),
  not a target. Do not "clean" them out, or a regenerated rule.cmake silently builds the wrong part.
  Its self-check had to be fixed to measure the body only - see `bugfixes.md` 2026-09-23.
- The per-device lookup tables in the harnesses (`INSTRUCTIONS_PER_MS = {...}.get(DEVICE, ...)`) and
  the `PICAMP_DEVICE` env indirection are gone: `DEVICE = "PIC18F47Q10"` and a single constant rate.
  The Q10 rates are NOT the same everywhere - `trace_ptt_sequence.py` and `first_dit_invariants.py`
  use **1625** instructions/ms while `test_first_dit.py` uses **1887**. That difference is measured,
  not a typo; do not "unify" them without re-measuring against that harness's own waits.
- **DO NOT ISSUE PARALLEL EDITS TO THE SAME FILE.** Two concurrent edits to `firmware/src/main.c`
  interleaved and duplicated whole blocks (the IPEN block and the ADFM block both came back mangled),
  and the file had to be restored from HEAD and redone one edit at a time. Batch edits across
  *different* files freely; keep the same file strictly sequential.
- macOS configure+build verified 2026-09-23: the DFP resolves out of the MPLAB X install
  (`/Applications/microchip/mplabx/v6.35/packs/Microchip/PIC18F-Q_DFP/1.30.487/xc8`), configure
  reports `PicAmpControl device: PIC18F47Q10 (mcpu=18F47Q10)`, and the Release build writes
  `out/My_Pic_Project_18F47Q10/default.elf`. Expect the benign linker warning
  `(1311) missing configuration setting for config word 0x300005; using default` on this part - it
  predates the 16F removal and is not caused by it.
