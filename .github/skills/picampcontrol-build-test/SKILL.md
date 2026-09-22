---
name: picampcontrol-build-test
description: "Use when building, testing or debugging PicAmpControl firmware on macOS or Windows: Debug or Release builds, CMake configuration, ctest, run_tests.sh / run_tests.ps1, simulator/mdb runs, the VS Code Simulate debug session, breakpoints and symbol reads, PTT/frequency-counter tests, band-lock tests, first-dit band detection, remembered-band fold-back, band-change/hot-switch guards, or build/test failures."
---

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

**Hard rule: commit often, and never leave a finding uncommitted** (user instruction, 2026-09-22:
"update git often!"). Working-tree state is not a record. Commit each coherent change as it lands -
a fix, a test, a doc, a skill update - rather than accumulating a large diff, so that a finding
cannot be lost by a later rebuild or revert.

**Hard rule: follow logs in a VS Code tab, and treat FileTail as conditional.** Long jobs - suites,
builds, spike runs - write their output to a log file, and the user watches that file in a VS Code
**tab**. **Opening that tab is part of doing the job, not a courtesy done afterwards.** The user had
to say this three times on 2026-09-22 - "no log file shown in my code-insiders instance", then "I want
to see logs during long ops in VSCode, Insiders or not. Always." - while effort was spent improving
what the log *contained*. A progress file the user cannot see is the same as no log, so: before
starting any operation that runs longer than a few seconds, get its log open in their editor. The
suite launcher now does this for itself (`tools/simulate/open_progress_log.py`, `code-insiders` then
`code`, `-r` to reuse the running window, `PICAMP_NO_EDITOR_OPEN=1` to suppress); for anything else,
run that helper. **Never tail in a terminal/console**: forbidden explicitly and more than once, and also
silently broken, because `Get-Content -Wait` holds a handle to a file the launcher used to unlink and
recreate. FileTail (`spacetown.filetail`, command `filetail.toggle`) is the follow mechanism *only
while a job is actually running*: it measured ~110% of one core in the extension host plus ~24% in the
main process while following a log, and toggling it off dropped both to ~1% (2026-09-22, user
instruction: "if FileTail hogs CPU, it is badly written and should not be used"). Turn it off when the
run ends; if it shows that load again, stop using it and read the log on demand instead - a one-shot
`Get-Content -Tail 20` is a read, not a console tail. Truncate logs with `Clear-Content`, never delete
one a watcher has open. Watching a log for visibility is sanctioned; judging a run from terminal
output is not - verdicts come from the run's own log file plus its appended exit code.

**A progress line the user actually uses must carry `delta`: bytes of MDB output since the previous
tick** (user correction, 2026-09-22: "no output of bytes since previous tick"). `mdb_bytes` alone is a
running total and says nothing about the last five seconds; `delta=0` on a frozen total is the signal
that distinguishes "hung" from "slow but healthy", and an earlier revision dropped it while adding the
MDB text. Keep it on the heartbeat line, and keep the beat **stamped and written before** the MDB tail
is read - the beat must never be delayed by the work of describing the run.

**Hard rule: never delete or recreate a file a FileTail tab is already watching.** Deleting the log
between runs drops the watcher: the tab keeps rendering its old buffer and the file looks frozen even
though heartbeats are landing in it (user report: "the heartbeat is not ticking again",
2026-09-22 - the run was perfectly healthy). Truncate the file (`Clear-Content`) or reopen the tab and
re-toggle FileTail after any recreation. The delete/create step is only safe *before* the tab exists.

**Hard rule: resolve the VS Code CLI, never assume it.** The user runs Insiders in this workspace but
may be on stable - check for `code-insiders` first and fall back to `code`, in every command and
script, so the workflow works either way (sticky user instruction, 2026-09-22).

**Hard rule: Windows Defender real-time exclusions must be in place.** Without them Defender scans
every MDB/JVM object and every build output, and the machine spends its CPU on the scanner (user
report: "Defender is killing my pc"). `tools/setup/windows-defender-exclusions.ps1` installs them and
needs an **elevated** shell, so a non-elevated process cannot even read the list back. Launch it as:

```powershell
Start-Process powershell -Verb RunAs -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass',`
  '-File',"$PWD\tools\setup\windows-defender-exclusions.ps1",'-NoPause','-AutoCloseSeconds','20'
