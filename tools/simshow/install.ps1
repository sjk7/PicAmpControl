# Install the PicAmpControl show-log helper into VS Code / VS Code Insiders.
#
# Why an installer at all: the extension has to live in the editor's extensions directory to be
# loaded, and VS Code has no "load this folder" command. Copying the folder in is the whole job -
# the only step left for a human is reloading the window, which is printed at the end.
#
#   powershell -ExecutionPolicy Bypass -File tools\simshow\install.ps1

$ErrorActionPreference = 'Stop'
$Source = $PSScriptRoot
$Name = 'picampcontrol-simshow'
$Version = '1.0.0'
$TargetName = "$Name-$Version"

$roots = @(
    (Join-Path $env:USERPROFILE '.vscode-insiders\extensions'),
    (Join-Path $env:USERPROFILE '.vscode\extensions')
)

$installed = @()
foreach ($root in $roots) {
    if (-not (Test-Path (Split-Path $root -Parent))) { continue }   # that editor is not installed
    New-Item -ItemType Directory -Force -Path $root | Out-Null
    $target = Join-Path $root $TargetName
    # A previous copy must go first: copying into an existing tree leaves stale files behind, and
    # VS Code caches the extension listing at startup.
    if (Test-Path $target) { Remove-Item -Recurse -Force $target }
    New-Item -ItemType Directory -Force -Path $target | Out-Null
    Copy-Item (Join-Path $Source 'package.json') $target -Force
    Copy-Item (Join-Path $Source 'extension.js') $target -Force
    $installed += $target
}

if ($installed.Count -eq 0) {
    Write-Host 'Neither VS Code nor VS Code Insiders appears to be installed for this user.'
    Write-Host 'Install one, then run this script again.'
    exit 1
}

Write-Host 'PicAmpControl show-log helper installed into:'
$installed | ForEach-Object { Write-Host "  $_" }
Write-Host ''
Write-Host 'One manual step remains: reload the VS Code window once so it loads the extension.'
Write-Host '  Ctrl+Shift+P  ->  Developer: Reload Window'
Write-Host 'After that, a simulator run shows its log without ever taking your focus.'
Write-Host ''
Write-Host 'Check it by hand with:'
Write-Host '  python tools/simulate/open_progress_log.py <log-file>'
exit 0
