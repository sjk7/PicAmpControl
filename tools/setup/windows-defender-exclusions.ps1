<#
.SYNOPSIS
Adds Windows Defender real-time exclusions for the PicAmpControl build/test toolchain.

.DESCRIPTION
Defender's real-time scanner inspects every process MDB starts and every object the build
writes. On this project that means the simulator JVM, the XC8 compiler, the pack files and
the whole `_build` tree, and the result is a machine that spends its CPU on the scanner
instead of on the simulation.

Run this once per machine (and again after a toolchain move). It MUST run elevated:
Get-MpPreference and Add-MpPreference both require administrator.

    # from an elevated PowerShell
    powershell -ExecutionPolicy Bypass -File tools\setup\windows-defender-exclusions.ps1

Notes
- Process exclusions are matched on image name, not on the parent, so `java.exe` covers the
  MDB JVM even though we never launch java ourselves - mdb.bat -> cmd.exe -> java.exe.
- `mplab_backend64.exe` is the MPLAB extension's resident backend: it is what runs MDB for
  the VS Code sessions, so it is excluded too.
- The script writes a marker file. tools/simulate/cleanup_sim_processes.py uses it to warn
  when the exclusions have not been applied on this machine.
#>
$ErrorActionPreference = 'Continue'

$report = Join-Path $env:TEMP 'pac_defender_exclusions.txt'
$lines = @()

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
    if (Test-Path -LiteralPath $p) {
        try { Add-MpPreference -ExclusionPath $p -ErrorAction Stop; $lines += "PATH OK   $p" }
        catch { $lines += "PATH ERR  $p :: $($_.Exception.Message)" }
    } else {
        $lines += "PATH SKIP $p (not present)"
    }
}
foreach ($p in $procs) {
    try { Add-MpPreference -ExclusionProcess $p -ErrorAction Stop; $lines += "PROC OK   $p" }
    catch { $lines += "PROC ERR  $p :: $($_.Exception.Message)" }
}

$pref = Get-MpPreference
$lines += '--- ExclusionPath ---'
$lines += $pref.ExclusionPath
$lines += '--- ExclusionProcess ---'
$lines += $pref.ExclusionProcess
$lines += "APPLIED_AT $(Get-Date -Format o)"
$lines | Set-Content -LiteralPath $report -Encoding UTF8

Write-Host "Wrote $report"