```

It verifies each entry, prints `ADDED`/`PRESENT`/`SKIPPED` per line with a `SUCCESS` or `FAILED`
verdict, exits 1 on failure, writes `%TEMP%\pac_defender_exclusions.log` always and
`%TEMP%\pac_defender_exclusions.ok` **only on success**, and with `-AutoCloseSeconds` closes its own
window so it does not sit open. On failure it dumps the whole report and waits for Enter instead -
that window is the one thing the user must be able to read.

## Watching a log: the three parts, and the two that were missing

Watching a long job needs **three** things, and doing two of them still leaves the user with a tab
that looks dead (this cost a whole session on 2026-09-22 - the log was written, opened, and still
"not working"):

1. **Write the log.** Redirect the job's output to a file. Done from the start.
2. **Fold the repeats.** MDB repeats warnings thousands of times: a 20 s temperature probe emitted
   `W0223-ADC: ADC input voltage low.  ADC output underflow.` **8,638 times**, i.e. 99% of the log
   was one line. The job still takes the same wall clock, but the user has to scroll past 8,000
   identical lines to reach the result, and the renderer pays for every one. `run_logged.py` now
   collapses a consecutive run of identical lines to `max_repeats` copies plus one
   `... (N more repeats of the line above)` marker. Measured: **8,707 lines -> 87**, with the
   key `g_*` reads and the exit code intact.
3. **Make the tab follow the tail.** Writing and folding a log the user has to scroll by hand is
   still a broken workflow. The follow is done by the **Log Follower extension**, whose source of
   truth is **`tools/logfollower/`** (command `Log Follower: Toggle auto-scroll for this file`).
   **It must live under `tools/`, not `_build/`.** It was originally only at
   `_build/logfollower/`, which `.gitignore` excludes - so every fix to it was uncommittable and
   lost, and the same following bugs came back session after session. `_build/logfollower/` is now
   only a build/staging copy. **Its automatic mode is driven by `logFollower.autoFollowGlobs`**,
   which matches on the file *name* only, so no path is needed. When it does not follow, check
   these in order - all were real on 2026-09-22 and the symptom of each is identical ("the tab
   never moves"):

   - **`main` in `package.json` must point at the polling file.** Two sources exist:
     `extension.js` (polls the file size) and `extension.eventdriven.js` (reacts only to
     `onDidChangeTextDocument`). **The event-driven one does not work for a log written by an
     external process** - VS Code does not reliably deliver appends to an unfocused document, so
     the extension never hears about them. `main` must be `./extension.js`.
   - **The extension must not hard-code the log names.** An earlier revision only auto-followed
     `/picampcontrol_(suite|mdb)_progress\.log$/` and ignored the setting entirely, so setting
     `autoFollowGlobs` did nothing and every other log silently never followed.
   - **`workbench.action.files.revert` is the WRONG primitive and froze the tab part-way down the
     file.** It acts on the **active** editor, not on the log's. With focus in the terminal - the
     normal case while a job runs - it reverted some other tab and left the log's stale in-memory
     buffer alone, so the poll kept firing while the visible text never changed. Measured: the tab
     sat on **line 15 of a 501-line file**. Use the per-document `TextDocument.revert()` instead;
     it does not care about focus.
   - Guard the visibility listener with the same self-move grace window as the selection listener,
     or the extension's own `revealRange()` is read back as "the user scrolled away" and the follow
     pauses itself.
   - **`TextEditorRevealType.Default` did NOT pin the view to the bottom and looked like lag.**
     `Default` only guarantees the revealed position is *visible*; on a long file the view settled
     part-way up with the newest line below the fold. Measured: the tab showed **line 136 of 201**
     with a current buffer. Use **`TextEditorRevealType.AtTop`** on the last line - because it *is*
     the last line, "at top" scrolls the document as far down as it will go, pinning the newest
     line to the bottom edge, which is what a tail looks like. This was the last of the bugs and
     the one that survived two earlier rounds of fixes, so change `Default` -> `AtTop` first if the
     symptom returns.
   - **Drive the refresh from a `FileSystemWatcher` per followed file, and keep the poll as a
     fallback.** Poll-only is up to one interval stale and a fast writer outruns it; a watcher alone
     was the original failing design (a producer that truncates/recreates invalidates it, and a
     file created after arming is invisible to it). Both together is the working combination.
   - A tab opened *after* output already exists must scroll to the end on first sight (adopt the
     current size and reveal), or it sits at the top until the next append.

   Current version: **0.6.0**; `logFollower.coalesceMs = 250` ms, watcher-driven with the poll as
   the safety net. **Verified working 2026-09-22**: a 200-line burst on an open log left the tab on
   the last line, growing it again kept following, and interacting with the tab then growing it
   again left the view exactly where the user had put it. Before these fixes the same test stopped
   at 136, and before that at 15.

   **Pause on interaction:** the follow must stop the moment the user touches the text or the
   scrollbar (user instruction). **Suppress our own scroll events with a COUNT, never a timestamp
   grace window.** A time-based window leaks: during a fast burst the extension scrolls, the
   resulting event then arrives after the window expires, and it is read as the user taking control
   - so the follow pauses itself part-way down the file, which looks like the follow being broken
   and is exactly why two "fixed" versions regressed at different line numbers. `scrollToEnd()`
   registers both events it is about to cause (`pendingSelfScroll`) *before* it makes them, and the
   handlers consume them. The timestamp remains only as a backstop for a coalesced trailing event.
   Two further traps, both of which paused the follow instantly and left the tab on line 1:
   - **`onDidChangeTextEditorVisibleRanges` fires when the document is OPENED**, before anything has
     been scrolled, so it must not be treated as interaction until at least one scroll has happened.
   - **Do not listen to `onDidChangeActiveTextEditor` at all.** It fires when a tab merely *becomes*
     active - including when this extension's own `code -r` opens it - so switching tabs must not be
     treated as taking control.

   **Resume is deliberate (the toggle command) and never automatic:** an earlier revision resumed as
   soon as the last line was merely visible, which re-armed the follow on a short log or a single
   wheel notch and yanked the view away from whatever the user had scrolled up to read.
   **After changing the extension, repackage and reinstall, then restart VS Code:**

```powershell
cd tools/logfollower
npx --yes @vscode/vsce package --no-dependencies --allow-missing-repository -o pac-log-follower.vsix
code-insiders --install-extension pac-log-follower.vsix --force   # or: code
# restart the editor - a running extension host keeps the old version loaded
```

   **A `url.parse()` DeprecationWarning printed during packaging comes from `vsce`'s own
   dependencies, not from this extension** - it is harmless and nothing here can fix it.

**Use `run_logged.py` for every long job - never hand-roll the spawn/heartbeat/fold logic.**
`tools/simulate/run_with_log.py` (any command) and `tools/simulate/run_mdb_probe.py` (one MDB
script) are thin CLIs over `run_logged.run_logged()`. Folding was added to one runner and missed in
the other, which is what produced "your folding thing clearly didn't work either"; one shared
implementation is the fix, and new runners must call it rather than copy it.

```powershell
# Build (any command), with folding + follow + heartbeat
python tools/simulate/run_with_log.py --log "$env:TEMP\pac_build.log" -- cmake --build _build/My_Pic_Project/q10_release -j4
# A single MDB probe
python tools/simulate/run_mdb_probe.py docs/hardware/q10-bringup/temp_verify.mdb
```

**Hard rule: at session start, run `python tools/simulate/cleanup_sim_processes.py`.** It kills
leftovers using the launcher's own pattern list, then checks Defender.The exclusion *list* is not readable without elevation - verified 2026-09-22: `Get-MpPreference`,
the `MSFT_MpPreference` CIM class, the `...\Windows Defender\Exclusions\Paths` registry key and even
`MpCmdRun.exe -CheckExclusion` all deny access unelevated. `Get-MpComputerStatus` *does* work, so the
check uses the only question that matters, all unelevated:

- real-time protection off -> exclusions are moot, nothing to do;
- on + a recorded successful install -> nothing to do;
- on + no record -> **raise the elevated installer itself** (rate limited to one request per 10 min,
  since each one is a UAC prompt; the installer closes its own window after a SUCCESS run).

Do not try to read the exclusion list unelevated and treat the placeholder string as "missing" -
that asks for a UAC prompt on every single run.

Use this skill for firmware builds, simulator verification and simulator debugging. Do not claim success from a missing or truncated terminal response; require a fresh exit code and final output.

Always use the **file-based pattern**: redirect every test command's output to a log file, append the exit code, and read the verdict from that file. MDB emits megabytes of trace, and the terminal scrollback and output capture regularly lose the pass/fail line (a command can even come back with no captured output while the run is still going). Never conclude anything from an empty terminal response - check the log and the exit-code line.

Always clean up an earlier run before starting another. The MDB suite can outlive a terminal wrapper if the wrapper is interrupted, and a stale Java/MDB process can make the next run appear hung.

## Repository facts

- CMake source directory: `cmake/My_Pic_Project/default`
- Debug build directory: `_build/My_Pic_Project/debug` (PIC16F18875, legacy)
- Release build directory: `_build/My_Pic_Project/release` (PIC16F18875, legacy)
- **Q10 build directories: `_build/My_Pic_Project/q10` (Debug) and `_build/My_Pic_Project/q10_release`
  (Release)**. Configure the device with `-DPICAMP_DEVICE=PIC18F47Q10`; VS Code tasks
  `Build PicAmpControl Q10 (Debug/Release)` do both steps.
- Firmware ELF used by MDB: `out/My_Pic_Project/default.elf`
- Merged simulator suite: `tools/simulate/trace_ptt_sequence.py --suite`
- Cleanup-aware suite launcher: `tools/simulate/run_suite_with_watchdog.py`
- First-dit band-detection proof (own MDB session): `tools/simulate/test_first_dit.py`
- Shared band-selection invariants: `tools/simulate/first_dit_invariants.py`
- CTest registration: `cmake/My_Pic_Project/default/user.cmake`
- CTest tests: `PTT_SequencerAndTripSuite` (labels `sim;suite`) and
  `FirstDit_BandDetectionAndHotSwitchGuards` (labels `sim;first-dit`)
- The standalone `test_freq_counter.py` is not the authoritative suite; frequency and band checks are merged into the PTT suite.
- Harness fault injection reads symbol addresses from `out/My_Pic_Project/default.sym` (regenerated every build).
- Design reference for the first-dit model, the invariants, and the defects each test is proven to catch: `docs/first-dit-band-detection.md`.
- Evidence log for defects found while testing: `bugfixes.md` (read it before "fixing" a suspicious harness assertion).
- **Q10 temperature-fault docs already exist — do not re-derive or search for them.** The
  AI-generated resolution analysis is `pic18f47q10_fault_resolution.md` (repo root); the
  hand-written pin-map + setup + fault reference is
  `docs/hardware/PIC18F47Q10_pin_map_and_setup.md`; the minimal temperature-only probe is
  `docs/hardware/q10-bringup/temp_probe.c` (built ELF + `temp_probe.mdb` script sit beside it).
  Both docs and the probe reach the same root cause: **the Q10 ADCC is 12-bit, `temperature_c()`
  assumes 10-bit, so 2.5 V reads 2048 and `2048 >> 2 = 512 > 250` trips the 150°C sentinel even
  after the `ADFM=1` justification fix.** MEASURED 2026-09-22 on the simulator
  (`docs/hardware/q10-bringup/temp_probe.c` + `run_mdb_probe.py`): 2.5 V on RA5 → `ADRES = 2048`
  (`ADRESH = 0x08`, `ADRESL = 0x00`), `ADCON0 = 0x84` (`ADON=1`, `ADFM=1`), `ADPCH = 5`. So the
  ADCC **is 12-bit and `ADFM=1` right-justifies correctly** (2048, not 32768) — but the 10-bit
  scaling in `temperature_c()` still trips. **The fix is to right-shift the raw result by 2 at
  capture (12-bit → 10-bit), not to keep fiddling with justification.** Run the probe with
  `python tools/simulate/run_mdb_probe.py docs/hardware/q10-bringup/temp_probe.mdb` (opens the log
  in VS Code and heartbeats it).
- VS Code debug config: `.vscode/launch.json` → `Simulate PicAmpControl (Debug)` (`mplab-core-da`, tool `Simulator`, device `PIC16F18875`, program `out/My_Pic_Project/default.elf`).
- Symbol table for breakpoints and harness state reads: `out/My_Pic_Project/default.sym`.
- **The workspace build tasks in `.vscode/tasks.json` are portable** - they use
  `${workspaceFolder}`, so `Build PicAmpControl (Debug/Release)` work on both OSes. (This file
  used to claim they hard-coded `E:/hamcode/...`; that was true of an older revision and is not
  any more - do not repeat it.)
- **`tools/simulate/platform_process.py` is the only place platform differences live.** Every
  harness imports it for temp paths, MDB discovery, spawning and process-tree teardown. If you
  need a platform branch, add it there rather than to a harness.
- **Temp paths are per-OS.** The progress logs and PID file sit in the OS temp directory:
  `/tmp/...` on macOS, `%TEMP%\...` on Windows. `platform_process.temp_dir()` resolves it; the
  concrete Windows path is typically `C:\Users\<user>\AppData\Local\Temp`.

## Platforms

Both macOS and Windows are supported, and everything below is written per-OS where it differs.
Read the matching half before running anything:

| | macOS | Windows |
|---|---|---|
| Shell | bash / zsh | PowerShell 7 (`pwsh`) |
| XC8 | `$HOME/tools/microchip/xc8/v4.00/xc8-v4.00/bin` | `C:/Program Files/Microchip/xc8/v4.00/bin` |
| DFP packs | `$HOME/.mchp_packs` | `%USERPROFILE%\.mchp_packs` |
| MDB launcher | `/Applications/microchip/mplabx/*/mplab_platform/bin/mdb.sh` | `C:\Program Files\Microchip\MPLABX\*\mplab_platform\bin\mdb.bat` |
| Python | `python3` | `python` (there is no `python3` on the PATH) |
| Helper scripts | `tools/simulate/*.sh`, `run_tests.sh` | `tools/simulate/*.ps1`, `run_tests.ps1` |

The XC8/DFP locations need no manual cache overrides on either OS:
`cmake/My_Pic_Project/default/.generated/toolchain.cmake` branches on `WIN32` and
`.generated/rule.cmake` falls back from `$ENV{HOME}` to `$ENV{USERPROFILE}` (CMake's spelling
for `%USERPROFILE%`) because `HOME` is not set by default on Windows. `XC8_BIN_DIR`
overrides are only needed for a non-standard unpack.

## Toolchain setup

On macOS, use the installed XC8 toolchain under `$HOME` (the MPLAB X installer also exposes it
at `/Applications/microchip/...`; either works):

```text
$HOME/tools/microchip/xc8/v4.00/xc8-v4.00/bin
```

On Windows it is `C:/Program Files/Microchip/xc8/v4.00/bin`, and `%USERPROFILE%\.mchp_packs` holds
the DFP packs (`$HOME/.mchp_packs` on macOS). Use `$HOME`/`%USERPROFILE%` rather than a literal
home directory: the committed docs and config must not carry a developer's account name, and the
paths differ per machine.

**Check MPLAB X's own pack directory before concluding a DFP is not installed.**
`%USERPROFILE%\.mchp_packs` is only the *user* pack repository. MPLAB X also ships a full pack set
inside its own install, e.g. `C:\Program Files\Microchip\MPLABX\v6.35\packs\Microchip\` (~130
DFPs, including `PIC18F-Q_DFP` 1.30.487, which contains `xc8/pic/include/proc/pic18f47q10.h`). One
of those paths works directly as `-mdfp=<pack>/<version>/xc8` with no download. A device can
therefore be fully buildable while the user pack repository shows only three packs - check both
roots before spending a cycle fetching anything. (2026-09-22: the PIC18F47Q10 was assumed
unbuildable for exactly this reason.)

A device's config-word names and values are authoritative in the DFP, not in memory:
`<pack>/<version>/xc8/pic/dat/cfgmap/<device>.cfgmap` lists every `#pragma config` setting and its
legal values, and `<pack>/<version>/xc8/pic/include/proc/<device>.h` lists every SFR and bitfield
member. Read both before writing device setup code - PIC18F-Q10, for example, wants
`MCLRE = EXTMCLR` where the PIC16F wants `MCLRE = ON`, and its Timer2 interrupt enable lives in
`PIE4bits.TMR2IE` with `T2PR` in place of `PR2`.

Verify the compiler exists before blaming a build; both halves of the checks below are copy-paste
ready.

```sh
# macOS
ls "$HOME/tools/microchip/xc8/v4.00/xc8-v4.00/bin/xc8-cc"
```

```powershell
# Windows
Test-Path 'C:\Program Files\Microchip\xc8\v4.00\bin\xc8-cc.exe'
```

`.clangd` **is** tracked and is deliberately machine-agnostic - do not add absolute include paths
back to it, and do not untrack it. It needs none: `CompilationDatabase` is relative to the config
file, the compile database CMake generates already carries that machine's compiler and `-mdfp` pack
path, and clangd then queries that compiler for its system includes ("System includes extractor:
successfully executed xc8-cc"), so the XC8 and DFP directories resolve automatically on either OS.
The firmware's own headers are included with relative paths (`../include/...`), so they need no `-I`
either. Verified on clangd 19.1.7: with no `-I`/`-mdfp` lines, `--check firmware/src/main.c` reports
0 errors. (An earlier revision of this file hard-coded one machine's home directory, which both
published a developer's account name and broke the other platform - see `bugfixes.md` 2026-09-21.)

Before building, confirm `xc8-cc` exists (the checks above do it). Existing build caches may contain
the invalid compiler value `c`; explicitly override the compiler paths when reconfiguring. The
repository root has no `CMakeLists.txt`, so do not configure with `cmake --preset` from the root
unless the preset is first corrected to specify the nested source directory.

## Debug build

```sh
cmake -S cmake/My_Pic_Project/default \
  -B _build/My_Pic_Project/debug \
  -G Ninja \
  -DCMAKE_BUILD_TYPE=Debug \
  -DCMAKE_TOOLCHAIN_FILE="$PWD/cmake/My_Pic_Project/default/.generated/toolchain.cmake" \
  -DCMAKE_USER_MAKE_RULES_OVERRIDE="$PWD/cmake/My_Pic_Project/default/.generated/overrides.cmake" \
  -DXC8_BIN_DIR="$HOME/tools/microchip/xc8/v4.00/xc8-v4.00/bin" \
  -DCMAKE_C_COMPILER="$HOME/tools/microchip/xc8/v4.00/xc8-v4.00/bin/xc8-cc" \
  -DCMAKE_ASM_COMPILER="$HOME/tools/microchip/xc8/v4.00/xc8-v4.00/bin/xc8-cc" \
  -DCMAKE_AR="$HOME/tools/microchip/xc8/v4.00/xc8-v4.00/bin/xc8-ar" \
  -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
cmake --build _build/My_Pic_Project/debug -j4
```

On Windows the same configure runs unchanged - the auto-detection resolves XC8 and the DFP packs,
so no `XC8_BIN_DIR`/compiler overrides are needed. The only differences are PowerShell syntax and
`$PWD` becoming `(Get-Location).Path`:

```powershell
$root = (Get-Location).Path
cmake -S cmake/My_Pic_Project/default `
  -B _build/My_Pic_Project/debug `
  -G Ninja `
  -DCMAKE_BUILD_TYPE=Debug `
  "-DCMAKE_TOOLCHAIN_FILE=$root/cmake/My_Pic_Project/default/.generated/toolchain.cmake" `
  "-DCMAKE_USER_MAKE_RULES_OVERRIDE=$root/cmake/My_Pic_Project/default/.generated/overrides.cmake" `
  -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
cmake --build _build/My_Pic_Project/debug -j4
```

Verified 2026-09-22 on Windows 10 + Python 3.14.7 + MPLAB X 6.35: configure and build are both
clean, and the Debug image links to the same `8117/8192 words (99.1%)` / `365/4096 bytes (35.6%)`
as the macOS build, so the Windows and macOS toolchains agree on code size.

Two Windows-only messages that appear during configure and mean nothing is wrong:

- `Windows is not configured with LongPathsEnabled` (printed twice) - only relevant to very deep
  build trees; this repo's paths are short enough.
- `Warning: Did not find file Compiler/-ASM` - emitted by the MPLAB-generated `overrides.cmake`,
  which never had one. The build links fine.
- `The C compiler identification is unknown` is expected, not a failure: the toolchain file
  pre-asserts `CMAKE_C_COMPILER_WORKS` because a cross-compiler cannot be executed at configure
  time on either OS.



Use the same configure command with:

```text
-B _build/My_Pic_Project/release -DCMAKE_BUILD_TYPE=Release
```

Then run:

```sh
cmake --build _build/My_Pic_Project/release -j4
```

**Both configurations link to the same `out/My_Pic_Project/default.elf`.** A Release build
replaces the ELF that MDB loads, and its stripped/optimized symbols break the `print <var>`
reads the harnesses depend on. After any Release build, delete that ELF and rebuild Debug before
running the simulator tests - Ninja will otherwise report "no work to do" and leave the Release
binary in place:

```sh
rm -f out/My_Pic_Project/default.elf
cmake --build _build/My_Pic_Project/debug -j4
```

## Flash space

**Reducing flash is a standing work item, not a nuisance to tolerate (user instruction,
2026-09-21).** A near-full Debug image is not an acceptable steady state. Concretely:

- When a build or test run leaves you waiting, spend that time finding space - do not idle.
- **Inline assembly is acceptable here, on one condition:** every block must carry an equivalent-C
  comment so it can be reviewed and re-derived. An uncommented asm block is not acceptable.
- Every saving is a code change like any other: it must keep the tests green, and ideally be proven
  by a fault injection. Space is never "free" just because the tests happen to pass.
- The purpose of the headroom is to be able to assert **strongly, and with test evidence, that the
  PTT sequencing cannot damage the amplifier** - the silicon in this project is expensive and the
  safety argument has to be airtight. No gaps, no excuses.

# WHICH CONFIGURATION TO TEST IN - THE RULE (standing user instruction, 2026-09-22):
# **"Run suite as fast as possible, with full optimisations. Only ever run suite in debug mode if
# there are known issues."**

On the PIC18F47Q10 branch (`upgrade/pic18f47q10`) that rule is now directly satisfiable, and the
old advice to test in Debug is obsolete **on this branch**:

| | PIC18F47Q10 Release | PIC18F47Q10 Debug | PIC16F18875 Debug (legacy) |
|---|---|---|---|
| Optimisation | `-Os`, full | `-O1` | `-O1` |
| Program space | 11,136 B = 8.5% | 12,732 B = 9.7% | 8,159 words = **99.6%** |
| Symbols for MDB | **complete** | complete | complete |

**Q10 Release is fully optimised AND symbol-complete, so that is what the suite runs.** Verified
2026-09-22 by reading every global the harnesses depend on out of the *Release* `default.sym`:
`g_state`, `g_fc_status`, `g_ptt_active`, `g_sequence_stage`, `g_band_cache_idle_ms`,
`g_band_cache_band`, `g_fault_latched`, `g_snoop_active` - all present with addresses. `-gdwarf-3`
plus a fresh `.sym` is what preserves them; the `-O1` in the Debug rule was never about symbols
per se, it was about the 16F's flash budget, and that constraint does not exist here.

Consequences to hold to:
- **Default the suite to the Q10 Release build.** Use Debug only to chase a specific problem, then
  go back to Release. Do not run both "to be safe" - the suite is minutes long and the point of the
  rule is speed.
- **Do not add `-O1` for Q10 "to be safe".** It would slow every run down for a 16F constraint that
  does not apply, and it is exactly the advice this section used to give.
- The `lcd_parallel.c` `-Os`-in-Debug override still exists and is still harmless; it is a 16F
  concern now.

## PIC16F18875 flash budget (LEGACY - do not apply to the Q10 branch)

The user has said "forget the 16F now" for this work (2026-09-22); the Q10 branch is Q10-only. This
is retained so nobody re-derives it, and because the numbers document *why* the 16F was replaced.

- Debug is the binding configuration at **8,159/8,192 words = 99.6%** (2026-09-22, after the
  frequency-counter atomic-read fix cost 36 words). Earlier snapshots: 8,123 (99.2%), 8,117 (99.1%).
  Always read the current figure from `memoryfile.xml`; `Ai-Notes.txt` tracks the same numbers.
- Release is ~84% used. Debug is closer to the limit than the shipped build **only because of the
  `-O1`**, so budget against the Debug number if the change must build on 16F.
- A link error reporting exhausted program space reads `(1347) can't find 0xN words ... for psect
  "<name>" in class "<class>"`. Read the exact figure from `memoryfile.xml` rather than guessing at
  the wording.
- `-O1` must stay in the 16F Debug rule: dropping to `-Os` there is what breaks MDB symbol
  resolution *on the 16F*, where space forces the compromise in the first place.

Known reduction levers if 16F work ever resumes, in rough order of value:

1. Table-drive the long `if`/`else` chain in `adjust_selected_setting()` (est. 80-100 words). The
   per-setting min/max/step bounds are irregular, so it needs a new menu-edit scenario in the suite.
2. ~~Compile `lcd_parallel.c` at `-Os` in the Debug build.~~ **MEASURED 2026-09-22: this reclaims
   NOTHING - do not retry it.** The override does apply (`set_source_files_properties(... lcd_parallel.c
   PROPERTIES COMPILE_OPTIONS "$<$<CONFIG:Debug>:-Os>")` gives `-O0 -O1 -Os` on the command line,
   last wins) and the file was forced to recompile by deleting its object, yet the linked Debug image
   was **8117/8192 words before and after - identical**. XC8's linker runs its own optimisation pass at
   the `-O1` in the link rule, which appears to normalise the per-TU level, so per-file `-O`
   overrides are the wrong layer. It also costs MDB symbol resolution *inside* that file.
3. Bit-pack the menu metadata (`g_menu_setting_offsets[]` 20 B + `g_menu_setting_types[]` 20 B).
4. Shorten the remaining display strings. The cheapest room is in string literals (`STRCODE`), which
   the linker fails to place first; on 2026-09-21 the LCD menu labels and boot text were shortened to
   reclaim ~72 words. It is a user-visible change - ask.
5. Only if the user explicitly agrees: build the whole Debug image `-Os`.

Prefer table-driven logic over long if/else chains when adding firmware code, and ask before adding
code to the 16F.

## Suite timeout, and the release-ordering assertion (Q10, 2026-09-22)

**Suite timing on Q10:** `PTT_SequencerAndTripSuite` took **263.8 s** (4 min 24 s) on Windows.
**Size the watchdog timeout at ~1.5x the last measured run** (user instruction) - so `--timeout 400`
for the next run, not the 1200 s default, so a genuine hang is reported in minutes rather than
twenty. Re-measure and re-size whenever the suite grows.

**`AssertionError: release did not raise RELAYS first` was a TEST bug, not a firmware bug.** The
assertion demanded the first stage-4 sample read exactly `(RC5,RC6,RC7) = (1,0,0)` - i.e. that the
5 ms sampler happened to catch the transient window with RELAYS up alone. On Q10 it missed that
window, so the assertion fired while the firmware was demonstrably correct: `ptt_trace.csv` shows
RELAYS rising at 1.897 s, TX_VCC at 1.912 s, TX_BIAS at 1.927 s. A phase-dependent snapshot test
that fails on a correct waveform is a broken test. It now asserts **monotonic ordering** over the
whole release - TX_VCC never high while RELAYS is low, and TX_BIAS never high unless both others are
- which is the property that actually matters and cannot be aliased by sampling. **General rule: when
a sequencing assertion fails, read the CSV trace before touching firmware** - if the trace shows the
correct order, fix the assertion, not the firmware.

**Look for `ptt_trace.csv` in `_build/My_Pic_Project/sim/csv/`** - it carries `time_s`, every
digital pin, every ADC pin voltage, `g_ptt_active`, `g_sequence_stage`, `g_state` and
`block_reason`, and it is the fastest way to answer "what did the pins actually do".

## Instruction rate per device, and "draw the graphs before the end"

**`INSTRUCTIONS_PER_MS` in `tools/simulate/trace_ptt_sequence.py` is a MEASURED per-device
constant, not a datasheet figure.** Getting it wrong does not just mistime assertions - it decides
how much firmware time each `Stepi` advances, which decides whether a short sequence stage is
observable at all. Measured 2026-09-22 by bracketing the 1000 ms startup inhibit against `Stepi`:
PIC16F18875 = 8000 instr/ms (historical), PIC18F47Q10 = ~1625 instr/ms. While the Q10 still used
8000, every step advanced ~5x too much firmware time: the 20 ms sequence stages 1/2/4 were shorter
than one sample so they were NEVER observed (`release did not enter stage 4`), and the suite
executed ~5x more instructions than needed (263.8 s -> 140.8 s once fixed). **A new device must
have this measured, never assumed** - the model does not track the configured oscillator. `stepi(ms)`
is the one helper to build scripts from; do not write literal `Stepi` counts.

**When a trip-recovery assertion fires (`did not clear and re-enter TX after a PTT re-arm`), read
the `recovery_trace` it prints.** The tuple is `(g_ptt_active, g_fault_latched, g_trip_reason,
g_sequence_stage, freq_khz, current_band, band_locked, (RC5,RC6,RC7), (RA0,RA1))`. On the Q10 run it
showed the firmware recovering correctly - trip cleared, stage 1, RC5 already low - and only the
harness's re-arm window (50 x 1 ms) was too short to reach stage 3. The re-arm is now 120 x 1 ms.
If the trace shows recovery in progress, extend the window; if it shows the fault never clearing,
that is a firmware bug.

**Draw/save the graphs and CSVs incrementally, before the suite finishes** (user request on the Q10
session). A failure mid-suite should leave the per-scenario trace and graph that explain it, rather
than requiring a full re-run to see anything. The transcript dump is already written first
(`suite_raw_mdb.log`); graph/CSV writes must also happen as each scenario is validated, not at the
end.

## Simulator verification
Run the full merged suite with the cleanup-aware launcher. This is the default test workflow: it records its PID, kills a stale prior launcher, owns the MDB process group, logs raw MDB stderr, records 10-second progress heartbeats, and cleans up on timeout or Ctrl-C:

```sh
python3 tools/simulate/run_suite_with_watchdog.py --timeout 180
```

Use the full default verification before calling the suite green - the 1200 s budget the CTest
registration uses, which is what "green" means for this suite:

```sh
python3 tools/simulate/run_suite_with_watchdog.py --timeout 1200
```

For a fast diagnostic run only, use one happy band plus the deliberate missing-frequency failure case:

```sh
python3 tools/simulate/run_suite_with_watchdog.py --quick-bands --timeout 180
```

This is diagnostic only. The default command remains the full six-band suite.

`python3` in these commands is macOS; on Windows it is `python` (there is no `python3` on the
PATH). The launcher takes the same arguments either way - `run_tests.ps1` discovers the Windows
interpreter for you.

Start this command in a fresh VS Code terminal/execution context. The launcher creates a new process group for the suite, so the caller can be interrupted without attaching the next run to an old MDB process. Do not reuse a terminal that still has a prior suite command queued.

Progress is written to `picampcontrol_suite_progress.log` in the OS temp directory
(`/tmp` on macOS, `%TEMP%` on Windows); live MDB output is written to
`picampcontrol_mdb_progress.log` beside it.

The launcher owns `picampcontrol_suite.pid` (same temp directory) and also scans for orphaned
`mdb`, `run_suite_with_watchdog.py`, and `trace_ptt_sequence.py --suite` processes at startup.
Before manually killing a run, read that PID and terminate its whole tree, then remove the PID
file. Verify no `trace_ptt_sequence.py --suite` or `mdb` process remains before starting another
run. Do not kill unrelated compiler language servers or system Java processes - on Windows that
means MPLAB X IDE's own `java.exe` and the Java updater, which is why the orphan pattern matches
`mdb.bat`/`mdb.jar` rather than `mplab_platform` (see the Windows gotchas below).

The live MDB log is intentionally separate from the suite result log. MDB produces a large amount of trace output because every simulator sample prints pins and state variables. During a long run, inspect both logs:

```sh
tail -n 20 /tmp/picampcontrol_suite_progress.log
tail -n 20 /tmp/picampcontrol_mdb_progress.log
```

```powershell
Get-Content "$env:TEMP\picampcontrol_suite_progress.log" -Tail 20
Get-Content "$env:TEMP\picampcontrol_mdb_progress.log" -Tail 20
```

The diagnostic runner should record periodic heartbeats containing:

- elapsed time and child exit status
- suite-log byte count
- MDB-log byte count
- the latest MDB output tail

If MDB-log bytes continue increasing, the simulator is working slowly rather than hung. In a recent full run, MDB output grew from about 47 bytes at startup to more than 3 MB while still progressing. The volume is expected to increase as all six bands and repeated TX scenarios are added, but it can make the run take substantially longer than the original two-minute test.

`trace_ptt_sequence.py` normally buffers MDB output until the process exits. Set `PICAMP_MDB_DEBUG_LOG` to enable its live stream drain for diagnosis; do not enable it for ordinary runs unless progress investigation is needed.

The suite must cover:

- all six nominal bands in RX preflight
- TX lock behavior for every band
- normal PTT/trip scenarios
- `FREQ_CTR_FAIL`, where no Timer1 signal must hold PTT latched in bypass-snoop with every TX
  output inactive and no band locked (first-dit model, not a refusal)
- the band-selection safety invariants over every scenario (`validate_keyed_band_invariants`,
  `validate_band_changes_are_cold` and `validate_t_r_closes_only_after_band_settle` in
  `tools/simulate/first_dit_invariants.py`): I1 no relay move
  between consecutive keyed samples, I2 never keyed while the band is unlocked, I3 never keyed
  while snooping, I4 the band-select output pins agree with `current_band`, I5 every relay move
  seen with the amplifier cold, I6 every T/R relay close follows a band relay selection that has
  already settled (never hot-switch the band relay)

`test_first_dit.py` additionally covers the first-dit clauses end to end in its own MDB session:
clause (a) bypass with no band, (b) first-burst decode with bypass held for `BAND_SETTLE_MS`,
(c) instant warm re-key with no RF injected, (d) cache expiry, (e) band re-detection, (f) a
hot-switch fault injection, and (g) the remembered-band fold-back - engage on a remembered 160m,
change to 80m, and assert the firmware forces bypass before releasing the band so the relay can
follow the new frequency. Both harnesses share `first_dit_invariants.py`, and the defects that
test is proven to catch are listed in `docs/first-dit-band-detection.md`.

For a bounded run:

```sh
timeout 150 python3 -u tools/simulate/trace_ptt_sequence.py --suite
```

(`timeout` is macOS/Linux only and is not needed on Windows - the watchdog launcher enforces its
own `--timeout`, which is the portable form and the one to prefer.)

Do not launch another suite while this launcher is running. If an old run exists, starting the launcher cleans it up through the PID file in the temp directory. A terminal response with exit `130`, `142`, no output, or an empty log is not a pass; inspect the saved logs and process state.

### Injecting stimuli and faults into the harness

Two techniques matter when writing or repairing a scenario, both already implemented in
`test_first_dit.py`:

- **RF is injected by writing the counter, not by driving the pin.** Set `TMR1H`/`TMR1L` to
  `counts = frequency_khz * 1000 / 400`. Because the firmware resets Timer1 on every 10 ms tick,
  an injection made once before a long step reads as an empty gate window afterwards, and the
  classifier reports its no-signal default of 160m. Re-inject before each short chunk inside a
  long step (`inject_step_hold()`), sample at 5 ms rather than on 10 ms boundaries, and keep the
  band frequency present for the whole keyed window when modelling a transmitting radio.
- **Firmware state is injected by address, not by name.** MDB in this version cannot write a C
  variable by symbol - `write g_x 1` fails with `For input string: "<addr> "`, and so does
  `print /a g_x`. Read the address from `out/My_Pic_Project/default.sym` (lines look like
  `_g_band_cache_idle_ms B4 0 BANK1 1`) and use `write /r 0x<addr> <lo> <hi>` for a 16-bit value
  (little-endian, one byte per word) or a single byte for a bool/enum. Addresses move on every
  rebuild, so parse the `.sym` at run time.

## CTest

The registered `PTT_SequencerAndTripSuite` test runs the merged suite through
`run_suite_with_watchdog.py`, so it owns the MDB process group, cleans up stale runs, and
enforces its own timeout without depending on the non-standard macOS `timeout` binary or on any
Windows equivalent.
The suite is Python 3 only: configuration fails fast if the discovered interpreter is not
Python 3, and `PYTHON_EXECUTABLE` may be stale in an existing cache, so clear it with
`-U PYTHON_EXECUTABLE` when reconfiguring. `NAMES python3 python` resolves to `python` on
Windows, which is correct there - `python3` simply does not exist on the PATH.

Run CTest with **all output redirected to a log file**. The MDB trace is megabytes of pin
and state dump; printing it to the terminal overflows the scrollback and loses the result.

```sh
ctest --test-dir _build/My_Pic_Project/debug --output-on-failure > /tmp/pac_ctest.log 2>&1
echo "CTEST_EXIT=$?" >> /tmp/pac_ctest.log
```

```powershell
$log = "$env:TEMP\pac_ctest.log"
ctest --test-dir _build/My_Pic_Project/debug --output-on-failure *> $log
Add-Content $log "CTEST_EXIT=$LASTEXITCODE"
```

In PowerShell use `*>` (all streams), not `2>&1`: the native-command merge turns stderr lines
into terminating `ErrorRecord`s when `$ErrorActionPreference = 'Stop'`, which aborts the run.
`run_tests.ps1` does this for you.

**A ctest log is NOT a progress indicator - do not watch it and conclude the run has hung.** With
`--output-on-failure` ctest prints nothing for a test that is still running and discards a passing
test's output entirely, so that file can sit at its first four lines (`Internal ctest changing into
directory`, `Test project`, `Start 1: ...`) for the whole run - ~400 s for the suite on Windows -
and then jump straight to `Passed` and `100% tests passed`. That is by design, not a stall. For
intermediate progress read the watchdog's heartbeat log instead, which the launcher updates every
10 s whether ctest says anything or not:

```powershell
Get-Content "$env:TEMP\picampcontrol_suite_progress.log" -Tail 12
```

It carries `HEARTBEAT elapsed=… timeout=… mdb_bytes=… delta=…` lines, the per-scenario invariant
results as they pass, and a final `END code=…`. `delta=0` with `mdb_bytes` frozen means genuinely
hung; growing `mdb_bytes` means slow but healthy. If you want the ctest log itself to move, use
`ctest -V` (streams test output live) rather than `--output-on-failure`.

**The heartbeat log goes quiet during the second test - that is expected, not a hang.** It is written
by `run_suite_with_watchdog.py`, which wraps only `PTT_SequencerAndTripSuite`. When that test passes
and `FirstDit_BandDetectionAndHotSwitchGuards` starts, nothing appends to the heartbeat log for its
~80 s, so a watcher sees `delta=0` and frozen bytes *while the run is perfectly healthy* (2026-09-22:
this was read as "the file is not updating" twice). Test-level progress, and the freeze that means
test 1 finished, is in the ctest job log instead: it prints `1/2 ... Passed` then `Start 2: ...`. So
the two logs answer different questions - heartbeat = progress *inside* the suite, ctest log = which
test is running - and neither one alone shows the whole run.

**HARD RULE - THE LOG MUST BE OPEN IN VS CODE, EVERY TIME, FOR EVERY LONG OPERATION.** Standing
user instruction, stated three times on 2026-09-22 ("no log file shown in my code-insiders instance",
"I want to see logs during long ops in VSCode, Insiders or not. Always."). A progress file the user
cannot see is the same as no log at all, and "I wrote a useful log" is not compliance. Before
starting any job that takes more than a few seconds - suite, build, spike run, MDB session - the log
must be open in the user's editor, in a tab they can watch. This is not a nicety that can be traded
against other work: fixing the log's *contents* while leaving it invisible is exactly the failure
that drew the complaint.

Mechanically: `run_suite_with_watchdog.py` now opens its own progress log in the editor as it starts
(`tools/simulate/open_progress_log.py`, `code-insiders` first then `code`, reusing the running window
with `-r`, best-effort so a headless host cannot fail the test). Set `PICAMP_NO_EDITOR_OPEN=1` to
suppress it. For a job the launcher does not wrap, open the log yourself with the snippets below -
and if neither CLI exists, say so explicitly rather than continuing silently, because that silence
is what made the missing log look like a non-event.

**Hard rule: the LAUNCHER clears the log for a new run - nobody clears it by hand.** A new run owns
its log from line 1. `run_suite_with_watchdog.py` truncates the progress log (and removes any stale
`.lock`) as its first act, before it writes `TEST_BEGIN`, so a watcher never sees the previous run's
lines mixed with the current one's. This was got wrong twice on 2026-09-22 - the user said "you did not
delete the file before starting! I still see all the last log's run as well as this one", and before
that had to ask for a restart because a hand-cleared file was the only thing standing between them
and a readable log. Rules that follow from it:

- **Truncate, never delete.** The file has to keep its path so the editor tab watching it stays
  valid; deleting it kills the watcher. `Clear-Content` / open-in-`"w"`-and-close, not `Remove-Item`.
- **Do not clear logs by hand before a run.** If a log still shows old content after a launcher
  started, that is a harness bug to fix, not a step to add to a checklist - a manual step is one the
  next session will forget, and the user should never have to ask for it.
- **One file per *run*, one `TEST_BEGIN`/`TEST_END` pair per *test*.** A ctest run of two tests still
  tells you which test is running; it is runs, not tests, that start a fresh file.
- For a job the launcher does not wrap, the same rule applies: clear it yourself as part of starting
  the job, then open it. Never open a log you have not cleared.

**Hard rule: never put run output in a terminal - file output only.** Standing user instruction,
2026-09-22: "stop putting stuff in terminals, if you please. File output only." Command output is not
evidence and is not for the user to read; it costs CPU to render, it scrolls away, and the user has
twice had to point out that they cannot see it. So: redirect long commands to a file, read the file
with `-Tail`/`Select-String`, and report one line plus the path. A verdict comes from the run's own log
file plus its appended exit code - never from terminal text.

**Open the log in the VS Code UI for any long-running job - on Windows too** (standing user
instruction, 2026-09-22, generalised and then restated for tail mode the same day). The user wants to
watch long jobs - suites, builds, spike runs - live in the UI, so truncate the log, start the job, and
have the file open in a tab. Follow it with FileTail while the job runs, subject to the conditional
rule above.

```powershell
# Windows: open in a TAB and let FileTail follow it (never a console tail - see the hard rule above)
# Resolve the CLI rather than assuming Insiders (hard rule at the top):
#   tools/simulate/open_progress_log.py does exactly this, and handles the .cmd path that
#   `Get-Command` may not resolve in a non-interactive shell (it fell back to %LOCALAPPDATA%).
python tools/simulate/open_progress_log.py "$env:TEMP\picampcontrol_suite_progress.log" "$env:TEMP\picampcontrol_mdb_progress.log"
```

```sh
# macOS / Linux
code -r /tmp/picampcontrol_suite_progress.log   # then `filetail.toggle`
```

Recreate the log *before* opening it: writing to a log that is already open in an editor tab makes VS
Code raise its own "file changed on disk" prompt.

**Why not a console tail (learned the hard way, 2026-09-22).** `Get-Content -Wait` holds a handle to
the file it opened. The suite launcher *unlinks and recreates* its log at startup, so a console tail
started before the run keeps reading the deleted file and goes permanently silent - the user sees an
empty pane and reasonably concludes nothing is happening. That is the second reason this is a tab
with FileTail rather than a terminal follow. (The first is that the user asked for it.)

**The progress log names the running test and always keeps moving (2026-09-22).** The launcher
appends, one file for the whole ctest run, and brackets each test with
`TEST_BEGIN name=<test> ...` / `TEST_END name=<test> code=<n>`, so a reader can tell which test is
running and that it moved on ("as it moves on to another test, this should also be in the file").
Both tests therefore go through `run_suite_with_watchdog.py` (`--test suite|first-dit`), including the
first-dit proof that used to be invoked directly.

**The heartbeat is its own process, on purpose.** It is a second copy of the launcher run with
`--heartbeat`, writing a line every 5 s for the whole test. A thread shares the launcher's fate, so
anything that blocks the launcher silences the file, and a shared non-append handle let the child's
buffered report clobber the heartbeat lines - which is exactly what "the heartbeat stops" looked like.
Two consequences worth remembering: a heartbeat writer that dies is invisible unless its stderr goes
to a file (it does now, `picampcontrol_heartbeat_err.log`, after a wrong argument silently killed it),
and the writer is spawned with `--label`, not `--test`, because `--test` is a validated choice.

Watching a log for visibility is sanctioned; judging a run from terminal output is not, so the
pass/fail line and the appended exit code still come from the run's own log file.

**A freshly recreated log is empty, and that is expected - say so.** Immediately after the
delete/create step there is no run in progress, so the tab and the tail both show nothing, which looks
exactly like "the file is not open" (2026-09-22: this cost a cycle and a round of confusion). Either
state plainly that it stays blank until the job starts, or start the job in the same breath. An empty
recreated log is never evidence of a missing file or a failed launch.

Both tests run by default. Windows is about 2.4x slower than macOS - the first-dit proof is ~20 s
on macOS / ~55 s on Windows, and the merged suite ~150 s / ~356 s (measured 2026-09-22) - so read
the elapsed time against the platform before calling a slow run anomalous. Run one at a time when
iterating; the first-dit proof is much the cheaper of the two:

```sh
ctest --test-dir _build/My_Pic_Project/debug -R FirstDit
ctest --test-dir _build/My_Pic_Project/debug -R PTT_Sequencer
ctest --test-dir _build/My_Pic_Project/debug -L sim
```

Neither test may run concurrently with the other: each owns MDB, and the suite launcher kills
stray MDB processes at startup.

Run that detached (or let it finish) and read the verdict from the CTest log in the temp
directory. Do not re-run another suite while one is active, and do not reuse a terminal that
still has a prior ctest/suite command queued.

Confirm that CTest discovers the merged `PTT_SequencerAndTripSuite` test
(`ctest --test-dir _build/My_Pic_Project/debug -N`). Report zero discovered tests as a
configuration failure, not success.

## Debugging

Two ways in, both against the simulator:

**VS Code GUI session.** Launch `Simulate PicAmpControl (Debug)` from `.vscode/launch.json` (breakpoints, variables, watch, registers, no terminal). It needs `out/My_Pic_Project/default.elf` to exist, so build first - and see the shared-ELF trap above, because a Release build leaves an optimized binary there and the session then misbehaves. Pin and register names cannot be pre-seeded through a file; add `PORTA`/`PORTB`/`PORTC`, `LATA`/`LATB`/`LATC`, `TRISA`/`TRISB`/`TRISC` or bitfields like `PORTCbits.RC5` to the Watch panel by hand.

**Headless `mdb`.** `tools/simulate/run_sim.sh [scenario.mdb]` builds, programs the simulator, and filters the benign `W0106-SIM` TMR1/3/5 warnings. Useful scripting commands: `break <function>` / `break <file>:<line>` with `Run`/`Continue`/`Halt`, `Stepi <count>` to single-step, `Stopwatch` for simulated elapsed time, `print pin <name>` to read an output and `write pin <name> high|low|<N>v` to drive an input. Scenario files must contain plain commands only - a `;` or `#` comment line aborts the rest of the script.

Prerequisites that decide whether debugging works at all:

- **Symbols come from whichever configuration was built last, and BOTH devices write the same
  `out/My_Pic_Project/default.elf` + `.sym`.** The `-O1`-in-Debug rule exists for the 16F's flash
  budget; Q10 Release keeps full symbols at `-Os` (verified 2026-09-22, see the configuration-policy
  section). If breakpoints or symbol reads stop resolving, first check *which device and
  configuration* produced the current `out/` artefact - a 16F Debug `.sym` read by a Q10 run looks
  like a firmware fault and is not.
- **You cannot write a C variable by name.** `write g_x 1` fails with `For input string: "<addr> "`, and `print /a g_x` fails the same way. Inject state by address from `out/My_Pic_Project/default.sym`, using `write /r 0x<addr> <lo> <hi>` (little-endian, one byte per word). Addresses move on every rebuild, so parse the `.sym` at run time.
- **The simulator is a debugger model, not silicon.** Timer1's external clock is not modelled and the suite injects `TMR1H`/`TMR1L` instead (see the triage section); exact timing still needs the bench. The simulator notes in `Ai-Notes.txt` are the reference for what the model does and does not implement.
- If the CPU appears stuck at the interrupt vector with continuous `W0223-ADC` spam on every `Halt`, suspect the ADC-ISR starvation bug class recorded in `bugfixes.md` rather than a debugger fault.

## Known snags (each one cost real time - do not rediscover them)

- **PIC18F47Q10 port findings (2026-09-22, sticky - add to this list as they are found; the port is in
  flight on branch `upgrade/pic18f47q10`).** Current state, re-measured 2026-09-22: all four
  translation units compile clean for `-mcpu=18F47Q10` against `PIC18F-Q_DFP/1.30.487` and the
  image **links** at 317Ah / 12666 bytes of 20000h program space (9.7%), 368 of 0xD1F bytes RAM,
  EEPROM 0 of 400h. Commands that reproduce it (no CMake): compile each `firmware/src/*.c` with
  `xc8-cc -mcpu=18F47Q10 "-mdfp=<Q_DFP>\xc8" -O1 -gdwarf-3 -std=c99 -I firmware/include -c`, then
  link the resulting `.p1` intermediates - **`-o foo.o` is ignored by XC8, which always emits
  `<stem>.p1` next to the output**, so a later link step must name the `.p1` files, not `.o`.
  Two `(1311) missing configuration setting for config word 0x300001/0x300005; using default`
  warnings on any scratch link are an artefact of that link passing no `#pragma config`; the real
  CMake build compiles `main.c` (which owns the config words) and does not show them.
  **The Q10 image has now actually run (2026-09-22), on a minimal bring-up probe rather than the
  firmware itself, and the six assumptions below all measured good on the MPLAB model:**
  | Assumption in the firmware | Measured on the Q10 model |
  |---|---|
  | `T2CLK = 0x01` (Fosc/4) makes Timer2 count | `T2TMR` moved 33 -> 409 -> ... across `Stepi` steps |
  | `IPEN = 1` + `IPR4bits.TMR2IP = 1` dispatches interrupts | `g_isr_any` went 0 -> 2 -> 5 as the tick ran |
  | `PR2 = 124`, `CKPS = 6` give a 1.000 ms tick | 3 ticks per 40000 `Stepi` steps, i.e. ~13.3 k steps/tick |
  | `T1CKIPPS = 0x19` is accepted | read back `25` |
  | PTT on RC0 with `ANSELCbits.ANSELC0 = 0`, pull-up on | `ANSELC = 254` (bit 0 cleared), `WPUC = 1` |
  | the NVM unlock + `WR` sequence completes | `g_nvm_done = 1`, `NVMDATL` read back `165` (0xA5) |
  | 64 MHz core runs the tick at 1.000 ms | 106 ticks per 200,000 `Stepi` steps; `OSCCON1` reads `96` |

  **THE FULL FIRMWARE IMAGE NOW RUNS ON THE Q10 MODEL (2026-09-22), and the first run found a
  real bug.** The image (not just the bring-up probe) was linked for `-mcpu=18F47Q10` at 317Ah /
  12,666 bytes and stepped under MDB. It boots and reaches `g_state = 5` (STATE_RESET_WAIT) via the
  main loop with no crash. What the run exposed: after 200,000 steps, `T2CON = 0`, `PR2 = 255`,
  `T2CLK = 0` and `OSCCON1 = 0` - i.e. **`timer0_init()`', and the clock config behind it, have not
  executed yet and the system tick is not running**. The cause is initialisation order, not the
  port: `main()` runs `adc_init(); load_settings(); lcd_init(); show_boot_message(); ...;
  timer0_init();` and the LCD boot path is slow enough under the simulator that the sample lands
  before the tick is armed. Two consequences worth keeping:
  - **When judging "does the tick run" on a probe run, sample late enough to be past
    `timer0_init()`, or arm the timer first.** A zero `T2CON` early in a run means "has not been
    initialised", not "broken".
  - It re-confirms the project rule that a boot-path stall is a real risk: `lcd_init()` and
    `show_boot_message()` run *before* the protection tick is armed, so a hang there leaves the
    amplifier with no 1 ms supervision. That ordering is worth a deliberate look on hardware,
    independent of the Q10 port.
  The registers that *are* set by then match the 16F design exactly (`ANSELA = 47`, `ANSELB = 14`,
  `ANSELC = 0`, `ANSELD = 0`, `TRISC = 5`), so the port sequence is behaving as intended.

  **PPS ON Q10: ONLY ONE ASSIGNMENT EXISTS, AND IT IS AN INPUT (2026-09-22).** The firmware's
  entire PPS surface is `T1CKIPPS = 0x19` in `freq_counter.c` - the Timer1 clock *input* from RD1.
  No `RPnR`/`*PPS` **output** register is written anywhere: every other pin is a plain LAT/PORT pin.
  So the "Q10 PPS output codes differ from the 16F's" risk does not apply to this design as it
  stands, and the band relays do not need PPS at all. If that ever changes, the output source codes
  come from the Q10's own output table, which is a different table from the input codes - do not
  carry `0x19` across. The input code itself measured good on the model (readback `25`).
  Still open on Q10 and only answerable on the bench: whether `RB4` (hardware fault latch) is
  digital with the right polarity, and whether the 64 MHz core changes the LCD parallel timing
  (`lcd_parallel.c` runs `-Os` in Debug and was never timed on Q10).

  **`W9602-COMP` IS NOT A BLOCKER FOR THIS DESIGN - the firmware never configures an on-chip
  comparator (clarified 2026-09-22).** The warning says the model cannot route a DAC voltage into a
  comparator input, and it was carried in `Ai-Notes.txt` as an open risk "in the overcurrent safety
  path". Reading `firmware/src/main.c` settles it: there is no `C1CON`/`C2CON`/`CM1CON`/`CM2CON`
  write anywhere. The overcurrent protection is an **external hardware comparator**, whose latch
  output the firmware only *reads* as a digital pin (`INPUT_OVERCURRENT_FAULT` = `RB4`), and whose
  reset is an output the firmware drives (`OUTPUT_COMP_RESET` = `RC1`). So the unimplemented model
  feature is a peripheral this firmware does not use, and `W9602-COMP` can be treated as benign
  simulator noise alongside `W0106-SIM` - do not re-open it as a blocker.
  What *does* still need care on Q10 is the electrical side: `RB4` must be digital (analogue-select
  cleared) and its polarity/level must match the external comparator's latch, and `RC1` must drive
  the reset with the same active-low sense the 16F used. Those are covered by the pin-map
  comparison (`docs/hardware/q10-pinout-compatibility.md`) plus bench validation, not by any
  firmware change.

  **THE Q10 CLOCK IS A DESIGN DECISION, NOT A CONFIG DETAIL (2026-09-22).** The Q10 config map
  offers exactly two reset-oscillator settings - `HFINTOSC_64MHZ` and `HFINTOSC_1MHZ` - and no
  `HFINT32`, which is a 16F-only name. The port had landed on `HFINTOSC_1MHZ`, i.e. running the
  whole amplifier at 1/32 of the design clock, because the 32 MHz name it wanted does not exist
  on this part. That silently stretches the 1 ms tick, every band-settle delay and the trip
  response by 32x - a wrong clock is a *safety* defect here, not a performance one. The rule that
  follows: **pick the highest available internal oscillator rate (64 MHz) and reach the design's
  8 MHz Timer2 input with the clock divider instead of lowering the core.** The tick chain is
  then 64 MHz -> `T2CLK = Fosc/8` (`T2CLK` is a code: `0x01` = Fosc/4, `0x02` = Fosc/8) -> 1:64 ->
  `PR2 = 124` -> 1.000 kHz, identical to the 16F's 32 MHz -> Fosc/4 -> 1:64 -> 125.
  The per-family difference is therefore in `T2CLK` (and the config word), guarded in `main.c`,
  not in `PR2` or `CKPS`.
  Independently verified on the simulator: `OSCCON1` reads `96` (0x60, the 64 MHz HFINTOSC rate),
  and 200,000 `Stepi` steps advance the tick by 106 - a measured ~1,887 steps per simulated
  millisecond against a 1.000 ms `PR2` tick. That is ~0.24x the 8,000 instructions/ms that
  `tools/simulate/test_first_dit.py` assumes from the 16F era, so **that constant is wrong for
  Q10 and every Q10 timing assertion is meaningless until it is recalibrated**.
  **`NVMCON1` on this device has NO `WREN` bit** - its members are `RD`, `SECRD`, `WR`, `SECWR`,
  `SECER`, straight from the DFP header. `Eeprom-changes.md` names `WREN`, `NVMCMD`,
  `NVMCON0bits.GO` and `INTCON0`; none of those exist here, so take the *procedure* from that file
  and the *bit names* from the header. Writing `NVMCON1bits.WREN` fails to compile, which is how
  this was caught a second time.
  **MDB script syntax, learned the hard way this session:** MDB rejects `//` and `;` comment lines
  as `Undefined command` and exits `-1` before running anything, so a probe script must carry **no
  comment lines at all** (put the explanation in the .c file). The step command is `Stepi`
  (capital S), `hwtool sim` is lower-case, and the working template is
  `_build/spike_q10_retest/ab.mdb` - copy its shape rather than writing a script from scratch.
  The instruction rate also needs recalibrating for Q10: `tools/simulate/test_first_dit.py` assumes
  8000 instructions/ms (16F-era), while the Q10 probe measured roughly 6000-6900 instructions per
  simulated tick against a 1.000 ms `PR2` tick - do that calibration before trusting any Q10 timing
  assertion.
  1. **Analog-select bitfield names differ by family.** `firmware/src/freq_counter.c` used
     `ANSELDbits.ANSD1..ANSD7`, which do not exist on the Q10 - the same register (0xF21) has
     members named `ANSELD1..7` there. Fixed by clearing the whole register (`ANSELD = 0x00`), which
     is family-neutral and correct here because every PORTD pin in this design is digital (RD0 LCD,
     RD1 T1CKI, RD2-RD7 band relays). Prefer a whole-register write whenever only the *names*
     differ.
  2. **Config words are named per family, and only three differ here.** The Q10 rejects
     `RSTOSC = HFINT32` (`error: (1363) unknown configuration setting/register`), `MCLRE = ON` and
     `BORV = 19`. It wants `RSTOSC = HFINTOSC_1MHZ`/`HFINTOSC_64MHZ`, `MCLRE = EXTMCLR`/`INTMCLR`,
     `BORV = VBOR_190`. Guarded with `#if defined(__18F47Q10__)` in `main.c`; `FEXTOSC`, `WDTE`,
     `PWRTE`, `CP` and `BOREN` are identical on both devices. Read the names from the DFP's
     `<device>.cfgmap`, never from memory.
  3. **BLOCKER: the legacy EEPROM API does not exist on the Q10.** `eeprom_read`/`eeprom_write`
     expand through `pic18.h` to `Read_b_eep`/`Write_b_eep`/`Busy_eep`; XC8 warns
     `unsupported: The Read_b_eep routine is no longer supported` and the link fails with
     `error: (2096) undefined symbol "_Write_b_eep"` (plus `_Busy_eep`, `_Read_b_eep`). The Q10
     needs the NVM-register API instead. `firmware/src/lcd_parallel.c` is the only user (the
     versioned, checksummed settings record), so that is the whole scope - but it is a real driver
     change, not a rename.
     **Read `Eeprom-changes.md` in the repo root before touching any EEPROM/NVM code** (user
     instruction, 2026-09-22): it is the owner's notes on this exact migration, and it is tracked
     precisely so a future session finds it. Use it for the *procedure* - the 0x55/0xAA unlock
     written to `NVMCON2` matches this device - but take the **bit names from the DFP header, not
     from that file**: the notes name `NVMCON1bits.NVMREG`, `NVMCON0bits.GO`, `NVMCMD`, `WREN` and
     `INTCON0`, and none of those exist in `PIC18F-Q_DFP/1.30.487`. This part has
     `NVMCON1` = {`RD`, `SECRD`, `WR`, `SECWR`, `SECER`}, `NVMCON0` = {`NVMERR`, `NVMEN`}, and the
     global interrupt enable is `INTCON.GIE`. The compiler is the arbiter: code that trusts the
     notes' names fails to build, and a driver that trusts them at runtime would be guessing.
     (Same class of error as the assumed `T2CLKCON` value - a plausible-looking external source is
     not a datasheet.)
  Generalisation worth keeping: family differences surface as **names** far more often than as
  behaviour, and a device-guarded block or whole-register write is usually smaller and clearer than
  a per-symbol shim.
- **Log presentation the user actually wants (2026-09-22, after two rounds of feedback).** These logs
  are read by a human *during* the run, so: emit MDB output as raw text, never as a repr
  (`{bytes!r}` renders every newline as `\n` and every tab as `\t`, and MDB's pin dumps are
  tab-separated tables, so escaping makes them unreadable); and on the heartbeat line show the recent
  bytes as the *text column of a dump* - printable bytes kept, everything else as `.` - which
  collapses MDB's blank-line spam into one compact, scannable string on the line that already
  carries the timestamp. The user does **not** want a full hex dump: they want the existing
  timestamp/heartbeat line with the recent bytes beside it, compact.
- **A returned terminal command of "no output" is not evidence about the run.** Learned twice this
  session: a command with everything redirected prints nothing, and a killed/cleaned terminal can
  swallow a pipeline's output entirely (`Write-Output` included). Verify state with a *fresh*
  command before concluding anything, and never read a test verdict out of terminal text.
- **An assumed register value can reject a whole device - and it did (2026-09-22, this cost most of
  a session and produced a wrong verdict that had to be retracted).** While writing minimal bring-up
  for the PIC18F47Q10 the Timer2 clock select was written as `T2CLKCON = 0x00` with the comment
  "Fosc/4 (the reset default)". The value was *assumed*. `firmware/src/main.c`'s own
  `timer0_init()` has carried `T2CLKCON = 0x01; /* Fosc/4 */` for this project's Timer2 the whole
  time. With `0x00`, `T2TMR` never moved, and the conclusion "MPLAB's simulator runs no time base on
  the Q10" was written into `bugfixes.md` and `Ai-Notes.txt` and the branch abandoned. Re-tested
  with `0x01`: `T2TMR` reads `106` then `92` - Timer2 counts immediately. The device was never the
  problem; the assumed value was. Four rules, all cheap:
  1. **Never write a peripheral code you have not seen** in the datasheet, the DFP
     (`xc8/pic/dat/cfgmap/<device>.cfgmap`, `xc8/pic/include/proc/<device>.h`), or this repository.
     "The reset default" is a guess unless you have read it.
  2. **Read the equivalent setup for the device the project already uses** before writing it for a
     new one. The correct value was in the repo the entire time, one file away.
  3. **Before blaming the simulator, A/B the suspect value.** Two builds differing in that one
     constant and one mdb session settle it in minutes. The re-test above did exactly that.
  4. **A negative simulator finding needs a positive control.** "No timer counts" is only evidence
     if the same firmware counts with a different code - otherwise it measures your configuration.
  This is `deepseek-pic.md`'s "never guess configuration" rule applied to SFRs, not just config words.
- **BUILD THE POSITIVE CONTROL BEFORE BELIEVING THE NEGATIVE RESULT - and check your own arithmetic
  with it (2026-09-22, twice in one session).** The Q10 suite reported **0 keyed runs in 552
  samples**. That is the exact signature the abandoned 18877 attempt produced ("the pattern says the
  firmware never sees PTT asserted"), so it was very plausible as a chip problem. It was not
  believed until a positive control existed, and building that control took minutes:

  `_build/My_Pic_Project/sim/stimulus_control_report.txt` / `tools/simulate/test_stimulus_positive_control.py`:
  read `PORTC`, `write pin RC0 low`, read again, release, read again. Result `229 -> 228 -> 229`.
  The stimulus reaches the firmware, so "0 keyed runs" is a **real firmware finding**.

  Two failures inside that one small exercise, both worth not repeating:

  1. **The control's first run reported the opposite of the truth - because I checked the wrong
     bit.** RC0 is bit **0** of `PORTC`; the check used bit 1. `229 -> 228` is exactly the change
     the control was looking for, and reading bit 1 made a perfect result look like "no change",
     so it declared the stimulus inert. **A positive control that you have not sanity-checked is
     worse than no control**: it manufactures confidence in the wrong direction. Before trusting a
     control's verdict, confirm the mask/bit/index it uses against the pin you actually drove, and
     confirm the direction of the effect (idle -> asserted -> released should return to idle).
  2. **A stimulus command that mdb accepts is not a stimulus that applied.** `write pin RA6 high`
     was echoed in the transcript and did nothing. Placing it *before* `program` was one cause (the
     target is not programmed yet); a special-function pin (`RA6` is also `CLKOUT/OSC2`) is a
     suspected second cause, still not proven. So any test whose whole point is a sad path must
     **assert that its stimulus took effect** and fail loudly if it did not. The first version of
     the boot sad-path test did not, and reported a PASS while exercising nothing - see
     `test_boot_safety_order.py`'s `hold_applied()`.
- **CHECK THE SIMULATED-TIME ARITHMETIC BEFORE CALLING ANYTHING A HANG - and note that "steps per
  ms" differs from "steps per PR2 tick" (2026-09-22; this cost a whole wrong verdict).** A staged
  probe ran 800,000 `Stepi` steps on Q10, saw `g_startup_inhibit` still `true` with `g_state` stuck
  at `STATE_RESET_WAIT`, and reported "the startup-inhibit timer never expires" as a firmware fault.
  It was pure arithmetic: **Q10 at 64 MHz runs at 16 MIPS, so one instruction is 62.5 ns, and
  800,000 steps is only 50 ms of simulated time** - against a 1000 ms startup gate. The probe cut
  off 20x too early. With `Stepi 16500000` everything passes: the inhibit clears, PTT latches,
  bypass-snoop engages. Nothing was ever broken.
  Two rules fall out of it:
  1. **Before reporting a timing fault, convert your step count into simulated milliseconds** and
     compare it to the gate you are testing. `steps = ms * MIPS * 1000`. 16F: 8 MIPS. Q10: 16 MIPS.
  2. **"steps per simulated millisecond" is not "steps per PR2 tick".** The `INSTRUCTIONS_PER_MS`
     values in `test_first_dit.py` (8000 on 16F, 1887 on Q10) are *steps per 1 ms hardware tick*, a
     measured conversion factor for that device's clock chain - they are not MIPS and must not be
     used to convert a step count into elapsed real time. Conflating the two produced the wrong
     verdict above.
  The general trap, worth stating plainly: **a probe built on a false premise will confirm the false
  premise.** This one was designed to walk the PTT path and found exactly the "fault" it was primed
  to look for. Positive controls (above) would have caught it - the control proves the *stimulus*
  works, and a second control on the *timing* would have proved the gate could be reached.
- **`FEXTOSC = OFF` plus `ANSELA` bit 6 clear is NOT enough to free RA6 on Q10 in MDB - and it does
  not matter (2026-09-22, from `blockers.txt`).** RA6 is multiplexed with the external-oscillator
  gate OSC2, and the Q10 model keeps reporting it as analogue (`RA6 Ain ... CLKOUT/OSC2`) even with
  `FEXTOSC = OFF`, `RSTOSC = HFINTOSC_64MHZ`, `ANSELA = 0x2F` (bit 6 clear) and `TRISA6 = 0` all in
  place. The model appears to keep the oscillator's claim on the pin, and `write pin RA6 ...` does
  nothing.
  **The practical impact is nil, and that is the part worth remembering:** RA6/RA7 are the LCD
  strobe and data line, they are **write-only**, and nothing in the firmware ever reads them back.
  The three pins that *are* read back for safety are `SENSE_TX`/`SENSE_TX_VCC`/`SENSE_TX_BIAS` =
  RC5/RC6/RC7, none of which is multiplexed with a special function. So RA6 is **untestable in
  simulation, not broken** - check it on the bench. Do not spend time trying to make MDB drive it.
- **When several symptoms share one cause, find the cause before chasing the symptoms (2026-09-22).**
  "0 keyed runs" looked like a PTT problem. A staged probe (`probe_q10_ptt_path.py`) walked the path
  one stage at a time - startup inhibit expired? PTT latched? snoop entered? - and showed
  `g_startup_inhibit` was still `true` after 800,000 steps with `g_state` stuck at `STATE_RESET_WAIT`.
  So PTT was never *able* to latch: the failure was upstream of PTT entirely, in the startup-inhibit
  timer not advancing. Walking the path in order costs one probe and replaces a symptom with an
  address. Prefer it to reasoning about the most visible symptom.
- **A family can need a different *enabling mechanism*, not just a different value - and the model
  will look broken until you use it (2026-09-22, same session as the bullet above).** With
  `IPEN = 0` - the PIC16F-style plain path - the PIC18F47Q10 model dispatches **no** interrupts at
  all: two independent sources (Timer2 overflow, and an RC0 interrupt-on-change driven from mdb)
  raised and cleared their request flags under polling, with `GIE = 1` (`INTCON=135`), `PIE4 = 2`
  and `PIE0 = 16`, while `g_isr_any` stayed `0`. That was written up as a simulator limitation. It
  was wrong: with `IPEN = 1` plus the source's priority bit (`IPR4bits.TMR2IP = 1`) the ISR runs
  immediately - `g_isr_any` and `g_tick` both `56 -> 172`, and a polled counter falls to `6 -> 18`
  because the ISR now consumes the flags first. Before declaring that a device model cannot do X,
  enumerate the ways X can be *enabled* on that family and try each: it is a one-line change and one
  mdb run per variant, and two such "the simulator can't do it" verdicts in one day both turned out
  to be unwritten firmware configuration. Related trap from the same run: `OSCCON3.ORDY` reads `0`
  on this part *while its timer demonstrably runs*, so a wrong-looking status flag is not evidence
  about the thing it names.
- **`W0106-SIM` is scoped to PPS / clock-source routing - it is NOT a statement that a peripheral,
  the core CPU, or the interrupt controller is unmodelled. Do not generalise it.** The warning text
  (`... partial support for TMR1 peripheral. Use internal oscillator as timer clock slection is not
  implemented`) names one thing: the simulator cannot route a virtual pin or `.scl` stimulus through
  the PPS multiplexer into a peripheral's clock input. Microchip's own guidance (supplied by the user
  in `mistakes.md` at the repo root; restated here so it does not depend on that file) is explicit
  that the engine handles the core and the interrupt controller correctly - a register such as TMR1
  that overflows to `0x0000` sets its interrupt flag, breaks execution, and steps into the ISR. Two
  consequences worth acting on:
  - **Never convert a W0106 warning into "interrupts do not work in the simulator".** That claim was
    made here on 2026-09-22 and was wrong; the interrupts were simply not enabled correctly (see the
    `IPEN` bullet above). The bounded limitation is external pin-routing, nothing more.
  - **The sanctioned workaround for a pin-routing gap is register injection in software**, optionally
    behind `#ifdef __MPLAB_DEBUGGER_SIMULATOR` so test-only register manipulation cannot reach
    silicon. That is exactly what this project already does when the suite writes `TMR1H`/`TMR1L`
    instead of clocking T1CKI - it is the recommended technique, not a compromise, so do not
    re-open it by trying to make a stimulus drive the pin (see the SCL notes above: it cannot, and
    the timer clock-source mux is not modelled in any case).
