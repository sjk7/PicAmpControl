#!/bin/sh
# Install the PicAmpControl show-log helper into VS Code / VS Code Insiders (macOS, Linux).
#
# Why an installer at all: the extension has to live in the editor's extensions directory to be
# loaded, and VS Code has no "load this folder" command. Copying the folder in is the whole job -
# the only step left for a human is reloading the window, which is printed at the end.
#
#   sh tools/simshow/install.sh
set -eu

source_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
target_name="picampcontrol-simshow-1.0.0"
installed=""

for root in "$HOME/.vscode-insiders/extensions" "$HOME/.vscode/extensions"; do
    editor_root=$(dirname -- "$root")
    [ -d "$editor_root" ] || continue          # that editor is not installed here
    mkdir -p "$root"
    target="$root/$target_name"
    # A previous copy goes first: copying over an existing tree leaves stale files behind, and
    # VS Code caches the extension listing at startup.
    rm -rf "$target"
    mkdir -p "$target"
    cp "$source_dir/package.json" "$source_dir/extension.js" "$target/"
    installed="$installed\n  $target"
done

if [ -z "$installed" ]; then
    echo "Neither VS Code nor VS Code Insiders appears to be installed for this user."
    echo "Install one, then run this script again."
    exit 1
fi

echo "PicAmpControl show-log helper installed into:"
printf "%b\n" "$installed"
echo ""
echo "One manual step remains: reload the VS Code window once so it loads the extension."
echo "  Cmd+Shift+P  ->  Developer: Reload Window"
echo "After that, a simulator run shows its log without ever taking your focus."
echo ""
echo "Check it by hand with:"
echo "  python3 tools/simulate/open_progress_log.py <log-file>"
