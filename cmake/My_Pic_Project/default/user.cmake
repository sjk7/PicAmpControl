set_property(TARGET My_Pic_Project_default_default_XC8_compile PROPERTY SOURCES
    "${CMAKE_CURRENT_LIST_DIR}/../../../firmware/src/main.c"
    "${CMAKE_CURRENT_LIST_DIR}/../../../firmware/src/lcd_parallel.c"
    "${CMAKE_CURRENT_LIST_DIR}/../../../firmware/src/freq_counter.c")

# Optimize Debug builds with -O1 to avoid XC8 -O0 string section code bloat, and Release with -Os.
target_compile_options(My_Pic_Project_default_default_XC8_compile PRIVATE "$<$<CONFIG:Debug>:-O1>" "$<$<CONFIG:Release>:-Os>")
target_link_options(My_Pic_Project_default_image_LRxgA9DB PRIVATE "$<$<CONFIG:Debug>:-O1>" "$<$<CONFIG:Release>:-Os>")

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
set(PICAMP_SUITE_LAUNCHER "${CMAKE_CURRENT_LIST_DIR}/../../../tools/simulate/run_suite_with_watchdog.py")
add_test(
    NAME PTT_SequencerAndTripSuite
    COMMAND "${PYTHON_EXECUTABLE}" "${PICAMP_SUITE_LAUNCHER}" --timeout 300)
set_tests_properties(PTT_SequencerAndTripSuite PROPERTIES LABELS "sim;suite")

# The first-dit band-detection proof runs as its own MDB session. Its stimulus (band snoop,
# warm re-key from the remembered band, cache expiry, and a hot-switch fault injection) is
# long enough that folding it into the merged suite would roughly double that suite's
# runtime, so it stays a separate test. See tools/simulate/test_first_dit.py.
add_test(
    NAME FirstDit_BandDetectionAndHotSwitchGuards
    COMMAND "${PYTHON_EXECUTABLE}"
            "${CMAKE_CURRENT_LIST_DIR}/../../../tools/simulate/test_first_dit.py")
set_tests_properties(FirstDit_BandDetectionAndHotSwitchGuards
    PROPERTIES LABELS "sim;first-dit")
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
