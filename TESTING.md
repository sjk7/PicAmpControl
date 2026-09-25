# Testing Guide

The simulator's clock is not the hardware's, and that does not invalidate these tests. MPLAB X
`mdb` does not model the oscillator - it ignores the config bits and the oscillator registers - so it
single-steps on its own fixed instruction timing (a ~4 MHz-equivalent core) rather than the part's
64 MHz. The firmware's time base is the Timer2 interrupt, and every assertion below checks
tick-relative sequencing, state and latches, which the model executes identically at any speed; the
harnesses convert firmware-ms into single-step counts with the measured **1695 steps per firmware-ms**,
so the sampling windows stay aligned to firmware time regardless of the model's absolute rate. What
the simulator cannot prove - absolute wall-clock latency, and the peripherals it does not implement
(T1CKI/PPS, the real ADC conversion rate, LCD bus timing) - is bench-only, and always was.

Firmware behaviour is verified in the MPLAB X `mdb` simulator. CTest drives two Python
harnesses against the built ELF, single-steps the firmware, samples pin state and firmware
variables, and asserts the sequencing, band-detection, band-locking, and fault-protection
behaviour:

- [`tools/simulate/trace_ptt_sequence.py`](tools/simulate/trace_ptt_sequence.py) — the merged
  PTT/trip/band suite (eleven scenarios in one MDB session)
- [`tools/simulate/test_first_dit.py`](tools/simulate/test_first_dit.py) — the first-dit
  band-detection proof, in its own MDB session

A full run takes roughly 3 minutes on macOS and roughly 7 minutes on Windows: MDB is about
2.4x slower there (measured 2026-09-22: suite 356 s vs ~150 s, first-dit 55 s vs ~20 s), so expect
the same tests to take proportionally longer rather than assume a slow run is a broken one.
Timeouts are sized for the slower platform.

## Prerequisites

- MPLAB X IDE 6.x (provides the `mdb` simulator)
- XC8 4.00 toolchain
- Python 3 (the suite is Python 3 only)
- CMake 3.24+ and Ninja

```bash
# macOS
brew install cmake ninja
brew install --cask mplabx-ide mplab-xc8
```

```powershell
# Windows
winget install Kitware.CMake
winget install Ninja-build.Ninja
# MPLAB X IDE (which bundles the XC8 compiler) from microchip.com - it is not a winget package
```

On Windows the interpreter is `python`; there is no `python3` on the PATH. CMake's
`find_program(PYTHON_EXECUTABLE NAMES python3 python)` and `run_tests.ps1` both handle this, so
the scripts work unchanged - it only matters when typing commands by hand.

## Quick start

```bash
./run_tests.sh          # macOS
```

```powershell
.\run_tests.ps1         # Windows
```

Both configure `_build/My_Pic_Project/sim`, build the firmware, then run CTest. They are the same
workflow with the same behaviour; `run_tests.sh` is the bash original and `run_tests.ps1` its
PowerShell twin.

**Build directories (canonical, 2026-09-24).** `_build/My_Pic_Project/sim` is the directory the tests
run in and the only one `run_tests.sh`/`.ps1` configure. `_build/My_Pic_Project/release` is the one the
editor reads (`.clangd`, `.vscode/settings.json`). The former Q10-suffixed trees (`q10`, `q10_release`,
`q10_lcdtest`) are gone: the Q10 is the only device, so it no longer needs a build tree or a set of VS
Code tasks of its own.

## Manual run

```bash
cd "$HOME/mydocs/code/PicAmpControl"   # wherever you cloned the repo

cmake -S cmake/My_Pic_Project/default \
  -B _build/My_Pic_Project/sim \
  -G Ninja \
  -DCMAKE_BUILD_TYPE=Debug \
  -DCMAKE_TOOLCHAIN_FILE="$PWD/cmake/My_Pic_Project/default/.generated/toolchain.cmake" \
  -DCMAKE_USER_MAKE_RULES_OVERRIDE="$PWD/cmake/My_Pic_Project/default/.generated/overrides.cmake" \
  -DXC8_BIN_DIR="$HOME/tools/microchip/xc8/v4.00/xc8-v4.00/bin" \
  -DCMAKE_C_COMPILER="$HOME/tools/microchip/xc8/v4.00/xc8-v4.00/bin/xc8-cc" \
  -DCMAKE_ASM_COMPILER="$HOME/tools/microchip/xc8/v4.00/xc8-v4.00/bin/xc8-cc" \
  -DCMAKE_AR="$HOME/tools/microchip/xc8/v4.00/xc8-v4.00/bin/xc8-ar" \
  -DCMAKE_EXPORT_COMPILE_COMMANDS=ON

cmake --build _build/My_Pic_Project/sim
ctest --test-dir _build/My_Pic_Project/sim --output-on-failure > /tmp/pac_ctest.log 2>&1
```

