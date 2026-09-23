# Device selection for the PicAmpControl firmware.
#
# PIC18F47Q10 ONLY (decided 2026-09-23). The PIC16F18875 port is gone: its code paths, build
# option, CI matrix entry and documentation were all removed. There is exactly one device and no
# decision left to make - do not add a second one back.
#
# WHY THE DEVICE FACTS LIVE HERE
# ------------------------------
# `.generated/rule.cmake` is machine-generated and hardcodes device tokens (`-mcpu=...`,
# `__18F47Q10__`, the DFP pack path) in every compile, assemble and link rule. So the facts are
# stated once here and `tools/setup/parameterise_device.py` rewrites those tokens to the CMake
# variables below. Editing a generated file is normally wrong; the alternative is a second copy
# of the whole generated tree that then drifts, and a drift between "what the tests load" and
# "what the target builds" is precisely the failure this is meant to remove. The edit is
# deliberately small, commented, and confined to the device tokens.
#
# MEMORY BUDGET (this part, the only part): 131072 bytes flash, 3359 B RAM, 1024 B EEPROM. The
# Debug image sits at ~10%, so there is room to write things clearly instead of smallest. Flash
# reduction is still a standing work item: the headroom exists so the PTT sequencing can be
# asserted strongly, with test evidence, as unable to damage the amplifier.

set(PICAMP_DEVICE "PIC18F47Q10" CACHE STRING "Target PIC device (PIC18F47Q10 only)")

# Device facts. `PICAMP_DFP` is the pack directory under the pack repository root; the Q10 DFP
# ships inside MPLAB X's own install as well as the user pack repo, and `rule.cmake` already
# resolves that distinction (see the pack-search rule in the build/test skill).
set(PICAMP_DEVICE_MCPU_PIC18F47Q10 "18F47Q10")
set(PICAMP_DEVICE_DEFINE_PIC18F47Q10 "__18F47Q10__")
set(PICAMP_DEVICE_DFP_PIC18F47Q10 "PIC18F-Q_DFP/1.30.487")

set(PICAMP_MCPU "${PICAMP_DEVICE_MCPU_${PICAMP_DEVICE}}")
set(PICAMP_DEFINE "${PICAMP_DEVICE_DEFINE_${PICAMP_DEVICE}}")
set(PICAMP_DFP "${PICAMP_DEVICE_DFP_${PICAMP_DEVICE}}")

if(NOT PICAMP_MCPU)
    message(FATAL_ERROR
        "PICAMP_DEVICE='${PICAMP_DEVICE}' is not a known device. "
        "PIC18F47Q10 is the only supported device. Add a PICAMP_DEVICE_<fact>_<device> entry if "
        "a new part is ever added.")
endif()

# ---------------------------------------------------------------- pack repository roots
# A DFP can live in either of two places, and the two parts in this project are split across them:
#
#   %USERPROFILE%\.mchp_packs/Microchip    the user pack repository; on this machine it holds no
#                                          PIC18F-Q_DFP.
#   <MPLABX install>/packs/Microchip       MPLAB X ships a full pack set; holds PIC18F-Q_DFP/1.30.487.
#
# Searching only the user repository is what produced `error: (2104) no device-support files
# found` for the Q10 build (2026-09-22) - the same wrong assumption that was already corrected once
# for the simulator's pack discovery. Both roots are searched, in order, and the first one holding
# the requested pack wins. A wrong `-mdfp=` is a build error with no fallback, so the path must be
# resolved rather than assumed.
#
# PACK_REPO_PATH is normally set by `.generated/rule.cmake`, but rule.cmake includes THIS file at
# its top BEFORE it defines PACK_REPO_PATH, so on a fresh configure the variable is still empty
# here and the user pack repository is never searched. That works only where MPLAB X ships the
# exact DFP being requested; MPLAB X 6.35 does ship PIC18F-Q_DFP/1.30.487 on macOS, but another
# install or a newer requested pack may not. Set a sensible
# per-OS default first, so the documented configure commands (run_tests.sh, the CMake presets)
# work on a clean checkout with no -DPACK_REPO_PATH. rule.cmake's later `set(... CACHE ...)` does
# not overwrite this value.
if(NOT PACK_REPO_PATH)
    if(DEFINED ENV{HOME})
        set(_PICAMP_PACK_REPO_DEFAULT "$ENV{HOME}/.mchp_packs")
    else()
        set(_PICAMP_PACK_REPO_DEFAULT "$ENV{USERPROFILE}/.mchp_packs")
    endif()
    set(PACK_REPO_PATH "${_PICAMP_PACK_REPO_DEFAULT}" CACHE PATH "Path to the root of a pack repository.")
endif()

set(PICAMP_PACK_ROOTS "${PACK_REPO_PATH}")

# `GLOB` is deliberately NOT used for the MPLAB X installs: the paths contain a space ("Program
# Files"), and a glob that fails to match there silently yields an empty list - which is exactly
# how the first attempt at this reported "not found" while the pack was sitting on disk
# (2026-09-22). Candidates are enumerated explicitly and tested with EXISTS instead.
#
# NOTE `CMAKE_HOST_WIN32`, NOT `WIN32`. This project's toolchain sets `CMAKE_SYSTEM_NAME=Generic`,
# so CMake treats the target as a bare-metal cross target and `WIN32` is FALSE even on Windows.
# Gating on `WIN32` here silently skipped the whole search and left only the user pack repo -
# the second reason this reported the pack missing. `CMAKE_HOST_WIN32` asks about the machine
# running CMake, which is what selecting an install directory is actually about.
if(CMAKE_HOST_WIN32)
    set(_picamp_mplabx_candidates
        "C:/Program Files/Microchip/MPLABX"
        "C:/Program Files (x86)/Microchip/MPLABX")
else()
    set(_picamp_mplabx_candidates "/Applications/microchip/mplabx")
endif()

foreach(_base ${_picamp_mplabx_candidates})
    if(EXISTS "${_base}")
        file(GLOB _picamp_versions LIST_DIRECTORIES true "${_base}/*")
        foreach(_version ${_picamp_versions})
            list(APPEND PICAMP_PACK_ROOTS "${_version}/packs")
        endforeach()
    endif()
endforeach()

set(PICAMP_DFP_PATH "")
foreach(_root ${PICAMP_PACK_ROOTS})
    if(EXISTS "${_root}/Microchip/${PICAMP_DFP}/xc8")
        set(PICAMP_DFP_PATH "${_root}/Microchip/${PICAMP_DFP}/xc8")
        break()
    endif()
endforeach()

if(NOT PICAMP_DFP_PATH)
    message(FATAL_ERROR
        "Device support pack '${PICAMP_DFP}' was not found for ${PICAMP_DEVICE}.\n"
        "Searched these roots for Microchip/${PICAMP_DFP}/xc8:\n"
        "  ${PICAMP_PACK_ROOTS}\n"
        "Install the DFP (MPLAB X ships a full pack set under its own install directory), or set "
        "-DPACK_REPO_PATH=<root>.")
endif()

message(STATUS "PicAmpControl device: ${PICAMP_DEVICE} (mcpu=${PICAMP_MCPU})")
message(STATUS "  device support pack: ${PICAMP_DFP_PATH}")
