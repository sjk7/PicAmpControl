# Build and install the in-repo Log Follower extension if the matching version is not already there.
#
# The VSIX is gitignored, so a fresh clone has no follower until this runs. Idempotent: exits 0 when
# ~/.vscode/extensions/log-follower.log-follower-<version> already exists. Called by run_tests.ps1
# before a run; safe to run by hand at any time. Needs no npm and no vsce.
$ErrorActionPreference = 'Stop'

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Resolve-Path (Join-Path $here '..\..')
$src = Join-Path $root 'tools\logfollower'
$pkg = Join-Path $src 'package.json'

if (-not (Test-Path $pkg)) { throw "logfollower: $pkg not found" }
$manifest = Get-Content $pkg -Raw | ConvertFrom-Json
$name = $manifest.name
$publisher = $manifest.publisher
$version = $manifest.version

$target = Join-Path $HOME ".vscode\extensions\$publisher.$name-$version"
if (Test-Path $target) { Write-Host "logfollower $version already installed"; exit 0 }

$code = Get-Command code -ErrorAction SilentlyContinue
if (-not $code) { throw "logfollower: 'code' is not on PATH - install it by hand from $src" }

$tmp = Join-Path ([System.IO.Path]::GetTempPath()) ("logfollower-" + [guid]::NewGuid().ToString('N'))
$ext = Join-Path $tmp 'extension'
New-Item -ItemType Directory -Force -Path $ext | Out-Null
Copy-Item (Join-Path $src 'extension.js'), $pkg, (Join-Path $src 'README.md') $ext

$contentTypes = @'
<?xml version="1.0" encoding="utf-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="json" ContentType="application/json"/>
  <Default Extension="js" ContentType="application/javascript"/>
  <Default Extension="md" ContentType="text/markdown"/>
  <Default Extension="xml" ContentType="text/xml"/>
</Types>
'@
Set-Content -Path (Join-Path $tmp '[Content_Types].xml') -Value $contentTypes -Encoding UTF8

$vsixManifest = @"
<?xml version="1.0" encoding="utf-8"?>
<PackageManifest Version="2.0.0" xmlns="http://schemas.microsoft.com/developer/vsx-schema/2011">
  <Metadata>
    <Identity Language="en-US" Id="$name" Version="$version" Publisher="$publisher"/>
    <DisplayName>Log Follower</DisplayName>
    <Description xml:space="preserve">Follow a growing log file in its editor tab.</Description>
  </Metadata>
  <Installation>
    <InstallationTarget Id="Microsoft.VisualStudio.Code"/>
  </Installation>
  <Assets>
    <Asset Type="Microsoft.VisualStudio.Code.Manifest" Path="extension/package.json"/>
  </Assets>
</PackageManifest>
"@
Set-Content -Path (Join-Path $tmp 'extension.vsixmanifest') -Value $vsixManifest -Encoding UTF8

$vsix = Join-Path $src 'pac-log-follower.vsix'
if (Test-Path $vsix) { Remove-Item $vsix -Force }
Compress-Archive -Path (Join-Path $tmp '[Content_Types].xml'), (Join-Path $tmp 'extension.vsixmanifest'), $ext -DestinationPath $vsix
Remove-Item $tmp -Recurse -Force

Write-Host "logfollower: packaging $version and installing"
& code --install-extension $vsix --force
