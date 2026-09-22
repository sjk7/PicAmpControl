// Log Follower: keep a growing log file scrolled to its tail in an editor tab, and stop the
// moment the user takes control of that tab.
//
// COST IS THE DESIGN CONSTRAINT. An earlier log-following extension measured ~110% of one core
// while following a file and was rejected for it ("a tool that eats a core to follow a text file
// is badly written and must not be used"). This one is built to cost nothing while idle and very
// little while following:
//
//   * One coalesced poll per COALESCE_MS, not a per-frame timer. 400 ms by default is 2.5 wakes a
//     second; each wake is a stat() plus, only when the size changed, one revealRange().
//   * Nothing at all while paused by the user, or while the followed file is not the visible tab.
//   * No filesystem watcher: a watcher object per open log plus its event plumbing costs more
//     than a 400 ms stat and adds failure modes when the producer truncates the file.
//
// WHY IT POLLS RATHER THAN REACTING TO DOCUMENT EVENTS: a log written by an *external* process is
// not reliably delivered as `onDidChangeTextDocument`. In practice VS Code reports auto-reverted
// content only if the file is refreshed, and a run in progress is not: the extension simply never
// hears about the append. (This was the first bug: document-event-only following did not scroll at
// all on a live run, which the user reported as "not scrolling automagically unless interacted
// with".) Polling the file size is the reliable trigger; the coalescing window is what keeps it
// cheap.
const vscode = require('vscode');

/** Uri strings currently being followed. */
const following = new Set();
/** Uri strings where the user has taken control, so we must not fight them for the scroll. */
const userTookOver = new Set();
/** Last observed file size per followed uri, to detect growth cheaply. */
const lastSize = new Map();
/** Suppress our own selection noise briefly so it is not mistaken for a user click. */
const lastSelfMove = new Map();
/** Live file watchers, one per followed uri, so an append scrolls immediately. */
const watchers = new Map();

const SELF_MOVE_GRACE_MS = 150;

function key(uri) {
  return uri.toString();
}

function config() {
  const cfg = vscode.workspace.getConfiguration('logFollower');
  const raw = cfg.get('coalesceMs', 400);
  return {
    // Floor of 100 ms: below that the poll stops being a trivially cheap operation, and a log
    // that grows faster than a human can read gains nothing from being followed faster.
    coalesceMs: Math.max(100, Number(raw) || 400),
    globs: cfg.get('autoFollowGlobs', []) || [],
  };
}

function matchesGlob(name, globs) {
  return globs.some((glob) => {
    if (!glob) return false;
    const escaped = glob.replace(/[.+^${}()|[\]\\]/g, '\\$&').replace(/\*/g, '.*').replace(/\?/g, '.');
    return new RegExp(`^${escaped}$`, 'i').test(name);
  });
}

function editorFor(uriString) {
  return vscode.window.visibleTextEditors.find(
    (editor) => editor.document.uri.toString() === uriString,
  );
}

function scrollToEnd(editor) {
  const doc = editor.document;
  if (doc.lineCount === 0) return;
  const last = doc.lineCount - 1;
  const end = doc.lineAt(last).range.end;
  // `revealRange` alone is not enough to behave like `tail -f`. Its Default reveal type only
  // guarantees the position is *visible*, not that it is at the bottom of the viewport, so on a
  // long file the view settles part-way up and the newest line can sit below the fold - which
  // reads as "the follow is behind" even though the buffer is current (measured 2026-09-22: the
  // tab showed line 136 of 201).
  //
  // The reliable sequence is: put the cursor on the last line, then reveal it AT THE TOP of the
  // viewport. Because it is the last line, "top of viewport" means the document is scrolled as far
  // down as it can go and the newest line is pinned to the bottom edge - which is what a tail
  // looks like. Doing both, in this order, is what makes it settle correctly.
  if (!editor.selection.active.isEqual(end)) {
    lastSelfMove.set(key(doc.uri), Date.now());
    editor.selection = new vscode.Selection(end, end);
  }
  lastSelfMove.set(key(doc.uri), Date.now());
  editor.revealRange(new vscode.Range(end, end), vscode.TextEditorRevealType.AtTop);
}

