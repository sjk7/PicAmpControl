#!/usr/bin/env python3
"""Scope trace for a FAILED simulator run, and the way it gets in front of the operator.

A verdict line says a scenario failed; it does not say what the firmware did. The sample dump
that would answer it is megabytes of MDB transcript, and the CSV that carries it is only useful
once someone plots it. So a failure writes its own scope trace - the harness's signals against
time, with the interesting ones picked automatically - and opens it, which is the one artefact
worth looking at immediately (user instruction, 2026-09-25: *"When a run fails, make sure there
is a scope trace with relevant variables shown. Then show it automatically in vscode."*).

"Relevant" is decided from the data, not by hand: every signal that CHANGES during the window
gets a lane, plus the four that always matter (`RC0`/PTT, `g_ptt_active`, `g_fault_latched`,
`g_sequence_stage`). A signal that is flat for the whole run cannot explain a failure and only
makes the trace taller.

Opening is done through `open_progress_log.open_in_editor`, which never steals focus: on macOS it
uses `open -g`, and on Windows it opens only when the editor is already the foreground window (a
`code -r` there activates the window over whatever the operator is doing).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import open_progress_log  # noqa: E402

# Always drawn, whatever the data does: these are the signals that decide whether a sequence is
# running, latched or released.
ALWAYS = ["RC0", "g_ptt_active", "g_fault_latched", "g_sequence_stage"]
# The rest of the candidate set, in the order they read best on a page.
CANDIDATES = ["RC5", "RC6", "RC7", "RC1", "g_trip_reason", "g_state", "g_trip_shutdown_active",
              "g_snoop_active", "g_band_settle_active", "g_band_verify_active",
              "g_band_established", "g_band_cache_valid", "g_fc_status.frequency_khz",
              "g_fc_status.current_band", "g_fc_status.band_locked",
              "RD2", "RD3", "RD4", "RD5", "RD6", "RD7",
              "RA0", "RA1", "RA2", "RA3", "RA5", "RB1", "RB2", "RB3"]
LABELS = {"RC0": "PTT (RC0, 0=keyed)", "RC1": "SETTLE (RC1)", "RC5": "RELAYS (RC5)",
          "RC6": "TX_VCC (RC6)", "RC7": "TX_BIAS (RC7)",
          "g_ptt_active": "g_ptt_active", "g_fault_latched": "g_fault_latched",
          "g_trip_reason": "g_trip_reason", "g_sequence_stage": "g_sequence_stage",
          "g_fc_status.frequency_khz": "freq (kHz)"}


def draw_stimulus(ax, stimulus):
    """Show the injected frequency ON the frequency lane, as a light overlay with a key.

    The measured frequency alternates between the injected value and 0 (the firmware resets TMR1 on
    every 10 ms gate, and nothing else clocks it in the model), and in the band-walking scenarios the
    injected value itself steps from band to band. Without the stimulus drawn beside it the lane
    reads as a wildly unstable counter instead of what it is (user instruction, 2026-09-25: *"put
    which frequency you are inputting to the freq counter so I can see why its changing so much. Or
    you can use a light selection on that trace, with a key just under the trace."*).

    Two cases, because they need different pictures (user instruction, 2026-09-25: *"The graph is not
    showing me whether you changed the frequency stimulus and what it was ... If there is only one
    freq in the test, then that should be stated near or under the kHz trace."*):
      * ONE injected frequency for the whole recording - a light dashed line at that level and the
        value stated on the lane, because there is nothing to key;
      * several - a light shaded band per constant-frequency stretch (colour keyed by frequency),
        the step outline drawn over them, and a key with the kHz value of every swatch placed UNDER
        the lane.
    """
    if not stimulus:
        return False
    # Lazy, like the rest of this module: the harness must still run on a machine with no matplotlib.
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch

    frequencies = []
    for _start, _end, freq_khz in stimulus:
        if freq_khz not in frequencies:
            frequencies.append(freq_khz)
    if len(frequencies) == 1:
        freq_khz = frequencies[0]
        ax.axhline(freq_khz, color="#b71c1c", linewidth=0.9, linestyle="--", alpha=0.45)
        ax.text(0.004, 0.94,
                f"stimulus: {freq_khz} kHz held throughout "
                f"({len(stimulus)} injections across the whole recording)",
                transform=ax.transAxes, fontsize=6.5, va="top", color="#b71c1c")
        return True
    palette = ["#ef9a9a", "#90caf9", "#a5d6a7", "#ffe082", "#ce93d8", "#ffab91",
               "#80cbc4", "#f48fb1", "#b0bec5", "#c5e1a5"]
    colour_for = {freq_khz: palette[index % len(palette)]
                  for index, freq_khz in enumerate(frequencies)}
    for start_ms, end_ms, freq_khz in stimulus:
        ax.axvspan(start_ms, end_ms, color=colour_for[freq_khz], alpha=0.35, linewidth=0)
    times, values = [], []
    for start_ms, end_ms, freq_khz in stimulus:
        times += [start_ms, end_ms]
        values += [freq_khz, freq_khz]
    ax.plot(times, values, color="#b71c1c", linewidth=0.8, linestyle="--", alpha=0.75)
    handles = [Patch(facecolor=colour_for[freq_khz], alpha=0.45, label=f"{freq_khz} kHz")
               for freq_khz in frequencies]
    handles.append(Line2D([], [], color="#b71c1c", linestyle="--", linewidth=0.8,
                          label="injected (stimulus)"))
    # The key goes UNDER the lane, as asked: a key inside a busy lane covers the very waveform it is
    # meant to explain.
    ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.0, -0.28),
              ncol=min(len(handles), 5), fontsize=6, framealpha=0.9, handlelength=1.4,
              columnspacing=0.8, borderpad=0.4)
    return True


def add_top_time_axis(axes, times):
    """Time ticks and labels across the TOP of a stacked trace, in MILLISECONDS.

    A tall stack of lanes puts the only time axis at the very bottom, so the reader has to scroll
    to the far end to learn the horizontal scale - and on a thumbnail they cannot see it at all. The
    user asked for the timebase to be visible "always ... across the top of the traces"
    (2026-09-25). The top lane therefore carries its own ms ticks and labels as well.

    The annotation also states the SAMPLING cadence. Two traces of the same event look alike
    whether they were sampled every 1 ms or every 5 ms, and they are not equally trustworthy at a
    5 ms feature: the release window `SEQ_RELEASE_RELAYS` is only as long as `tx_vcc_delay_ms`, so
    a 5 ms-sampled trace can miss it entirely. "Sampled every N ms" makes that visible.
    """
    if not axes:
        return
    top = axes[0]
    top.tick_params(axis="x", which="both", top=True, labeltop=True, labelsize=7)
    note = "time (ms)"
    if len(times) > 1:
        deltas = sorted(times[index + 1] - times[index] for index in range(len(times) - 1))
        note += (f"     span {times[-1] - times[0]:.0f} ms     "
                 f"sampled every {deltas[len(deltas) // 2]:.1f} ms (median)")
    top.set_xlabel(note, fontsize=7, labelpad=2)
    top.xaxis.set_label_position("top")


def _series(samples, key):
    """`(values, is_analogue)` for `key`, read from the pin dict and the state dict alike."""
    pins = {"RC0", "RC1", "RC2", "RC5", "RC6", "RC7", "RD2", "RD3", "RD4", "RD5", "RD6", "RD7"}
    analogue = key.startswith("RA") or key in {"RB1", "RB2", "RB3"}
    values = []
    for _instr, pin_values, state, adc in samples:
        if key in pins:
            values.append(pin_values.get(key))
        elif analogue:
            values.append(adc.get(key))
        else:
            raw = str(state.get(key)).strip()
            # The firmware's bools print as `true`/`false`, not 1/0. Treating them as
            # unparseable numbers silently plotted them as a flat zero line - which on a FAILED
            # trace is worse than useless: `g_ptt_active` is exactly the lane that shows whether
            # an edge was seen at all.
            if raw.lower() == "true":
                values.append(1.0)
            elif raw.lower() == "false":
                values.append(0.0)
            else:
                try:
                    values.append(float(raw))
                except (TypeError, ValueError):
                    values.append(None)
    return values, analogue


def _varies(values):
    seen = [v for v in values if v is not None]
    return len(set(seen)) > 1


# `g_trip_reason` is a bit-mask (main.c `TRIP_REASON_*`). The panel prints the highest-priority
# NAME, never the raw mask, so a reconstructed screen must do the same - and 0 or an unknown bit
# has to name as "UNKNOWN" rather than print nothing.
TRIP_REASON_NAMES = [(0x10, "TEMPERATURE"), (0x01, "SWR1"), (0x02, "SWR2"), (0x08, "CURRENT"),
                     (0x20, "OVERDRIVE"), (0x04, "HARDWARE"), (0x40, "DRAIN")]
BAND_NAMES = {1: "160m", 2: "80m", 3: "40m", 4: "20m", 5: "15m", 6: "10m"}


# Firmware enum names for `g_trip_reason`, so the panel caption can quote the symbol a reader would
# grep for in main.c as well as the bit and the name the panel prints.
TRIP_REASON_ENUMS = [(0x01, "TRIP_REASON_SWR1"), (0x02, "TRIP_REASON_SWR2"),
                     (0x04, "TRIP_REASON_HWFAULT"), (0x08, "TRIP_REASON_CURRENT"),
                     (0x10, "TRIP_REASON_TEMP"), (0x20, "TRIP_REASON_OVERDRIVE"),
                     (0x40, "TRIP_REASON_DRAIN")]


def trip_reason_detail(mask) -> str:
    """`0x04 -> HARDWARE (TRIP_REASON_HWFAULT)` for the panel caption; never blank."""
    try:
        value = int(str(mask).strip())
    except (TypeError, ValueError):
        value = 0
    for bit, enum_name in TRIP_REASON_ENUMS:
        if value & bit:
            return f"0x{value:02X} -> {trip_reason_name(value)} ({enum_name})"
    return f"0x{value:02X} -> UNKNOWN (no TRIP_REASON_* bit set)"


def failure_lcd_state(samples):
    """`(state, why)` for the panel: the TRIP if one latched, else the last sample.

    The panel is supposed to show the FAILURE, not whatever the run happened to end on (user
    instruction, 2026-09-25: *"LCD at failure is supposed to be showing the failure code/enum
    string."*). A latched fault is that moment - the firmware's trip screen, which names the reason -
    even if the harness kept stepping for another 400 ms afterwards; only when nothing latched is
    the last sample the right instant.
    """
    if not samples:
        return None, "no samples"
    latched = next((sample for sample in samples
                    if sample[2].get("g_fault_latched") == "true"), None)
    if latched is not None:
        return latched[2], f"first latched sample (t={latched[0] * SECONDS_PER_INSTRUCTION * 1000:.1f} ms)"
    return samples[-1][2], "last sample of the failed window (no fault latched)"


def trip_reason_name(mask) -> str:
    try:
        value = int(str(mask).strip())
    except (TypeError, ValueError):
        return "UNKNOWN"
    for bit, name in TRIP_REASON_NAMES:
        if value & bit:
            return name
    return "UNKNOWN"


def lcd_screen(state: dict) -> tuple:
    """The two 16-character rows the firmware would be showing for `state`.

    Mirrors `show_menu_page()` in firmware/src/main.c, in its precedence order: a latched trip wins
    over everything, then the PTT-COMPLETE confirmation, then "keyed but not complete", then the
    status page (which shows `SEQ <STAGE>` when the sequence is not idle - i.e. a release that never
    finished), then the home page.

    The CHARACTERS themselves are not in the trace (the harness samples the TX and band pins, not
    the LCD data bus), so this is a faithful RECONSTRUCTION from the sampled state, not a capture.
    It is reported as such on the trace, because the distinction matters to anyone reading it as
    evidence.
    """
    import trace_ptt_sequence as harness   # lazy: the harness imports this module

    stage = harness.stage_name(state.get("g_sequence_stage"))
    stage_word = stage.split(" ", 1)[1] if " " in stage else stage
    if state.get("g_fault_latched") == "true":
        # Line 0 is the enumerator, line 1 the evidence - exactly what the firmware writes
        # (main.c, STATE_TRIP branch). The numeric half of line 1 is NOT reconstructed here: it is
        # derived from the live ADC readings and the configured limits, and inventing it would be
        # worse than showing that it is missing.
        name = trip_reason_name(state.get("g_trip_reason"))
        evidence = "TRIP LATCHED" if name in ("HARDWARE", "DRAIN", "UNKNOWN") else "[value]/[limit]"
        return (name, evidence)
    if state.get("g_ptt_complete_display_active") == "true":
        return ("PTT COMPLETE", f"TX {stage_word}")
    if state.get("g_ptt_active") == "true":
        band = BAND_NAMES.get(int(str(state.get("g_fc_status.current_band", "0")).strip() or 0), "?")
        return (f"TX {stage_word}", f"{band} {state.get('g_fc_status.frequency_khz')}kHz")
    if stage_word != "IDLE":
        return ("P=   0W SWR=1.00", f"SEQ {stage_word}")
    return ("P=   0W ........", "TEMP  25C")


def render_scope(samples, title, path, events=(), check=None, observed=None, why=None,
                 lcd_state=None, stimulus=(), lcd_caption=None):
    """Write a scope-trace PNG for `samples`; returns the path (or None if matplotlib is absent).

    `events` is a list of `(time_ms, label)`: the moments the failure is about (trip raised,
    bridge made safe, PTT released, PTT re-armed), drawn as labelled vertical lines.

    `check`, `observed` and `why` are the WORDS a reader needs beside the waveforms (user
    instruction, 2026-09-25): what the test was looking for, what the firmware actually did, and the
    assertion that failed. A trace with no prose is a puzzle - the reader has to re-derive the
    expectation from the harness source to know whether the picture is wrong. `lcd_state` is a
    sample's state dict, rendered as the 16x2 panel the firmware would be showing (see `lcd_screen`).
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.patches import Rectangle  # noqa: F401  (lcd_panel needs it via the module)
    except ImportError:
        print("matplotlib not installed; skipping scope trace (pip install matplotlib)")
        return None

    from trace_ptt_sequence import SECONDS_PER_INSTRUCTION, stage_name

    times = [s[0] * SECONDS_PER_INSTRUCTION * 1000 for s in samples]
    chosen = []
    for key in ALWAYS + CANDIDATES:
        values, analogue = _series(samples, key)
        if key in ALWAYS or _varies(values):
            chosen.append((key, values, analogue))
    if not chosen:
        return None

    prose = bool(check or observed or why or lcd_state is not None)
    fig, axes = plt.subplots(len(chosen), 1, sharex=True,
                             figsize=(12, max(4, 1.15 * len(chosen)) + (3.2 if prose else 0)))
    axes = list(axes) if hasattr(axes, "__len__") else [axes]
    for ax, (key, values, analogue) in zip(axes, chosen):
        if analogue:
            ax.plot(times, [v if v is not None else 0.0 for v in values],
                    drawstyle="steps-post", color="tab:red")
        else:
            ax.step(times, [v if v is not None else 0 for v in values], where="post")
            if key == "g_sequence_stage":
                ticks = sorted({int(v) for v in values if v is not None})
                ax.set_yticks(ticks)
                ax.set_yticklabels([stage_name(t) for t in ticks], fontsize=7)
            elif {v for v in values if v is not None} <= {0.0, 1.0}:
                ax.set_ylim(-0.2, 1.2)
                ax.set_yticks([0, 1])
        ax.set_ylabel(LABELS.get(key, key), rotation=0, labelpad=58, va="center", fontsize=8)
        ax.grid(True, alpha=0.3)
        if key == "g_fc_status.frequency_khz":
            draw_stimulus(ax, stimulus)
        for event_time, _label in events:
            ax.axvline(event_time, color="red", linestyle=":", alpha=0.5)
    # Event labels are staggered in vertical bands and drawn INSIDE the top lane: the top time
    # axis owns the space just above it, and label text sitting up there collides with the ms
    # tick labels (user instruction, 2026-09-25: the timebase must be readable across the top).
    for index, (event_time, label) in enumerate(events):
        axes[0].annotate(label, (event_time, 1.0), xytext=(4, -10 - 46 * (index % 3)),
                         textcoords="offset points", fontsize=7, rotation=90, va="top",
                         color="red")
    axes[-1].set_xlabel("time (ms, approx)")
    add_top_time_axis(axes, times)
    axes[-1].set_xlim(times[0], times[-1])

    if prose:
        fig.tight_layout(rect=(0, 0.34, 1, 0.98))
        _draw_failure_notes(fig, plt, check, observed, why, lcd_state, lcd_caption)
    else:
        fig.tight_layout(rect=(0, 0, 1, 0.98))
    fig.suptitle(title, fontsize=10)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=120)
    plt.close(fig)
    print(f"Wrote scope trace {path}")
    return path


def _draw_failure_notes(fig, plt, check, observed, why, lcd_state, lcd_caption=None):
    """The prose + the reconstructed 16x2 panel, in the band reserved under the lanes.

    The prose is ONE text object with the headings inline: drawing each wrapped line separately
    spaced them by figure fraction, which on a tall figure left a hand's width between lines (seen
    and rejected 2026-09-25). A single text object lets matplotlib space the lines properly.
    """
    import textwrap

    body = []
    if check:
        body += ["WHAT THIS TEST IS FOR",
                 *textwrap.wrap(str(check), 104), ""]
    if observed:
        body += ["WHAT THE FIRMWARE ACTUALLY DID",
                 *textwrap.wrap(str(observed), 104), ""]
    if why:
        body += ["WHY THAT IS A FAILURE",
                 *textwrap.wrap(str(why), 104)]
    if body:
        note_ax = fig.add_axes([0.30, 0.02, 0.68, 0.30])
        note_ax.axis("off")
        note_ax.text(0.0, 1.0, "\n".join(body), fontsize=8, color="#263238", va="top",
                     linespacing=1.5, transform=note_ax.transAxes)

    if lcd_state is not None:
        line1, line2 = lcd_screen(lcd_state)
        # The panel's OWN aspect is fixed (16 characters wide by 2 rows in the LCD module's drawing
        # space), so the axes height is derived from the figure size rather than picked - on a tall
        # trace the first attempt produced a stretched panel that did not look like the hardware.
        fig_width, fig_height = fig.get_size_inches()
        width_fraction = 0.24
        height_fraction = ((width_fraction * fig_width) / (7.6 / 3.1)) / fig_height
        panel_ax = fig.add_axes([0.03, 0.04, width_fraction, height_fraction])
        # Same coordinate space the LCD diagram module draws in, so the panel is the same object the
        # operator sees on the bench rather than a second, different-looking drawing of it.
        panel_ax.set_xlim(0, 7.6)
        panel_ax.set_ylim(0, 3.1)
        panel_ax.axis("off")
        try:
            from render_lcd_lifecycle_diagram import lcd_panel
        except ImportError as exc:
            # Never fail silently: a missing panel looked exactly like a panel that had been
            # deliberately left out, and the reader has no way to tell the difference.
            print(f"scope_trace: LCD panel not drawn ({exc})")
            return
        # The caption goes BELOW the box, drawn here rather than passed in: the LCD module's own
        # note sits inside the dark bezel, where its dark-grey text is unreadable. It carries the
        # fault CODE as well as the screen, because "which fault" is the question the panel is
        # asked (user instruction, 2026-09-25).
        lcd_panel(panel_ax, 0.2, 0.85, "LCD AT FAILURE (reconstructed)", line1, line2, "",
                  "#b71c1c")
        caption = lcd_caption or "last sample of the failed window"
        if lcd_state.get("g_fault_latched") == "true":
            caption += f"   g_trip_reason={trip_reason_detail(lcd_state.get('g_trip_reason'))}"
        panel_ax.text(3.8, 0.4, caption, ha="center", va="center", fontsize=7, color="#455a64")


def show(path):
    """Best-effort: put the trace in front of the operator WITHOUT stealing focus."""
    if path is None:
        return False
    return open_progress_log.open_in_editor([path], quiet=True)


def on_failure(samples, name, graph_dir, title, events=(), check=None, observed=None, why=None,
               lcd_state=None, stimulus=(), lcd_caption=None):
    """Render and show the scope trace for a failure; the caller re-raises its own error."""
    if lcd_state is None:
        lcd_state, instant = failure_lcd_state(samples)
        lcd_caption = lcd_caption or instant
    path = render_scope(samples, title, Path(graph_dir) / f"{name}_scope.png", events=events,
                        check=check, observed=observed, why=why, lcd_state=lcd_state,
                        stimulus=stimulus, lcd_caption=lcd_caption)
    show(path)
    return path
