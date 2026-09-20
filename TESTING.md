# Testing Guide

This project uses CTest to run simulator-based tests that validate the firmware state machine, sequencing logic, and fault protection behavior.

## Running Tests Locally

### Prerequisites

- MPLAB X IDE (with `mdb` simulator)
- XC8 compiler
- Python 3
- CMake 3.24+
- Ninja build tool

Install via Homebrew:
```bash
brew install cmake ninja
brew install --cask mplabx-ide mplab-xc8
```

### Quick Start

Run all tests:
```bash
cd /Users/stevekerr/mydocs/code/PicAmpControl
./run_tests.sh
```

Or manually:
```bash
cd /Users/stevekerr/mydocs/code/PicAmpControl

# Configure the build
cmake -S cmake/My_Pic_Project/default \
  -B _build/My_Pic_Project/sim \
  -G Ninja \
  -DCMAKE_BUILD_TYPE=Debug \
  -DCMAKE_TOOLCHAIN_FILE="$(pwd)/cmake/My_Pic_Project/default/.generated/toolchain.cmake" \
  -DCMAKE_USER_MAKE_RULES_OVERRIDE="$(pwd)/cmake/My_Pic_Project/default/.generated/overrides.cmake" \
  -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
  -DPYTHON_EXECUTABLE=$(which python3)

# Build the firmware
cmake --build _build/My_Pic_Project/sim

# Run tests via CTest
cd _build/My_Pic_Project/sim
ctest --output-on-failure
```

## Test Suite

The default test suite (`PTT_SequencerAndTripSuite`) runs comprehensive simulation scenarios:

- **Boot sequence**: Startup inhibit and initialization
- **PTT active-low sequencing**: Normal TX activation and shutdown
- **Temperature trip**: Thermal protection during transmission
- **SWR trips**: Standing wave ratio fault detection (SWR1 and SWR2)
- **Frequency counter band lock**: Timer1 frequency measurement in RX and strict band-locking during TX
- **Hardware fault**: Comparator-based overcurrent protection
- **Current trip**: Software-based overcurrent detection
- **Overdrive trip**: RF overdrive protection
- **Drain trip**: Drain current protection

Each scenario validates:
- Correct output pin sequencing (TX, TX_VCC, TX_BIAS)
- Proper fault latching and reset behavior
- LCD status display state
- Startup inhibit timing

## Individual Tests

To run individual test scenarios instead of the full suite, configure with:
```bash
-DPICAMP_ENABLE_INDIVIDUAL_SIM_TESTS=ON
```

Then run with CTest:
```bash
ctest -R "PTT_TemperatureTrip" --output-on-failure
```

Available individual tests:
- `PTT_ActiveLow_StartupAndReleaseSequence`
- `PTT_TemperatureTrip_InTransmit`
- `PTT_SWR1_1P5_NoTrip_At2kW`
- `PTT_FrequencyCounter_BandLock`
- `PTT_SWR1Trip_InTransmit`
- `PTT_SWR2Trip_InTransmit`
- `PTT_HWFAULTTrip_InTransmit`
- `PTT_CURRENTTrip_InTransmit`
- `PTT_OVERDRIVETrip_InTransmit`
- `PTT_DRAINTrip_InTransmit`

## Test Implementation

Tests are implemented in [`tools/simulate/trace_ptt_sequence.py`](tools/simulate/trace_ptt_sequence.py), which:

1. Builds the firmware via CMake/Ninja
2. Launches MPLAB X `mdb` simulator with the compiled ELF
3. Single-steps through firmware execution
4. Samples pin states and firmware variables at ~2ms intervals
5. Renders logic-analyzer-style PNG trace diagrams
6. Validates expected sequencing behavior
7. Exits with non-zero code if any checks fail

The test script is registered with CMake in [`cmake/My_Pic_Project/default/user.cmake`](cmake/My_Pic_Project/default/user.cmake).

## Generated Trace Diagrams

Test runs generate scope-like trace diagrams saved to:
```
_build/My_Pic_Project/sim/
  ├── trace_ptt_active_low.png          # PTT assertion/release timing
  ├── trace_temp_trip.png               # Temperature trip response
  ├── trace_swr1_trip.png               # SWR1 fault detection
  └── [other scenario traces...]
```

These PNG files show:
- Digital logic levels for TX, TX_VCC, TX_BIAS, and SETTLE pins
- Timing of sequencer delays (typically 10-20ms)
- Fault detection and latching behavior
- Startup inhibit period (~1000ms)

## Troubleshooting

### "mdb not found" errors
Ensure MPLAB X IDE is installed:
```bash
brew install --cask mplabx-ide
```

### Python version errors
The test script requires Python 3. If you see "python: command not found":
```bash
# Use explicit Python path during CMake configuration
-DPYTHON_EXECUTABLE=$(which python3)
```

### Build failures
Verify XC8 compiler is installed:
```bash
brew install --cask mplab-xc8
```

Check compiler availability:
```bash
ls -la /Users/stevekerr/tools/microchip/xc8/
```

### Slow test execution
Tests run sequentially and can take 2-5 minutes depending on system load. Each scenario runs multiple simulator steps to capture detailed state transitions. This is normal.

## CI/CD Integration

Tests run automatically in GitHub Actions on every push to `main`:
- Workflow: [`.github/workflows/firmware-build.yml`](.github/workflows/firmware-build.yml)
- Uses Ubuntu runner with MPLAB X installed via apt
- Fails the build if any test scenario fails