function startFollow() {
  const editor = vscode.window.activeTextEditor;
  if (!editor) {
    vscode.window.showInformationMessage('Log Follower: no active editor to follow.');
    return;
  }
  const k = key(editor.document.uri);
  following.add(k);
  userTookOver.delete(k);
  lastSize.delete(k);
  armWatcher(k);
  scrollToEnd(editor);
}
function stopFollow() {
  const editor = vscode.window.activeTextEditor;
  if (!editor) return;
  const k = key(editor.document.uri);
  following.delete(k);
  lastSize.delete(k);
  releaseWatcher(k);
}

function toggleFollow() {
  const editor = vscode.window.activeTextEditor;
  if (!editor) return;
  const k = key(editor.document.uri);
  if (following.has(k) && !userTookOver.has(k)) {
    following.delete(k);
    lastSize.delete(k);
    releaseWatcher(k);
    vscode.window.setStatusBarMessage('Log Follower: stopped', 2000);
  } else {
    // Covers both "never followed" and "paused by interaction": either way, this is the explicit
    // resume, so it clears the pause as well as arming the follow.
    following.add(k);
    userTookOver.delete(k);
    lastSize.delete(k);
    armWatcher(k);
    scrollToEnd(editor);
    vscode.window.setStatusBarMessage('Log Follower: following (interact to pause)', 3000);
  }
}

function pollOnce() {
  for (const uriString of [...following]) {
    if (userTookOver.has(uriString)) continue;
    const editor = editorFor(uriString);
    if (!editor) continue;                    // not the visible tab: nothing to scroll
    const uri = editor.document.uri;
    if (uri.scheme !== 'file') continue;
    let size;
    try {
      // eslint-disable-next-line global-require
      size = require('fs').statSync(uri.fsPath).size;
    } catch {
      continue;                               // gone or not yet created
    }
    const previous = lastSize.get(uriString);
    lastSize.set(uriString, size);
    if (previous === undefined) {
      // First sight of this file: adopt its current size and scroll once, so a tab opened after
      // the producer has already written some output still lands at the end instead of the top.
      scrollToEnd(editor);
      continue;
    }
    if (size === previous) continue;
    refreshAndScroll(uriString, editor, uri);
  }
}

/** Pull this document's bytes back from disk, then pin the view to the newest line.
 *
 * `workbench.action.files.revert` is NOT usable here: it acts on the ACTIVE editor, not on this
 * one. With focus in the terminal (the normal case while a job runs) it reverted whatever tab was
 * active and left the log's stale in-memory buffer untouched, so the tab appeared to freeze
 * part-way down the file even though the poll kept firing - measured 2026-09-22, the tab sat on
 * line 15 of 501. `TextDocument.revert()` is per-document and does not care about focus, which is
 * the only correct primitive for this job.
 */
function refreshAndScroll(uriString, editor, uri) {
  const after = () => {
    for (const ed of vscode.window.visibleTextEditors) {
      if (ed.document.uri.toString() === uriString) scrollToEnd(ed);
    }
  };
  if (typeof uri.revert !== 'function') {
    after();
    return;
  }
  uri.revert().then(after, after);
}

/** Arm a change watcher for one followed file, so an append scrolls without waiting for the poll.
 *
 * A watcher is an *optimisation*, never the only trigger: it can be invalidated by a producer that
 * truncates and recreates the file, and it cannot see a file created after arming. The poll
 * remains the safety net, which is why both exist.
 */
function armWatcher(uriString) {
  if (watchers.has(uriString)) return;
  const editor = editorFor(uriString);
  if (!editor || editor.document.uri.scheme !== 'file') return;
  // eslint-disable-next-line global-require
  const path = require('path');
  const filePath = editor.document.uri.fsPath;
  try {
    const watcher = vscode.workspace.createFileSystemWatcher(
      new vscode.RelativePattern(path.dirname(filePath), path.basename(filePath)),
    );
    watcher.onDidChange(() => {
      if (!following.has(uriString) || userTookOver.has(uriString)) return;
      const ed = editorFor(uriString);
      if (ed) refreshAndScroll(uriString, ed, ed.document.uri);
    });
    watchers.set(uriString, watcher);
  } catch {
    // A watcher is an optimisation; the poll still covers this file.
  }
}

