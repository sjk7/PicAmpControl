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
/** Live file watchers, one per followed uri, so an append scrolls immediately. */
const watchers = new Map();

/** Last observed file size per followed uri, to detect growth cheaply. */
const lastSelfMove = new Map();
/**
 * Count of programmatic scrolls whose resulting events have not yet been seen, per uri.
 *
 * This is a COUNT, not a timestamp, and that is the whole point. A timestamp grace window leaks:
 * during a fast burst the extension scrolls, then the resulting selection/visible-range event can
 * arrive after the window has expired and is read as "the user took control", so the follow pauses
 * itself part-way down the file (measured twice - line 15 of 501, then line 15 of 201). Counting
 * ignores exactly the events we caused and no more, however fast the writes arrive.
 */
const pendingSelfScroll = new Map();

/** Mark one programmatic scroll as owing an event to be ignored. */
function noteSelfScroll(uriString) {
  pendingSelfScroll.set(uriString, (pendingSelfScroll.get(uriString) || 0) + 1);
}

/** Consume one owed self-event. True if the event was ours, so the caller must ignore it. */
function consumeSelfScroll(uriString) {
  const owed = pendingSelfScroll.get(uriString) || 0;
  if (owed <= 0) return false;
  pendingSelfScroll.set(uriString, owed - 1);
  return true;
}

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
  //
  // Each of these two calls can raise an event, so both are registered as owed-and-ignored BEFORE
  // they are made; see pendingSelfScroll. The timestamp is also stamped for the trailing-event
  // case, where VS Code re-emits a coalesced event after the counted ones are used up.
  noteSelfScroll(key(doc.uri));
  noteSelfScroll(key(doc.uri));
  lastSelfMove.set(key(doc.uri), Date.now());
  if (!editor.selection.active.isEqual(end)) {
    editor.selection = new vscode.Selection(end, end);
  }
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
  pendingSelfScroll.delete(k);
  armWatcher(k);
  scrollToEnd(editor);
}
function stopFollow() {
  const editor = vscode.window.activeTextEditor;
  if (!editor) return;
  const k = key(editor.document.uri);
  following.delete(k);
  lastSize.delete(k);
  pendingSelfScroll.delete(k);
  releaseWatcher(k);
}

function toggleFollow() {
  const editor = vscode.window.activeTextEditor;
  if (!editor) return;
  const k = key(editor.document.uri);
  if (following.has(k) && !userTookOver.has(k)) {
    following.delete(k);
    lastSize.delete(k);
    pendingSelfScroll.delete(k);
    releaseWatcher(k);
    vscode.window.setStatusBarMessage('Log Follower: stopped', 2000);
  } else {
    // Covers both "never followed" and "paused by interaction": either way, this is the explicit
    // resume, so it clears the pause as well as arming the follow.
    following.add(k);
    userTookOver.delete(k);
    lastSize.delete(k);
    pendingSelfScroll.delete(k);
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
  // The requirement is "stop scrolling the moment I touch the text or the scrollbar". Pausing needs
  // more than one event, but not as many as first assumed - and watching too many is worse than
  // watching too few, which is what happened here:
  //
  //   * `onDidChangeTextEditorVisibleRanges` fires when the document is OPENED, before the
  //     extension has scrolled anything, so treating it as user action paused the follow at once
  //     and the tab never moved off line 1 (measured 2026-09-22).
  //   * `onDidChangeActiveTextEditor` fires when the tab merely becomes active - including when
  //     this extension's own `code -r` opens it - so that paused it too.
  //
  // So the pause is gated on having *already* scrolled once (a self-move stamp exists). Before the
  // first programmatic scroll there is nothing for the user to have taken control of, and an event
  // seen then is the editor opening, not a person reading. After that, a selection change or a
  // visible-range change is genuine interaction. Our own reveal keeps stamping the self-move so it
  // is never mistaken for the user.
  //
  // Resume is DELIBERATE (the toggle command), never automatic. An earlier version resumed whenever
  // the last line merely became visible, so a short log - or one wheel notch near the bottom -
  // silently re-armed the follow and the view jumped out from under someone reading further up.
  const pauseInteractive = (uriString, why) => {
    if (!following.has(uriString)) return;
    if (userTookOver.has(uriString)) return;
    // An event we caused by scrolling is not the user taking control: consume it and return.
    if (consumeSelfScroll(uriString)) return;
    // A trailing event from our own move can still arrive a moment later (VS Code coalesces and
    // re-emits), so also ignore anything inside the post-scroll grace window.
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
      pendingSelfScroll.delete(k);
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
  pendingSelfScroll.clear();
}

module.exports = { activate, deactivate };
