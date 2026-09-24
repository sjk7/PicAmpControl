#!/usr/bin/env bash
# Builds firmware/ locally with the checked-in CMake toolchain files, producing
# out/My_Pic_Project_18F47Q10/default.hex for use by run_sim.sh.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CMAKE_SRC="$REPO_ROOT/cmake/My_Pic_Project/default"
BUILD_DIR="$REPO_ROOT/_build/My_Pic_Project/sim"

cmake -S "$CMAKE_SRC" -B "$BUILD_DIR" -G Ninja \
    -DCMAKE_BUILD_TYPE=Debug \
    -DCMAKE_TOOLCHAIN_FILE="$CMAKE_SRC/.generated/toolchain.cmake" \
    -DCMAKE_USER_MAKE_RULES_OVERRIDE="$CMAKE_SRC/.generated/overrides.cmake" \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON

cmake --build "$BUILD_DIR"

HEX_PATH="$REPO_ROOT/out/My_Pic_Project_18F47Q10/default.hex"
if [[ ! -f "$HEX_PATH" ]]; then
    echo "error: expected hex not found at $HEX_PATH" >&2
    exit 1
fi
echo "Built: $HEX_PATH"
