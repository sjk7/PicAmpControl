# PicAmpControl test runner for Windows - the PowerShell twin of run_tests.sh.
# Configures CMake for the simulator build, builds the firmware, then runs CTest.
#
# CTest and simulator output is redirected to a log file: the MDB trace is megabytes
# of pin/state dump and overflows the terminal scrollback, losing the verdict line.

$ErrorActionPreference = 'Stop'
$RepoRoot = $PSScriptRoot
$BuildDir = Join-Path $RepoRoot '_build\My_Pic_Project\sim'
$CmakeSrc = Join-Path $RepoRoot 'cmake\My_Pic_Project\default'
$CtestLog = Join-Path $env:TEMP 'pac_ctest.log'

Write-Host 'PicAmpControl Test Runner'
Write-Host ''

# --- Prerequisites -----------------------------------------------------------
foreach ($tool in @('cmake', 'ninja')) {
    if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) {
        Write-Host "CMake/Ninja '$tool' not found. Install with: winget install Kitware.CMake; winget install Ninja-build.Ninja"
        exit 1
    }
}

$Python = $null
foreach ($candidate in @('python', 'python3', 'py')) {
    $cmd = Get-Command $candidate -ErrorAction SilentlyContinue
    if ($cmd) { $Python = $cmd.Source; break }
}
if (-not $Python) {
    Write-Host 'Python 3 not found. The simulator suite is Python 3 only.'
    exit 1
}

$Mplab = @('C:\Program Files\Microchip\MPLABX', "$env:USERPROFILE\.mchp_packs")
if (-not ($Mplab | Where-Object { Test-Path $_ })) {
    Write-Host 'MPLAB X IDE / XC8 not found. Install MPLAB X IDE (it bundles the XC8 compiler).'
    exit 1
}

Write-Host 'Prerequisites OK'
Write-Host "  CMake:  $((cmake --version)[0])"
Write-Host "  Python: $(& $Python --version)"
Write-Host "  Ninja:  $(ninja --version)"
Write-Host ''

# --- Configure ---------------------------------------------------------------
Write-Host 'Configuring CMake...'
cmake -S $CmakeSrc -B $BuildDir -G Ninja -DCMAKE_BUILD_TYPE=Debug `
    "-DCMAKE_TOOLCHAIN_FILE=$CmakeSrc\.generated\toolchain.cmake" `
    "-DCMAKE_USER_MAKE_RULES_OVERRIDE=$CmakeSrc\.generated\overrides.cmake" `
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON `
    "-DPYTHON_EXECUTABLE=$Python"
if ($LASTEXITCODE -ne 0) {
    Write-Host 'CMake configure failed.'
    exit 1
}
Write-Host 'CMake configured'
Write-Host ''

# --- Build -------------------------------------------------------------------
Write-Host 'Building firmware...'
cmake --build $BuildDir
if ($LASTEXITCODE -ne 0) {
    Write-Host 'Firmware build failed.'
    exit 1
}
Write-Host 'Firmware built'
Write-Host ''

# --- Test --------------------------------------------------------------------
Write-Host 'Running CTest suite (this may take 2-3 minutes)...'
Write-Host "  Logging to $CtestLog"
Write-Host ''

ctest --test-dir $BuildDir --output-on-failure *> $CtestLog
$exitCode = $LASTEXITCODE

Select-String -Path $CtestLog -Pattern 'Test #\d+:', 'tests passed', 'FAILED' |
    ForEach-Object { $_.Line }
Write-Host ''

if ($exitCode -ne 0) {
    Write-Host "Tests failed - see $CtestLog"
    exit $exitCode
}

Write-Host 'All tests passed.'
Write-Host "Full log: $CtestLog"
exit 0
