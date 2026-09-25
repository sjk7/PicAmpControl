---
name: build-test
description: "Use when building, testing or debugging PicAmpControl firmware on macOS and Windows: Debug or Release builds, CMake configuration, ctest, run_tests.sh / run_tests.ps1, simulator/mdb runs, the VS Code Simulate debug session, breakpoints and symbol reads, PTT/frequency-counter tests, band-lock tests, first-dit band detection, remembered-band fold-back, band-change/hot-switch guards, or build/test failures."

# PicAmpControl Build, Test and Debug

**The general rules - terse output, never "Hmm", verdicts from files, watchdog-only runs,
commit-and-push often, record durable findings - are ALWAYS-ON in `.github/copilot-instructions.md`.**
They are not restated here: this skill carries only the method and the traps of this domain.
**Hard rule: NEVER ASK A RUNNING TEST FOR ITS TERMINAL OUTPUT - IT BREAKS THE TERMINAL.** (user
instruction, restated 2026-09-23: *"we should not ask for terminal output when running tests --
this breaks the terminal. We are using a file-based approach instead."*) The verdict method is
file-based, always: launch the run with its output redirected into a log file, append the exit-code
line, then read the log, that line, and the watchdog progress log. Do not run a test in order to
watch it, do not `tail`/`grep` a log into the console, and do not ask the tool for captured terminal
output - MDB emits megabytes, the capture wedges the shell, and "the terminal showed nothing" says
nothing at all about the run. The terminal is for launching and for short bounded process checks
only.

**Hard rule: the PTT line is ACTIVE LOW - `RC0` HIGH is RX (idle), and it must FALL LOW for TX.**
(user instruction, 2026-09-25, after the agent drew conclusions from traces while getting this
backwards - *"You are making a fundamental error here. What's more you do not seem to know you are
doing it."*) So in every harness level, every trace annotation and every diagram lane:
`write pin RC0 5v` = RX/idle/unkeyed, `write pin RC0 0v` = key down / TX asserted, and `print pin RC0`
reading **0** means the operator is keying. Never describe a HIGH RC0 as "keyed" or "active".
The second half of the rule is what the key-down means: **on the falling edge of PTT the firmware
must WAIT for a valid frequency detection before it continues the rest of the sequence** - refusing
to transmit only if no frequency can be detected. It is not a fixed delay, and it is not immediate:
the key produces three jobs (band relays switch immediately, the frequency counter is sniffed and its
band confirmed against the relay output, then the TX path is enabled) in that order. The user's own
word-for-word statement is kept in `docs/steves-sequence.md`; read it before changing or judging the
key-down path, and do NOT re-derive it. When a trace looks wrong, check the polarity first: a
"PTT never latched" or "release never keyed" conclusion is usually RC0 read the wrong way round.

**`g_sequence_stage` names (2026-09-25) - use these, never "stage 4" alone.** The numbers are the
harness contract (traces and assertions read `g_sequence_stage` by number); `firmware/src/main.c`
now carries the same names as `#define`s. Engage runs 0->1->2->3 on key-down; unkey runs 3 or 2 ->
4 -> 5 -> 0.

| # | firmware name | harness trace label | what the outputs are doing |
|---|---|---|---|
| 0 | `SEQ_IDLE` | idle | not transmitting: TX path open, TX_VCC and TX_BIAS off |
| 1 | `SEQ_TX_ON` | tx-on | RELAYS closed; counting `tx_vcc_delay_ms` before TX_VCC |
| 2 | `SEQ_VCC_ON` | vcc-on | TX_VCC up; counting `tx_bias_delay_ms` before TX_BIAS |
| 3 | `SEQ_BIAS_ON` | bias-on / transmitting | TX_BIAS up and sensed; PTT COMPLETE shown |
| 4 | `SEQ_RELEASE_RELAYS` | release-relays | unkey: RELAYS opened, TX_VCC STILL UP, counting |
| 5 | `SEQ_RELEASE_VCC` | release-vcc | unkey: TX_VCC removed, TX_BIAS STILL UP, counting |

So `release did not enter stage 4` = "the `SEQ_RELEASE_RELAYS` window (relays already open, TX_VCC
still on) was never captured by a sample". Write the name beside the number in every report and in
every annotation: a bare "stage 4" is unreadable, which is exactly the complaint that produced this
table (user, 2026-09-25: *"It would be much more useful if you gave these 'stages' names. How can I
know what stage 4 is ffs?"*).

**Fault names (`g_trip_reason`, an enum of bit flags).** Same rule: never report the raw mask.
`trip_reason_name()` in `main.c` maps a mask to the highest-priority cause, and the LCD trip screen
always prints a name (`FAULT: <NAME>`) - on the bench, with no harness attached, the panel is the
only read-out there is (user, 2026-09-25).

| bit | firmware enum | name shown / harness `block_reason` |
|---|---|---|
| 0x01 | `TRIP_REASON_SWR1` | `SWR1` |
| 0x02 | `TRIP_REASON_SWR2` | `SWR2` |
| 0x04 | `TRIP_REASON_HWFAULT` | `HARDWARE` (`FAULT: HWFAULT` in the harness) |
| 0x08 | `TRIP_REASON_CURRENT` | `CURRENT` |
| 0x10 | `TRIP_REASON_TEMP` | `TEMPERATURE` |
| 0x20 | `TRIP_REASON_OVERDRIVE` | `OVERDRIVE` |
| 0x40 | `TRIP_REASON_DRAIN` | `DRAIN` |

Mask 0, and any bit the table does not know, names as `UNKNOWN` - never blank.

**The LCD names both while the harness is absent** (user, 2026-09-25: *"if we get an unexpected
sequence error, the LCD displays actually what went wrong in the sequence"*): the stage is shown as
`TX <STAGE-NAME>` while keyed and on the PTT COMPLETE screen, the STATUS page shows `SEQ <STAGE-NAME>`
whenever the sequence is not `SEQ_IDLE` (i.e. a release that never finished), and the trip screen
always prints the fault name. So a stall and a trip are both readable off the panel with no harness
attached, and a harness report should quote the same names.

**Process traps re-hit the hard way on 2026-09-24 - read these before touching a run.**
1. **The rule above was broken repeatedly and the terminal did wedge.** The damage is concrete: after
   one `grep` over a multi-megabyte MDB transcript, *every* later `run_in_terminal` call in that
   shell returned empty - even `echo`, `pwd` and `git log` - until the shell was recreated. A wedged
   shell looks identical to "the command found nothing", so it silently produced wrong conclusions
   ("the run isn't progressing") for a long stretch. If a terminal stops echoing a plain `echo`, STOP
   using it and relaunch rather than re-running the command.
2. **Run the suite through the sanctioned wrapper only.** `run_suite_with_watchdog.py` is the entry
   point the skill mandates: it opens the log in a VS Code tab and beats a heartbeat into it. That is
   the ONLY thing that makes a run visible to the user. `run_detached.py` starts a private session
   and does **not** open a tab: on 2026-09-24 its child died silently (empty run log, empty heartbeat
   log, `ps` showed the PID dead, zero sim processes), so the user was told to "watch the tab" while
   nothing existed to watch. Use `run_detached.py` only to escape the terminal's SIGTERM, and only
   when its log is opened by hand.
3. **Commit each verified increment the moment it passes.** A fix that passed its own test was held
   uncommitted for many steps because a *different, later* assertion was still failing - the user's
   complaint: "been a looooong time with no commits". Bundling unrelated work behind an open item is
   the failure; commit the verified step, then continue.
4. **One hypothesis, one cheap test - no essays.** When a failure "moves" (SWR1 -> 80m -> 15m across
   runs), suspect the shared stimulus, not the band. Isolate with the single-band repro
   (`repro_i5_15m_10m.py`) instead of re-running the 11-scenario suite; state the hypothesis in one
   clause, test it, then move.
5. **DO NOT over-analyse: act on first instinct and prove it with a quick test, do not re-litigate
   the same deduction in circles.** (user instruction, restated twice on 2026-09-24: *"Why are you
   making it so hard?"*, *"Stop saying 'but wait'. Go with your first instinct instead of over-
   analyzing, and prove it (or not) with a quick test. You are spending more time thinking than you
   are testing."*) The failure mode it guards: the agent spent dozens of tool calls re-deriving the
   SAME conclusion (a frequency-classification timing artifact) while the user had already given the
   correct, simpler rule, and each "but wait, let me reconsider" cost a full round-trip. The rule:
   once a hypothesis explains the evidence, TEST it immediately - write the change, build, run one
   harness - and only broaden if the test contradicts it. Never emit a visible chain of "reconsider
   X / reconsider Y" reasoning; it is billed output for zero information.
   **DO NOT HEDGE.** (user instruction, 2026-09-24) No "I can fix it -> actually -> wait, no ->
   or even...". No "maybe", no "perhaps", no "I think", no qualifying every claim. State what you
   know and what you are doing, and do it. When evidence contradicts a hypothesis, say so in one
   sentence and state the NEXT action; do not narrate the reversal. Every hedge line is billed
   output and reads as indecision.

**How a run is watched (STICKY user instruction, 2026-09-23): the user watches the log file - the
heartbeat file - in a VS Code tab while the tests run. Never in the terminal.** The user's words:
*"we watch files now during sim runs, and never output to terminal. The code user sees the log file
(heartbeat file) in VSCODE when the tests run."* So the log must stay visible while the run is live,
but **it must NOT steal focus** (user instruction, 2026-09-24): the user types in the chat or works
in another window, and a `code -r <log>` call raises VS Code over what they are doing. The method:
1. Truncate the log FIRST (`Clear-Content <log>`, or `: > <log>` on macOS). The launcher appends, and
   deleting a file a watcher holds open kills the watcher.
2. Launch the run with its output redirected into that log. `run_suite_with_watchdog.py` /
   `run_logged.py` write a `RUN_BEGIN` header and append the exit-code line at the end.
3. **On Windows, NOTHING is opened for you - and that is deliberate.** VS Code's CLI has no
   background-open: `code -r <log>` reveals the file as the ACTIVE EDITOR TAB and un-minimises the
   window, and putting the window focus back afterwards does not undo the tab change. The user's
   rule is "show the log, never move the focus, not even to the tab" (2026-09-25: *"I still want the
   log shown, I just don't want it to have focus, that's all"*, then, after a `code -r` plus
   focus-restore attempt, *"The log is still getting focus when shown. Leave the focus ALONE."*).
   So `open_progress_log.open_in_editor()` opens on macOS (`open -g`, no activation, no tab change)
   and returns False on Windows, printing the path instead; the launcher writes
   `LOG_TO_WATCH <path>` into the run log's header so the file to follow is discoverable. The ways
   to watch on Windows are the operator's own: a tab they already have open, or the **Log Viewer**
   extension following the file (it re-reads inside its own webview and never touches a tab).
   Do NOT "fix" this by calling `code -r` "just to be helpful" - that IS the complaint.
   `AppendLog` in `platform_process.py` is the heartbeat helper.
4. Which file is the moving one depends on how you launched it: **when you pass `--log <file>`, the
   heartbeat appends INTO that file** (verified 2026-09-23: the heartbeat process is spawned with
   `--log` pointing at the same path). Only when `--log` is
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
7. **Launch a single-harness debugging run through the watchdog too**, e.g.
   `run_suite_with_watchdog.py --test first-dit`. Running `test_first_dit.py` directly gives a tab
   that NEVER moves: the harness's stdout is block-buffered through the redirect, so the file stays
   at zero bytes until the process exits, and the user is left looking at an empty tab (reported
   2026-09-23). The watchdog is what writes the `HEARTBEAT`/`MDB` lines that make the log live - its
   value is not just the timeout, it is the visibility.

**The tool that follows the file (moved from `Ai-Notes.md` 2026-09-24, replaced 2026-09-24).**
Following is done by the marketplace **Log Viewer** extension (`berublan.vscode-log-viewer`): it
re-reads the file on an interval (`logViewer.options.fileCheckInterval`, default 500 ms) and follows
tail by scroll position (`logViewer.followTailMode`, "auto"/"manual"), all inside its own Webview
panel - it never opens or reclaims the text-editor tab, and never pulls focus, in VS Code or from
another app. That focus-stealing is exactly why the in-repo `tools/logfollower` extension (Log
Follower) and its `install_logfollower.sh`/`.ps1` installers were DELETED on 2026-09-24 - it kept
raising VS Code above other windows while the user was elsewhere. **Install it once per machine:
`code --install-extension berublan.vscode-log-viewer`** (its install is not automated - neither
`run_tests.sh` nor `run_tests.ps1` touches it). To watch a run: open the Log Viewer panel and point
it at the log (a `logViewer.watch` entry or the "Toggle log view" command).
`tools/simulate/open_progress_log.py <log>` still opens the log in a plain tab (it is the file, not
the following, that the user reads), and `tools/simulate/run_detached.py` starts a run in its OWN
session so the agent's terminal harness cannot SIGTERM it mid-run - it did exactly that twice on
2026-09-23, and the damage reads as `SUITE_EXIT=143` with the log stopping mid-file, i.e. like a test
failure when it is not one. `spacetown.filetail` was rejected for cost (~110% of one core in the
extension host plus ~24% in the main process); any tool showing that load again is dropped in favour
of reading the log on demand. **A console tail is forbidden**, and it is also silently broken:
`Get-Content -Wait` holds the handle to the file it opened, and the launcher unlinks and recreates its
log at startup, so a tail started before the run reads a deleted file and shows nothing.
**Hard rule: EVERY simulator run goes through the watchdog wrapper - NO CHEATING.** (user
instruction, 2026-09-23: *"ALL these tests should run through the watchdog -- always"*, then
*"everything runs via the watchdog. No cheating!"* - the second time because a raw `mdb.sh` probe had
already slipped through under "it is only a probe and I want the values now".) **Everything means
every test AND every probe. No cheating means no exception** for a quick check, a one-off
measurement, a harness you are only debugging, or a run whose values you want sooner. If you are
about to type `mdb.sh`, `test_first_dit.py` or `trace_ptt_sequence.py` directly, that IS the cheat -
stop and wrap it.

Wrapped entry points, and nothing else:

| What | Wrapped launch |
|---|---|
| The two registered tests | `ctest --test-dir _build/My_Pic_Project/release --output-on-failure` (both route through the watchdog - see `user.cmake`) |
| One test on its own | `run_suite_with_watchdog.py --test suite`, `... --test first-dit` |
| A minimal repro | `run_suite_with_watchdog.py --test repro-swr1-rearm` (`repro_swr1_rearm.py`), `--test repro-20m`, `--test repro-release` |
| A probe / one-off MDB script | `python tools/simulate/run_mdb_probe.py <script.mdb> --log <log>` |

Why it is not optional: a bare run has **no timeout**, **no heartbeat** (so the log tab the user is
watching never moves - the harness's stdout is block-buffered and stays at zero bytes until exit),
**no orphan clean-up**, and its verdict lines land **outside the run's log**, which is the one place
the standing rules say a verdict may be read from.

**Hard rule: NEVER POLL, SLEEP OR WAIT FOR A RUN - THE HARNESS TELLS YOU WHEN IT FINISHES** (user
instruction, 2026-09-25: *"Note the run is finished. Don't wait there like an idiot!"*, then *"It's
finished. Why you not realise?"*). A launch in the background terminal REPORTS ITS COMPLETION on the
next turn, with the exit code, and the user is watching the same log. Sitting in `Start-Sleep` loops
tailing the log is wrong three ways: it burns turns and tokens, it outlives the notification (the
agent kept sleeping after the run had ended, twice), and it hides the one thing worth doing - real
work on the fix in the meantime. So: launch, then spend the same turn on the next piece of real work
(fix, harness, skill note). Verdicts still come from FILES, never from the terminal.

**A LOG THAT LOOKS DEAD IS NOT EVIDENCE THAT THE RUN IS DEAD - READ THE BYTE DELTA (2026-09-25).**
The user reported *"Your currently running test is producing no output"* about a repro run whose log
was in fact complete: a short stdout burst from the harness, then `HEARTBEAT ... delta=0` and
`MDB (no new output)` for the rest of a 30 s run. Three things made that log look dead:
- The heartbeat writes `mdb_bytes=<n> delta=<n>` **and** a separate `MDB <line>`. When the MDB side
  log has grown but holds no new COMPLETE line yet (MDB writes in bursts; the reader stops at the
  last newline), the MDB line still says `(no new output)`. `delta` is the liveness field; `(no new
  output)` means only "no whole new line to show". Never read the MDB line alone as "the run is
  stuck".
- A repro harness prints only on failure (or only a summary), so a *passing* repro is deliberately
  quiet. That is the harness, not the run.
- The heartbeat process outlives the child's last write by tens of seconds on Windows, so a tail of
  nothing after the last output is normal.
**The trap is the inference, not the log.** Before saying anything about a run's health, check the
side log's size/mtime delta and the run log's content; if a log really is empty, that is a
launcher/tooling bug (see the `PermissionError` note below) - never re-run blindly.

**Only one run at a time, and a launch that fails fast says so.** The MDB progress log is now derived
from the run log's own name, so a second concurrent run used to die in `unlink` with
`PermissionError: [WinError 32] ... used by another process` before it started (2026-09-25 - a live
suite blocked a repro run, which reads as a broken launcher rather than as "a run is already
going"). The same situation also shows up as `cleanup_sim_processes.py` answering `REFUSING TO CLEAN
UP: a run appears to be in progress` with the live PIDs listed - that refusal is CORRECT, and the
answer is to wait for the run, not to force the sweep.

Known gap, and the right way to close it: `run_mdb_probe.py`'s log has been seen to omit MDB's
`print` values on macOS (2026-09-23 - a ~180-byte log for a probe that ran fine). Fix that log, do
not work around it with raw `mdb.sh`; the workaround is exactly the cheat this rule forbids. A new
test must be registered in `cmake/My_Pic_Project/default/user.cmake` **and** given a `--test` choice
in the launcher, or the watchdog cannot wrap it and this rule is broken by construction.

**Trap (2026-09-24): the docs can teach the cheat.** `TESTING.md` listed the first-dit test's command
as a bare `test_first_dit.py`, while `user.cmake` actually registers
`run_suite_with_watchdog.py --test first-dit --timeout 600`. A session following the doc would have
run a harness directly - the forbidden thing - and been given a tab that never moves. **When a test
registration or a budget changes, grep the docs for the old command in the same commit.** The same
check applies to `--timeout` values: `--timeout 400` was still quoted in
`docs/lcd-test-handoff.md` long after the budget became 1200/1500, and a 400 s budget would have
killed a healthy Windows suite.

**Canonical build directories (2026-09-24).** `_build/My_Pic_Project/release` is the one the editor
reads (`.clangd`, `.vscode/settings.json`); `_build/My_Pic_Project/sim` is where the tests run and
what `run_tests.sh`/`.ps1` configure. **The `q10_*` trees are gone** - the Q10 is the default device,
so it no longer needs a build tree, a `-DPICAMP_DEVICE` on every command, or its own VS Code tasks.
A new build directory is a new place for a stale database and a stale ELF to hide, so do not add one
without a reason that a single directory cannot serve.

**A FAILED SCENARIO NOW WRITES AND OPENS ITS OWN SCOPE TRACE (2026-09-25, user instruction: *"When a
run fails, make sure there is a scope trace with relevant variables shown. Then show it
automagically in vscode."*).** `tools/simulate/scope_trace.py` renders `_build/My_Pic_Project/sim/
graphs/<scenario>_scope.png` from the samples the harness already parsed, picks the lanes from the
data (every signal that CHANGES, plus `RC0`/`g_ptt_active`/`g_fault_latched`/`g_sequence_stage`,
which matter whether they move or not), and marks the trip / PTT-release / PTT-re-arm instants as
labelled vertical lines. `trace_ptt_sequence.py` calls it from the `except` of both the suite's
per-scenario validation and single-trip mode (`--trip SWR1`); a repro calls `scope_trace.on_failure()`
itself. Traps found while building it, each of which produces a trace that looks fine and says
nothing: **the firmware's bools print `true`/`false`**, so a naive `float()` conversion plots
`g_ptt_active` and `g_fault_latched` as flat zero lines (map the words to 1/0); and **the events must
be staggered vertically, inside the top lane**, or a release and the re-arm that follows it overprint
each other into a smear (and, since 2026-09-25, the top lane also carries the ms time axis - labels
above it collide with the tick labels).

**A FAILURE TRACE MUST SAY IN WORDS WHAT FAILED AND WHAT WAS EXPECTED, AND SHOW THE LCD (user
instruction, 2026-09-25: *"You still are not summarizing with text at the end of the graph why
exactly it 'failed' and what it should have done instead (ie what you were testing for). Show the
display you would send to the LCD, too, when failure detected."*).** Every failure trace therefore
carries three prose blocks under the lanes - **WHAT THIS TEST IS FOR** (the expectation, from
`SCENARIO_CHECKS` in `trace_ptt_sequence.py`), **WHAT THE FIRMWARE ACTUALLY DID** (counts read out of
the samples: keyed samples, stage-3 samples, latched samples, how many released samples the firmware
acknowledged, and for FREQ_CTR the per-band locked/non-zero counts), and **WHY THAT IS A FAILURE**
(the assertion text) - plus a 16x2 **LCD panel reconstructed from the failure sample's state**
(`scope_trace.lcd_screen()`, mirroring `show_menu_page()`'s precedence: trip > PTT COMPLETE > keyed
stage > `SEQ <STAGE>` > home page; the raw `g_trip_reason` mask is named, never printed). The
characters are NOT captured - the harness samples the TX and band pins, not the LCD bus - so the
panel is labelled "reconstructed", and that distinction is part of the evidence. Three findings:
- **Draw the prose as ONE text object.** Building it line by line and advancing a y position per
  wrapped line spaced the lines by figure fraction, which on a tall trace left a hand's width
  between them (seen and rejected in the first attempt).
- **Never let the LCD panel fail silently** - the first version caught `ImportError` and returned
  with no message, so a missing panel looked exactly like a panel deliberately left out.
- **The panel's axes height must follow the LCD's own aspect** (16 characters x 2 rows in the
  `render_lcd_lifecycle_diagram.lcd_panel` drawing space): a fixed fraction stretched it into a
  shape that did not look like the hardware. Pass that helper an EMPTY note and caption below the
  box yourself - its own note sits inside the dark bezel, where its dark-grey text is unreadable.
  Render and inspect a failure trace OFFLINE from the last run's `suite_raw_mdb.log`
  (`scope_trace.render_scope(..., **harness._failure_context(samples, scenario, exc))`) instead of
  re-running the suite to look at a picture.

**ROOT CAUSE of the Windows `SWR1 did not clear and re-enter TX after a PTT re-arm` failure
(2026-09-25): the harness's PTT release was shorter than the firmware's PTT poll latency, so the
release edge was never seen.** The trip itself was fine and the bridge was already back to a safe
reading; the firmware simply never observed the release, so `handle_ptt_transition(false)` never ran,
the re-key that followed was not an edge, and `clear_fault_latches()` was never reached - the latch
stayed set for the whole 400 ms re-arm window (`g_ptt_active` `true` in every one of 451 samples,
`g_fault_latched` `true`, `g_trip_reason` 1). **MEASURED 54.0 ms** from `write pin RC0 5v` to the
first sample with `g_ptt_active=false`, against a release window of 10 x 5 ms = **50 ms**. It is a
main-loop pass-length effect, not a trip effect: the LCD refresh runs `__delay_ms` loops compiled
for the real 64 MHz core against a model ~8x slower, so a pass can straddle the whole release
window. It is also PHASE-SENSITIVE, which is why it moved between platforms and looked
intermittent - the repro only reproduces it when it mirrors the suite's phase, including the
throwaway `assert PTT during startup, then release` prelude the suite emits.
Repro: `tools/simulate/repro_swr1_rearm.py` (`--test repro-swr1-rearm`), which drives only this
sequence and prints the measured release poll latency. Fix: the release window is now
`40 x 5 ms = 200 ms` (~4x the measured latency, matching the base scenario's own release), in the
`trip_inputs` branch of `trace_ptt_sequence.py`. **When a harness holds PTT released before a
re-arm, size that window against the measured poll latency, never against what looks sensible** -
any release shorter than ~60 ms can silently produce a "did not re-arm" failure with no firmware
fault behind it.

**Hard rule: never run the pre-flight cleanup while a run is live - it kills it.** User-visible
symptom: the wrapper records `SUITE_EXIT=143` / `CTEST_EXIT=143` (SIGTERM) and the log stops
mid-file, which reads exactly like a test failure and is not one (2026-09-23: one complete
merged-suite pass and one barely-started run were destroyed this way). The cause is that
`ORPHAN_PATTERNS` contains `run_suite_with_watchdog.py`, `trace_ptt_sequence.py --suite` and
`test_first_dit.py`, so the sweep matches a run in progress, not only MDB/JVM leftovers.
`cleanup_sim_processes.py` now refuses and prints what it found; treat that refusal as correct and
wait for the run. Run it *before* launching, never during.

**`<script>.mdb` files have NO comment syntax - a `;` line is a command.** MDB answers
`Undefined command: "; ..."` and the probe exits 255 with nothing measured (cost a run on
2026-09-23). Keep `.mdb` scripts comment-free and document them in the neighbouring `README.md`
(`docs/hardware/q10-bringup/README.md` now carries the rate-probe method for exactly this reason).

**What the simulator models - and what `W0106-SIM` is really about (2026-09-22; folded in from the
user's `mistakes.md` on 2026-09-24, when that file was deleted).** The core CPU and the interrupt
controller ARE modelled: a pending flag breaks execution and the ISR is entered. `W0106-SIM` is scoped
strictly to **PPS / clock-source routing** - the model cannot route an external stimulus pin through
the PPS mux to a peripheral clock input - and it says nothing about interrupts in general. So never
report "interrupts do not work in the simulator"; that was claimed, and it was wrong. When a
pin-routed clock source is the thing under test, bypass the PPS model rather than abandoning the test:
drive the peripheral or flag register directly behind `#ifdef __MPLAB_DEBUGGER_SIMULATOR` and validate
the ISR and everything downstream. In this project that is the T1CKI band-snoop path (`T1CKIPPS`) -
hence the harnesses inject into `TMR1H`/`TMR1L` instead (see `tools/simulate/trace_ptt_sequence.py`
and `docs/first-dit-band-detection.md`). The same warning fires on every reset for TMR1/TMR3/TMR5 and
is stripped as noise by the harnesses and by `run_sim.sh`/`.ps1`.

**Editor/language-server problems belong to a different skill.** If the Problems panel or IntelliSense
misreports the firmware - `'xc.h' file not found`, undeclared registers such as `LATCbits`/`ADCON1`/
`ADRES`/`PIR1bits`, `Unknown argument`/`Unsupported argument` for `-mdfp=`/`-mcpu=`, a stale
`compile_commands.json`, or `.clangd` / `.vscode/settings.json` / `c_cpp_properties.json` edits - then
**read `.github/skills/editor-clangd/SKILL.md`** rather than working it out from here.
None of it can affect a build or a test: XC8 is invoked directly and needs none of that configuration,
so a green build says nothing about it.

**Skill identity.** The *folder* name is the skill's name and must equal the frontmatter `name:`; the
file must be exactly `SKILL.md`. Renaming the file - even to something descriptive - makes the skill
silently undiscoverable, because VS Code matches that literal filename inside `.github/skills/<name>/`.
The two skills here are `build-test` (this one) and `editor-clangd`; the delegate agent is
`build-runner`, and an agent with no `name:` simply takes its filename.

**Output discipline and the "record every durable finding" rule are always-on in
`.github/copilot-instructions.md`.** What is specific to this skill: findings from a build or a test
run belong in THIS file, and the session that found one is the only one that still has the context -
so write it before moving on, never "for later". The test of whether it is recorded: could a fresh
session hit the same problem and be stopped by what is written here? If not, it is not written yet.
**Traps found 2026-09-23 (second batch) - each one cost a run or a wrong conclusion.**

- **A probe that reads a peripheral register BEFORE stepping gets reset defaults.** `print T2CLK` and
  `print PR2` straight after `program` answered `0` and `255` - the reset values - which reads
  exactly like "the firmware's timer configuration never took effect". Step past init first
  (`Stepi 300000`), then read SFRs.
- **Pick a counter that actually runs.** `g_band_cache_idle_ms` stays at 0 at startup (it only counts
  once the band cache exists), so bracketing it measured nothing and looked like a dead tick. The
  startup inhibit (`g_startup_inhibit` clearing 1000 ms after the tick starts) is the counter to
  bracket for a rate measurement - that is what the original Windows probe did.
- **`run_mdb_probe.py`'s log did not contain the probe's printed values on macOS** - only its
  `RUN_BEGIN`/heartbeat lines (a ~180-byte file), so a probe that had run fine looked like it had
  produced nothing. For a probe whose *values* you need, run `mdb.sh <script> > /tmp/x.log 2>&1` and
  read that file. The watchdog-launched runs (`--test first-dit`, the suite) do capture the
  harness's own prints in their log.
- **`.mdb` scripts carry absolute `program` paths**, so a probe copied from the Windows side points
  silently at `E:/...`. Check the path whenever one is reused, and prefer generating the script from
  Python (as the harnesses do) when it has to work on both platforms.

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

**2026-09-24: the same aliasing re-found, worse, and re-found AGAIN the same session.** After the
band-coverage assertion was relaxed to `current_band == expected` (the right fix), the failure moved
to `validate_freq_ctr`'s *lock* check, at a LATER band each run (80m once, then 15m). The added
`FREQ_DEBUG ... lock_samples` trace is decisive: for the failing band every sample reads
`(cache_valid=false, current_band=1, freq=0, locked=false, ptp=false, stage=0, establish=false,
snoop=false, settle=false, verify=false)` - the classifier is parked on its 160m no-signal default
with `freq=0`, so the band is never established and PTT never latches. The frequency injection is NOT
reaching the classifier for later bands (not even an aliased 1740/1756 - a hard 0). This is the
TMR1-10ms-tick aliasing from the 2026-09-22 note, but manifesting as total injection loss rather than
an off-by-a-few-counts reading. It is a harness stimulus bug, not firmware. Do NOT widen the
own-frequency hold window blindly or relax `validate_freq_ctr` - the injection itself must be fixed
(see the single-band repro `repro_i5_15m_10m.py`); the 40->80->30->40 widening I made did not address
it and masked the real symptom. The reliable repro is isolating ONE band with `BAND_TESTS`, not the
full 11-scenario suite.

**2026-09-24 (later): the FREQ_CTR failure was a STIMULUS CADENCE bug, and the fix is the cadence,
not the windows - SOLVED.** Root cause, proved with the per-sample dump: the firmware classifies a
band only after `STABILITY_REQUIRED_TICKS = 2` consecutive 10 ms gates read the SAME band, and the
harness's `write_tmr1_count` + `stepi(5)` cadence races the firmware's 10 ms `freq_counter_tick_10ms()`
gate, so the measured frequency flickers (1800 -> 16 -> 3600 -> 0) and `current_band` never settles.
The failure then moves to whichever band runs last (80m, 15m, 10m) and reads `freq=0, current_band=1,
locked=false, stage=0` - the classifier parked on its 160m no-signal default, NOT a lock loss and NOT
a firmware bug. Injecting with a FULL 10 ms gate per iteration reaches stability and the bands do
lock - but **every full-gate variant traded the lock check for the I5 hot-switch invariant**
(`band-select outputs changed while the amplifier was keyed`), because a longer hold moves the
injected-frequency switch relative to the keyed window. Tested and rejected on 2026-09-24: widening
the per-band windows (40/20/30 -> 80/30/40), full-gate PREFLIGHT (breaks the base PTT release -
"release did not enter stage 5" - because the preflight is shared by every scenario), full-gate
band-check holds (passes lock, fails I5), atomic T1CON stop/inject/restart (no effect on the lock
bug), and an 800 ms trip re-arm window.

**The working design (verified green on the full 11-scenario suite, 2026-09-24):** a `hold_band`
helper re-injects the Timer1 count every 5 ms (`write_tmr1_count(f); stepi(5); sample()`) and each
band check is split into three phases that never change frequency while keyed:

1. Phase A - `hold_band(f, 60)` (300 ms) UNKEYED: all relay movement for the band happens here.
2. Phase B - `write pin RC0 0v` then `hold_band(f, 120)` (600 ms) keyed at the SAME frequency.
3. Phase C - `write pin RC0 5v` then `hold_band(f, 40)` (200 ms).

Two properties make it work and both are required: **5 ms chunks** re-inject faster than the 10 ms
gate, so a fresh count is in TMR1 whatever the tick/step phase (the earlier 10 ms step assumed the
injection landed inside the gate and drifted out of phase later in the run - it passed in isolation
and failed at 20m in the suite); and **one constant frequency per phase** satisfies
`STABILITY_REQUIRED_TICKS = 2` while guaranteeing no relay can move under the keyed amplifier.
`validate_band_outputs` only needs `current_band == expected` plus the single band-change sample
skipped, so the design is otherwise unchanged. Keep the whole-suite run as the verdict - this bug
reproduces only in the suite, never in `repro_i5_15m_10m.py`.

**ROOT CAUSE of every "injection lost / freq=0 / freq=73" symptom above (2026-09-25): the Timer1
injection wrote `TMR1L` BEFORE `TMR1H`.** With `RD16` set (`T1CON` running value `0x27`), a write to
`TMR1H` is buffered and only committed when `TMR1L` is written, so L-then-H silently DROPS the high
byte: the count is truncated to its low byte. 14000 kHz injects as `0x88B8` -> read back `0x00B8` =
184 pulses = **73 kHz** (band 1), which is the exact `freq=73` this skill had been attributing to
"aliasing with the 10 ms TMR1 reset". 7000 kHz (`0x445C`) truncated the same way to `0x005C` = 92
counts = 37 kHz (band 1, the no-signal default), so the base PTT scenario's "40m" preflight was never
band 3 either. Every injected band read as roughly 0.4 x its own low byte, which is why the failures
looked like "fails at a later band each run".
**Fix: always write `TMR1H` first, then `TMR1L`**, and if a torn read is still feared, bracket with
`T1CON 0x26` / `0x27` as before. Proved with the minimal repro `tools/simulate/repro_first_dit_20m.py`:
L-then-H gives `freq_khz=73 current_band=1`, H-then-L gives
`freq_khz=14000 current_band=4 locked=true` (PASS). Check byte order FIRST whenever an injected
frequency reads as a small number (roughly 0.4 x the low byte). **Superseded:** the 5 ms/10 ms cadence
experiments listed above were chasing this truncation, so treat the "aliasing" explanation in the
2026-09-22 and 2026-09-24 notes as historical.

**`release did not enter stage 4` is a SAMPLING ALIAS, not a firmware fault (2026-09-25).** Once the
injection above was fixed the base (plain PTT) scenario moved to
`AssertionError: release did not enter stage 4`, and its own trace shows stage 3 -> 5 -> 0 with RC5 and
RC6 both rising inside one 5 ms sample. `tools/simulate/repro_release_stage4.py` (watchdog
`--test repro-release`) reproduces the same release path at **1 ms** sampling and PASSES: stage 4 is
present and lasts ~4 ms (measured 1513-1516 ms), i.e. shorter than the suite's 5 ms release sample,
so no 5 ms sample can be guaranteed to land in it. `tx_vcc_delay_ms` is the stage-4 length - check it
before assuming a firmware bug. That the repro PASSES means it is evidence, not a repro: do not
"fix" the firmware for this, and do not relax the assertion - make the release sampling fine enough
to see a stage whose length it cannot exceed. The repro writes a CSV, a timing diagram and its log;
open them with the focus-safe helper (`open_progress_log.open_in_editor`, which uses `open -g` on
macOS and refuses to open at all on Windows unless the editor is already the foreground window), never
by stealing focus into the tab.

**Trap (2026-09-24): a key-down that lands inside the startup inhibit looks exactly like "PTT was
never latched".** `FREQ_CTR_FAIL` keys at the end of a fixed idle, and at `105 x 10 ms` the keyed
window (1.05-1.25 s of harness time) ended just as the inhibit cleared at ~1.25 s, so every keyed
sample still read `g_state=5 STARTUP INHIBIT` and the assertion
`PTT was not latched when the frequency counter had no signal` fired. The harness time axis is not
firmware time (`INSTRUCTIONS_PER_MS = 1625` under-advances against the measured 1695), so the inhibit
appears longer in harness samples than its 1100 ms nominal. Fixed by idling 130 x 10 ms before keying
and holding the key 400 ms; the firmware has no snoop timeout, so a longer key-down cannot unlatch
PTT. When a negative test asserts a latch, always confirm the key-down is clear of the inhibit in the
written CSV (`freq_ctr_fail_trace.csv`, `block_reason` column) rather than trusting the sample count.

**Resolved (2026-09-24):** the SWR1 trip re-arm "did not clear and re-enter TX" failure seen earlier
the same day is gone on the committed tree - SWR1 passes with the 400-iteration re-arm window
(`de2ebe3`) in the full 11-scenario run, so the 800 ms window experiment was unnecessary. The
full-suite verdict on that run was 11/11 `SUITE_SCENARIO_PASS` with every I1-I6 band invariant PASS,
including 0 I5 hot-switch violations and all 6 FREQ_CTR bands keyed-and-locked.

**Harness note: sample settle/verify state when debugging band timing.** `STATE_VARS` in
`trace_ptt_sequence.py` now carries `g_band_settle_active`, `g_band_settle_elapsed_ms`,
`g_band_verify_active`, `g_band_verify_mismatch_ms`, and `first_dit_invariants.describe()` prints
them as `settle`/`settle_ms`/`verify`/`verify_ms`. Without these the settle/verify interaction is
invisible and only the symptom (the hot-switch sample) is seen. `tools/simulate/repro_i5_15m_10m.py`
is the minimal single-band repro (set `BAND_TESTS` to isolate a band); it runs
`validate_band_changes_are_cold` + `validate_freq_ctr` so the isolated verdict matches the suite.
**`test_first_dit.py` keeps its OWN `STATE_VARS` list** (it reassigns `harness.STATE_VARS`) and was
left out of that change: it printed `settle=? verify=?` on every sample while the merged suite
printed real numbers from the same ELF, and `describe()`'s `?` means "key absent from the sample",
NOT "symbol unreadable" - so the state that decides whether a remembered-band engage is abandoned
was invisible in exactly the harness whose clause (c) needs it. Both lists must be kept in step;
fixed 2026-09-23.
**A clause that prints its samples only on success is undiagnosable when it fails.** Clause (c)
raised `the warm-start PTT never keyed the amplifier` with no trace of the window at all, because
`show()` is called on the success path. Failures now print the phase's samples before raising.

**Finding (2026-09-23): the device strip, and the traps in it.** The project is PIC18F47Q10 ONLY;
the 16F port, its build option, its CI matrix leg and its docs are gone (`Ai-Notes.md` carries the
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
  the `PICAMP_DEVICE` env indirection are gone: each harness now names `DEVICE = "PIC18F47Q10"`.
  **The per-harness instruction rates disagree, and the disagreement is UNRESOLVED (2026-09-24).**
  `trace_ptt_sequence.py` and `first_dit_invariants.py` use **1625**; `test_first_dit.py` uses
  **1887**. Neither is a typo or a guess: 1887 came from a probe recorded in commit `ff931f7`
  (*"the Q10's rate MEASURED at ~1887 steps per simulated millisecond"*), and 1625 is the figure the
  later macOS work settled on. **One of the two is wrong and neither has been re-measured against the
  ELF the tests load today.** Do not "unify" them by picking the tidier number - re-measure both
  against the current ELF (method in `docs/hardware/q10-bringup/README.md`) and set both. Note that
  correcting 1887 *down* to 1625 only **shortens** every window, so on its own it is not an
  explanation for the first-dit clause (c) failure - but the constant has to be right before that
  clause's verdict means anything. **A second, larger contradiction sits in the same area (found
  2026-09-24): `tools/simulate/probe_q10_ptt_path.py` sets `BOOT_STEPS = 16_500_000` for a 1000 ms
  gate, derived from "Q10 at 64 MHz = 16 MIPS, so 1000 ms needs ~16,000,000 steps" - while the direct
  probe of that same 1000 ms boundary put it at ~1.5-1.75M steps. The two differ by ~10x, and they can
  both be right only if `Stepi` counts something other than one instruction. Nothing was changed in
  either place: settle it with a single measurement, because if the harness rate is wrong by 10x then
  every assertion window in both harnesses is wrong by 10x.**
  **MEASURED 2026-09-24 on the current ELF, and it settles the argument: ~1695 `Stepi` steps per
  firmware millisecond.** Method: let the firmware run, bracket its own tick counter
  (`g_startup_elapsed_ms`, incremented once per Timer2 interrupt drained by the main loop) across
  fixed `Stepi` blocks - `docs/hardware/q10-bringup/tick_rate_probe.mdb`, run through
  `run_mdb_probe.py`. Readings: 381 -> 559 -> 734 -> 912 ticks over four 300,000-step blocks, so
  531 ticks per 900,000 steps = **1694.9 steps/ms** (each single block agrees within ~1%: 1685, 1714,
  1685). So **1625 is ~4% low, 1887 is ~11% high, and `BOOT_STEPS = 16_500_000` in
  `probe_q10_ptt_path.py` is ~10x too large (the 1000 ms boundary is at ~1.70M steps).** The startup
  window caps this counter at 1000 ticks, so it is the widest clean span available; the ±1% per-block
  spread is the simulator's own jitter, not measurement noise. **Do NOT set every harness to 1695 -
  tried 2026-09-24 and it broke the merged suite's SWR1 scenario ("did not clear and re-enter TX
  after a PTT re-arm").** The scenario sample windows are phase-tuned to the per-harness value they
  were built with, and one global rate is only an approximation of the boot/loop instruction mix, so
  the measured 1695 does not transfer across harnesses. The harnesses therefore keep their validated
  constants (1625 in `trace_ptt_sequence.py`/`first_dit_invariants.py`, 1887 in `test_first_dit.py`);
  1695 stands as the tighter *measurement*, not the value to run with. This is why the open
  first-dit clause (c) macOS failure must be read against the rate the harness actually uses, not the
  probe's. The 10m band (25000 kHz injects as 24985/25022 via TMR1 tick aliasing) is the one the old
  cadence used to fail on last; the constant-frequency `hold_band` design above now passes it.
  **Do not use `TMR2` to measure time in the simulator.** It reads back a value that advances only
  ~16 counts per 300,000 steps (177 firmware-ms), which no Fosc/8-and-1:64 model can produce; the
  interrupt arrives on schedule but the model's timer *count* is not the datasheet count. `T2CON`
  readback is trustworthy and confirms the configuration (`224` = `ON`, `CKPS = 6`, `OUTPS = 0`,
  since `CKPS` is bits 6:4 and `ON` is bit 7).
- **What the simulator's own clock says (2026-09-24, `clock_check_probe.mdb`): there is no single
  "sim MHz" for this model, and the core is NOT running at the configured 64 MHz.** `Stopwatch`
  reports a cycle count plus a time, and it converts **1000 cycles = 1 ms**, i.e. it treats one
  instruction cycle as 1 us - a ~1 MHz instruction-cycle clock, a **4 MHz-equivalent core**, not this
  one. Measured against that base: 300,000 `Stepi` steps advanced 354,269 cycles = 354.3 ms, so
  **~847 instructions per simulated millisecond** (0.85 MIPS; instructions average 1.18 cycles each),
  and the firmware's 1 ms Timer2 tick arrived every **1990 cycles = 2.0 simulated ms**.
- **DO NOT TRY TO "SET THE CHIP UP AT 64 MHz" BEFORE MEASURING - the model ignores the oscillator
  configuration entirely (verified 2026-09-24, after being challenged on exactly this).** After
  300,000 steps the registers read `OSCCON1 = 0`, `OSCFRQ = 0`, `OSCCON3 = 0`: the model does not
  apply `#pragma config RSTOSC = HFINTOSC_64MHZ`, and `main.c` never writes `OSCFRQ` because on
  silicon the config word already sets HFFRQ to 64 MHz. Forcing it - `write OSCFRQ 0x07`, read back
  `7` - changed nothing measurable: 354,174 and 354,267 cycles per 300,000 steps after the write,
  against 354,269 before, with tick counts of 175/178 per block throughout. The model's core and timer
  rates are fixed by the simulator, so the core behaves like a ~4 MHz-equivalent part while its Timer2
  is clocked as if Fosc were ~32 MHz - a ~8x disagreement *inside the model*, and an order of
  magnitude below the hardware's 64 MHz / 16 MIPS. **The only valid conversion is the measured one:
  1695 `Stepi` steps per firmware millisecond** - never datasheet arithmetic. This invalidates
  `BOOT_STEPS = 16_500_000` (derived from "16 MIPS at 64 MHz") and any harness that multiplies a
  firmware-ms window by a simulated-MHz figure. Cross-check with `Stopwatch`, and expect the
  firmware's ms to run 2x the model's ms.
- **Clock-only control (2026-09-24, `clock_only_probe.c`/`.mdb`): the 2x is the model's Timer2, not
  the firmware's work load, and no setup can fix it.** Strip everything - config words, the
  `timer0_init()` Timer2 setup, one ISR incrementing a counter, a bare `while (1) {}`, no LCD, no ADC,
  no NVM, no printing - and program the oscillator in code (`OSCCON1 = 0x60`, `OSCFRQ = 0x07`), since
  the model does not apply the `RSTOSC` config word. Result: **exactly 1000.0 `Stepi` steps per tick**
  in every 300,000-step block, 599,098 cycles per 300,000 steps (1.997 cycles/step), i.e. **1997 model
  cycles = 2.0 model-ms per tick** where silicon gives 1000 cycles = 1.000 ms - the same ~1990
  cycles/tick the full firmware showed. So the model ignores the clock configuration (config word and
  SFR writes alike), clocks Timer2 2x slow and the core ~8x slow against the real 64 MHz / 16 MIPS.
  **The authoritative fix (Microchip docs, 2026-09-24): the MPLAB X Simulator is a discrete-event
  model that ignores config bits and oscillator registers, and times everything from
  Project Properties > Simulator > Oscillator Options > Instruction Frequency (Fcyc).** Set Fcyc to
  64 MHz there and the Stopwatch and instruction timing run at 64 MHz regardless of the code.
  **Scripted `mdb.sh <file>` runs have no project, so that property cannot reach the harnesses** - a
  64 MHz simulation needs an MPLAB X project (or the VS Code `microchip.mplab-core-da` Simulate
  session) with Fcyc set there. The MDB `set` command does not expose it either (tried 2026-09-24):
  `set InstructionFrequency 64` and `... 64000000` are accepted without error but leave the tick
  counts and `Stopwatch` bit-identical (4/304 ticks, 9958/609056 cycles), and `print
  InstructionFrequency` / `print Simulator.InstructionFrequency` both answer `Symbol does not exist`,
  so the key is not settable in command-file mode. Until a project exists, keep every timing
  assertion in measured `Stepi`
  counts (1695 per firmware-ms), and when a measurement is wanted, use a peripheral-free image like
  `clock_only_probe.c` so the rate is not blended with LCD/ADC work. This firmware has no PLL-lock
  wait (HFINTOSC is directly 64 MHz), so the usual `#ifndef SIMULATION` skip is not required.
  **None of this invalidates the tests**: the firmware's time base is the Timer2 tick and every
  assertion is tick-relative, so the model's absolute speed only changes the step-count-per-firmware-ms
  (1695), which the harnesses already use - not the behaviour being asserted.
- **`_XTAL_FREQ` must match the real 64 MHz core (fixed 2026-09-24 - it had been 32 MHz).** XC8
  compiles `__delay_us()`/`__delay_ms()` from it, and the firmware uses them for the LCD init sequence
  (50/5/2/1 ms), the page-clear settle and `ADC_ACQUISITION_US`. It now reads `64000000UL` in
  `firmware/include/pin_map.h`, matching `RSTOSC = HFINTOSC_64MHZ`. Timer2's `T2CLK = Fosc/8` is
  separate and untouched. This changes only the firmware's compiled delay loops - it does NOT change
  the harness `Stepi` constants (1625/1887, measured 1695), which are independent of `_XTAL_FREQ` and
  remain unsettled until the operator picks one.
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
- **Search inside the MPLAB X install for a DFP before concluding a device is unbuildable.** MPLAB X
  6.35 ships `PIC18F-Q_DFP/1.30.487` under its own install root
  (`/Applications/microchip/mplabx/v6.35/packs/Microchip/`,
  `C:\Program Files\Microchip\MPLABX\v6.35\packs\Microchip\`), which is a **different root** from the
  user pack repository that the tooling also searches (`~/.mchp_packs` / `%USERPROFILE%\.mchp_packs`).
  A "no Q10 DFP is installed" conclusion drawn from the user repository alone was wrong and cost a
  session: the toolchain was never the blocker. Check both roots before reporting a part unbuildable.

**Finding (2026-09-23): the first macOS run of the whole tree - and how to read a verdict when the
agent's terminal launched the run.**

- The merged suite PASSES on macOS: `PTT suite passed: 11 scenarios in one MDB session`, ~110 s, all
  I1-I6 invariant lines PASS. first-dit FAILS: `AssertionError: clause (c): the warm-start PTT never
  keyed the amplifier`, with I1-I6 and clauses (a)/(b) passing first. See `bugfixes.md` 2026-09-23.
- **Update 2026-09-24 (later): the first-dit macOS blocker MOVED from clause (c) to I6, and it is
  still failing - do not report first-dit as OK on macOS.** Clauses (a)-(j) now pass (nothing is
  printed for them on success; the log goes straight from `Parsed 552 samples across 11 phases` to the
  invariant block), I1-I4 and I5 PASS, then:
  `AssertionError: first-dit I6: the T/R relay closed 4.6ms after the band relay selection changed
  (HOT SWITCH of the band relay ...)` with
  `t=1392.3ms PTT=0 TX/VCC/BIAS=011 bandpins=000100 stage=1 state=6 snoop=false locked=true
  cur_band=4 freq_khz=13926 settle=false settle_ms=20` - the band change itself was seen at t=1388ms
  (RD2 -> RD5, amplifier cold). **This is NOT caused by the FREQ_CTR work:** `test_first_dit.py` does
  its own stepping (`INSTRUCTIONS_PER_MS = 1887`) and only borrows `parse_trace`/`run_mdb` from
  `trace_ptt_sequence.py`.

**RESOLVED AND ROOT-CAUSED, 2026-09-24 (read this before touching any harness timing again): the
model's steps-per-firmware-millisecond is NOT a constant, and it is not even a property of the
firmware - it depends on HOW THE HARNESS STEPPED.** Same run, same tick counters (both are incremented
once per pending TMR2 tick in the same drain loop), measured from one first-dit transcript:

| window | how the harness stepped | measured steps per firmware-ms |
| --- | --- | --- |
| startup inhibit, 1000 ticks | `Stepi 18870` (10 ms steps) | ~2000 |
| 20-tick band settle | `write TMR1L/H` + `Stepi 1887` per sample | ~380-470 |
| released, cache valid | `Stepi 18870` | ~5000 |
| released, cache valid, right after a PTT assert | `Stepi 1887` | ~5000+ |

The last two rows are the give-away: the rate changes with the *sample cadence*, so the model is
charging time per MDB command as well as per instruction. Consequences, all of which cost runs here:

- A millisecond threshold compared against a sample-index gap measures the harness, not the firmware.
  I6, clause (b) and clause (i) each failed on the firmware holding its full `BAND_SETTLE_MS = 20`
  bypass window (settle counter plainly visible going 4 -> 10 -> 14 -> 20, T/R relay closing only
  afterwards) purely because 20 ticks came out as 4.0 ms of harness time against a 10 ms floor.
- `INSTRUCTIONS_PER_MS` (1625 / 1887) is an approximation of an average and cannot be made right.
  Fix applied: I6, clause (b) and clause (i) now witness the window through the FIRMWARE's own
  `g_band_settle_elapsed_ms` (`first_dit_invariants.settle_counts_reached()`), and the wall-clock gap
  is reported as evidence only. `first_dit_invariants.set_instruction_rate()` lets each harness
  declare the rate it steps at, so reported times are at least self-consistent.
- **A key-down that lands while the startup inhibit is still active is silently lost.** With
  `Stepi 18870` the inhibit (1000 ticks) did not clear until ~1070 ms of harness time, so the old
  105-step startup wait put the phase (a) key-down inside the inhibit; `handle_ptt_transition()`
  returns early on an asserted edge, no new edge follows, and every phase (a) sample read
  `ptt_active=false`. The startup phase is now 150 steps (1500 ms). Wait with real margin; never to
  the nominal figure.

**Harness trap: a STATE_VARS entry that is not `g_`-prefixed voids the whole run.** `parse_trace()`
recognises a printed variable with `VAR_NAME_RE = ^(g_[\w\.]+)=$`, so a register (e.g. `PORTC`) or
any non-`g_` symbol never sets `awaiting_var`, never lands in `state_pending`, and no sample is ever
emitted - the run dies as `error: no samples parsed from mdb output`, which names the harness rather
than the one line that was wrong (cost a run on 2026-09-24, adding `PORTC`/`TRISC` to read the PTT
pin). `parse_trace()` now refuses such a name up front with the offending entries listed. The
diagnostic you want for "what is the firmware reading on this pin" is a `g_`-named firmware global or
a value the harness already prints - not a register added to `STATE_VARS`.

**Still open (2026-09-24): clause (c) does not pass, and the reason is NOT a clock threshold now.**
Facts from the window dump:

- The old clause (c) engage check was **vacuous**: the previous over is still unwinding when PTT is
  re-asserted (the release ramp holds TX_BIAS up for its delay), so `next(keyed_sample)` picked the
  LEFTOVER ramp and reported "engaged 0.0ms after the falling edge". Clause (c) now counts the
  engage from the first fully COLD sample (fixed), and the phase gives the firmware RF to verify the
  remembered band against, because `docs/first-dit-band-detection.md` requires the amplifier to hold
  bypass until the first usable measurement confirms the memory - an ultra-short "engage with zero RF"
  phase can never reach stage 2 by design.
- With that fixed, the run fails with `clause (c): the warm-start PTT never keyed the amplifier`, and
  the window shows the firmware STOPPING: `ptt_active=false` at every sample after the re-assert even
  though `print pin RC0` reads 0, `idle_ms` frozen at 151, `freq_khz` frozen, `stage=0`. The last
  observed movement is `idle_ms` crossing 100 - i.e. the first LCD status refresh during a long
  released run - and the freeze begins ~8 ms of harness time later. Next step is a focused repro of
  that freeze (does the firmware hang in `show_menu_page()`/`lcd_service()` when the model has no LCD
  rising edge to give it?), NOT more clause tuning: the PTT poll and the tick drain are both inside
  the same main-loop pass, and a pass that never returns explains "no latch AND no ticks" at once.
- **Do not read the wrapper's exit line as the verdict when the run came from the agent's terminal.**
  When the terminal is cleaned up, the harness SIGTERMs the wrapper, so a run that COMPLETED still
  leaves `SUITE_EXIT=143` / `CTEST_EXIT=143` behind. The harness's own printed lines - the scenario
  list, the `PASS`/`FAIL` lines, the assertion - are authoritative, and 143 on its own says nothing
  about the test. (This cost two rounds of "the run was killed" before the transcript showed a
  complete 11-scenario pass above the 143.)
- first-dit prints `settle=? settle_ms=? verify=? verify_ms=?` on every sample on macOS, while the
  merged suite prints real numbers from the same ELF (`tightest 92.0ms`). The harness is blind to
  the settle/verify state - which is precisely the state that decides whether an engage is
  abandoned - so fix that before theorising about a clause (c) failure.
- A VS Code `shell` task whose command ends in `echo "EXIT=$?"` always exits 0, so a task that
  silently failed to start python looks exactly like success (empty log, exit 0). Keep the exit-code
  capture, but check the log has content before believing a task ran.

## Build output paths: the device suffix, and the stale-16F-path defect class (2026-09-24)

**CMake emits into a device-suffixed `out/` directory: `out/My_Pic_Project_18F47Q10/`.**
`tools/setup/parameterise_output_dir.py` derives that suffix from the device, so it is not a free
choice - hard-coding `out/My_Pic_Project/` anywhere names a directory the build no longer writes.
Six live scripts did exactly that and were fixed in one pass: `tools/simulate/build_firmware.{sh,ps1}`,
`tools/simulate/run_sim.{sh,ps1}` and `run_tests.sh` (the hex/ELF size echo). The damage was not
cosmetic: `build_firmware.*` *verified* a hex the build had not produced - passing silently on any
machine that still had the stale 2026-09-22 16F hex lying there - and `run_sim.*` handed **that 16F
hex** to MDB. After any device or output-directory change, grep for the old path *and* the old device
tokens before trusting a "verified" run.

**Same class, `.vscode/`:** the `Windows-XC8` editor profile was still the 16F one
(`PIC16F1xxxx_DFP` include path, `__16F18875__` defines), and `.vscode/launch.json` programmed the
debug session with `out/My_Pic_Project/default.elf` - the stale 16F image. Both now use the Q10 pack
and the suffixed path. Check `.vscode/` in any device sweep: it is not covered by the build, so
nothing fails when it is wrong. Also note the pack roots differ per platform - on this Mac
`~/.mchp_packs/Microchip` holds only `PIC16F1xxxx_DFP`, and the Q10 pack resolves from the MPLAB X
install at `/Applications/microchip/mplabx/v6.35/packs/Microchip/`, which is why both roots are listed
in each profile.

## The ADC clock is not set by `ADCON1` (2026-09-24)

Worth knowing before anyone derives a timing budget again. On the Q10's ADCC, **`ADCON1` has no
clock-select field**: it is `ADDSEN`/`ADGPOL`/`ADIPEN`/`ADPPOL`, so `ADCON1 = 0x20` in `adc_init()`
sets a guard-ring polarity bit. The divider is `ADCLKbits.ADCS` (6 bits, off Fosc), and **`adc_init()`
never writes `ADCLK`** - the ADC runs at that register's reset default. So no TAD can be computed from
the firmware as written; read `ADCLK`'s reset value from the datasheet and confirm it against the
module minimum. The `Fosc/32 => TAD = 1.0 us` figure that `docs/hardware/bench-validation.md` used to
carry was a PIC16F-era number dressed up as a derivation.

## Simulation method (moved here from `Ai-Notes.md` 2026-09-24)

**mdb command reference.** `write pin <name> high|low|<N>v` drives an input, `print pin <name>` reads
an output, `Stepi <count>` single-steps, `break <function>` / `break <file>:<line>` plus
`Run`/`Continue`/`Halt` gives real breakpoint debugging, and `Stopwatch [nror]` reports real simulated
elapsed time. Worked examples: `tools/simulate/scenarios/boot_smoke.mdb`, `ptt_cycle.mdb`.

**`run_sim.sh` / `run_sim.ps1 [scenario.mdb]`** build, then launch mdb with the hex programmed and the
benign TMR1/3/5 `W0106-SIM` warnings filtered out. With no argument it is an interactive mdb session;
with a scenario file it runs those commands and exits. It is a build-and-drive helper, **not** a
substitute for the watchdog: a scenario run still has no timeout, no heartbeat and no orphan clean-up.

**Fault injection into firmware state: parse the address, never invent it.** This mdb build cannot
write a C variable by name (`write g_x 1` fails with `For input string: "<addr> "`, and `print /a g_x`
fails the same way). Read the address from `out/My_Pic_Project_18F47Q10/default.sym` (line format
`_g_name <hexaddr> 0 BANKn <size>`, e.g. `_g_band_cache_idle_ms B4 0 BANK1 1`), then use
`write /r 0x<addr> <lo> <hi>` for a 16-bit value (little-endian, one byte per word) or
`write /r 0x<addr> <byte>` for a bool/enum. **Addresses move on every rebuild**, so parse the `.sym`
at run time - `test_first_dit.py` does.

**Stimulus recipe for a steady-state-then-PTT run.** Drive plausible idle ADC voltages first: without
explicit stimulus the floating analogue inputs read very low or very high, which spams `W0222/W0223-ADC`
(cosmetic) but can also make `swr_trip()` and friends behave unpredictably. `write pin RA0/RA1/RA2/RA3 0v`
(the two SWR pairs' forward/reflected), `RA5 2.5v` (temperature), `RB1/RB2/RB3 0v`
(current/overdrive/drain), `RB4 low` (hardware overcurrent fault, active-high). PTT is `RC0` and is
active-low: hold `high` for idle, then `low` to assert.

**`ANSELC` is cleared explicitly in `main.c`** so RC0 and RC3-RC7 are digital I/O. Keep that
initialisation when the port map changes; losing it turns those pins analogue again.

**Why the tick is Timer2 and not Timer0:** mdb's Timer0 model stalled during the original bring-up, so
the ~1 ms scheduler tick moved to Timer2.

**`gpsim` is not an option** for this part - its newest PIC16F1 support stops at the 1788/1823/1825/1847
family, which lacks this chip's ADCC/CLC peripherals.

**VS Code GUI debug session.** `.vscode/launch.json`'s "Simulate PicAmpControl (Debug)" drives
`microchip.mplab-core-da` against `Simulator`/`PIC18F47Q10` - breakpoints, variables, watch, registers,
no terminal. It needs `out/My_Pic_Project_18F47Q10/default.elf` to exist (build first). Watch
expressions cannot be pre-seeded from a file: add `PORTA`/`LATA`/`TRISA` (or `PORTCbits.RC5`) to the
Watch panel by hand. Breakpoints on functions/statics that mysteriously fail to resolve are usually a
lost `-O0`: check `user.cmake`, where `-Os` is gated behind `$<$<CONFIG:Release>:-Os>` for exactly this
reason.

## Timeout and platform policy (moved here from `Ai-Notes.md` 2026-09-24)

- **Budgets are sized for the slowest platform, and that is Windows.** MDB is ~2.4x slower there (suite
  356 s vs ~150 s; first-dit ~55 s vs ~20 s). `run_mdb(timeout=1500)` is the last-resort inner net,
  `run_suite_with_watchdog.py --timeout 1200` is the real suite budget, and the CTest registrations
  match (1500 for the suite, 900 for first-dit). **Never shrink them to macOS-sized numbers** - the old
  280 s inner timeout killed a perfectly healthy Windows run while it was still printing progress. And
  never read a timeout as a firmware regression: check the heartbeat log (`delta=0` with frozen
  `mdb_bytes` = hung; still increasing = slow but healthy).
- **All platform-specific harness code lives in `tools/simulate/platform_process.py`** (`temp_dir`,
  `find_mdb`, `isolated_spawn_kwargs`, `pid_is_alive`, `terminate_tree`/`kill_tree`,
  `running_processes`), and every harness imports it. Do not put `start_new_session` / `os.killpg` /
  `signal.SIGKILL` / `ps` / `/tmp` back into a harness: on Windows the first three raise
  `AttributeError` or are silently ignored, and `os.kill(pid, 0)` actually KILLS the process there.
- The suite is Python 3 only, and configure now **fails** if the discovered interpreter is not Python 3.
  `PYTHON_EXECUTABLE` is cached, so clear it with `-U PYTHON_EXECUTABLE` when reconfiguring an existing
  build directory.
- `tools/simulate/build_firmware.sh` (macOS) / `build_firmware.ps1` (Windows) build locally into
  `_build/My_Pic_Project/sim` and `out/My_Pic_Project/default.hex`.
- macOS setup: `brew install --cask mplabx-ide mplab-xc8`. Windows: install the full MPLAB X IDE (not
  just MPLAB IPE) so `mdb.bat` under `mplab_platform/bin` is present. The already-installed
  `microchip.mplab-core-da` and `microchip.mplab-data-visualizer` extensions drive the same mdb engine,
  so scripted simulation does not need them.

## Harness design rules (moved from `deepseek-pic.md` 2026-09-24)

- **Cover the boundaries, not just the happy path.** Every harness needs a register-overflow case (the
  16-bit `TMR1` count wrapping), a timeout that never arrives, and a missing sensor pulse. The last is
  `FREQ_CTR_FAIL`, which is deliberately a negative test and must never be "fixed" into a passing trip.
- **A harness must not block the device under test.** Wait with non-blocking timing - a deadline plus a
  poll, the way the watchdog does it - rather than sleeping inside the sample loop, or the harness's own
  latency becomes part of the timing being measured.
- **Drive the device, do not stub it.** Stimulus goes through the simulator's own interface (`write pin`,
  `write /r` into a `.sym`-resolved address) so the firmware under test is the shipping image, not a
  build with compiled-in test stubs. Anything that has to be reached by address must be parsed from the
  `.sym` at run time, because addresses move on every rebuild.

## Windows shell traps (moved here from `Ai-Notes.md` 2026-09-24)

These silently no-op a build, i.e. they return success while compiling nothing:

- **Nested `cmd /c` quoting.** Wrapping a command in `cmd /c "..."` where the inner command has its own
  quotes mangles the argument list; the command does nothing and still exits 0.
- **A mangled multi-line invocation returned exit 0 and compiled nothing.** Whenever a build seems to
  have succeeded, confirm the log has content and that the compile line for the file you changed is in
  it - an empty log plus exit 0 is not a build.
- **`2>&1` is unsafe in PowerShell.** With `$ErrorActionPreference = 'Stop'`, merging a native
  command's stderr turns its warnings into terminating `ErrorRecord`s and aborts the script. Use `*>` to
  redirect both streams to the log, then `Add-Content $log "EXIT=$LASTEXITCODE"`.
- **The interpreter is `python` on Windows** - there is no `python3` on the PATH. CMake's
  `find_program(PYTHON_EXECUTABLE NAMES python3 python)` and `run_tests.ps1` both resolve this, so it
  only matters when typing a command by hand.
- The cross-platform toolchain files auto-detect XC8 and the DFP per OS (macOS `$HOME/tools/microchip/`,
  Windows `C:/Program Files/Microchip/xc8/` plus `%USERPROFILE%/.mchp_packs`, since `$ENV{HOME}` is not
  set there), so no cache overrides are needed on a standard install.

## Flash space (policy moved here from `Ai-Notes.md` 2026-09-24)

**Measured on the Q10, Release, 2026-09-24: program 11214/131072 bytes used (8.6%), data 368/3359
bytes (11.0%). The flash pressure that drove this policy was a PIC16F18875 property (8192 words) and
does not exist on this part - the standing "flash reduction" work item is satisfied and only needs
re-opening if something runs that figure up by an order of magnitude.**

- `memoryfile.xml` (and `mem.map`) is regenerated by XC8 on every build and ships inside every
  release, so it always reflects the current firmware rather than a stale snapshot. To read the live
  figure, take it from the build directory, or `gh release download <tag> -p memoryfile.xml` and read
  `<memory name="program">`/`<memory name="data">` `used`/`free`/`length`.
- **Debug is the binding image, not Release.** `user.cmake` compiles Debug at `-O1` (not `-Os`) so mdb
  can resolve symbols and breakpoints. Budget against Release and expect Debug to be the larger of the
  two, but measure before believing any estimate.
- If space ever does bind: the cheapest room is in the `STRCODE` string literals (the LCD text), as it
  was when the 16F was full. Inline assembly is allowed when it genuinely wins, **and every block must
  carry an equivalent-C comment for review**.
- Do not trust estimates of a refactor's saving. Two recorded cases: table-driving
  `adjust_selected_setting()` was estimated at 80-100 words and is probably a loss once the ~6-byte rows
  and the lookup code are counted, and compiling the harness-invisible translation units at `-Os` was
  measured to reclaim exactly nothing, because XC8's linker optimises at the `-O1` in the link rule and
  normalises the per-file level. Measure the real sizes (the map's psects, or a build-delta experiment)
  before implementing anything "for space".