function releaseWatcher(uriString) {
  const watcher = watchers.get(uriString);
  if (watcher) {
    watcher.dispose();
    watchers.delete(uriString);
  }
}

function activate(context) {
  const settings = config();
  // Two triggers, deliberately. The watcher reacts to an append and feels instant; the poll is the
  // safety net for the cases a watcher misses (a file created after the watcher was armed, a
  // watcher invalidated by the producer's open/truncate/recreate cycle, a filesystem where change
  // events are unreliable). Neither alone is enough: events-only proved unreliable for an
  // externally-written log, and poll-only is always up to one interval stale.
  setInterval(pollOnce, settings.coalesceMs);

  // --- Pause on ANY interaction with the tab, resume only deliberately. -------------------
  //
  // The requirement is "stop scrolling the moment I touch the text or the scrollbar". Three
  // separate events have to be watched, because none of them covers the others:
  //   1. selection change      - clicking in the text, arrow keys, selecting a range;
  //   2. visible-range change  - wheeling / dragging the scrollbar (fires with no selection change);
  //   3. active-editor change  - focusing another tab, which must not leave this one scrolling.
  // Our own programmatic moves are filtered out by the self-move grace window, or the extension
  // would pause itself the first time it scrolled.
  //
  // Resume is DELIBERATE (the toggle command), never automatic. An earlier version resumed whenever
  // the last line merely became visible, so a short log - or one wheel notch near the bottom -
  // silently re-armed the follow and the view jumped out from under someone reading further up.
  const pauseInteractive = (uriString, why) => {
    if (!following.has(uriString)) return;
    if (userTookOver.has(uriString)) return;
    const self = lastSelfMove.get(uriString) || 0;
    if (Date.now() - self < SELF_MOVE_GRACE_MS) return;
    userTookOver.add(uriString);
    vscode.window.setStatusBarMessage(
      `Log Follower: paused (${why}); run "Log Follower: Toggle" to resume`, 4000,
    );
  };

  context.subscriptions.push(
    { dispose: () => { for (const w of watchers.values()) w.dispose(); watchers.clear(); } },
    vscode.window.onDidChangeTextEditorSelection((event) => {
      if (event.kind === undefined) return;
      pauseInteractive(key(event.textEditor.document.uri), 'you took control');
    }),
    vscode.window.onDidChangeTextEditorVisibleRanges((event) => {
      pauseInteractive(key(event.textEditor.document.uri), 'you scrolled');
    }),
    vscode.window.onDidChangeActiveTextEditor((editor) => {
      if (!editor) return;
      pauseInteractive(key(editor.document.uri), 'you switched tabs');
    }),
    // Opening a matching log follows it automatically, so the common case needs no command.
    vscode.workspace.onDidOpenTextDocument((doc) => {
      const { globs } = config();
      const auto = matchesGlob(doc.uri.path.split('/').pop() || '', globs);
      if (!auto) return;
      const k = key(doc.uri);
      following.add(k);
      userTookOver.delete(k);
      lastSize.delete(k);
      armWatcher(k);
    }),
    vscode.workspace.onDidCloseTextDocument((doc) => {
      const k = key(doc.uri);
      following.delete(k);
      userTookOver.delete(k);
      lastSize.delete(k);
      lastSelfMove.delete(k);
      releaseWatcher(k);
    }),
    vscode.commands.registerCommand('logFollower.start', startFollow),
    vscode.commands.registerCommand('logFollower.stop', stopFollow),
    vscode.commands.registerCommand('logFollower.toggle', toggleFollow),
    vscode.commands.registerCommand('logFollower.followThis', startFollow),
  );

  const { globs } = config();
  for (const doc of vscode.workspace.textDocuments) {
    if (matchesGlob(doc.uri.path.split('/').pop() || '', globs)) {
      following.add(key(doc.uri));
    }
  }
}

function deactivate() {
  following.clear();
  userTookOver.clear();
  lastSize.clear();
  lastSelfMove.clear();
}

module.exports = { activate, deactivate };
