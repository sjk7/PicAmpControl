set_property(TARGET My_Pic_Project_default_default_XC8_compile PROPERTY SOURCES
    "${CMAKE_CURRENT_LIST_DIR}/../../../firmware/src/main.c"
    "${CMAKE_CURRENT_LIST_DIR}/../../../firmware/src/lcd_i2c.c")

target_compile_options(My_Pic_Project_default_default_XC8_compile PRIVATE "-Os")
target_link_options(My_Pic_Project_default_image_LRxgA9DB PRIVATE "-Os")