- **`write <SFR> <value>` is not universally supported by this mdb build.** `write T1CON 0x01` and
  `write TMR1L 0xAB` work, but `write T2CLKCON 0x00` fails with `For input string: "fbe "` and
  **aborts the rest of the script** (`MDB_EXIT=-1`). Inject peripheral registers through a rebuilt
  image, or put speculative register writes last in the script. (Same class as `write g_x 1` /
  `print /a g_x` failing - see the fault-injection notes above.)
- **Do NOT swap the target device without first checking that MPLAB models it equivalently.** On
  2026-09-22 the PIC16F18877 (same family, 40-pin PDIP, 4x flash and RAM, ~£2, in stock) was trialled
  as a drop-in upgrade for the PIC16F18875. It **builds perfectly** - the whole change is
  `-mcpu=16F18877` in `.generated/rule.cmake` plus the `__16F1887x__` defines and `.clangd` - and
  gives 8117/32768 words = 24.8% flash, 365/4096 bytes = 8.9% RAM. `mdb` also **accepts** the device
  and runs the script. But the firmware then behaves differently: **0 keyed runs**, only 3 band-select
  changes (all `locked=false`), and `g_state` never reaches STATE_BYPASS_SNOOP, so `test_first_dit.py`
  aborts at the first clause with `clause (a): snooping did not report STATE_BYPASS_SNOOP`.
  Band-change timing is unchanged (1161/1705ms vs 1162/1699ms), which rules out a clock-rate
  difference, and `ANSELC = 0x00` / `TRISC0 = 1` / `WPUC0 = 1` are already set in `main.c`, which
  rules out a pin-config omission. The pattern says the firmware never sees PTT asserted on the
  18877 model. Reverted.
  **REQUALIFIED 2026-09-22, later the same day: treat this rejection as provisional, not settled.**
  It was reached from a single configuration with no positive control - the method that then produced
  TWO wrong verdicts for the PIC18F47Q10 (an assumed `T2CLKCON` value, then a missing `IPEN`/priority
  enable), each of which blamed the model for firmware configuration nobody had written. The 18877
  *symptoms* above are real and recorded, but "MPLAB does not model it equivalently" is not
  established by them, because a wrong register value, a pin-table difference in the model, and a
  different interrupt-enable form all look identical from outside. Note too that the unchanged
  band-change timing implies the timer tick *was* running, which sits badly with a blanket
  non-equivalence claim. Before any further 18877 work, derive its register values from the DFP
  instead of assuming 18875 equivalence, and apply the discipline the Q10 re-test settled on:
  minimal bring-up, one variant per suspect setting, and a positive control behind every negative
  finding.
  **The lesson that survives the requalification: a clean build says nothing about the simulator.**
  Every suite in this project runs on `mdb`, so before trusting a device swap, check the simulator.
  Treat an unexplained behaviour change on a new device as something to investigate properly - not
  as a puzzle to work around, and not as a verdict to record after one attempt.
