# Launches the MPLAB X headless simulator (mdb) against our locally-built firmware.
#
# Usage:
#   tools/simulate/run_sim.ps1                        # interactive mdb session
#   tools/simulate/run_sim.ps1 scenarios/foo.mdb       # run a scripted scenario, then exit
#
# Requires MPLAB X IDE (provides mdb.bat) and MPLAB XC8.

param(
    [string]$Scenario
)

$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path "$PSScriptRoot/../..").Path
$HexPath = Join-Path $RepoRoot "out/My_Pic_Project/default.hex"
$Device = "PIC16F18855"

$MdbBat = Get-ChildItem "C:\Program Files\Microchip\MPLABX\*\mplab_platform\bin\mdb.bat" -ErrorAction SilentlyContinue |
    Sort-Object FullName | Select-Object -Last 1
if (-not $MdbBat) {
    Write-Error "mdb.bat not found. Install MPLAB X IDE (with debug tools) from Microchip."
    exit 1
}

& "$RepoRoot/tools/simulate/build_firmware.ps1"

$Preamble = New-TemporaryFile
try {
    $Lines = @("device $Device", "hwtool sim", "program $HexPath")
    if ($Scenario) {
        $Lines += Get-Content $Scenario
        $Lines += "quit"
    }
    Set-Content -Path $Preamble.FullName -Value $Lines

    # W0106-SIM TMR1/3/5 warnings are benign simulator-model noise (see Ai-Notes.txt); filter them out.
    # Merge stderr via cmd.exe (not PowerShell's 2>&1) so lines aren't wrapped as terminating ErrorRecords.
    cmd /c "`"$($MdbBat.FullName)`" `"$($Preamble.FullName)`" 2>&1" | Where-Object { $_ -notmatch "W0106-SIM" }
}
finally {
    Remove-Item $Preamble.FullName -ErrorAction SilentlyContinue
}
