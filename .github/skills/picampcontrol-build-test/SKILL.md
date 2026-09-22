---
name: picampcontrol-build-test
description: "Use when building, testing or debugging PicAmpControl firmware on macOS or Windows: Debug or Release builds, CMake configuration, ctest, run_tests.sh / run_tests.ps1, simulator/mdb runs, the VS Code Simulate debug session, breakpoints and symbol reads, PTT/frequency-counter tests, band-lock tests, first-dit band detection, remembered-band fold-back, band-change/hot-switch guards, or build/test failures."
---

# PicAmpControl Build, Test and Debug

**Hard writing rule: never write "Hmm". Not in a reply, not in a reasoning trace, not as a preamble
or a hedge.** The user reads the reasoning as well as the final answer, and this was repeated three
times on 2026-09-22 *after* the rule already existed in `Ai-Notes.txt` - the third time the user
quoted the word straight back. A bullet buried in a long list did not stop it, so it lives here too.
State the finding, or the uncertainty, plainly, and move on.

**Hard environment rule: the FileTail extension (`spacetown.filetail`) MUST be installed.** Long jobs
- suites, builds, spike runs - write their output to a log file, and that file is opened in a VS Code
**tab** with FileTail toggled on (`filetail.toggle`) so it reloads and scrolls to the end while the
user is still at the end: auto-scrolling until they interact, then stopping. **Never tail these logs
in a terminal/console** - the user has forbidden it explicitly and more than once. If FileTail is
missing, install it (`spacetown.filetail`) before starting anything long. This rule exists because
the log is the user's window into a multi-minute run; console tails were both unwanted and, worse,
silently broken (see the log-viewing note under Simulator verification).

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

**Hard rule: at session start, run `python tools/simulate/cleanup_sim_processes.py`.** It kills
leftovers using the launcher's own pattern list, then checks Defender.

The exclusion *list* is not readable without elevation - verified 2026-09-22: `Get-MpPreference`,
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
- Debug build directory: `_build/My_Pic_Project/debug`
- Release build directory: `_build/My_Pic_Project/release`
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

Known reduction levers, in rough order of value:

1. Table-drive the long `if`/`else` chain in `adjust_selected_setting()` (est. 80-100 words). The
   per-setting min/max/step bounds are irregular, so it needs a new menu-edit scenario in the suite.
2. ~~Compile `lcd_parallel.c` at `-Os` in the Debug build.~~ **MEASURED 2026-09-22: this reclaims
   NOTHING - do not retry it.** The override does apply (`set_source_files_properties(... lcd_parallel.c
   PROPERTIES COMPILE_OPTIONS "$<$<CONFIG:Debug>:-Os>")` gives `-O0 -O1 -Os` on the command line,
   last wins) and the file was forced to recompile by deleting its object, yet the linked Debug image
   was **8117/8192 words before and after - identical**. XC8's linker runs its own optimisation pass at
   the `-O1` in the link rule, which appears to normalise the per-TU level, so per-file `-O`
   overrides are the wrong layer. It also costs MDB symbol resolution *inside* that file. The only
   lever at this layer is lowering the **link** step's `-O`, which weakens symbol resolution
   everywhere and needs the user's consent (item 3).
3. Bit-pack the menu metadata (`g_menu_setting_offsets[]` 20 B + `g_menu_setting_types[]` 20 B).
4. Shorten the remaining display strings.
5. Only if the user explicitly agrees: build the whole Debug image `-Os` - it costs ~1200 words but
   silently breaks MDB symbol and breakpoint resolution.

Flash is the binding constraint on this project, and it is easy to trip from a test change:

- Release (shipping) uses ~6899/8192 words = ~84% used; Debug is the binding one at 8117/8192 = 99.1%
  (2026-09-21 snapshot - always read the current value from `memoryfile.xml`, and note that the same
  figures are tracked in `Ai-Notes.txt` under "Device memory usage").
