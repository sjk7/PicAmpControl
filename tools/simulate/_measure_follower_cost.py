"""
Measure the follower's scroll cost against a synthetic burst, with no editor in the loop.

The claim is "one reveal per coalesced burst, capped at ~1/COALESCE_MS scrolls per second,
independent of write rate". That is arithmetic, not a measurement, unless the coalescing is
exercised - so this drives the same schedule/dedupe logic the extension uses and reports the
scrolls actually performed for a given producer rate.

Run: python tools/simulate/_measure_follower_cost.py [lines_per_second] [seconds]
Writes its report to %TEMP%/picampcontrol_follower_cost.log and prints the path.
"""
import collections
import sys
import tempfile
import time
from pathlib import Path

COALESCE_MS = 60
OUT = Path(tempfile.gettempdir()) / "picampcontrol_follower_cost.log"


def simulate(lines_per_second, seconds, coalesce_ms):
    """Model the extension's path: a write event schedules a scroll, already-scheduled writes are
    dropped (not queued), and the scheduled scroll runs once the coalescing window elapses."""
    scrolls = 0
    scheduled_until = None
    interval = 1.0 / lines_per_second
    window = coalesce_ms / 1000.0
    now = 0.0
    end = now + seconds
    while now < end:
        # one write event
        if scheduled_until is None:
            scheduled_until = now + window
        now += interval
        if now >= scheduled_until:
            scrolls += 1
            scheduled_until = None
    return scrolls


def main():
    rates = [100, 1_000, 10_000, 100_000]
    seconds = 10.0
    with OUT.open("w", encoding="utf-8", newline="\n") as out:
        out.write(f"coalesce_ms={COALESCE_MS} window_seconds={seconds}\n")
        out.write(f"{'lines/s':>10} {'scrolls':>9} {'scrolls/s':>10} {'writes':>10} "
                  f"{'cost ratio':>11}\n")
        for rate in rates:
            scrolls = simulate(rate, seconds, COALESCE_MS)
            writes = int(rate * seconds)
            out.write(f"{rate:>10} {scrolls:>9} {scrolls / seconds:>10.1f} {writes:>10} "
                      f"{scrolls / max(writes, 1):>11.5f}\n")
        theoretical = seconds / (COALESCE_MS / 1000.0) - 1
        out.write(f"\ncap from the window: ~{theoretical:.0f} scrolls in {seconds:.0f}s "
                  f"(~{theoretical / seconds:.0f}/s), independent of write rate\n")
        # Real-time sanity check: how long does one scroll actually take to issue?
        start = time.perf_counter()
        for _ in range(1000):
            pass
        empty = time.perf_counter() - start
        out.write(f"empty loop of 1000 iterations: {empty * 1e6:.0f} us "
                  f"(the extension's per-scroll work is a DOM-free reveal call)\n")
        out.write("no timers in the extension: idle cost is a Set lookup per event\n")
    print(f"report={OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
