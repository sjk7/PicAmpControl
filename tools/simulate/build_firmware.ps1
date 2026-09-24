# Builds firmware/ locally with the checked-in CMake toolchain files, producing
# out/My_Pic_Project_18F47Q10/default.hex for use by run_sim.ps1.

$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path "$PSScriptRoot/../..").Path
$CMakeSrc = Join-Path $RepoRoot "cmake/My_Pic_Project/default"
$BuildDir = Join-Path $RepoRoot "_build/My_Pic_Project/sim"

# toolchain.cmake reads $ENV{HOME}, which PowerShell doesn't export by default
if (-not $env:HOME) { $env:HOME = $env:USERPROFILE }

cmake -S $CMakeSrc -B $BuildDir -G Ninja `
    -DCMAKE_BUILD_TYPE=Debug `
    -DCMAKE_TOOLCHAIN_FILE="$CMakeSrc/.generated/toolchain.cmake" `
    -DCMAKE_USER_MAKE_RULES_OVERRIDE="$CMakeSrc/.generated/overrides.cmake" `
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

cmake --build $BuildDir
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$HexPath = Join-Path $RepoRoot "out/My_Pic_Project_18F47Q10/default.hex"
if (-not (Test-Path $HexPath)) {
    Write-Error "expected hex not found at $HexPath"
    exit 1
}
Write-Output "Built: $HexPath"
