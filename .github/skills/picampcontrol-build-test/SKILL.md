---
name: picampcontrol-build-test
description: "Use when building or testing PicAmpControl firmware: Debug or Release builds, CMake configuration, ctest, run_tests.sh, simulator runs, PTT/frequency-counter tests, band-lock tests, or build/test failures."
---

# PicAmpControl Build and Test

Use this skill for firmware builds and simulator verification. Do not claim success from a missing or truncated terminal response; require a fresh exit code and final output.

Always clean up an earlier run before starting another. The MDB suite can outlive a terminal wrapper if the wrapper is interrupted, and a stale Java/MDB process can make the next run appear hung.

## Repository facts

- CMake source directory: `cmake/My_Pic_Project/default`
- Debug build directory: `_build/My_Pic_Project/debug`
- Release build directory: `_build/My_Pic_Project/release`
- Firmware ELF used by MDB: `out/My_Pic_Project/default.elf`
- Merged simulator suite: `tools/simulate/trace_ptt_sequence.py --suite`
- Cleanup-aware suite launcher: `tools/simulate/run_suite_with_watchdog.py`
- CTest registration: `cmake/My_Pic_Project/default/user.cmake`
- The standalone `test_freq_counter.py` is not the authoritative suite; frequency and band checks are merged into the PTT suite.

## Toolchain setup

On macOS, use the installed XC8 toolchain:

```text
/Users/stevekerr/tools/microchip/xc8/v4.00/xc8-v4.00/bin
```

Before building, check that `xc8-cc` exists. Existing build caches may contain the invalid compiler value `c`; explicitly override the compiler paths when reconfiguring. The repository root has no `CMakeLists.txt`, so do not configure with `cmake --preset` from the root unless the preset is first corrected to specify the nested source directory.

## Debug build

```sh
cmake -S cmake/My_Pic_Project/default \
  -B _build/My_Pic_Project/debug \
  -G Ninja \
  -DCMAKE_BUILD_TYPE=Debug \
  -DCMAKE_TOOLCHAIN_FILE="$PWD/cmake/My_Pic_Project/default/.generated/toolchain.cmake" \
  -DCMAKE_USER_MAKE_RULES_OVERRIDE="$PWD/cmake/My_Pic_Project/default/.generated/overrides.cmake" \
  -DXC8_BIN_DIR=/Users/stevekerr/tools/microchip/xc8/v4.00/xc8-v4.00/bin \
  -DCMAKE_C_COMPILER=/Users/stevekerr/tools/microchip/xc8/v4.00/xc8-v4.00/bin/xc8-cc \
  -DCMAKE_ASM_COMPILER=/Users/stevekerr/tools/microchip/xc8/v4.00/xc8-v4.00/bin/xc8-cc \
  -DCMAKE_AR=/Users/stevekerr/tools/microchip/xc8/v4.00/xc8-v4.00/bin/xc8-ar \
  -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
cmake --build _build/My_Pic_Project/debug -j4
```

## Release build

Use the same configure command with:

```text
-B _build/My_Pic_Project/release -DCMAKE_BUILD_TYPE=Release
```

Then run:

```sh
cmake --build _build/My_Pic_Project/release -j4
```

## Simulator verification

Run the full merged suite with the cleanup-aware launcher. This is the default test workflow: it records its PID, kills a stale prior launcher, owns the MDB process group, logs raw MDB stderr, records 10-second progress heartbeats, and cleans up on timeout or Ctrl-C:

```sh
python3 tools/simulate/run_suite_with_watchdog.py --timeout 180
```

Use the full five-minute default verification before calling the suite green:

```sh
python3 tools/simulate/run_suite_with_watchdog.py --timeout 300
```

For a fast diagnostic run only, use one happy band plus the deliberate missing-frequency failure case:

```sh
python3 tools/simulate/run_suite_with_watchdog.py --quick-bands --timeout 180
```

This is diagnostic only. The default command remains the full six-band suite.

