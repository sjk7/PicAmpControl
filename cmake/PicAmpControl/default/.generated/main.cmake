include("${CMAKE_CURRENT_LIST_DIR}/rule.cmake")
include("${CMAKE_CURRENT_LIST_DIR}/file.cmake")

set(PicAmpControl_default_library_list )

# Handle files with suffix (s|as|asm|AS|ASM|As|aS|Asm), for group default-XC8
if(PicAmpControl_default_default_XC8_FILE_TYPE_assemble)
add_library(PicAmpControl_default_default_XC8_assemble OBJECT ${PicAmpControl_default_default_XC8_FILE_TYPE_assemble})
    PicAmpControl_default_default_XC8_assemble_rule(PicAmpControl_default_default_XC8_assemble)
    list(APPEND PicAmpControl_default_library_list "$<TARGET_OBJECTS:PicAmpControl_default_default_XC8_assemble>")

endif()

# Handle files with suffix S, for group default-XC8
if(PicAmpControl_default_default_XC8_FILE_TYPE_assemblePreprocess)
add_library(PicAmpControl_default_default_XC8_assemblePreprocess OBJECT ${PicAmpControl_default_default_XC8_FILE_TYPE_assemblePreprocess})
    PicAmpControl_default_default_XC8_assemblePreprocess_rule(PicAmpControl_default_default_XC8_assemblePreprocess)
    list(APPEND PicAmpControl_default_library_list "$<TARGET_OBJECTS:PicAmpControl_default_default_XC8_assemblePreprocess>")

endif()

# Handle files with suffix [cC], for group default-XC8
if(PicAmpControl_default_default_XC8_FILE_TYPE_compile)
add_library(PicAmpControl_default_default_XC8_compile OBJECT ${PicAmpControl_default_default_XC8_FILE_TYPE_compile})
    PicAmpControl_default_default_XC8_compile_rule(PicAmpControl_default_default_XC8_compile)
    list(APPEND PicAmpControl_default_library_list "$<TARGET_OBJECTS:PicAmpControl_default_default_XC8_compile>")

endif()


# Main target for this project
add_executable(PicAmpControl_default_image_ClMxQJv6 ${PicAmpControl_default_library_list})

set_target_properties(PicAmpControl_default_image_ClMxQJv6 PROPERTIES
    OUTPUT_NAME "default"
    SUFFIX ".elf"
    ADDITIONAL_CLEAN_FILES "${output_extensions}"
    RUNTIME_OUTPUT_DIRECTORY "${PicAmpControl_default_output_dir}")
target_link_libraries(PicAmpControl_default_image_ClMxQJv6 PRIVATE ${PicAmpControl_default_default_XC8_FILE_TYPE_link})
# Add the link options from the rule file.
PicAmpControl_default_link_rule( PicAmpControl_default_image_ClMxQJv6)