- **Delete large logs as soon as their verdict is read.** MDB transcripts and captured suite output
  run to megabytes. Remove them (`rm -f /tmp/<log>`) the moment the verdict has been extracted, and
  do not leave them on disk even in `/tmp`. Keep a log only while its run's verdict is still needed;
  never accumulate a series of run logs. Copying a log to a second path to defeat a stale read (see
  below) doubles the space, so delete both once read.
- **A fault-injection proof must fail on the clause that names the defect.** Re-introducing a defect
  can trip an *earlier* clause instead, because the suite is one continuous MDB session and one phase
  feeds the next. That is still evidence the defect is caught, but it is NOT evidence for the clause
  you wrote - record the failure message actually observed, and if it does not name your clause,
  either make the injection narrower or say plainly that the clause's own proof is outstanding. Do
  not upgrade an incidental cascade into a claim about the new clause.
- **Clause (d)'s idle-counter check was layout-sensitive; it is fixed - do not reintroduce the old
  form.** It used to build its delta list from consecutive entries of the *filtered* idle-sample list,
  so exactly one delta always spanned the keyed gap between two released runs, and the assertion
  required `len(resets) == 1`. Shift the phase boundary by a single sample and that one pair splits
  into a small positive plus a large negative: two "resets", and the clause fails for reasons that
  have nothing to do with the firmware. Fixed 2026-09-21 by grouping released samples into runs that
  are adjacent in the transcript (`idle_runs()`) and validating each run against **its own measured
  span**, not an assumed sample spacing - these phases mix 1 ms and 10 ms steps, so a fixed-spacing
  assumption is wrong even within one run. Symptom to watch for: a fault-injection run failing at
  clause (d) instead of at the clause under test.
