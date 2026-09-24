// Log Follower: keep a growing log file scrolled to its tail in an editor tab, and stop the
// moment the user takes control of that tab.
//
// COST IS THE DESIGN CONSTRAINT. An earlier log-following extension measured ~110% of one core
// while following a file and was rejected for it ("a tool that eats a core to follow a text file
// is badly written and must not be used"). This one is built to cost nothing while idle and very
// little while following:
//
//   * One coalesced poll per coalesceMs, not a per-frame timer. 400 ms by default is 2.5 wakes a
//     second; each wake is a stat() plus, only when the size changed, one revert()/revealRange().
//   * Nothing at all while paused by the user, or while the followed file is not the visible tab.
//   * Optionally one FileSystemWatcher per followed file (armWatcher), purely as an optimisation so
//     an append scrolls without waiting for the poll. It is NEVER the only trigger - a producer
//     that truncates and recreates the file invalidates the watcher - so the poll stays the safety
//     net. (An earlier version of this comment claimed there was no watcher at all; v0.7 added one
//     and the comment was left behind, which is how the README ended up claiming the opposite.)
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

/** Uris we have programmatically scrolled at least once.
 *
 * This is a ONE-TIME FLAG, not a timestamp, and it is the whole answer to "is this event ours or
 * the user's?". Before our first scroll a document-open event fires a visible-range change with the
 * tail off-screen (a long log opens at the top), which must NOT count as the user scrolling away.
 * After our first scroll, whether to pause is decided purely by POSITION (is the tail visible?),
 * which cannot drift and needs no timing. The earlier attempts all failed on timing: a grace-window
 * timestamp leaked under fast writes (our own event arrives after it expires), and while the log
 * grew, scrollToEnd re-stamped it on every append so it never expired and the user's scrolls were
 * swallowed forever - the bug the user reported. No timestamps, no counters.
 */
const hasScrolled = new Set();

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

/** True when the editor is scrolled to the tail - the last line is visible near the bottom.
 *
 * This is the honest answer to "did the user scroll away?", and it is what decides whether the
 * follow pauses. A couple of lines of slack covers the viewport edge and a trailing render.
 */
function isShowingTail(editor) {
  const doc = editor.document;
  if (doc.lineCount === 0) return true;
  const ranges = editor.visibleRanges;
  if (ranges.length === 0) return true;
  return ranges[ranges.length - 1].end.line >= doc.lineCount - 3;
}

/** True when this VS Code window is the frontmost one.
 *
 * Used to decide whether the follow may MOVE the view. It must not while the window is in the
 * background: setting `editor.selection` activates its editor group, and on macOS that brings the
 * whole VS Code window to the front - so following a log from another application dragged VS Code
 * over the top of whatever the user was doing, once per append (user report 2026-09-24: the
 * follower "is forcing vscode to be top window and it should not do that"). A background window
 * cannot be being read, so while it is unfocused the follow degrades to keeping the buffer current
 * (refreshAndScroll still reverts the document) and the tail is pinned again on the next poll, or
 * immediately when the window is re-focused (onDidChangeWindowState below).
 */
function windowIsFocused() {
  return vscode.window.state ? vscode.window.state.focused : true;
}

