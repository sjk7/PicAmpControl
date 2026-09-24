#!/usr/bin/env bash
# Build and install the in-repo Log Follower extension if the matching version is not already there.
#
# A VSIX is just a zip holding [Content_Types].xml, extension.vsixmanifest and the extension/ payload,
# so this needs no npm and no vsce - which matters because the .vsix itself is gitignored and a fresh
# clone therefore has no follower until this runs.
#
# Idempotent: exits 0 immediately when ~/.vscode/extensions/log-follower.log-follower-<version>
# already exists. Called by run_tests.sh before a run; safe to run by hand at any time.
set -euo pipefail

here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../.." && pwd)
src="$root/tools/logfollower"

[ -f "$src/package.json" ] || { echo "logfollower: $src/package.json not found" >&2; exit 1; }

name=$(python3 -c "import json;print(json.load(open('$src/package.json'))['name'])")
publisher=$(python3 -c "import json;print(json.load(open('$src/package.json'))['publisher'])")
version=$(python3 -c "import json;print(json.load(open('$src/package.json'))['version'])")

target="$HOME/.vscode/extensions/${publisher}.${name}-${version}"
if [ -d "$target" ]; then
    echo "logfollower $version already installed"
    exit 0
fi

if ! command -v code >/dev/null 2>&1; then
    echo "logfollower: 'code' is not on PATH - install it by hand from $src" >&2
    exit 1
fi

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/extension"
cp "$src/extension.js" "$src/package.json" "$src/README.md" "$tmp/extension/"

cat > "$tmp/[Content_Types].xml" <<'XML'
<?xml version="1.0" encoding="utf-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="json" ContentType="application/json"/>
  <Default Extension="js" ContentType="application/javascript"/>
  <Default Extension="md" ContentType="text/markdown"/>
  <Default Extension="xml" ContentType="text/xml"/>
</Types>
XML

cat > "$tmp/extension.vsixmanifest" <<XML
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
XML

vsix="$src/pac-log-follower.vsix"
(cd "$tmp" && zip -q -r "$vsix" '[Content_Types].xml' extension.vsixmanifest extension)
echo "logfollower: packaging $version and installing"
code --install-extension "$vsix" --force
