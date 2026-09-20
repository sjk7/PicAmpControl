set_property(TARGET My_Pic_Project_default_default_XC8_compile PROPERTY SOURCES
    "${CMAKE_CURRENT_LIST_DIR}/../../../firmware/src/main.c"
    "${CMAKE_CURRENT_LIST_DIR}/../../../firmware/src/lcd_parallel.c"
    "${CMAKE_CURRENT_LIST_DIR}/../../../firmware/src/freq_counter.c")

# Optimize Debug builds with -O1 to avoid XC8 -O0 string section code bloat, and Release with -Os.
target_compile_options(My_Pic_Project_default_default_XC8_compile PRIVATE "$<$<CONFIG:Debug>:-O1>" "$<$<CONFIG:Release>:-Os>")
target_link_options(My_Pic_Project_default_image_LRxgA9DB PRIVATE "$<$<CONFIG:Debug>:-O1>" "$<$<CONFIG:Release>:-Os>")

enable_testing()
find_program(PYTHON_EXECUTABLE NAMES python python3 REQUIRED)
add_test(
    NAME PTT_SequencerAndTripSuite
    COMMAND timeout 300 "${PYTHON_EXECUTABLE}"
            "${CMAKE_CURRENT_LIST_DIR}/../../../tools/simulate/trace_ptt_sequence.py"
            --suite)
add_test(
    NAME PTT_FrequencyCounter_BandLock
    COMMAND timeout 60 "${PYTHON_EXECUTABLE}"
            "${CMAKE_CURRENT_LIST_DIR}/../../../tools/simulate/test_freq_counter.py")

option(PICAMP_ENABLE_INDIVIDUAL_SIM_TESTS "Register each simulator scenario separately" OFF)
if (PICAMP_ENABLE_INDIVIDUAL_SIM_TESTS)
    add_test(
        NAME PTT_ActiveLow_StartupAndReleaseSequence
        COMMAND timeout 120 "${PYTHON_EXECUTABLE}"
                "${CMAKE_CURRENT_LIST_DIR}/../../../tools/simulate/trace_ptt_sequence.py"
                --test)
    add_test(
        NAME PTT_TemperatureTrip_InTransmit
        COMMAND timeout 120 "${PYTHON_EXECUTABLE}"
                "${CMAKE_CURRENT_LIST_DIR}/../../../tools/simulate/trace_ptt_sequence.py"
                --temperature-trip)
    add_test(
        NAME PTT_SWR1_1P5_NoTrip_At2kW
        COMMAND timeout 120 "${PYTHON_EXECUTABLE}"
                "${CMAKE_CURRENT_LIST_DIR}/../../../tools/simulate/trace_ptt_sequence.py"
                --swr1-1p5)
    foreach(TRIP_NAME SWR1 SWR2 HWFAULT CURRENT OVERDRIVE DRAIN)
        add_test(
            NAME PTT_${TRIP_NAME}Trip_InTransmit
            COMMAND timeout 120 "${PYTHON_EXECUTABLE}"
                    "${CMAKE_CURRENT_LIST_DIR}/../../../tools/simulate/trace_ptt_sequence.py"
                    --trip ${TRIP_NAME})
    endforeach()
endif()
