set_property(TARGET My_Pic_Project_default_default_XC8_compile PROPERTY SOURCES
    "${CMAKE_CURRENT_LIST_DIR}/../../../firmware/src/main.c"
    "${CMAKE_CURRENT_LIST_DIR}/../../../firmware/src/state.c"
    "${CMAKE_CURRENT_LIST_DIR}/../../../firmware/src/init.c"
    "${CMAKE_CURRENT_LIST_DIR}/../../../firmware/src/lcd_parallel.c"
    "${CMAKE_CURRENT_LIST_DIR}/../../../firmware/src/lcd_format.c"
    "${CMAKE_CURRENT_LIST_DIR}/../../../firmware/src/freq_counter.c"
    "${CMAKE_CURRENT_LIST_DIR}/../../../firmware/src/nvm.c"
    "${CMAKE_CURRENT_LIST_DIR}/../../../firmware/src/self_test.c"
    "${CMAKE_CURRENT_LIST_DIR}/../../../firmware/src/outputs.c"
    "${CMAKE_CURRENT_LIST_DIR}/../../../firmware/src/labels.c"
    "${CMAKE_CURRENT_LIST_DIR}/../../../firmware/src/settings.c"
    "${CMAKE_CURRENT_LIST_DIR}/../../../firmware/src/protection.c"
    "${CMAKE_CURRENT_LIST_DIR}/../../../firmware/src/tx_selftest.c"
    "${CMAKE_CURRENT_LIST_DIR}/../../../firmware/src/menu.c"
    "${CMAKE_CURRENT_LIST_DIR}/../../../firmware/src/sequencer.c")

# Include paths for the LANGUAGE SERVERS, not for the build.
#
# XC8's driver is the normal way clangd discovers a toolchain's system includes, and it cannot work
# here: clangd queries it as `xc8-cc -E -v -x c -`, and XC8 answers "(2042) no target device
# specified" because clangd does not forward the `-mcpu=`/`-mdfp=` flags it does not understand. The
# extraction fails, nothing is added to the search path, and the Problems panel fills with
# `'xc.h' file not found` plus ~20 cascading undeclared-register errors (LATCbits, ADCON1, ADPCH,
# NVMCON1bits...) - verified with `clangd --check`, whose log says
#   System include extraction: driver execution failed with return code: 1 - ''
# 2026-09-23.
#
# So state them here, where CMake resolves this machine's paths at configure time and writes them
# into compile_commands.json as plain -I flags that any consumer understands. Every path is DERIVED
# - the compiler's include from ${CMAKE_C_COMPILER}, the pack's from ${PICAMP_DFP_PATH}, which
# device.cmake already resolves per OS (user pack repository vs the MPLAB X install) - so nothing
# OS-specific is committed and Windows resolves its own. Harmless for XC8: it takes -I like any
# compiler, and the build is unaffected either way.
#
# Three directories, for three different reasons:
#   pic/include        the pack's pic18.h / pic18_chip_select.h
#   pic/include/proc   the device header itself: pic18_chip_select.h does `#include
#                      <pic18f47q10.h>` with NO proc/ prefix (verified in the 1.30.487 pack),
#                      because XC8's `-mdfp` normally puts this directory on the search path
#   <compiler>/pic/include  xc.h and the C library headers
#
# THE MACROS ARE THE ACTUAL ROOT CAUSE, and they matter more than the paths. XC8 defines these
# itself, so a build never needs them - but a language server does, and without them the whole
# header chain is inert:
#   __XC8       xc.h's entire body is `#ifdef __XC8`; undefined, xc.h expands to nothing at all
#   __PICC18__  xc.h reaches pic18.h only under `#if defined(__PICC18__)`
#   _18F47Q10   pic18_chip_select.h tests this (single underscores, not __18F47Q10__) before
#               including the device header
# With all three, `LATCbits` and friends exist and the file parses cleanly; without them every
# register is an undeclared identifier while every header is "found" - which is the confusing part.
# Verified by preprocessing xc.h directly, 2026-09-23.
get_filename_component(_picamp_xc8_bin "${CMAKE_C_COMPILER}" DIRECTORY)
get_filename_component(_picamp_xc8_include "${_picamp_xc8_bin}/../pic/include" ABSOLUTE)
target_compile_options(My_Pic_Project_default_default_XC8_compile PRIVATE
    "-D__XC8"
    "-D__PICC18__"
    "-D_18F47Q10"
    "-I${PICAMP_DFP_PATH}/pic/include"
    "-I${PICAMP_DFP_PATH}/pic/include/proc"
    "-I${PICAMP_DFP_PATH}/pic/include/c99"
    "-I${_picamp_xc8_include}"
    "-I${_picamp_xc8_include}/c99")

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
