# The following variables contains the files used by the different stages of the build process.
set(PicAmpControl_default_default_XC8_FILE_TYPE_assemble)
set_source_files_properties(${PicAmpControl_default_default_XC8_FILE_TYPE_assemble} PROPERTIES LANGUAGE ASM)

# For assembly files, add "." to the include path for each file so that .include with a relative path works
foreach(source_file ${PicAmpControl_default_default_XC8_FILE_TYPE_assemble})
        set_source_files_properties(${source_file} PROPERTIES INCLUDE_DIRECTORIES "$<PATH:NORMAL_PATH,$<PATH:REMOVE_FILENAME,${source_file}>>")
endforeach()

set(PicAmpControl_default_default_XC8_FILE_TYPE_assemblePreprocess)
set_source_files_properties(${PicAmpControl_default_default_XC8_FILE_TYPE_assemblePreprocess} PROPERTIES LANGUAGE ASM)

# For assembly files, add "." to the include path for each file so that .include with a relative path works
foreach(source_file ${PicAmpControl_default_default_XC8_FILE_TYPE_assemblePreprocess})
        set_source_files_properties(${source_file} PROPERTIES INCLUDE_DIRECTORIES "$<PATH:NORMAL_PATH,$<PATH:REMOVE_FILENAME,${source_file}>>")
endforeach()

set(PicAmpControl_default_default_XC8_FILE_TYPE_compile
    "${CMAKE_CURRENT_SOURCE_DIR}/../../../docs/hardware/q10-bringup/clock_only_probe.c"
    "${CMAKE_CURRENT_SOURCE_DIR}/../../../docs/hardware/q10-bringup/q10_probe.c"
    "${CMAKE_CURRENT_SOURCE_DIR}/../../../docs/hardware/q10-bringup/temp_probe.c"
    "${CMAKE_CURRENT_SOURCE_DIR}/../../../firmware/src/freq_counter.c"
    "${CMAKE_CURRENT_SOURCE_DIR}/../../../firmware/src/lcd_parallel.c"
    "${CMAKE_CURRENT_SOURCE_DIR}/../../../firmware/src/main.c"
    "${CMAKE_CURRENT_SOURCE_DIR}/../../../firmware/src/nvm.c"
    "${CMAKE_CURRENT_SOURCE_DIR}/../../../main.c")
set_source_files_properties(${PicAmpControl_default_default_XC8_FILE_TYPE_compile} PROPERTIES LANGUAGE C)
set(PicAmpControl_default_default_XC8_FILE_TYPE_link)
set(PicAmpControl_default_image_name "default.elf")
set(PicAmpControl_default_image_base_name "default")

# The output directory of the final image.
set(PicAmpControl_default_output_dir "${CMAKE_CURRENT_SOURCE_DIR}/../../../out/PicAmpControl")

# The full path to the final image.
set(PicAmpControl_default_full_path_to_image ${PicAmpControl_default_output_dir}/${PicAmpControl_default_image_name})

# Potential output file extensions
set(output_extensions
    .hex
    .hxl
    .mum
    .o
    .sdb
    .sym
    .cmf)
list(TRANSFORM output_extensions PREPEND "${PicAmpControl_default_output_dir}/${PicAmpControl_default_image_base_name}")
