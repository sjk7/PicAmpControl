# Device selection for the PicAmpControl firmware.
#
# WHY THIS IS A VARIABLE NOW (2026-09-22)
# --------------------------------------
# `.generated/rule.cmake` is machine-generated and hardcoded `-mcpu=16F18875`,
# `__16F18875__` and the `PIC16F1xxxx_DFP` pack in every compile, assemble and link rule. That
# was fine while there was one device, but it means the PIC18F47Q10 image could only be built by
# hand-written `xc8-cc` invocations - which is exactly what made the Q10 port hard to test
# thoroughly, because `ctest` and every harness load `out/My_Pic_Project/default.elf`.
#
# So the device facts live here, and `.generated/rule.cmake` reads them. Editing a generated file
# is normally wrong; the alternative is a second copy of the whole generated tree that then
# drifts, and a drift between "what the tests load" and "what the target builds" is precisely the
# failure this is meant to remove. The edit is deliberately small, commented, and confined to the
# device tokens.
#
# Choose with `-DPICAMP_DEVICE=PIC18F47Q10` (default: PIC16F18875, so nothing changes for the
# existing device or for anyone who does not pass the option).
#
# MEMORY ASYMMETRY - read this before adding code:
#   PIC16F18875  8192 words flash, 1024 B RAM,  256 B EEPROM. The Debug image sits at ~99% of
#                flash, so on this part a new feature usually means removing something else.
#   PIC18F47Q10  131072 bytes flash, 3359 B RAM, 1024 B EEPROM. The Debug image sits at ~10%,
#                so there is room to write things clearly instead of smallest.
# Anything that must build on BOTH parts stays inside the 16F budget.

set(PICAMP_DEVICE "PIC16F18875" CACHE STRING "Target PIC device (PIC16F18875 or PIC18F47Q10)")

# Per-device facts. `DFP_PACK` is the pack directory under the pack repository root; the Q10 DFP
# ships inside MPLAB X's own install as well as the user pack repo, and `rule.cmake` already
# resolves that distinction (see the pack-search rule in the build/test skill).
set(PICAMP_DEVICE_MCPU_PIC16F18875 "16F18875")
set(PICAMP_DEVICE_DEFINE_PIC16F18875 "__16F18875__")
set(PICAMP_DEVICE_DFP_PIC16F18875 "PIC16F1xxxx_DFP/1.32.471")

set(PICAMP_DEVICE_MCPU_PIC18F47Q10 "18F47Q10")
set(PICAMP_DEVICE_DEFINE_PIC18F47Q10 "__18F47Q10__")
set(PICAMP_DEVICE_DFP_PIC18F47Q10 "PIC18F-Q_DFP/1.30.487")

set(PICAMP_MCPU "${PICAMP_DEVICE_MCPU_${PICAMP_DEVICE}}")
set(PICAMP_DEFINE "${PICAMP_DEVICE_DEFINE_${PICAMP_DEVICE}}")
set(PICAMP_DFP "${PICAMP_DEVICE_DFP_${PICAMP_DEVICE}}")

if(NOT PICAMP_MCPU)
    message(FATAL_ERROR
        "PICAMP_DEVICE='${PICAMP_DEVICE}' is not a known device. "
        "Known: PIC16F18875, PIC18F47Q10. Add a PICAMP_DEVICE_<fact>_<device> entry for a new one.")
endif()

# ---------------------------------------------------------------- pack repository roots
# A DFP can live in either of two places, and the two parts in this project are split across them:
#
#   %USERPROFILE%\.mchp_packs/Microchip    the user pack repository; has PIC16F1xxxx_DFP, but on
#                                          this machine has NO PIC18F-Q_DFP.
#   <MPLABX install>/packs/Microchip       MPLAB X ships a full pack set; holds PIC18F-Q_DFP/1.30.487.
#
# Searching only the user repository is what produced `error: (2104) no device-support files
# found` for the Q10 build (2026-09-22) - the same wrong assumption that was already corrected once
# for the simulator's pack discovery. Both roots are searched, in order, and the first one holding
# the requested pack wins. A wrong `-mdfp=` is a build error with no fallback, so the path must be
# resolved rather than assumed.
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
