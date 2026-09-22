# DEVICE SELECTION (hand-edited by tools/setup/parameterise_device.py, 2026-09-22).
# The device tokens below are CMake variables from device.cmake, so this one tree builds either
# the PIC16F18875 or the PIC18F47Q10 image. See device.cmake for why a generated file is edited
# here, and for the flash/RAM asymmetry between the two parts.
include("${CMAKE_CURRENT_LIST_DIR}/../device.cmake")

# The following functions contains all the flags passed to the different build stages.

# $ENV{HOME} is not set on Windows; fall back to $ENV{USERPROFILE} there.
if(DEFINED ENV{HOME})
    set(_PACK_REPO_HOME "$ENV{HOME}")
else()
    set(_PACK_REPO_HOME "$ENV{USERPROFILE}")
endif()
set(PACK_REPO_PATH "${_PACK_REPO_HOME}/.mchp_packs" CACHE PATH "Path to the root of a pack repository.")

function(My_Pic_Project_default_default_XC8_assemble_rule target)
    set(options
        "-c"
        "${MP_EXTRA_AS_PRE}"
        "-mcpu=${PICAMP_MCPU}"
        "${DEBUGGER_NAME}"
        "-mdfp=${PICAMP_DFP_PATH}"
        "-fno-short-double"
        "-fno-short-float"
        "-O0"
        "-maddrqual=ignore"
        "-mwarn=-3"
        "-msummary=-psect,-class,+mem,-hex,-file"
        "-ginhx32"
        "-Wl,--data-init"
        "-mno-keep-startup"
        "-mno-osccal"
        "-mno-resetbits"
        "-mno-save-resetbits"
        "-mno-download"
        "-mno-stackcall"
        "-mno-default-config-bits"
        "-std=c99"
        "-gdwarf-3"
        "-mstack=compiled:auto:auto")
    list(REMOVE_ITEM options "")
    target_compile_options(${target} PRIVATE "${options}")
    target_compile_definitions(${target}
        PRIVATE "${PICAMP_DEFINE}"
        PRIVATE "__DEBUG=1"
        PRIVATE "XPRJ_default=default")
endfunction()
function(My_Pic_Project_default_default_XC8_assemblePreprocess_rule target)
    set(options
        "-c"
        "${MP_EXTRA_AS_PRE}"
        "-mcpu=${PICAMP_MCPU}"
        "-x"
        "assembler-with-cpp"
        "-mdfp=${PICAMP_DFP_PATH}"
        "-fno-short-double"
        "-fno-short-float"
        "-O0"
        "-maddrqual=ignore"
        "-mwarn=-3"
        "-msummary=-psect,-class,+mem,-hex,-file"
        "-ginhx32"
        "-Wl,--data-init"
        "-mno-keep-startup"
        "-mno-osccal"
        "-mno-resetbits"
        "-mno-save-resetbits"
        "-mno-download"
        "-mno-stackcall"
        "-mno-default-config-bits"
        "-std=c99"
        "-gdwarf-3"
        "-mstack=compiled:auto:auto")
    list(REMOVE_ITEM options "")
    target_compile_options(${target} PRIVATE "${options}")
    target_compile_definitions(${target}
        PRIVATE "${PICAMP_DEFINE}"
        PRIVATE "__DEBUG=1"
        PRIVATE "XPRJ_default=default")
endfunction()
function(My_Pic_Project_default_default_XC8_compile_rule target)
    set(options
        "-c"
        "${MP_EXTRA_CC_PRE}"
        "-mcpu=${PICAMP_MCPU}"
        "${DEBUGGER_NAME}"
        "-mdfp=${PICAMP_DFP_PATH}"
        "-fno-short-double"
        "-fno-short-float"
        "-O0"
        "-maddrqual=ignore"
        "-mwarn=-3"
        "-msummary=-psect,-class,+mem,-hex,-file"
        "-ginhx32"
        "-Wl,--data-init"
        "-mno-keep-startup"
        "-mno-osccal"
        "-mno-resetbits"
        "-mno-save-resetbits"
        "-mno-download"
        "-mno-stackcall"
        "-mno-default-config-bits"
        "-std=c99"
        "-gdwarf-3"
        "-mstack=compiled:auto:auto")
    list(REMOVE_ITEM options "")
    target_compile_options(${target} PRIVATE "${options}")
    target_compile_definitions(${target}
        PRIVATE "${PICAMP_DEFINE}"
        PRIVATE "__DEBUG=1"
        PRIVATE "XPRJ_default=default")
endfunction()
function(My_Pic_Project_default_link_rule target)
    set(options
        "-Wl,-Map=mem.map"
        "${MP_EXTRA_LD_PRE}"
        "-mcpu=${PICAMP_MCPU}"
        "${DEBUGGER_NAME}"
        "-Wl,--defsym=__MPLAB_BUILD=1"
        "-mdfp=${PICAMP_DFP_PATH}"
        "-fno-short-double"
        "-fno-short-float"
        "-O0"
        "-maddrqual=ignore"
        "-mwarn=-3"
        "-msummary=-psect,-class,+mem,-hex,-file"
        "-ginhx32"
        "-Wl,--data-init"
        "-mno-keep-startup"
        "-mno-osccal"
        "-mno-resetbits"
        "-mno-save-resetbits"
        "-mno-download"
        "-mno-stackcall"
        "-mno-default-config-bits"
        "-std=c99"
        "-gdwarf-3"
        "-mstack=compiled:auto:auto"
        "-Wl,--memorysummary,memoryfile.xml")
    list(REMOVE_ITEM options "")
    target_link_options(${target} PRIVATE "${options}")
    target_compile_definitions(${target}
        PRIVATE "__DEBUG=1"
        PRIVATE "XPRJ_default=default")
endfunction()
