# Testing Guide

Firmware behaviour is verified in the MPLAB X `mdb` simulator. CTest drives
[`tools/simulate/trace_ptt_sequence.py`](tools/simulate/trace_ptt_sequence.py) against the
built ELF, single-steps the firmware, samples pin state and firmware variables, and asserts
the sequencing, band-locking, and fault-protection behaviour.

A full run takes roughly 2-3 minutes.

## Prerequisites

- MPLAB X IDE 6.x (provides the `mdb` simulator)
- XC8 4.00 toolchain
- Python 3 (the suite is Python 3 only)
- CMake 3.24+ and Ninja

```bash
brew install cmake ninja
brew install --cask mplabx-ide mplab-xc8
```

## Quick start

```bash
./run_tests.sh
```

[`run_tests.sh`](run_tests.sh) configures `_build/My_Pic_Project/sim`, builds the firmware,
then runs CTest.

## Manual run

```bash
cd /Users/stevekerr/mydocs/code/PicAmpControl

cmake -S cmake/My_Pic_Project/default \
  -B _build/My_Pic_Project/sim \
  -G Ninja \
  -DCMAKE_BUILD_TYPE=Debug \
  -DCMAKE_TOOLCHAIN_FILE="$PWD/cmake/My_Pic_Project/default/.generated/toolchain.cmake" \
  -DCMAKE_USER_MAKE_RULES_OVERRIDE="$PWD/cmake/My_Pic_Project/default/.generated/overrides.cmake" \
  -DXC8_BIN_DIR=/Users/stevekerr/tools/microchip/xc8/v4.00/xc8-v4.00/bin \
  -DCMAKE_C_COMPILER=/Users/stevekerr/tools/microchip/xc8/v4.00/xc8-v4.00/bin/xc8-cc \
  -DCMAKE_ASM_COMPILER=/Users/stevekerr/tools/microchip/xc8/v4.00/xc8-v4.00/bin/xc8-cc \
  -DCMAKE_AR=/Users/stevekerr/tools/microchip/xc8/v4.00/xc8-v4.00/bin/xc8-ar \
  -DCMAKE_EXPORT_COMPILE_COMMANDS=ON

cmake --build _build/My_Pic_Project/sim
ctest --test-dir _build/My_Pic_Project/sim --output-on-failure > /tmp/pac_ctest.log 2>&1
```

## Test output goes to files, not the terminal

Every simulator sample prints pins and state variables, so an MDB run produces megabytes of
trace. Printing that to the terminal overflows the scrollback and destroys the pass/fail
line, so always send CTest output to a log file and read the verdict from there.

| File | Contents |
|---|---|
| `/tmp/pac_ctest.log` | CTest verdict (one line per test, discovery, total time) |
| `/tmp/picampcontrol_suite_progress.log` | Suite progress: START/CHILD, 10-second heartbeats, `END code=<n>` |
| `/tmp/picampcontrol_mdb_progress.log` | Raw live MDB output |
| `_build/My_Pic_Project/sim/csv/` | Per-scenario CSV sample dumps |
| `_build/My_Pic_Project/sim/graphs/` | Per-scenario logic-analyzer PNG traces |

A successful run ends with `100% tests passed`, `CTEST_EXIT=0`, and the suite log line
`PTT suite passed: 11 scenarios in one MDB session`.

## Test suite

CTest registers one merged test, `PTT_SequencerAndTripSuite`, in
[`cmake/My_Pic_Project/default/user.cmake`](cmake/My_Pic_Project/default/user.cmake). Its
command is:

```text
python3 tools/simulate/run_suite_with_watchdog.py --timeout 300
```

The launcher runs `trace_ptt_sequence.py --suite` in its own process group, kills stale
runs, records progress logs, and enforces the timeout itself. All eleven scenarios run
inside **one** MDB session, so the run time is dominated by simulator startup and
single-stepping rather than per-scenario overhead.

