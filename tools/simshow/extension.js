// Show a log file in front of the operator WITHOUT EVER TAKING THEIR FOCUS.
//
// Why this exists (user instruction, 2026-09-25): running a simulator test must put its log in
// front of the operator, but every external mechanism changes the focus:
//   * `code -r <file>` sends the file to the VS Code window, which makes it the ACTIVE editor tab
//     (so the operator's next keystrokes land in the log - one run was damaged exactly that way)
//     and un-minimises the window;
//   * restoring the window focus afterwards is too late, the active tab has already moved.
// The VS Code API has the one flag the CLI lacks: `preserveFocus: true`. This extension therefore
// does the showing from INSIDE the editor, driven by a plain request file, so no external process
// ever touches the window, the CLI or the active tab:
//   1. the harness writes  <tmp>/picampcontrol_show.request.json  containing {"path": "..."}
//   2. this watcher reads it, opens that file in a NON-ACTIVE editor group with preserveFocus,
//      then puts the operator's original document and group back exactly as they were
//   3. it writes <tmp>/picampcontrol_show.done.json so the harness can confirm what happened
//
// It never runs if no request file appears, and it never touches a request file's own contents.
const vscode = require("vscode");
const fs = require("fs");
const os = require("os");
const path = require("path");

const REQUEST = "picampcontrol_show.request.json";
const RECEIPT = "picampcontrol_show.done.json";

function requestPath() {
  return path.join(os.tmpdir(), REQUEST);
}

function receiptPath() {
  return path.join(os.tmpdir(), RECEIPT);
}

function writeReceipt(payload) {
  try {
    fs.writeFileSync(receiptPath(), JSON.stringify({ at: Date.now(), ...payload }));
  } catch (err) {
    // A missing receipt must never break the show itself.
  }
}

// The group the operator is working in, and the document inside it. Both are restored after the
// log has been shown, because the point is that nothing about their editing session moves.
function activeGroupSnapshot() {
  const group = vscode.window.tabGroups.activeTabGroup;
  const tab = group && group.activeTab;
  return { group: group ? group.viewColumn : undefined, uri: tab && tab.input && tab.input.uri };
}

// Find a group that is NOT the one the operator is typing in. Creating one is the last resort:
// a new group can itself become active, which is why the snapshot above is restored afterwards.
function nonActiveColumn(activeColumn) {
  const other = vscode.window.tabGroups.all.find((group) => group.viewColumn !== activeColumn);
  if (other) {
    return other.viewColumn;
  }
  return undefined;
}

async function showRequestedLog() {
  let payload;
  try {
    payload = JSON.parse(fs.readFileSync(requestPath(), "utf8"));
  } catch (err) {
    return; // no request, or mid-write: the next event will catch it
  }
  if (!payload || !payload.path) {
    return;
  }
  try {
    fs.unlinkSync(requestPath());
  } catch (err) {
    // If it cannot be removed it will simply be handled again on the next change.
  }
  const before = activeGroupSnapshot();
  const uri = vscode.Uri.file(payload.path);
  try {
    const doc = await vscode.workspace.openTextDocument(uri);
    let column = nonActiveColumn(before.group);
    const options = { preview: false, preserveFocus: true };
    if (column === undefined) {
      // No second group yet: make one (Beside), which is the only way to have somewhere the log
      // can live that is not the operator's tab.
      options.viewColumn = vscode.ViewColumn.Beside;
    } else {
      options.viewColumn = column;
    }
    await vscode.window.showTextDocument(doc, options);
    // Put the operator back exactly where they were: same document, same group, focused.
    if (before.uri) {
      const original = await vscode.workspace.openTextDocument(before.uri);
      await vscode.window.showTextDocument(original, {
        viewColumn: before.group,
        preserveFocus: false,
        preview: false,
      });
    }
    writeReceipt({ shown: payload.path, column: options.viewColumn, preserved: true });
  } catch (err) {
    writeReceipt({ shown: payload.path, error: String(err) });
  }
}

function activate(context) {
  const dir = vscode.Uri.file(os.tmpdir());
  // Absolute path -> RelativePattern, so the watcher only watches this one file and not the whole
  // temp directory (which holds multi-megabyte simulator logs).
  const watcher = vscode.workspace.createFileSystemWatcher(
    new vscode.RelativePattern(dir, REQUEST)
  );
  context.subscriptions.push(watcher);
  context.subscriptions.push(watcher.onDidCreate(showRequestedLog));
  context.subscriptions.push(watcher.onDidChange(showRequestedLog));
  context.subscriptions.push(
    vscode.commands.registerCommand("picampcontrol.showLog", showRequestedLog)
  );
  // A request written while the window was starting must not be lost.
  void showRequestedLog();
}

function deactivate() {}

module.exports = { activate, deactivate };
