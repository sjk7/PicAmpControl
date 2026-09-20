set_property(TARGET My_Pic_Project_default_default_XC8_compile PROPERTY SOURCES
    "${CMAKE_CURRENT_LIST_DIR}/../../../firmware/src/main.c"
    "${CMAKE_CURRENT_LIST_DIR}/../../../firmware/src/lcd_parallel.c")

# Only optimize Release builds; -Os after Debug's -O0 would win (last -O flag wins) and
# defeat breakpoints/symbols needed for simulation and debugging.
target_compile_options(My_Pic_Project_default_default_XC8_compile PRIVATE "$<$<CONFIG:Release>:-Os>")
target_link_options(My_Pic_Project_default_image_LRxgA9DB PRIVATE "$<$<CONFIG:Release>:-Os>")

enable_testing()
find_program(PYTHON_EXECUTABLE NAMES python python3 REQUIRED)
add_test(
    NAME PTT_SequencerAndTripSuite
    COMMAND "${PYTHON_EXECUTABLE}"
            "${CMAKE_CURRENT_LIST_DIR}/../../../tools/simulate/trace_ptt_sequence.py"
            --suite)

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
