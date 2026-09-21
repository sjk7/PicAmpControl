#!/usr/bin/env bash
# Simple test runner for PicAmpControl firmware simulator tests
# Configures CMake with proper Python 3 path and runs CTest

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="$REPO_ROOT/_build/My_Pic_Project/sim"
CMAKE_SRC="$REPO_ROOT/cmake/My_Pic_Project/default"
PYTHON_EXE="$(which python3)"

echo "🔧 PicAmpControl Test Runner"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check prerequisites
if ! command -v cmake &> /dev/null; then
    echo "❌ CMake not found. Install: brew install cmake"
    exit 1
fi

if ! command -v ninja &> /dev/null; then
    echo "❌ Ninja not found. Install: brew install ninja"
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found"
    exit 1
fi

if ! ls /opt/homebrew/Caskroom/mplabx* &> /dev/null && ! ls /Applications/microchip/mplabx* &> /dev/null; then
    echo "❌ MPLAB X IDE not found. Install: brew install --cask mplabx-ide"
    exit 1
fi

echo "✓ Prerequisites OK"
echo "  • CMake: $(cmake --version | head -1)"
echo "  • Python: $(python3 --version)"
echo "  • Ninja: $(ninja --version)"
echo ""

# Configure
echo "📦 Configuring CMake..."
cmake -S "$CMAKE_SRC" \
  -B "$BUILD_DIR" \
  -G Ninja \
  -DCMAKE_BUILD_TYPE=Debug \
  -DCMAKE_TOOLCHAIN_FILE="$CMAKE_SRC/.generated/toolchain.cmake" \
  -DCMAKE_USER_MAKE_RULES_OVERRIDE="$CMAKE_SRC/.generated/overrides.cmake" \
  -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
  -DPYTHON_EXECUTABLE="$PYTHON_EXE" \
  > /dev/null 2>&1
echo "✓ CMake configured"
echo ""

# Build
echo "🔨 Building firmware..."
cmake --build "$BUILD_DIR" > /dev/null 2>&1
echo "✓ Firmware built"
echo "  Hex: $(ls -lh "$REPO_ROOT/out/My_Pic_Project/default.hex" | awk '{print $5}')"
echo "  ELF: $(ls -lh "$REPO_ROOT/out/My_Pic_Project/default.elf" | awk '{print $5}')"
echo ""

# Run tests. All CTest and simulator output goes to a log file: the MDB trace is
# megabytes of pin/state dump and overflows the terminal scrollback.
CTEST_LOG="${CTEST_LOG:-/tmp/pac_ctest.log}"
echo "🧪 Running CTest suite (this may take 2-3 minutes)..."
echo "   Logging to $CTEST_LOG"
echo ""
if ctest --test-dir "$BUILD_DIR" --output-on-failure > "$CTEST_LOG" 2>&1; then
    echo "✓ All tests passed! 🎉"
    grep -E 'Test #[0-9]+:|tests passed' "$CTEST_LOG" || true
    echo ""
    echo "Full log: $CTEST_LOG"
    exit 0
else
    echo "❌ Tests failed — see $CTEST_LOG"
    grep -E 'Test #[0-9]+:|tests passed|FAILED' "$CTEST_LOG" || true
    exit 1
fi