- Debug is deliberately compiled `-O1` (not `-Os`) so MDB can resolve symbols and breakpoints. That is why the build the simulator loads is far closer to the limit than the shipped build. Budget against the Release number.
- A link error reporting that program space is exhausted reproduces in the Debug build first, long before Release breaks. It reads as `(1347) can't find 0xN words ... for psect "<name>" in class "<class>"` and lists several psects, because the last few words are fragmented. Treat it as a signal that the test image needs `-O1` kept and the change needs to be smaller — not as a reason to switch Debug to `-Os`, which would silently break MDB symbol resolution. Read the exact figure from `memoryfile.xml` rather than guessing at the wording of the linker message.
- The cheapest room is in string literals (`STRCODE`), which the linker fails to place first. On
  2026-09-21 the LCD menu labels and boot text were shortened to reclaim ~72 words; that is the
  precedent to follow before reaching for anything structural, but it is a user-visible change - ask.
- Prefer table-driven logic over long if/else chains when adding firmware code, and ask before adding code.

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

**Delete the log before you launch the job, not after.** The sequence is: delete -> create fresh ->
*start the job* -> open the file in a tab -> FileTail on. Opening a tab that a previous run already
created, or reusing one mid-run, leaves the user looking at a stale buffer and was called out on
2026-09-22. Note the launcher now *appends* (one file across both tests, never recreated per run), so
once the tab exists use `Clear-Content` - deleting the file would drop the watcher.

**Open the log in TAIL mode in the VS Code UI for any long-running job - on Windows too** (standing
user instruction, 2026-09-22, generalised and then restated for tail mode the same day). The user
wants to watch long jobs - suites, builds, spike runs - live in the UI, so delete the log, recreate it
fresh for the run, and open a *follow*, not a static editor tab: VS Code reloads a changed file but
does not track the end of a growing one.

```powershell
# Windows: open in a TAB and let FileTail follow it (never a console tail - see the hard rule above)
# Resolve the CLI rather than assuming Insiders (hard rule at the top):
$code = if (Get-Command code-insiders -ErrorAction SilentlyContinue) { 'code-insiders' } else { 'code' }
& $code -r "$env:TEMP\picampcontrol_suite_progress.log"
# then run the command `filetail.toggle` with that tab active
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

- **Symbols come from the Debug build.** `user.cmake` compiles Debug with `-O1` and Release with `-Os` per configuration precisely so breakpoints and symbol reads resolve; a bare `-Os` overriding an `-O0` is a past bug that silently broke them, so if breakpoints on functions or statics stop resolving, read that file first.
- **You cannot write a C variable by name.** `write g_x 1` fails with `For input string: "<addr> "`, and `print /a g_x` fails the same way. Inject state by address from `out/My_Pic_Project/default.sym`, using `write /r 0x<addr> <lo> <hi>` (little-endian, one byte per word). Addresses move on every rebuild, so parse the `.sym` at run time.
- **The simulator is a debugger model, not silicon.** Timer1's external clock is not modelled and the suite injects `TMR1H`/`TMR1L` instead (see the triage section); exact timing still needs the bench. The simulator notes in `Ai-Notes.txt` are the reference for what the model does and does not implement.
- If the CPU appears stuck at the interrupt vector with continuous `W0223-ADC` spam on every `Halt`, suspect the ADC-ISR starvation bug class recorded in `bugfixes.md` rather than a debugger fault.

## Known snags (each one cost real time - do not rediscover them)

- **PIC18F-Q10 port findings (2026-09-22, sticky - add to this list as they are found; the port is in
  flight on branch `upgrade/pic18f47q10`).** Compiling the *unmodified* firmware for
  `-mcpu=18F47Q10` against the shipping Q DFP is far closer than expected: all three translation
  units compile with only seven errors, all of a single kind.
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
   it and push to `origin/main`. Do not batch a session's work into one large commit at the end, and
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