| # | Scenario | Expected behaviour |
|---|---|---|
| 1 | Baseline PTT cycle | Startup inhibit, then TX → TX_VCC → TX_BIAS in order with the configured delays, then the ordered release |
| 2 | `TEMPERATURE` | Thermal fault during transmit trips and latches |
| 3 | `SWR1` | Pre-filter SWR fault trips |
| 4 | `SWR2` | Post-filter SWR fault trips |
| 5 | `HWFAULT` | Hardware overcurrent comparator fault blocks/trips |
| 6 | `CURRENT` | Software overcurrent trip |
| 7 | `OVERDRIVE` | Overdrive trip |
| 8 | `DRAIN` | Drain-peak trip |
| 9 | `SWR1_1P5` | SWR1 at 1.5:1 and 2 kW must **not** trip |
| 10 | `FREQ_CTR` | Frequency counter classifies all six nominal bands in RX and keeps each band locked through TX injection |
| 11 | `FREQ_CTR_FAIL` | Negative test: a missing Timer1 signal cancels PTT before TX, with no active TX stage and inactive TX outputs |

Each scenario also validates output pin sequencing, fault latching and re-arm behaviour, LCD
status state, and startup-inhibit timing. `FREQ_CTR_FAIL` is intentionally a negative test —
it must never be "fixed" into a passing trip.

### What the band/frequency-counter test does and does not cover

The band scenarios inject Timer1 counts by writing `TMR1H`/`TMR1L` directly, using the
inverse of the firmware's own scaling (`counts = kHz x 1000 / 400`). This is deliberate: the
MPLAB X simulator does not implement Timer1's external clock, so T1CKI edges never increment
TMR1 no matter how the pin is driven.

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
- the no-signal rejection path, including a check that PTT really was asserted

Not covered, and not coverable in simulation:

- the T1CKI pin, its PPS routing, and the Timer1 1:4 prescaler
- the Timer1 overflow path (`g_tmr1_overflows`), because the injected counts fit in 16 bits
- true 10m coverage: a real 10m frequency (28.0-29.7 MHz) needs 70000-74250 counts, beyond a
  single 16-bit TMR1 write, so the 10m case uses 25000 kHz (inside the classifier's wider window)

Bench validation with a real signal generator is required for those.

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
6. Validates sequencing, band locking, and each trip path
7. Writes CSV samples and logic-analyzer PNG traces
8. Exits non-zero on any failed assertion (the message names the scenario and the state)

[`tools/simulate/run_suite_with_watchdog.py`](tools/simulate/run_suite_with_watchdog.py)
wraps that script: it starts it in a new session/process group, records the PID in
`/tmp/picampcontrol_suite.pid`, cleans up stale runs, writes 10-second heartbeats to
`/tmp/picampcontrol_suite_progress.log`, streams MDB output to
`/tmp/picampcontrol_mdb_progress.log`, and kills the whole process group on timeout.

Do not start a second suite while one is running. If a run looks stuck, read the PID file,
terminate that process group, and remove the PID file before starting again.

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

MPLAB X IDE supplies the simulator:

```bash
brew install --cask mplabx-ide
```

### Build failures / XC8 not found

```bash
brew install --cask mplab-xc8
ls -la /Users/stevekerr/tools/microchip/xc8/v4.00/xc8-v4.00/bin
```

Pass `-DXC8_BIN_DIR`, `-DCMAKE_C_COMPILER`, `-DCMAKE_ASM_COMPILER`, and `-DCMAKE_AR` as
shown in the manual run above.

### The run looks hung

Check the heartbeat in `/tmp/picampcontrol_suite_progress.log`. If the `mdb_bytes` value is
still increasing, the simulator is working, just slowly — the trace volume is large. If MDB
output has stopped, kill the process group recorded in `/tmp/picampcontrol_suite.pid` and
start a fresh run.

Never reuse a terminal that still has a previous suite command queued.

### Runtime

The merged suite takes roughly 2-3 minutes on this machine and the full watchdog timeout is
300 s. Slow runs are normal: each scenario single-steps the simulator to capture detailed
state transitions.

## CI

Simulator tests are **not** run in CI — they need MPLAB X `mdb`, which is not installed on
the GitHub runners.

[`.github/workflows/firmware-build.yml`](.github/workflows/firmware-build.yml) runs on
`ubuntu-latest`, installs XC8 v4.00 and the `PIC16F1xxxx_DFP` pack, builds the Release
firmware, and uploads a `firmware-<sha>` artifact. It compiles only. Run the simulator suite
locally before pushing.