On Windows the same configure runs **without** the XC8 overrides - the checked-in
`.generated/toolchain.cmake` detects the compiler at `C:/Program Files/Microchip/xc8/v4.00/bin`
and the packs at `%USERPROFILE%\.mchp_packs` itself:

```powershell
$root = (Get-Location).Path
cmake -S cmake/My_Pic_Project/default `
  -B _build/My_Pic_Project/sim `
  -G Ninja `
  -DCMAKE_BUILD_TYPE=Debug `
  "-DCMAKE_TOOLCHAIN_FILE=$root/cmake/My_Pic_Project/default/.generated/toolchain.cmake" `
  "-DCMAKE_USER_MAKE_RULES_OVERRIDE=$root/cmake/My_Pic_Project/default/.generated/overrides.cmake" `
  -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
cmake --build _build/My_Pic_Project/sim
$log = "$env:TEMP\pac_ctest.log"
ctest --test-dir _build/My_Pic_Project/sim --output-on-failure *> $log
Add-Content $log "CTEST_EXIT=$LASTEXITCODE"
```

## Test output goes to files, not the terminal

Every simulator sample prints pins and state variables, so an MDB run produces megabytes of
trace. Printing that to the terminal overflows the scrollback and destroys the pass/fail
line, so always send CTest output to a log file and read the verdict from there.

| File | Contents |
|---|---|
| `/tmp/pac_ctest.log` (`%TEMP%\pac_ctest.log` on Windows) | CTest verdict (one line per test, discovery, total time) |
| `/tmp/picampcontrol_suite_progress.log` (`%TEMP%\...`) | Suite progress: START/CHILD, 10-second heartbeats, `END code=<n>` |
| `<run log name>.mdb_progress.log` beside the run log (`%TEMP%\...`) | Raw live MDB output |
| `_build/My_Pic_Project/sim/csv/` | Per-scenario CSV sample dumps |
| `_build/My_Pic_Project/sim/graphs/` | Per-scenario logic-analyzer PNG traces, plus `<scenario>_scope.png` for a failure |

A successful run ends with `100% tests passed` and `CTEST_EXIT=0`; the suite log line
`PTT suite passed: 11 scenarios in one MDB session` and the first-dit proof line
`FIRST-DIT PROOF PASSED: ...` confirm that each harness ran to completion.

**A failed scenario also writes `<scenario>_scope.png`** - a scope trace of the harness's own
samples, with the lanes picked from the data and the trip / PTT-release / PTT-re-arm instants marked
- and hands it to the editor without stealing focus. That is the artefact to look at first when a
scenario fails (`tools/simulate/scope_trace.py`).

## Test suite

CTest registers two tests in [`cmake/My_Pic_Project/default/user.cmake`](cmake/My_Pic_Project/default/user.cmake):

| Test | Command | Labels | Time |
|---|---|---|---|
| `PTT_SequencerAndTripSuite` | `run_suite_with_watchdog.py --timeout 1200` | `sim`, `suite` | ~150 s macOS / ~356 s Windows |
| `FirstDit_BandDetectionAndHotSwitchGuards` | `run_suite_with_watchdog.py --test first-dit --timeout 600` | `sim`, `first-dit` | ~20 s macOS / ~55 s Windows |

