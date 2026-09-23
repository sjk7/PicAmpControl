set_property(TARGET My_Pic_Project_default_default_XC8_compile PROPERTY SOURCES
    "${CMAKE_CURRENT_LIST_DIR}/../../../firmware/src/main.c"
    "${CMAKE_CURRENT_LIST_DIR}/../../../firmware/src/lcd_parallel.c"
    "${CMAKE_CURRENT_LIST_DIR}/../../../firmware/src/freq_counter.c"
    "${CMAKE_CURRENT_LIST_DIR}/../../../firmware/src/nvm.c")

# Optimisation policy (PIC18F47Q10 only).
#
# 8.5% of flash in Release, so there is no bloat problem to work around and no reason to pay for
# it. Release is the default configuration on this device and is FULLY OPTIMISED (-Os)
# while keeping complete symbols through -gdwarf-3 - verified 2026-09-22 by reading every symbol
# the harnesses depend on (g_state, g_fc_status, g_ptt_active, g_sequence_stage, g_band_cache_*,
# g_fault_latched, g_snoop_active) straight out of the Release `default.sym`. The suite therefore
# runs at full speed on Q10; Debug exists only to chase a known problem.
#
# So: Q10 Release = optimised + symbol-complete + fast. Do not re-introduce -O1 for Q10 "to be
# safe" - it would only slow the suite down for a constraint that does not apply here.
target_compile_options(My_Pic_Project_default_default_XC8_compile PRIVATE
    "$<$<CONFIG:Debug>:-O1>" "$<$<CONFIG:Release>:-Os>")
target_link_options(My_Pic_Project_default_image_LRxgA9DB PRIVATE
    "$<$<CONFIG:Debug>:-O1>" "$<$<CONFIG:Release>:-Os>")
# Build the LCD transport with -Os even in Debug. Debug carries -O1 (not -Os) only so MDB can
# resolve symbols and breakpoints, and the simulator harnesses read globals that live in main.c
# and freq_counter.c - never in lcd_parallel.c - so this file does not need the -O1 encoding for
# anything the tests depend on. Release is -Os throughout anyway.
# Trade accepted: function/static symbol resolution *inside* lcd_parallel.c is weaker in the Debug
# image, so breakpointing the LCD driver itself is harder. The sequencer, protection and band
# logic - the code the harnesses step through and that the safety argument rests on - is untouched.
set_source_files_properties(
    "${CMAKE_CURRENT_LIST_DIR}/../../../firmware/src/lcd_parallel.c"
    PROPERTIES COMPILE_OPTIONS "$<$<CONFIG:Debug>:-Os>")
enable_testing()

# The simulator suite is Python 3 only. Search for python3 first and verify the
# interpreter at configure time, so a `python` that resolves to Python 2 (common on
# macOS) fails the configure step instead of silently failing the test at run time.
find_program(PYTHON_EXECUTABLE NAMES python3 python REQUIRED)
execute_process(
    COMMAND "${PYTHON_EXECUTABLE}" -c "import sys; sys.exit(0 if sys.version_info[0] == 3 else 1)"
    RESULT_VARIABLE PICAMP_PYTHON3_CHECK)
if (NOT PICAMP_PYTHON3_CHECK EQUAL 0)
    message(FATAL_ERROR
        "Python 3 is required for the simulator suite, but '${PYTHON_EXECUTABLE}' is not Python 3. "
        "Reconfigure with -DPYTHON_EXECUTABLE=/path/to/python3.")
endif()

# Run the merged suite through the cleanup-aware launcher. It owns the MDB process
# group, kills stale runs, records progress logs, and enforces its own timeout, so the
# test does not depend on the non-standard macOS `timeout` binary.
# The budget is sized for the slowest supported host: MDB is ~2.4x slower on Windows
# than macOS (measured 2026-09-22 - suite 356 s vs ~150 s), and the earlier 280 s bound
# killed a healthy Windows run mid-flight. Do not shrink it back to a macOS-sized
# number - a too-small value fails the test on a healthy run, which reads as a firmware
# regression.
set(PICAMP_SUITE_LAUNCHER "${CMAKE_CURRENT_LIST_DIR}/../../../tools/simulate/run_suite_with_watchdog.py")
set(PICAMP_SUITE_TIMEOUT 1200)
# Both simulator tests go through the same watchdog launcher so that they append to a single
# progress log: the reader watching that log sees the suite finish and the first-dit proof
# begin, with the running test named on every line (user request, 2026-09-22).
set(PICAMP_FIRST_DIT_TIMEOUT 600)
add_test(
    NAME PTT_SequencerAndTripSuite
    COMMAND "${PYTHON_EXECUTABLE}" "${PICAMP_SUITE_LAUNCHER}" --timeout ${PICAMP_SUITE_TIMEOUT})
set_tests_properties(PTT_SequencerAndTripSuite PROPERTIES LABELS "sim;suite")
# CTest's own default timeout is 1500 s, which would mask the launcher's diagnosis if the
# launcher ever wedged, so both bounds are stated and the outer one is the launcher's.
set_tests_properties(PTT_SequencerAndTripSuite PROPERTIES TIMEOUT 1500)

# The first-dit band-detection proof runs as its own MDB session. Its stimulus (band snoop,
# warm re-key from the remembered band, cache expiry, and a hot-switch fault injection) is
# long enough that folding it into the merged suite would roughly double that suite's
# runtime, so it stays a separate test. See tools/simulate/test_first_dit.py.
add_test(
    NAME FirstDit_BandDetectionAndHotSwitchGuards
    COMMAND "${PYTHON_EXECUTABLE}" "${PICAMP_SUITE_LAUNCHER}"
            --test first-dit --timeout ${PICAMP_FIRST_DIT_TIMEOUT})
set_tests_properties(FirstDit_BandDetectionAndHotSwitchGuards
    PROPERTIES LABELS "sim;first-dit")
set_tests_properties(FirstDit_BandDetectionAndHotSwitchGuards PROPERTIES TIMEOUT 900)
option(PICAMP_ENABLE_INDIVIDUAL_SIM_TESTS "Register each simulator scenario separately" OFF)
if (PICAMP_ENABLE_INDIVIDUAL_SIM_TESTS)
    add_test(
        NAME PTT_ActiveLow_StartupAndReleaseSequence
        COMMAND "${PYTHON_EXECUTABLE}"
                "${CMAKE_CURRENT_LIST_DIR}/../../../tools/simulate/trace_ptt_sequence.py"
                --test)
    add_test(
        NAME PTT_TemperatureTrip_InTransmit
        COMMAND "${PYTHON_EXECUTABLE}"
                "${CMAKE_CURRENT_LIST_DIR}/../../../tools/simulate/trace_ptt_sequence.py"
                --temperature-trip)
    add_test(
        NAME PTT_SWR1_1P5_NoTrip_At2kW
        COMMAND "${PYTHON_EXECUTABLE}"
                "${CMAKE_CURRENT_LIST_DIR}/../../../tools/simulate/trace_ptt_sequence.py"
                --swr1-1p5)
    foreach(TRIP_NAME SWR1 SWR2 HWFAULT CURRENT OVERDRIVE DRAIN)
        add_test(
            NAME PTT_${TRIP_NAME}Trip_InTransmit
            COMMAND "${PYTHON_EXECUTABLE}"
                    "${CMAKE_CURRENT_LIST_DIR}/../../../tools/simulate/trace_ptt_sequence.py"
                    --trip ${TRIP_NAME})
    endforeach()
endif()