- **A foreground `test_first_dit.py` run can be killed by the terminal capture.** Twice on 2026-09-21
  it came back with `Command produced no output`, exit `130`, and an **empty** log - the run never
  happened. Do not treat that as a pass or a fail. Check that the log is non-empty before judging
  anything, and launch these runs in the background (async) with output redirected, which is
  reliable; if the shell is wedged, `workbench.action.terminal.killAll` first.
- **A log read back through a file tool can be STALE.** Reading a log while it is still being
  written, or re-reading a path that was read earlier in the same session, can hand back an old copy
  - which looks exactly like "the run produced nothing". Copy it to a path that has never been read
  before (`cp /tmp/run.log /tmp/run_v2.log`) and read that, incrementing the suffix each time. Never
  judge a run from a log path you have already read.
- **Never reuse a log path across runs.** Truncate it (`> file`) or use a new name per run, or a
  stale verdict from an earlier run is indistinguishable from the current one. The appended
  exit-code line only helps if the file was genuinely rewritten.
- **The terminal's output capture can die and take the run with it.** A long suite printed enough to
  make VS Code report "Output exceeded terminal scrollback; beginning of output was lost", after
  which every command in that shell returned no output at all while the once-healthy run had stopped
  mid-trace. Recover with `workbench.action.terminal.killAll` and a fresh command; prevent it by
  launching long runs in the background with everything redirected to a file, so the run does not
  depend on the terminal staying healthy.
