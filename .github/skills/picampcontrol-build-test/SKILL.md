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