function scrollToEnd(editor) {
  const doc = editor.document;
  if (doc.lineCount === 0) return;
  // Never move the cursor or the view while this window is in the background - see
  // windowIsFocused(). The buffer is still refreshed; the view catches up when the window is
  // focused again.
  if (!windowIsFocused()) return;
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
  hasScrolled.add(key(doc.uri));
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
    if (size < previous) {
      // The file SHRANK, which for these logs means the producer truncated it: a new session/run has
      // started in the same tab. The pause is per-session by design (user instruction 2026-09-23:
      // "on the next session, it should autoscroll again by default"), so this is where it ends -
      // following re-arms on its own, with no command to remember.
      userTookOver.delete(uriString);
      hasScrolled.delete(uriString);   // re-stamped by the scroll below, for the new document view
      vscode.window.setStatusBarMessage(
        'Log Follower: new session detected - following resumed', 3000,
      );
    }
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
  // Resume is DELIBERATE WITHIN A RUN (the toggle command): an earlier version resumed whenever the
  // last line merely became visible, so a short log - or one wheel notch near the bottom - silently
  // re-armed the follow and the view jumped out from under someone reading further up. But a pause
  // must never outlive the run it was made in: when the producer truncates the file for the next
  // session, pollOnce clears the pause and following re-arms by default (user instruction
  // 2026-09-23: "on the next session, it should autoscroll again by default").
  const pauseInteractive = (uriString, why, force = false) => {
    if (!following.has(uriString)) return;
    if (userTookOver.has(uriString)) return;
    // Before our first scroll there is nothing for the user to have taken control of: the only
    // event that can fire with the tail off-screen is the document OPENING, not a person reading.
    if (!hasScrolled.has(uriString)) return;
    // After that, position decides: our own scroll always leaves the tail visible, so a
    // tail-visible event is ours (or a click at the bottom - harmless to keep following), and a
    // tail-off-screen event can only be the user scrolling away to read. `force` overrides that for
    // a genuine text selection, where the user is inside the text even if the tail is still
    // visible. No timing, no counting - position cannot drift.
    const editor = editorFor(uriString);
    if (!force && editor && isShowingTail(editor)) return;
    userTookOver.add(uriString);
    // The pause is per RUN, not permanent (user instruction 2026-09-23): the producer truncating
    // the file for the next run clears it, so nobody has to remember to re-enable the follow.
    vscode.window.setStatusBarMessage(
      `Log Follower: paused for this run (${why}); resumes on the next run, or run "Log Follower: Toggle"`,
      5000,
    );
  };

  context.subscriptions.push(
    { dispose: () => { for (const w of watchers.values()) w.dispose(); watchers.clear(); } },
    // A SELECTION is the clearest "I am reading this" signal there is: highlighting text with the
    // mouse (or shift-arrowing) pauses even when the tail is still on screen, because the user is
    // now working inside the text and any scroll moves it out from under them. Our own scroll
    // leaves a zero-length cursor at the end, so an EMPTY selection is never a pause - only a real
    // range is. `event.kind === undefined` means this extension set the selection itself.
    vscode.window.onDidChangeTextEditorSelection((event) => {
      if (event.kind === undefined) return;
      const highlighting = event.selections.some((s) => !s.isEmpty);
      pauseInteractive(
        key(event.textEditor.document.uri),
        highlighting ? 'you highlighted text' : 'you took control',
        highlighting,
      );
    }),
    // Wheel, scrollbar drag, page keys, minimap and goto-line all land here.
    vscode.window.onDidChangeTextEditorVisibleRanges((event) => {
      pauseInteractive(key(event.textEditor.document.uri), 'you scrolled');
    }),
    // While the window is in the background scrollToEnd() deliberately does nothing, so a followed
    // log can be behind the moment the user comes back to it. Pin every followed tab as soon as the
    // window is focused again - that is a user action, so it can never steal focus from anything.
    vscode.window.onDidChangeWindowState((state) => {
      if (!state.focused) return;
      for (const editor of vscode.window.visibleTextEditors) {
        const k = key(editor.document.uri);
        if (following.has(k) && !userTookOver.has(k)) scrollToEnd(editor);
      }
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
      hasScrolled.delete(k);
      releaseWatcher(k);
    }),
    vscode.commands.registerCommand('logFollower.start', startFollow),
    vscode.commands.registerCommand('logFollower.stop', stopFollow),
    vscode.commands.registerCommand('logFollower.toggle', toggleFollow),
    vscode.commands.registerCommand('logFollower.followThis', startFollow),
  );

  // Adopt every matching document that is ALREADY OPEN when the extension activates.
  //
  // `onDidOpenTextDocument` only fires for documents opened *after* activation, so without this a
  // log tab that was already open when the editor started - or when the extension was reloaded -
  // is never followed, and the user sees a perfectly live log that simply does not move. That is
  // the single most likely way to hit "the log is not following" even though everything works
  // (measured 2026-09-22, on a suite run started with the progress tab already open).
  const { globs } = config();
  for (const doc of vscode.workspace.textDocuments) {
    if (matchesGlob(doc.uri.path.split('/').pop() || '', globs)) {
      const k = key(doc.uri);
      following.add(k);
      userTookOver.delete(k);
      lastSize.delete(k);
      armWatcher(k);
    }
  }
  // A visible editor for an adopted document may not exist yet at activation, so scroll the ones
  // that are on screen as soon as the extension is active.
  for (const editor of vscode.window.visibleTextEditors) {
    if (following.has(key(editor.document.uri))) scrollToEnd(editor);
  }
}

function deactivate() {
  following.clear();
  userTookOver.clear();
  lastSize.clear();
  hasScrolled.clear();
}

module.exports = { activate, deactivate };
