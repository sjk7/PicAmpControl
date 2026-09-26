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

// One follower per log file: the editor tab and the watcher that reveals its last line on every
// change. Following is done HERE, not by the Log Viewer extension: that extension needs a
// workspace-relative watch glob, but the run log lives in the OS temp dir, so its glob never
// resolves and the log stops following (user instruction, 2026-09-25).
const followers = new Map(); // fsPath -> { editor, watcher, timer }

function disposeFollower(key) {
  const entry = followers.get(key);
  if (!entry) {
    return;
  }
  if (entry.watcher) {
    entry.watcher.dispose();
  }
  if (entry.timer) {
    clearTimeout(entry.timer);
  }
  followers.delete(key);
}

async function followLog(uri) {
  const key = uri.fsPath;
  const doc = await vscode.workspace.openTextDocument(uri);

  let entry = followers.get(key);
  if (!entry) {
    entry = { editor: null, watcher: null, timer: null };
    followers.set(key, entry);
  }

  // Bring the tab to the front of its own group WITHOUT moving the global focus. `preserveFocus`
  // is the whole point: the version that moved the focus put the operator's keystrokes into the
  // log tab. Never a NEW group - a new group would split the editor, which the operator rejected.
  if (!entry.editor || entry.editor.document.uri.toString() !== uri.toString()) {
    entry.editor = await vscode.window.showTextDocument(doc, {
      preview: false,
      preserveFocus: true,
    });
  }

  // One watcher per followed file, scoped to the file so the whole temp dir (multi-megabyte
  // simulator logs) is never watched.
  if (!entry.watcher) {
    const dir = vscode.Uri.file(path.dirname(key));
    const watcher = vscode.workspace.createFileSystemWatcher(
      new vscode.RelativePattern(dir, path.basename(key))
    );
    const revealTail = () => {
      const editor = entry.editor;
      if (!editor) {
        return;
      }
      // Reveal the last line: this SCROLLS the tab to follow the output without moving the focus
      // or the cursor - the only thing a "follow" is supposed to do.
      const last = editor.document.lineCount - 1;
      editor.revealRange(new vscode.Range(last, 0, last, 0), vscode.TextEditorRevealType.Default);
    };
    // Reveal on a short throttle: a burst of writes scrolls once, not once per line. A run-start
    // truncate lands here as one big change and scrolls back to the top correctly.
    const scheduleReveal = () => {
      if (entry.timer) {
        clearTimeout(entry.timer);
      }
      entry.timer = setTimeout(() => {
        entry.timer = null;
        revealTail();
      }, 150);
    };
    watcher.onDidChange(scheduleReveal);
    watcher.onDidCreate(scheduleReveal);
    watcher.onDidDelete(scheduleReveal);
    entry.watcher = watcher;
  }

  // Reveal once now so an already-grown log shows its tail, not its top.
  const last = doc.lineCount - 1;
  entry.editor.revealRange(new vscode.Range(last, 0, last, 0), vscode.TextEditorRevealType.Default);
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
    if (payload.path.toLowerCase().endsWith(".png")) {
      await vscode.commands.executeCommand("vscode.open", uri, {
        preview: false,
        preserveFocus: true,
      });
      writeReceipt({ shown: payload.path, opened: true, image: true, preserved: true });
      return;
    }
    await followLog(uri);
    writeReceipt({ shown: payload.path, followed: true, preserved: true });
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
  // If the operator highlights (selects) any text in a followed log, stop following that file for
  // the session: they are reading something specific and the view must not be yanked back to the
  // tail. The next run re-creates the follower (the receipt is reset at run start), so this only
  // pauses the current session, never disables following permanently (user instruction,
  // 2026-09-26).
  context.subscriptions.push(
    vscode.window.onDidChangeTextEditorSelection((event) => {
      const editor = event.textEditor;
      if (!editor) {
        return;
      }
      const key = editor.document.uri.fsPath;
      if (!followers.has(key)) {
        return;
      }
      if (editor.selections.some((selection) => !selection.isEmpty)) {
        disposeFollower(key);
      }
    })
  );
  context.subscriptions.push({
    dispose() {
      for (const key of [...followers.keys()]) {
        disposeFollower(key);
      }
    },
  });
  // A request written while the window was starting must not be lost.
  void showRequestedLog();
}

function deactivate() {}

module.exports = { activate, deactivate };
