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

// The viewport belongs to this extension, not to VS Code's own default of tracking a file that is
// edited underneath an open editor. One rule, stated plainly:
//   * the pane must be FULL - while the whole file still fits on screen there is no overflow, so
//     nothing is scrolled at all ("don't scroll until the pane is full");
//   * and we must be FOLLOWING - `entry.following` is true only while the operator is parked on
//     the tail, and flips false the moment they scroll up to read, so a reader is never yanked.
// This is the ONE place that moves the view, so nothing can race against it.
function followIfFull(entry) {
  const editor = entry.editor;
  if (!editor || !entry.following) {
    return;
  }
  const lineCount = editor.document.lineCount;
  const last = lineCount - 1;
  const first = editor.visibleRanges[0];
  const viewportLines = first ? first.end.line - first.start.line + 1 : 0;
  if (lineCount <= viewportLines) {
    return; // pane not full yet - nothing to follow
  }
  if (editor.visibleRanges.some((range) => range.end.line >= last)) {
    return; // tail already on screen
  }
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
  const doc = await vscode.workspace.openTextDocument(uri);

  let entry = followers.get(key);
  if (!entry) {
    entry = { editor: null, watcher: null, timer: null, following: true };
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
  // Only the window that OWNS this log may open it. Two gates, because this Insiders install
  // runs all windows under ONE shared main process (verified 2026-09-26: every window's extension
  // host descends from the same `Code - Insiders.exe`), so a main-process-PID compare cannot tell
  // two windows apart and the log used to follow in EVERY window (user: "duplicated on my other
  // instance"). The reliable discriminator is which window is FOCUSED: the harness runs in the
  // terminal of the window the operator is looking at, so only that window follows. The `root`
  // gate is a coarse pre-filter (reject windows on a different repo); the PID is retained only as
  // a cheap early-out that works on the rare single-main-per-window layout.
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
  if (vscode.window.state.focused === false) {
    trace(`gate: FOCUS reject (another window owns the terminal)`);
    return; // a different window is focused; this one must not follow the log
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
      const now = editor.visibleRanges.some((range) => range.end.line >= last);
      const top = editor.visibleRanges[0] ? editor.visibleRanges[0].start.line : -1;
      if (now !== entry.following || top !== entry.topLine) {
        trace(`visible: following=${now} top=${top} last=${last}`);
      }
      entry.following = now;
      entry.topLine = top;
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
