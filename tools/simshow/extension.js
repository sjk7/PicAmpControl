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
const { execSync } = require("child_process");

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

// Diagnostic: append one line to the follow trace so the harness can read back exactly what this
// extension decided (which code is running, and every following flip / reveal choice). Never
// affects the show; a missing/read-only temp dir must not break anything.
const TRACE = "picampcontrol_follow.trace.log";
function trace(msg) {
  try {
    fs.appendFileSync(path.join(os.tmpdir(), TRACE), `${Date.now()} ${msg}\n`, "utf8");
  } catch (err) {
    // trace is best-effort only
  }
}

// The PID of THIS VS Code window's main process, or null. Every window is one main process; the
// harness (run in a terminal) has its window's main process as an ancestor and tags its request
// with that PID, so this extension must only act when the request PID is its own. Walk up the
// parent chain from this extension host until we leave the `Code*` process group; the topmost
// Code process is the window main. (user instruction, 2026-09-26: *"only talk to your own pid"*).
let cachedMainPid = null;
function mainPid() {
  if (cachedMainPid !== null) {
    return cachedMainPid;
  }
  try {
    const out = execSync(
      "wmic process get ProcessId,ParentProcessId,Name /format:list",
      { windowsHide: true, timeout: 15000, encoding: "utf8" }
    );
    const procs = new Map(); // pid -> { ppid, name }
    // wmic /format:list emits Name=, ParentProcessId=, ProcessId= in that order per process with
    // stray blank lines between, so walk line-by-line and record on ProcessId= - never on blocks.
    let name = null;
    let ppid = null;
    for (const raw of out.split(/\r?\n/)) {
      const line = raw.trim();
      if (line.startsWith("Name=")) name = line.slice(5);
      else if (line.startsWith("ParentProcessId=")) ppid = line.slice(16);
      else if (line.startsWith("ProcessId=")) {
        const pidStr = line.slice(10);
        if (/^\d+$/.test(pidStr)) {
          procs.set(parseInt(pidStr, 10), {
            ppid: ppid && /^\d+$/.test(ppid) ? parseInt(ppid, 10) : 0,
            name: name || "",
          });
        }
        name = null;
        ppid = null;
      }
    }
    const isCode = (n) => n.toLowerCase().startsWith("code");
    let pid = process.pid;
    let lastCode = null;
    while (procs.has(pid)) {
      const rec = procs.get(pid);
      if (isCode(rec.name)) lastCode = pid;
      if (!rec.ppid) break;
      pid = rec.ppid;
    }
    cachedMainPid = lastCode;
    return lastCode;
  } catch (err) {
    cachedMainPid = null;
    return null;
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
const followers = new Map(); // fsPath -> { editor, watcher, timer, following }

// The viewport belongs to this extension, not to VS Code's own habit of following a file that is
// edited underneath an open editor (nor to any other log-follower - the marketplace Log Viewer and
// log-follower extensions are NOT to be installed, 2026-09-26). One rule: scroll only once the pane
// is FULL.
//
// "Full" is detected WITHOUT measuring the pane, because VS Code's `visibleRanges` reports the
// span of lines that carry content, which is smaller than the pane whenever a view is scrolled past
// the end of a short file - so it cannot be trusted as a height. The pane is full exactly when the
// LAST line is not on screen while the view is still parked at the TOP: while the whole log fits it
// stays put, and the moment it does not, the tail is kept on screen. Only while the operator is
// parked on the tail too (`entry.following`, false the moment they scroll up to read).
function followIfFull(entry) {
  const editor = entry.editor;
  if (!editor) {
    return;
  }
  const lineCount = editor.document.lineCount;
  if (lineCount < entry.lastLineCount) {
    // The run truncated the log: the view is back at the top of a fresh file. Follow again.
    entry.lastTop = 0;
    entry.following = true;
  }
  entry.lastLineCount = lineCount;
  if (!entry.following) {
    trace(`full: SKIP following=false`);
    return;
  }
  const ranges = editor.visibleRanges;
  const last = lineCount - 1;
  const top = ranges.length ? ranges[0].start.line : 0;
  const tailVisible = ranges.some((range) => range.end.line >= last);
  trace(`full: lineCount=${lineCount} top=${top} tail=${tailVisible}`);
  if (top === 0 && tailVisible) {
    return; // whole log on screen from the top: the pane is not full, so do not scroll
  }
  trace(`full: REVEAL tail`);
  editor.revealRange(new vscode.Range(last, 0, last, 0), vscode.TextEditorRevealType.AtBottom);
}

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
  trace(`followLog: ${key}`);
  const doc = await vscode.workspace.openTextDocument(uri);

  let entry = followers.get(key);
  if (!entry) {
    entry = { editor: null, watcher: null, timer: null, following: true, lastTop: 0, lastLineCount: 0 };
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
    const scheduleReveal = () => {
      if (entry.timer) {
        clearTimeout(entry.timer);
      }
      entry.timer = setTimeout(() => {
        entry.timer = null;
        followIfFull(entry);
      }, 150);
    };
    watcher.onDidChange(scheduleReveal);
    watcher.onDidCreate(scheduleReveal);
    watcher.onDidDelete(scheduleReveal);
    entry.watcher = watcher;
  }

  // Park on the tail only when the pane is already full; an unfilled pane is left at the top.
  entry.following = true;
  entry.lastTop = 0;
  followIfFull(entry);
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
  // Only the window that OWNS this log may open it: a request is ignored unless this window has the
  // harness's workspace root open. A main-process-PID compare was tried and is USELESS here - this
  // Insiders install runs every window under ONE shared `Code - Insiders.exe`, so all windows match.
  // The "opened in the wrong window / duplicated" trouble of 2026-09-26 turned out to be the
  // marketplace log-follower extensions (`berublan.vscode-log-viewer`, `log-follower.log-follower`),
  // which are now uninstalled and must NOT be reinstalled. The PID tag is kept only as a cheap
  // early-out for single-main-per-window layouts.
  if (payload.pid) {
    const mine = mainPid();
    if (mine !== null && mine !== payload.pid) {
      trace(`gate: PID reject mine=${mine} theirs=${payload.pid}`);
      return; // not this window; leave the file for the owning window to handle
    }
  }
  if (payload.root) {
    const folders = vscode.workspace.workspaceFolders || [];
    const root = path.resolve(String(payload.root)).toLowerCase();
    const owns = folders.some((folder) =>
      path.resolve(folder.uri.fsPath).toLowerCase() === root
    );
    if (!owns) {
      trace(`gate: ROOT reject root=${payload.root}`);
      return;
    }
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
  trace("activate: extension loaded (guard-removed build)");
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
  // Auto-follow is driven off the VISIBLE RANGES, not off file changes: `entry.following` is true
  // while the tail line is on screen and flips false the moment the operator scrolls away, then
  // true again if they scroll back. This is what stops the yank - a plain mouse-wheel scroll away
  // from the tail must stop the auto-scroll, and scrolling back must resume it. The earlier
  // "reveal whenever the tail is not visible" read "scrolled away" and "new content arrived" as
  // the same thing and fought the reader's own scroll (user instruction, 2026-09-26).
  context.subscriptions.push(
    vscode.window.onDidChangeTextEditorVisibleRanges((event) => {
      const editor = event.textEditor;
      if (!editor) {
        return;
      }
      const key = editor.document.uri.fsPath;
      const entry = followers.get(key);
      if (!entry) {
        return;
      }
      const last = editor.document.lineCount - 1;
      const ranges = editor.visibleRanges;
      const top = ranges.length ? ranges[0].start.line : 0;
      const tailVisible = ranges.some((range) => range.end.line >= last);
      // Following means "the operator has not scrolled away". The tail being on screen is one sign of
      // that; the other is simply that the view has not moved UP. The log growing past the pane
      // takes the tail off screen WITHOUT any scroll, and that must not switch following off (the
      // old "tail visible" test alone did exactly that, so following never began). A view that
      // moves UP is a deliberate scroll-away, so that - and only that - turns following off,
      // including a scroll all the way to the top, which must not be yanked to the tail.
      if (tailVisible) {
        entry.following = true;
      } else if (top < entry.lastTop) {
        entry.following = false;
      }
      entry.lastTop = top;
      trace(`visible: last=${last} top=${top} tail=${tailVisible} -> following=${entry.following}`);
    })
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
        trace(`selection: dispose follower (non-empty selection)`);
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