Both registered tests go through the watchdog launcher. **`test_first_dit.py` is never run directly**
- that gives a log tab that never moves (the harness's stdout is block-buffered through the redirect)
and no timeout, no heartbeat and no orphan clean-up. `--test first-dit` is the wrapped spelling of
the same harness. See `.github/skills/build-test/SKILL.md`.

The 1200 s figure is the *budget*, not the expected time - it is sized so that a healthy run on
the slower platform cannot be mistaken for a failure. A timeout is a budget problem: before
treating one as a firmware regression, check the heartbeat log, where a slow-but-healthy run keeps
producing MDB output while a genuinely hung one sits at `delta=0`.

Run everything, or select one test at a time, from the build directory:

```bash
ctest --test-dir _build/My_Pic_Project/sim --output-on-failure     # both tests
ctest --test-dir _build/My_Pic_Project/sim -R FirstDit             # first-dit only
ctest --test-dir _build/My_Pic_Project/sim -R PTT_Sequencer        # merged suite only
ctest --test-dir _build/My_Pic_Project/sim -L sim                  # everything labelled sim
ctest --test-dir _build/My_Pic_Project/sim -N                      # list without running
```

Redirect to a log file as in the examples above when you need the pass/fail line to survive.

### Merged suite

The suite's command is:

```text
python3 tools/simulate/run_suite_with_watchdog.py --timeout 1200
```

`python3` is the macOS spelling; on Windows it is `python`. `run_tests.ps1` and the CTest
registration both resolve the right interpreter themselves.

The launcher runs `trace_ptt_sequence.py --suite` in its own process group, kills stale
runs, records progress logs, and enforces the timeout itself. The process plumbing it needs is
platform-specific and lives in `tools/simulate/platform_process.py` - POSIX uses process groups
plus `os.killpg`, Windows uses `CREATE_NEW_PROCESS_GROUP` plus `taskkill /T /F`, and the PID-progress
and orphan scans sit behind one interface. All eleven scenarios run
inside **one** MDB session, so the run time is dominated by simulator startup and
single-stepping rather than per-scenario overhead.

| # | Scenario | Expected behaviour |
|---|---|---|
| 1 | Baseline PTT cycle | Startup inhibit, then the first-dit bypass-snoop decode of the 40 m signal, then TX → TX_VCC → TX_BIAS in order with the configured delays, then the ordered release |
| 2 | `TEMPERATURE` | Thermal fault during transmit trips and latches |
| 3 | `SWR1` | Pre-filter SWR fault trips |
| 4 | `SWR2` | Post-filter SWR fault trips |
| 5 | `HWFAULT` | Hardware overcurrent comparator fault blocks/trips |
| 6 | `CURRENT` | Software overcurrent trip |
| 7 | `OVERDRIVE` | Overdrive trip |
| 8 | `DRAIN` | Drain-peak trip |
| 9 | `SWR1_1P5` | SWR1 at 1.5:1 and 2 kW must **not** trip |
| 10 | `FREQ_CTR` | Frequency counter classifies all six nominal bands in RX and keeps each band locked through TX injection. Each band is engaged from its own live measurement, which wins over the remembered band (see the design doc). The firmware's own keyed self-test is what the scenario asserts: per band, either the keyed band lock is verified, or the firmware named the reason it refused to key |
| 11 | `FREQ_CTR_FAIL` | Negative test: with no Timer1 signal, PTT is latched but held in bypass-snoop - no band is locked, no TX stage advances, every TX output stays inactive, and the firmware's self-test names why (`NO_BAND`/`NO_LOCK`) |

Each scenario also validates output pin sequencing, fault latching and re-arm behaviour, LCD
status state, and startup-inhibit timing. `FREQ_CTR_FAIL` is intentionally a negative test -
it must never be "fixed" into a passing trip.

**The firmware's verdict is the contract, not a counter reading.** While keyed the firmware tests
itself (`tx_selftest_run()`; `docs/tx-sequencer.md` §9), and every scenario reads that verdict from
`g_selftest_failed` / `g_selftest_reason` instead of re-deriving it from the model. A check must hold
for 200 ms to count, several failures are reported together as `+`-joined names, and the reason is
held on the panel until the next key-down. In particular no **keyed** `frequency_khz` reading is
asserted: the firmware resets TMR1 on every 10 ms gate and nothing in the simulator clocks it, so such
a reading measures the simulator's pacing rather than the firmware.

Every scenario additionally has the band-selection safety invariants checked on its samples
(relay selection frozen while keyed, never keyed with an unlocked band, and every relay move
observed with the amplifier cold). The checks live in
[`tools/simulate/first_dit_invariants.py`](tools/simulate/first_dit_invariants.py).

### What the band/frequency-counter test does and does not cover

The band scenarios inject Timer1 counts by writing `TMR1H`/`TMR1L` directly, using the
inverse of the firmware's own scaling (`counts = kHz x 1000 / 400`). This is deliberate: the
MPLAB X simulator does not implement Timer1's external clock, so T1CKI edges never increment
TMR1 no matter how the pin is driven.

The band under test is injected for the **whole keyed window**, not just before PTT, because
the firmware resets TMR1 on every 10 ms tick: a measurement taken only in RX goes stale at the
assert, which is the opposite of a real transmission and (correctly, under the first-dit model)
leaves the amplifier in bypass.

Verified 2026-09-21 by driving RD1 with an SCL stimulus (`stim <file>.scl`) as fast as the
simulator can represent: `print pin RD1` reported `HIGH`/`Din` (the pin really was driven) and
`T1CON` read `0x27` (T1CKI selected, 1:4 prescaler), yet `TMR1L`/`TMR1H` stayed `0`. The
simulator's own diagnostic explains why:

```text
W0106-SIM: This device only has partial support for TMR1 peripheral.
Use internal oscillator as timer clock slection is not implemented
```

Covered by the injected-count tests:

- the counts-to-kHz arithmetic and the 400 Hz-per-count scaling
- band classification for all six bands, including the two-tick stability requirement
- the band-select outputs themselves — RD2-RD7 are sampled and must match `current_band`,
  so a regression in `update_band_outputs()` fails the test
- band lock during TX (with a *different* band's frequency injected) and unlock on return to RX/idle
- the no-band path, including a check that PTT really was asserted: PTT must latch, the
  amplifier must stay in bypass-snoop, and no band may be locked

Not covered, and not coverable in simulation:

- the T1CKI pin, its PPS routing, and the Timer1 1:4 prescaler
- the Timer1 overflow path (`g_tmr1_overflows`), because the injected counts fit in 16 bits
- true 10m coverage: a real 10m frequency (28.0-29.7 MHz) needs 70000-74250 counts, beyond a
  single 16-bit TMR1 write, so the 10m case uses 25000 kHz (inside the classifier's wider window)

Bench validation with a real signal generator is required for those.

## First-dit band detection

[`tools/simulate/test_first_dit.py`](tools/simulate/test_first_dit.py) proves the first-dit
model described in [`docs/first-dit-band-detection.md`](docs/first-dit-band-detection.md). It
runs its own MDB session and covers, in one transcript:

1. PTT with no RF at all: PTT latches, the amplifier stays in bypass, no band is locked.
2. The first RF burst (20 m): decoded while bypassed, the relay selection moves cold, the band
   is cached, the amplifier is keyed only after the relay settle window.
3. A second PTT on the remembered band engages with **no RF injected anywhere in that window**,
   which is what proves the cache — not a fresh snoop — drove the engagement.
4. The cache idle counter advances, and crossing `BAND_CACHE_IDLE_TIMEOUT_MS` drops the cache so
   the next PTT snoops again.
5. A band change to 40 m is re-detected on the next first burst.
6. Hot-switch fault injection: the cached band is deliberately overwritten with a different band
   and the amplifier is re-keyed during the release ramp (while `TX_VCC`/`TX_BIAS` are still
   asserted). The relays must move only after the firmware forces bypass.
7. A blind cached-band engage that is corrected: the amplifier is keyed on the remembered band
   with no RF to verify it, then 40m RF appears. Within `BAND_VERIFY_MS` the firmware must fold
   back to bypass, re-select the relay cold and re-engage on the band actually being received.

Every sample of the session is checked against invariants I1-I5 (see the design doc), and the
three defects in that doc's table were re-introduced to confirm the test fails on each of them
rather than passing vacuously.

The test drives two firmware globals directly (`write /r <address> <bytes>`), because this mdb
build cannot write a C variable by name — it fails with `For input string: "<addr> "`. The
addresses are read from `out/My_Pic_Project_18F47Q10/default.sym` at run time, so they follow rebuilds.

Because simulating the full 60 s timeout would need ~480M instructions, clause 4 proves the
counter really advances (~1 ms/ms) and then injects an idle count just below the threshold, so
the expiry comparison itself still runs in the firmware.

## Individual scenario tests

The merged suite is the default and the authoritative check. To register each scenario as
its own CTest test instead, configure with `-DPICAMP_ENABLE_INDIVIDUAL_SIM_TESTS=ON`
(default `OFF`):

```bash
cmake -S cmake/My_Pic_Project/default -B _build/My_Pic_Project/sim ... -DPICAMP_ENABLE_INDIVIDUAL_SIM_TESTS=ON
ctest --test-dir _build/My_Pic_Project/sim -R "PTT_TemperatureTrip" --output-on-failure
```

Registered names:

- `PTT_ActiveLow_StartupAndReleaseSequence`
- `PTT_TemperatureTrip_InTransmit`
- `PTT_SWR1_1P5_NoTrip_At2kW`
- `PTT_SWR1Trip_InTransmit`
- `PTT_SWR2Trip_InTransmit`
- `PTT_HWFAULTTrip_InTransmit`
- `PTT_CURRENTTrip_InTransmit`
- `PTT_OVERDRIVETrip_InTransmit`
- `PTT_DRAINTrip_InTransmit`

These run one MDB session each, so they are much slower in total than the merged suite.
There is no individual frequency-counter test; the band-lock and `FREQ_CTR_FAIL` checks are
part of the merged suite only.

## How the test runs

[`tools/simulate/trace_ptt_sequence.py`](tools/simulate/trace_ptt_sequence.py):

1. Checks that the built ELF exists (build the firmware first)
2. Locates MPLAB X `mdb` and launches it with a generated command script
3. Single-steps firmware execution
4. Samples pin states and firmware variables at fixed instruction intervals
5. Parses the trace into per-scenario sample groups

[`tools/simulate/platform_process.py`](tools/simulate/platform_process.py) holds the only
platform-specific code in the harnesses: temp-path resolution, MDB discovery, how a child is
detached from the console, how a process is probed for liveness, and how a hung process tree is
torn down (`os.killpg`/`SIGKILL` on POSIX, `taskkill /T /F` on Windows) plus the orphan scan
(`ps` vs `Get-CimInstance`). If a platform difference needs handling, it belongs there, not in an
individual harness.
6. Validates sequencing, band locking, and each trip path
7. Writes CSV samples and logic-analyzer PNG traces
8. Exits non-zero on any failed assertion (the message names the scenario and the state)

[`tools/simulate/run_suite_with_watchdog.py`](tools/simulate/run_suite_with_watchdog.py)
wraps that script: it starts it in a new session/process group, records the PID in
`/tmp/picampcontrol_suite.pid`, cleans up stale runs, writes 10-second heartbeats to
`/tmp/picampcontrol_suite_progress.log`, streams MDB output to a `.mdb_progress.log` derived from
the run log's own name (one run, one log - a fixed name made a second run fail to start), and kills
the whole process group on timeout.

Do not start a second suite while one is running. If a run looks stuck, read the PID file,
terminate that process group, and remove the PID file before starting again.

### Targeted repros

When one scenario fails, do not re-run the whole suite to diagnose it - run the smallest harness that
reproduces that scenario, then re-run the suite once as the verdict:

| Repro | Command | What it isolates |
|---|---|---|
| One suite scenario | `run_suite_with_watchdog.py --test suite --only FREQ_CTR` (or `--only base,SWR1`) | that scenario alone, through the suite's own code path (~40-80 s instead of ~350 s). **This is the repro for a suite failure** - a scenario that fails in the suite does not have to fail in isolation. |
| SWR1 trip re-arm | `run_suite_with_watchdog.py --test repro-swr1-rearm` | the trip latch clearing and TX re-entering stage 3 after a PTT re-arm; `PICAMP_RELEASE_MS` sets the release window |
| FREQ_CTR band slice | `run_suite_with_watchdog.py --test check-freq-ctr` | the classifier and band lock for one band (`PICAMP_BANDS`, default `80m`). A **check**, not a repro: it passes whether or not the suite fails. |
| first-dit 20 m | `run_suite_with_watchdog.py --test repro-20m` | the Timer1 injection byte order for a 20 m count |
| release stage 4 | `run_suite_with_watchdog.py --test repro-release` | the 5 ms `SEQ_RELEASE_RELAYS` window at 1 ms sampling |

A failed run ends its log with a copy-pasteable `===== FAILURE SUMMARY =====` block - what the
scenario was testing for, what the firmware actually did (counts read out of the samples), the
assertion, and the reconstructed LCD panel plus the fault code. It is the same text drawn at the
bottom of the scenario's `_scope.png`; the log carries it because a PNG cannot be quoted into a
report. Files are opened in the editor only when `PICAMP_SHOW_FILES=1` is set: automatic opening
could not be made focus-safe, and interrupting the operator's typing is worse than a path they can
open themselves.

## Generated artifacts

CSV samples are written to `_build/My_Pic_Project/sim/csv/` and PNG traces to
`_build/My_Pic_Project/sim/graphs/`, one pair per scenario:

```text
_build/My_Pic_Project/sim/
├── csv/
│   ├── ptt_trace.csv
│   ├── temperature_trip_trace.csv
│   └── ... one per scenario
└── graphs/
    ├── ptt_trace.png
    ├── temperature_trip_trace.png
    ├── swr1_trip_trace.png
    ├── swr2_trip_trace.png
    ├── hwfault_trip_trace.png
    ├── current_trip_trace.png
    ├── overdrive_trip_trace.png
    ├── drain_trip_trace.png
    ├── swr1_1p5_trace.png
    ├── freq_ctr_trace.png
    └── freq_ctr_fail_trace.png
```

The PNG traces show digital logic levels for the TX, TX_VCC, and TX_BIAS outputs, sequencer
delay timing, fault detection and latching, and the startup-inhibit period.

The LCD lifecycle diagrams (`graphs/lcd/`) are separate; generate them with
`python3 tools/simulate/render_lcd_lifecycle_diagram.py` and
`python3 tools/simulate/render_display_menu_diagram.py` (requires matplotlib).

## Troubleshooting

### Tests fail instantly with `Bad CPU type in executable`

A stale CMake cache bound `PYTHON_EXECUTABLE` to an unusable interpreter (typically
macOS's `/Library/Frameworks/Python.framework/Versions/2.7/bin/python`). The suite is
Python 3 only. Clear the cached value and reconfigure:

```bash
cmake -S cmake/My_Pic_Project/default -B _build/My_Pic_Project/sim -U PYTHON_EXECUTABLE ...
```

Configuration now fails with an explicit message if the discovered interpreter is not
Python 3, rather than failing the test at run time.

### "mdb not found"

MPLAB X IDE supplies the simulator. `tools/simulate/platform_process.py::find_mdb()` searches the
standard install roots on both OSes and picks the newest MPLAB version; set `MPLABX_MDB` to the
`mdb.bat`/`mdb.sh` path to override it for a non-standard install.

```bash
brew install --cask mplabx-ide                                   # macOS
```

```powershell
# Windows: install MPLAB X IDE from microchip.com; verify it is where the search expects
Test-Path 'C:\Program Files\Microchip\MPLABX\*\mplab_platform\bin\mdb.bat'
```

### Build failures / XC8 not found

```bash
# macOS
brew install --cask mplab-xc8
ls -la "$HOME/tools/microchip/xc8/v4.00/xc8-v4.00/bin"
```

```powershell
# Windows
Test-Path 'C:\Program Files\Microchip\xc8\v4.00\bin\xc8-cc.exe'
```

Pass `-DXC8_BIN_DIR`, `-DCMAKE_C_COMPILER`, `-DCMAKE_ASM_COMPILER`, and `-DCMAKE_AR` as
shown in the macOS manual run above — only needed for a non-standard unpack, since the checked-in
toolchain file detects both the default macOS and Windows locations.

### The run looks hung

Check the heartbeat in the suite progress log (`/tmp` on macOS, `%TEMP%` on Windows). If the
`mdb_bytes` value is still increasing, the simulator is working, just slowly — the trace volume is
large. If MDB output has stopped, kill the tree of the PID recorded in `picampcontrol_suite.pid`
and start a fresh run.

Never reuse a terminal that still has a previous suite command queued.

### Nothing happens at all on Windows

If CTest reports no result and the suite progress log has no `CHILD pid=...` line, the launcher
died before spawning the simulator — that is a harness problem, not a firmware one. The launcher
needs `taskkill` and PowerShell's `Get-CimInstance` for its process scan; both are present on any
supported Windows build, so check the log's last line for the actual error.

### Runtime

The merged suite takes roughly 150 s on macOS and ~356 s on Windows, where MDB is about 2.4x
slower. The watchdog budget is 1200 s - generous on purpose, because a budget-induced timeout on a
healthy run is far more confusing than a slow green run. Slow runs are normal: each scenario
single-steps the simulator to capture detailed state transitions.

## CI

Simulator tests are **not** run in CI — they need MPLAB X `mdb`, which is not installed on
the GitHub runners.

[`.github/workflows/firmware-build.yml`](.github/workflows/firmware-build.yml) runs on
`ubuntu-latest`, installs XC8 v4.00 and the `PIC18F-Q_DFP` pack, builds the Release
firmware, and uploads a `firmware-<sha>` artifact. It compiles only. Run the simulator suite
locally before pushing.