- **A stale PID file used to stop the next launch before it started** - fixed 2026-09-22, but the
  symptom is worth recognising if it regresses. `run_suite_with_watchdog.py` used to signal the
  previous run's process group unconditionally and died with `PermissionError: [Errno 1] Operation
  not permitted` from `os.killpg` when the PID file belonged to a run that was already gone. The
  launcher now checks `platform_process.pid_is_alive()` first and clears the file if the process is
  gone. If it regresses, delete the PID file in the temp directory and relaunch.
- **A missing program-memory line means "nothing was relinked", not "no space used".** Both
  configurations link to the same `out/My_Pic_Project/default.elf`, so after a Release build the
  Debug `cmake --build` can print no summary at all because Ninja has no work to do. Force the relink
  with `rm -f out/My_Pic_Project/default.elf` before the Debug build.
- **`test_first_dit.py` can only inject the variables in `SYSTEM_SYMBOLS`** (`g_band_cache_band`,
  `g_band_cache_idle_ms`). Writing any other name raises `KeyError: '<name>'` before the simulator
  even starts. Either add the name to `SYSTEM_SYMBOLS`, or drive the state through the firmware's own
  mechanism - it puts the cache back into bypass-snoop by injecting an idle count past
  `IDLE_TIMEOUT_MS` rather than clearing `g_band_cache_valid`, which is not injectable.

### Windows gotchas (found 2026-09-22 porting the harnesses)

All of these are now handled in `tools/simulate/platform_process.py`. They are listed because each
one fails in a way that looks like something else, and because the *reason* they were present is
the actual lesson: every one of them was invisible on macOS and only appears when the same code
first runs on Windows. Assume any new POSIX-flavoured helper needs the same scrutiny.

- **`os.killpg`, `os.getpgid` and `signal.SIGKILL` do not exist on Windows.** They raise
  `AttributeError` - and only on the timeout/interrupt path, i.e. exactly when a run has hung and
  cleanup matters. Use `platform_process.kill_tree()` / `terminate_tree()`. Note `import signal`
  succeeds on Windows; only the individual constants are missing, so a static import check proves
  nothing.
- **`os.kill(pid, 0)` KILLS the process on Windows instead of probing it.** Python's Windows
  `os.kill` maps every signal except `CTRL_C_EVENT`/`CTRL_BREAK_EVENT` onto `TerminateProcess`, so
  the idiomatic POSIX liveness check is destructive here. Use
  `platform_process.pid_is_alive()`, which uses `OpenProcess`/`GetExitCodeProcess`.
- **`start_new_session=True` is silently ignored on Windows** - it is accepted, not rejected, so
  the child stays attached to the console and a Ctrl-C reaches `mdb`. Windows needs
  `creationflags=subprocess.CREATE_NEW_PROCESS_GROUP`; use
  `platform_process.isolated_spawn_kwargs()`.
- **There are no signalable process groups on Windows.** Teardown is
  `taskkill /PID <pid> /T /F`, which walks the child tree. Exit code `128` from `taskkill` means
  "no such process", which is a fine outcome, not an error.
- **`ps` does not exist on Windows, and its absence is not a `CalledProcessError`.** The old
  `kill_orphaned_processes()` guarded `subprocess.check_output(["ps", ...])` with
  `except subprocess.CalledProcessError`, so on Windows it raised an uncaught `FileNotFoundError`
  and the launcher died *before starting any run*. Use `platform_process.running_processes()`, which
  uses `Get-CimInstance Win32_Process` there. `wmic` is deprecated and absent from current Windows
  builds, so do not reach for it.
- **Match the mdb launcher narrowly, or you will kill MPLAB X IDE's JVM.** A Windows run is
  `cmd.exe /c "…\mplab_platform\bin\mdb.bat" <script>` plus
  `java.exe … -classpath "…lib\mdb.jar" com.microchip.mplab.mdb.debugcommands.Main <script>`.
  Matching `mplab_platform` (the natural transliteration of the POSIX pattern
  `/mplab_platform/bin/mdb`) also matches the IDE's own JVM and a Java updater daemon, and
  matching a bare `mdb.jar` is a path the IDE's classpath could carry too. The JVM is therefore
  matched on its **main class** (`com.microchip.mplab.mdb`) and the wrapper on `mdb.bat` -
  both chosen from a full `Win32_Process` dump of 262 processes, not guessed. Do not "simplify"
  these back to the install directory or the jar name. A healthy run is exactly four processes:
  launcher → suite → `cmd.exe`/`mdb.bat` → `java.exe`; if the `java.exe` has no `cmd.exe` parent
  the tree was torn down with `taskkill /T`.
- **`Path().glob()` rejects absolute patterns from Python 3.13 on**
  (`NotImplementedError: Non-relative patterns are unsupported`), so
  `Path().glob("C:/Program Files/.../mdb.bat")` fails. Use `glob.glob()`. The existing harnesses
  avoided this only by globbing a *relative* pattern under an absolute base
  (`Path("C:/…/MPLABX").glob("*/…")`) and rewriting it broke the instant the pattern itself became
  absolute. This machine runs Python 3.14.7, so it is live here.
- **MPLAB version directories must be sorted as versions, not strings.** `sorted(...)[-1]` on
  `v6.20`/`v6.35` happens to work, but it would pick `v6.9` over `v6.35`. `find_mdb()` now compares
  the version tuple.
- **`python3` is not on the Windows PATH** - the interpreter is `python`. Use `python` in Windows
  commands; `run_tests.ps1` and the CMake `find_program(PYTHON_EXECUTABLE NAMES python3 python)`
  both resolve it correctly.
- **Windows MDB is ~2.4x slower than macOS, so macOS-sized timeouts fail healthy runs.**
  Measured 2026-09-22 on the same firmware: the first-dit proof takes ~55 s on Windows against
  ~20 s on macOS, and the merged suite **356 s against ~150 s**. The old 280 s inner timeout
  therefore killed the suite mid-run on Windows while it was still printing progress on every
  heartbeat - the verdict was `error: mdb timed out after 280s and was killed` and CTest reported
  `PTT_SequencerAndTripSuite ***Failed 281.75 sec`, `50% tests passed`, which reads exactly like a
  firmware regression. Nothing in the firmware or the toolchain caused it. This is a property of
  MDB's JVM plus the simulator, not of this repo. The timeouts are therefore sized for the slowest
  host: `run_mdb(timeout=1500)` as a last-resort net, `run_suite_with_watchdog.py --timeout 1200`
  and the matching CTest registration as the real budget. Do not shrink any of them back to a
  macOS-sized number, and do not read a timeout-killed suite as a firmware regression - a timeout
  is a *budget* failure, and the heartbeat log tells the two apart in seconds (a genuinely hung run
  shows `delta=0` and a frozen `mdb_bytes`; a slow-but-healthy one keeps producing output).
- **Sizing rule learned here:** the inner per-session timeout must sit *above* the launcher's
  outer `--timeout`, otherwise the child dies first and the harness reports its own message
  instead of the launcher's clean `TIMEOUT ... END code=` line. When you change one, check the
  other.
- **Python can launch `mdb.bat` directly**; no `shell=True` and no `cmd /c` wrapper is needed for
  `subprocess.Popen([r"…\mdb.bat", script])`. Do not "fix" a nonexistent problem by adding
  `shell=True`, which loses the argument quoting.
- **A short throwaway probe script is the right tool for this class of problem** - a 20-line script
  that launches `mdb` and dumps matching command lines found the whole Windows process picture in
  one run, where reading code would have only produced guesses. Delete the probe when you are done;
  the build tree is not a scratch directory.

### Invoking XC8 / MPLAB tools directly from the Windows shell

Some work (a device spike, a one-off probe) needs a compiler or `mdb` call that is *not* the CMake
build. Two shell habits produced silent no-op runs on Windows - exit code 0, no error message, no
artefact - and both were avoidable:

- **Never wrap an executable in `cmd /c ""C:\Program Files\...\xc8-cc.exe" args 2>&1"`.** The
  nested double quotes collapse and `cmd` reports
  `'C:\Program' is not recognized as an internal or external command, operable program or batch file.`
  Use PowerShell's `&` call operator and quote **each** argument separately, so a path with spaces
  stays one token: `& 'C:\Program Files\Microchip\xc8\v4.00\bin\xc8-cc.exe' '-mcpu=18F47Q10'
  "-mdfp=C:\Program Files\Microchip\MPLABX\v6.35\packs\Microchip\PIC18F-Q_DFP\1.30.487\xc8" ...`.
- **Do not build the call out of a multi-line snippet that assigns a variable and then interpolates
  it into `&`** (`$p='C:\Program Files\...'; & '...xc8-cc.exe' "-mdfp=$p" ...`). One such command
  reached the shell mangled, compiled nothing, and still reported `XCC_EXIT=0`; its redirected log
  contained only that exit-code line. Prefer a single-line command with literal absolute paths over
  a multi-line one, and treat a mangled terminal echo as "the command did not run", not as noise.
- **For a build, verify the artefact rather than the exit code.** Redirecting to a log and appending
  `$LASTEXITCODE` is the right verdict pattern for a *test* run, but for a compile it proves nothing
  on its own: check the `.elf`/`.hex`/`.map` exist (`Get-ChildItem _build/...`). XC8 also prints its
  memory summary on stdout, so an empty log next to exit 0 always means "the compiler never ran".
- **A device spike's compiler flags can be passed directly** - no CMake needed. For the PIC18F47Q10
  bring-up the whole command was `xc8-cc -mcpu=18F47Q10 -mdfp=<Q_DFP>/xc8 -O1 -gdwarf-3 -std=c99
  -o <elf> -Wl,-Map=<map> <source>.c`, which linked 202 bytes of program space and warned only
  `(1311) missing configuration setting for config word 0x300005; using default` (benign - one
  config word was left at its DFP default).

## ADCC registers: the PIC18F47Q10 is NOT the generic PIC18 ADC

The Q10 uses the **ADCC** (ADC with Computation), and its register map is not the one the family
name suggests. Verified 2026-09-22 against the actual DFP headers, because a written "resolution"
brief asserted otherwise and it was wrong on every point:

| Register | PIC18F47Q10 (ADCC, PIC18F-Q_DFP 1.30.487) | Classic PIC18 (e.g. PIC18F47J53, PIC18F-J_DFP) |
| --- | --- | --- |
| `ADREF` | **exists**, `ADPREF<1:0>` at bits 0-1, `ADNREF` at bit 4 | does not exist |
| ref-select bits | `ADPREF` 2 bits, `ADNREF` 1 bit, in `ADREF` | `VCFG<1:0>` = `VCFG0` (ADCON0 bit 6) and `VCFG1` (ADCON0 bit 7), `ADCON0` at `0xFC2` |
| `ADPCH` | exists, 6-bit positive channel at `0xF5A` | does not exist; channel is `CHS<3:0>` in `ADCON0` bits 2-5 |
| `ADCON0` | `__at(0xF5B)`: `ADGO` 0, `ADFM` 2, `ADCONT` 6, `ADON` 7 | `__at(0xFC2)`, plus separate `ADCON1`/`ADCON2` |
| `ADCON1` | `__at(0xF54)`: `ADDSEN` 0 and comparator polarity bits only - **no `ADFM`, no `ADCS`** | `__at(0xFC1)`: `ADCS<2:0>`, `ACQT<2:0>`, `ADCAL`, `ADFM<1:0>` |
| conversion clock | `ADCLK` (`0xF52`), `ADCS<5:0>` | `ADCON1` `ADCS<2:0>` |
| result | `ADRES`/`ADRESH`/`ADRESL`, but ADCC also has `ADACC`, `ADPREV`, `ADSEL`, `ADSTAT`, `ADCON2/3` | `ADRESH`/`ADRESL` |
| `ADCON1 = 0x20` means | `ADGPOL = 1` (comparator polarity) | benign |

The practical consequences: **there is no `ADREF` byte write in the firmware, and there must not be
one** - `adc_init()` sets the reference implicitly by leaving `ADREF` at its all-zero reset (VDD/VSS),
which is exactly what the project wants. Writing `ADREF = 0x00` is a no-op for the same reason. Code
copied from a classic PIC18 (or from a PIC16F188x, whose registers are `ADCON0`/`ADCON1`/`ADPCH` too
but with different bit positions) will silently set a *comparator* polarity bit or a different
channel. Always confirm the register layout in the device's own header before adding an ADC write:

```
<MPLABX install>/packs/Microchip/PIC18F-Q_DFP/<ver>/xc8/pic/include/proc/pic18f47q10.h
```

and grep for the register name - a `NOT FOUND` there is a real answer, not a bad path.

**Do not transfer PIC16F18875 ADC findings to the Q10.** The 16F header does have `ADPCH`, but the
control/format bits differ (`ADFM` lives at a different position and `ADCON1` carries `ADPREF`), so
even a same-named register can mean something else.

### Mistakes made while chasing the Q10 trip (2026-09-22) - do not repeat these

A "trip resolution" brief was written for this blocker and reviewed against the headers. Five of its
claims and one of mine were wrong. The pattern in every one of them is the same: **a plausible story
about register layout or timing was believed without being checked against the device header, a
warning log, or a converted unit.**

1. **"The Q10's `ADREF` bit map differs from the PIC16's" - wrong conclusion from a false premise.**
   The real error was asserting *any* legacy `ADREF` byte write existed to be misinterpreted. There is
   none. The correct handling is the one already in `adc_init()`: never write `ADREF`, i.e. rely on
   its reset value. An added `ADREFbits.ADPREF = 0; ADREFbits.ADNREF = 0;` would be harmless but
   pointless - do not add it as a "fix".
2. **`ADFM` does not behave differently between the families here.** On the Q10, `ADFM` is `ADCON0`
   bit 2 and `ADCON0 = 0x88` sets it: `ADON = 1`, `ADCONT = 0` (single-shot), `ADCS = 0` (Frc),
   `ADFM = 0`. The comment in `adc_init()` describing `ADFM<1:0>=10` is **inaccurate for the Q10** -
   the field is 1 bit. The code is still correct because the ADCC result is right-justified by
   default in this configuration, but the comment is misleading and should not be trusted as a
   spec. `ADFM = 0` is the *justified-right* setting on the classic PIC18 and on the Q10 alike.
3. **A log line was quoted as evidence without being read.** The brief cited a simulator warning
   "`W0223-ADC: ADC input voltage low. ADC output underflow`" as the "definitive smoking gun". That
   string appears nowhere in this repo's logs or in MDB's message set. Before quoting a tool
   message as the decisive clue, grep the run's own log for the exact text; if it is not there, the
   clue does not exist.
4. **"The PIC16 code did a raw byte write to `ADREF`" established a claim by looking in the wrong
   file.** The PIC16 firmware has no `ADREF` write either - `adc_init()` is a single shared function
   under one `#if` on the device define, not a per-device pair. A claim about what "the legacy code