Start this command in a fresh VS Code terminal/execution context. The launcher creates a new process group for the suite, so the caller can be interrupted without attaching the next run to an old MDB process. Do not reuse a terminal that still has a prior suite command queued.

Progress is written to `/tmp/picampcontrol_suite_progress.log`; live MDB output is written to `/tmp/picampcontrol_mdb_progress.log`.

The launcher owns `/tmp/picampcontrol_suite.pid` and also scans for orphaned `mdb`, `run_suite_with_watchdog.py`, and `trace_ptt_sequence.py --suite` processes at startup. Before manually killing a run, read that PID and terminate the process group, then remove the PID file. Verify no `trace_ptt_sequence.py --suite` or `mdb.sh` process remains before starting another run. Do not kill unrelated compiler language servers or system Java processes.

The live MDB log is intentionally separate from the suite result log. MDB produces a large amount of trace output because every simulator sample prints pins and state variables. During a long run, inspect both logs:

```sh
tail -n 20 /tmp/picampcontrol_suite_progress.log
tail -n 20 /tmp/picampcontrol_mdb_progress.log
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
- `FREQ_CTR_FAIL`, where no Timer1 signal must cancel PTT before TX

For a bounded run:

```sh
timeout 150 python3 -u tools/simulate/trace_ptt_sequence.py --suite
```

Do not launch another suite while this launcher is running. If an old run exists, starting the launcher cleans it up through `/tmp/picampcontrol_suite.pid`. A terminal response with exit `130`, `142`, no output, or an empty log is not a pass; inspect the saved logs and process state.

## CTest

The registered `PTT_SequencerAndTripSuite` test runs the merged suite through
`run_suite_with_watchdog.py`, so it owns the MDB process group, cleans up stale runs, and
enforces its own timeout without depending on the non-standard macOS `timeout` binary.
The suite is Python 3 only: configuration fails fast if the discovered interpreter is not
Python 3, and `PYTHON_EXECUTABLE` may be stale in an existing cache, so clear it with
`-U PYTHON_EXECUTABLE` when reconfiguring.

Run CTest with **all output redirected to a log file**. The MDB trace is megabytes of pin
and state dump; printing it to the terminal overflows the scrollback and loses the result.

```sh
ctest --test-dir _build/My_Pic_Project/debug --output-on-failure > /tmp/pac_ctest.log 2>&1
echo "CTEST_EXIT=$?" >> /tmp/pac_ctest.log
```

Run that detached (or let it finish) and read the verdict from `/tmp/pac_ctest.log`. Do not
re-run another suite while one is active, and do not reuse a terminal that still has a prior
ctest/suite command queued.

Confirm that CTest discovers the merged `PTT_SequencerAndTripSuite` test
(`ctest --test-dir _build/My_Pic_Project/debug -N`). Report zero discovered tests as a
configuration failure, not success.

## Failure triage

- `Frequency counter failed to classify ...`: inspect the scenario name, `FREQ_DEBUG` lines, Timer1 writes, measured `frequency_khz`, `current_band`, `band_locked`, PTT state, and sequence stage.
- `did not clear and re-enter TX after a PTT re-arm`: check that the re-arm stimulus writes a valid Timer1 count after the new frequency-validity gate; fault scenarios must not reassert PTT with frequency `0`.
- `FREQ_CTR_FAIL` must remain a negative test and must prove no active TX stage and inactive TX outputs.
- MDB output ending without a final validator line is inconclusive; inspect the saved log and process table.
- Keep source fixes separate from test-harness timing fixes. Re-run the narrow failing scenario first, then the full suite.
- If the terminal wrapper reports a command as finished while the PID file remains, the run is still active or the wrapper lost control of it. Kill the recorded process group before doing anything else.

## Reporting

Report:

1. Debug and Release build exit status and important compiler/linker warnings.
2. CTest test discovery and result.
3. Merged suite exit status, elapsed time, and final pass/fail line.
4. The first failing scenario and its diagnostic state, if any.

Never say all tests are green unless Debug/Release and the requested test command have fresh successful exit codes.
