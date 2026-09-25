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

// Any tab that already shows `uri`, anywhere. Re-opening a file that is already on screen is how the
// operator ended up with two follows of the same log side by side in a split editor, which is not
// wanted (user instruction, 2026-09-25: *"I ended up with TWO log follows then, in split screen. I
// don't want this."*).
function findOpenTab(uri) {
  for (const group of vscode.window.tabGroups.all) {
    for (const tab of group.tabs) {
      const input = tab.input;
      if (input && input.uri && input.uri.toString() === uri.toString()) {
        return { group, tab };
      }
    }
  }
  return null;
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
  const uri = vscode.Uri.file(payload.path);
  try {
    // NOTHING is opened automatically. Both automatic routes are ruled out by the operator:
    // making it the active tab in the one group takes their typing (it wrecked a run), and putting
    // it in a second group SPLITS the editor, which is the "split screen" they do not want
    // (2026-09-25: *"Ah well its the second editor group that I DO NOT WANT. That's what I meant by
    // 'split-screen'"*). So: if it is already on screen, do nothing; otherwise offer it with a
    // NON-MODAL notification whose buttons the operator clicks - their click, their choice, and the
    // notification itself never takes focus.
    if (findOpenTab(uri)) {
      // Already on screen, but the operator asked (2026-09-25) that a new run re-shows it: a plain
      // text tab keeps its scroll position, so an already-open log LOOKS frozen even though the file
      // is growing. Bring it to the front of its own group WITHOUT moving focus - that is what
      // preserveFocus is for - and without creating a second editor (same doc, no duplicate).
      try {
        const doc = await vscode.workspace.openTextDocument(uri);
        await vscode.window.showTextDocument(doc, {
          viewColumn: findOpenTab(uri).group.viewColumn ?? vscode.ViewColumn.One,
          preview: false,
          preserveFocus: true,
        });
        writeReceipt({ shown: payload.path, already_open: true, preserved: true });
      } catch (err) {
        writeReceipt({ shown: payload.path, already_open: true, error: String(err) });
      }
      return;
    }
    // OPEN IT, with `preserveFocus: true` - so the tab appears and keeps updating (the operator
    // expects to see the run they just started: *"I expect to see the log followed now"*) while the
    // focus stays exactly where it was. `preserveFocus` is the whole point: the version that moved
    // the focus is what put their keystrokes into the log tab. The tab is opened in the ACTIVE group
    // because creating a group would split the editor, which they have rejected outright.
    try {
      if (payload.path.toLowerCase().endsWith(".png")) {
        await vscode.commands.executeCommand("vscode.open", uri, {
          preview: false,
          preserveFocus: true,
        });
      } else {
        const doc = await vscode.workspace.openTextDocument(uri);
        await vscode.window.showTextDocument(doc, { preview: false, preserveFocus: true });
      }
      writeReceipt({ shown: payload.path, opened: true, preserved: true });
    } catch (err) {
      writeReceipt({ shown: payload.path, opened: false, error: String(err) });
    }
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
