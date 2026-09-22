<#
.SYNOPSIS
Adds Windows Defender real-time exclusions for the PicAmpControl build/test toolchain.

.DESCRIPTION
Defender's real-time scanner inspects every process MDB starts and every object the build writes.
On this project that means the simulator JVM, the XC8 compiler, the pack files and the whole
`_build` tree, and the result is a machine that spends its CPU on the scanner instead of on the
simulation.

It MUST run elevated - Get-MpPreference and Add-MpPreference both require administrator. The
supported way in, from any shell:

    Start-Process powershell -Verb RunAs -ArgumentList '-NoExit','-ExecutionPolicy','Bypass','-File',"$PWD\tools\setup\windows-defender-exclusions.ps1"

Behaviour
- Prints one line per exclusion: ADDED, ALREADY EXCLUDED, SKIPPED (path not on this machine).
- On success prints a SUCCESS summary and exits 0.
- On any failure prints FAILED for each item, dumps the full report, and (unless -NoPause is given)
  waits for Enter so an elevated window started with `-Verb RunAs` does not vanish before the user
  can read why it broke. It exits 1.
- On success it says so, and closes its window after -AutoCloseSeconds if that was requested.
- Writes the full report to %TEMP%\pac_defender_exclusions.log, and writes the marker
  %TEMP%\pac_defender_exclusions.ok *only* on success. tools/simulate/cleanup_sim_processes.py
  uses that marker to prompt when the exclusions are missing on this machine.

Notes
- Process exclusions match the image name, not the parent, so `java.exe` covers the MDB JVM even
  though we never launch java ourselves: mdb.bat -> cmd.exe -> java.exe.
- `mplab_backend64.exe` is the MPLAB extension's resident backend - the thing that runs MDB for the
  VS Code sessions - so it is excluded too.
#>
[CmdletBinding()]
param(
    # Skip the "press Enter" pause on failure. Used when an agent or a script runs this
    # unattended; without it a failure would block forever on a hidden console.
    [switch]$NoPause,

    # Close this window this many seconds after a SUCCESS run, so an elevated window opened
    # for the user does not sit around forever (0 = leave it open). A failure always waits for
    # Enter instead, because the reason it broke is the thing the user needs to read.
    [int]$AutoCloseSeconds = 0
)

$ErrorActionPreference = 'Continue'

$reportPath = Join-Path $env:TEMP 'pac_defender_exclusions.log'
$markerPath = Join-Path $env:TEMP 'pac_defender_exclusions.ok'
$lines = @()
$failures = @()
$added = 0
$already = 0
$skipped = 0

function Show-And-Stop {
    param([string]$Message)
    Write-Host ''
    Write-Host $Message -ForegroundColor Red
    Write-Host "Report: $reportPath"
    if (-not $NoPause) {
        Write-Host ''
        Read-Host 'Press Enter to close'
    }
    exit 1
}

function Write-Report {
    # `$script:lines`, not `$lines`: an assignment inside a function creates a *local* copy in
    # PowerShell, so a bare `$lines += ...` here silently wrote a report holding only these two
    # lines and dropped every ADDED/PRESENT/FAILED entry (found 2026-09-22).
    $script:lines += "VERDICT $(if ($failures.Count) { 'FAILED failures=' + $failures.Count } else { 'SUCCESS' })"
    $script:lines += "APPLIED_AT $(Get-Date -Format o)"
    $script:lines | Set-Content -LiteralPath $reportPath -Encoding UTF8
}

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    $lines += 'ERROR not running elevated; Add-MpPreference requires administrator'
    $failures += 'elevation'
    Write-Report
    Show-And-Stop @'
FAILED: this script is not running elevated, so nothing was changed.

Re-run it from an elevated PowerShell, e.g.:
  Start-Process powershell -Verb RunAs -ArgumentList '-NoExit','-ExecutionPolicy','Bypass','-File',"$PWD\tools\setup\windows-defender-exclusions.ps1"
'@
}

try {
    $pref = Get-MpPreference
} catch {
    $lines += "ERROR Get-MpPreference failed: $($_.Exception.Message)"
    $failures += 'Get-MpPreference'
    Write-Report
    Show-And-Stop "FAILED: could not read the current Defender settings.`n$($_.Exception.Message)"
}
$currentPaths = @($pref.ExclusionPath)
$currentProcs = @($pref.ExclusionProcess)

$paths = @(
    'E:\hamcode\PicAmpControl',
    'C:\Program Files\Microchip',
    'C:\Python314',
    'C:\Python313',
    "$env:TEMP"
)
$procs = @(
    'xc8-cc.exe', 'xc8.exe', 'xc8-ld.exe',
    'mdb.bat', 'java.exe', 'javaw.exe',
    'mplab_backend64.exe',
    'python.exe', 'python3.13.exe', 'pythonw.exe',
    'cmake.exe', 'ctest.exe', 'ninja.exe',
    'clangd.exe'
)

foreach ($p in $paths) {
    if (-not (Test-Path -LiteralPath $p)) {
        Write-Host "SKIPPED  $p (not on this machine)"
        $lines += "SKIPPED  $p (not present)"
        $skipped++
        continue
    }
    if ($currentPaths -contains $p) {
        Write-Host "PRESENT  $p"
        $lines += "PRESENT  $p"
        $already++
        continue
    }
    try {
        Add-MpPreference -ExclusionPath $p -ErrorAction Stop
        Write-Host "ADDED    $p" -ForegroundColor Green
        $lines += "ADDED    $p"
        $added++
    } catch {
        Write-Host "FAILED   $p :: $($_.Exception.Message)" -ForegroundColor Red
        $lines += "FAILED   $p :: $($_.Exception.Message)"
        $failures += "path $p"
    }
}
foreach ($p in $procs) {
    if ($currentProcs -contains $p) {
        Write-Host "PRESENT  $p"
        $lines += "PRESENT  $p"
        $already++
        continue
    }
    try {
        Add-MpPreference -ExclusionProcess $p -ErrorAction Stop
        Write-Host "ADDED    $p" -ForegroundColor Green
        $lines += "ADDED    $p"
        $added++
    } catch {
        Write-Host "FAILED   $p :: $($_.Exception.Message)" -ForegroundColor Red
        $lines += "FAILED   $p :: $($_.Exception.Message)"
        $failures += "process $p"
    }
}

Write-Report

if ($failures.Count) {
    Write-Host ''
    Write-Host '--- full report ---' -ForegroundColor Yellow
    Get-Content -LiteralPath $reportPath | ForEach-Object { Write-Host $_ }
    Show-And-Stop "FAILED: $($failures.Count) exclusion(s) could not be applied: $($failures -join ', ')"
}

Set-Content -LiteralPath $markerPath -Value "applied $(Get-Date -Format o)" -Encoding UTF8
Write-Host ''
Write-Host "SUCCESS: Defender exclusions are in place - $added added, $already already present, $skipped skipped." -ForegroundColor Green
Write-Host "Report: $reportPath"
Write-Host "Marker: $markerPath"

if ($AutoCloseSeconds -gt 0) {
    Write-Host "Closing this window in $AutoCloseSeconds seconds..."
    Start-Sleep -Seconds $AutoCloseSeconds
    # Stops this shell, which is the process owning the console window.
    Stop-Process -Id $PID -Force
}
exit 0