does" must be checked in the legacy code, not inferred from the new one.
5. **"Guard the thresholds with `#ifdef __MPLAB_DEBUGGER_SIMULATOR__` and force safe values" is the
   wrong shape of fix, twice over.** Forcing `g_thresholds` to magic numbers makes the test pass by
   disabling the behaviour under test; and if a threshold really had loaded as 0, the honest fix is
   to make `load_settings()` fail closed and report, not to paper over it in a simulator-only branch.
   Reject any proposal that makes the suite green by changing what the firmware does when it is
   being tested.
6. **A probe script was requested that could not run as written.** The brief specified a five-line
   MDB fragment (`print g_state`, `print g_trip_reason`, `print ADRES`, `print ADPCH`, `print ADREF`)
   that is not a runnable script: it has no `Device`/`Halt`/`Step` sequence, so it would be echoed and
   ignored, and `print ADRES`/`print ADPCH`/`print ADREF` name *registers*, not the firmware symbols
   `SYSTEM_SYMBOLS` allows. MDB symbol reads work on the firmware's own variable names; the adapter
   raises `KeyError` on anything else **before the simulator starts**. Extend
   `tools/simulate/probe_q10_ptt_path.py` instead of hand-writing a script fragment.

**The one-line test that catches all six:** name the file and line that proves it, or the command
whose output proves it, before acting on it. If neither exists, the claim is a hypothesis to test,
not a finding to act on.

