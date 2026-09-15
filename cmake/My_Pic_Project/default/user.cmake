set_property(TARGET My_Pic_Project_default_default_XC8_compile PROPERTY SOURCES
    "${CMAKE_CURRENT_LIST_DIR}/../../../firmware/src/main.c"
    "${CMAKE_CURRENT_LIST_DIR}/../../../firmware/src/lcd_i2c.c")

# Only optimize Release builds; -Os after Debug's -O0 would win (last -O flag wins) and
# defeat breakpoints/symbols needed for simulation and debugging.
target_compile_options(My_Pic_Project_default_default_XC8_compile PRIVATE "$<$<CONFIG:Release>:-Os>")
target_link_options(My_Pic_Project_default_image_LRxgA9DB PRIVATE "$<$<CONFIG:Release>:-Os>")
