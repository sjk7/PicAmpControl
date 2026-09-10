# The following variables contains the files used by the different stages of the build process.
set(My_Pic_Project_default_default_XC8_FILE_TYPE_assemble)
set_source_files_properties(${My_Pic_Project_default_default_XC8_FILE_TYPE_assemble} PROPERTIES LANGUAGE ASM)

# For assembly files, add "." to the include path for each file so that .include with a relative path works
foreach(source_file ${My_Pic_Project_default_default_XC8_FILE_TYPE_assemble})
        set_source_files_properties(${source_file} PROPERTIES INCLUDE_DIRECTORIES "$<PATH:NORMAL_PATH,$<PATH:REMOVE_FILENAME,${source_file}>>")
endforeach()

set(My_Pic_Project_default_default_XC8_FILE_TYPE_assemblePreprocess)
set_source_files_properties(${My_Pic_Project_default_default_XC8_FILE_TYPE_assemblePreprocess} PROPERTIES LANGUAGE ASM)

# For assembly files, add "." to the include path for each file so that .include with a relative path works
foreach(source_file ${My_Pic_Project_default_default_XC8_FILE_TYPE_assemblePreprocess})
        set_source_files_properties(${source_file} PROPERTIES INCLUDE_DIRECTORIES "$<PATH:NORMAL_PATH,$<PATH:REMOVE_FILENAME,${source_file}>>")
endforeach()

set(My_Pic_Project_default_default_XC8_FILE_TYPE_compile
    "${CMAKE_CURRENT_SOURCE_DIR}/../../../firmware/src/lcd_i2c.c"
    "${CMAKE_CURRENT_SOURCE_DIR}/../../../firmware/src/main.c")
set_source_files_properties(${My_Pic_Project_default_default_XC8_FILE_TYPE_compile} PROPERTIES LANGUAGE C)
set(My_Pic_Project_default_default_XC8_FILE_TYPE_link)
set(My_Pic_Project_default_image_name "default.elf")
set(My_Pic_Project_default_image_base_name "default")

# The output directory of the final image.
set(My_Pic_Project_default_output_dir "${CMAKE_CURRENT_SOURCE_DIR}/../../../out/My_Pic_Project")

# The full path to the final image.
set(My_Pic_Project_default_full_path_to_image ${My_Pic_Project_default_output_dir}/${My_Pic_Project_default_image_name})

# Potential output file extensions
set(output_extensions
    .hex
    .hxl
    .mum
    .o
    .sdb
    .sym
    .cmf)
list(TRANSFORM output_extensions PREPEND "${My_Pic_Project_default_output_dir}/${My_Pic_Project_default_image_base_name}")