## Failure triage

- `Frequency counter failed to classify ...`: inspect the scenario name, `FREQ_DEBUG` lines, Timer1 writes, measured `frequency_khz`, `current_band`, `band_locked`, PTT state, and sequence stage.
- `<band> TX lock failed while injecting <N> kHz`: check the injection timing before you touch the
  firmware. This signature is usually a stimulus artefact of the 10 ms tick resetting Timer1 while
  the harness sampled on 10 ms boundaries, so the sample always landed before the tick that
  consumed the count. It is the classic "passed standalone, failed in the suite" case (a
  standalone run can start at a favourable phase). Fix it with 5 ms sampling and
  `inject_step_hold()`; the historical instance is logged in `bugfixes.md`.
- A band assertion that "fails" only under `--quick-bands`: check whether the scenario is still
  injecting a frequency that actually differs from the band under test. Injecting the same
  frequency makes a lock-freeze assertion vacuous.
- `did not clear and re-enter TX after a PTT re-arm`: the re-arm must keep a valid Timer1 count
  present across the keyed window (see the injection notes above); a fault scenario must not
  re-assert PTT with frequency `0`.
- `I1:`/`I5:` or `clause (x):` failures naming a HOT SWITCH mean the invariant caught a real
  firmware defect, not a test problem. Do not relax the invariant to get green - fix the ordering
  so the amplifier is bypassed before the relay selection moves. `I2: amplifier keyed with the
  band unlocked` and `I4:` (relay pins disagreeing with `current_band`) are the same class.
- `FREQ_CTR_FAIL` must remain a negative test and must prove no active TX stage and inactive TX outputs.
- Band/frequency-counter coverage is deliberately indirect. The MPLAB X simulator does not
  model Timer1's external clock (it warns `W0106-SIM: ... partial support for TMR1 ...
  timer clock selection is not implemented`), so the suite injects `TMR1H`/`TMR1L` rather than
  clocking the pin. T1CKI, PPS routing, the 1:4 prescaler and the Timer1 overflow path can only be
  validated on the bench.
- **An SCL stimulus cannot rescue the timer test - it is not even loadable here.** Re-tested
  2026-09-22: `help stim` documents `stim <file>` as loading an SCL stimulus file, but this MDB
  build rejected both a `configuration for "pic16f18875" is ... end configuration;` block with a
  named `testbench`/`process` (`Error: syntax error`, `Error: stack underflow. aborting...`,
  `E0101-SIM: Failed to disassemble instruction (line 3)`) and the same file without the
  configuration block (`... (line 1)`). So an earlier claim in this file that SCL "does drive the
  pin correctly - verified" is **wrong** and has been removed: it rested on a run whose SCL file
  was never recorded. Treat SCL as unavailable, and treat any stimulus that has not been confirmed
  with `print pin <name>` as undelivered. Do not spend a cycle trying to make SCL work for T1CKI -
  even if it loaded, the timer clock-source mux is not modelled, so TMR1 could never advance.
- A handler that drives `RC0` is a **PTT** handler, not a frequency-counter one: `RC0` is
  `INPUT_PTT`. T1CKI is `RD1`, routed by PPS (`T1CKIPPS = 0x19` in `firmware/src/freq_counter.c`).
  Scripts offered from outside the project get this wrong routinely - check the pin against
  `pin_map.h` before believing a stimulus claim.
- MDB output ending without a final validator line is inconclusive; inspect the saved log and process table.
- Keep source fixes separate from test-harness timing fixes. Re-run the narrow failing scenario first, then the full suite.
- If the terminal wrapper reports a command as finished while the PID file remains, the run is still active or the wrapper lost control of it. Kill the recorded tree before doing anything else. To see what survived, use `ps -axo pid=,command=` on macOS or
  `Get-CimInstance Win32_Process | Where-Object CommandLine -match 'mdb\.(bat|jar)'` on Windows -
  never `mplab_platform`, which also matches MPLAB X IDE's own JVM.
- **A Windows run that produces no CTest result has usually died before the simulator starts.** The
  first Windows failure here was not the firmware, the toolchain, or `mdb`: `kill_orphaned_processes()`
  called `ps`, which does not exist, and the launcher exited on an uncaught `FileNotFoundError`
  before it ever spawned the suite. When a Windows run reports nothing at all, check the launcher's
  own progress log for whether it even reached `START`/`CHILD`; an absent `CHILD` line means the
  failure is in the launcher, not in the simulation.

## Reporting

Report:

0. **Commit and push as you go - local and remote.** As soon as a change is verified green, commit
   it and push to the branch you are working on - `origin/main` only when that *is* the branch; the
   Q10 work is on `upgrade/pic18f47q10` and pushing it to `main` is wrong. Do not batch a session's
   work into one large commit at the end, and
   never leave verified work sitting only in the working tree. Small verified commits are the rule;
   the only acceptable reason to hold one is a verdict that is still running, and then it is
   committed the moment that verdict reads green. This is a standing user instruction - it has been
   forgotten before.

1. Debug and Release build exit status and important compiler/linker warnings, plus the program-memory figure when a build is near the limit. State which OS the run was on - the two toolchains are known to agree on code size as of 2026-09-22, so a divergence is a finding, not noise.
2. CTest test discovery and result.
3. Merged suite exit status, elapsed time, and final pass/fail line.
4. The first failing scenario and its diagnostic state, if any.
5. Whether a fix that touched `firmware/` was pushed and whether the triggered `PIC firmware build` run for that commit succeeded (repo convention: commit and push verified-green work promptly, then confirm the triggered CI build rather than waiting for it before pushing).

Never say all tests are green unless Debug/Release and the requested test command have fresh successful exit codes, read from a log file rather than the terminal.
