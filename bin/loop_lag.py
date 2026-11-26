"""A watchdog for stalls of an asyncio event loop, with the culprit's location.

A thread checks a heartbeat the loop writes every 100 ms. When the heartbeat is older than
the threshold, the thread takes a stack sample of the loop thread on EVERY tick of the stall
(not once at its start) and reports the most frequent frame when the loop recovers.

Why every tick: the frame at the first tick is often an innocent bystander. The code that
holds the loop is where it spent most ticks.

Why `other-thread`: when the loop's own frame is just the event loop waiting (the loop is
starved of the GIL, not busy itself), the culprit is a different thread. The report then
names the most frequent frame among the other threads.

    wd = LoopLagWatchdog(threshold=0.5, on_stall=lambda r: log.warning(r))
    # inside the running loop:
    wd.start()
    ...
    await wd.stop()

Stdlib only. `on_stall` receives a `StallReport`; it must not raise (it is guarded anyway).
"""

from __future__ import annotations

import asyncio
import collections
import sys
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

HEARTBEAT = 0.1
# Frames that only say "the loop is waiting": the loop is idle there, not blocked.
_IDLE_FILES = ("selectors.py", "base_events.py", "events.py", "runners.py")


@dataclass(frozen=True)
class StallReport:
    blocked_ms: int
    where: str  # most frequent loop-thread frame, "file:function:line"
    samples: int  # ticks that hit that frame
    total: int  # ticks sampled during the stall
    other_thread: str | None  # set when the loop frame was idle


def _frame_label(frame, depth: int = 3) -> str:
    parts = []
    while frame is not None and len(parts) < depth:
        code = frame.f_code
        name = code.co_filename.rsplit("/", 1)[-1]
        parts.append(f"{name}:{code.co_name}:{frame.f_lineno}")
        frame = frame.f_back
    return " < ".join(parts)


def _is_idle(label: str) -> bool:
    return label.split(":", 1)[0] in _IDLE_FILES


def _sample(loop_tid: int | None, me: int, counts: dict, others: dict) -> None:
    frames = sys._current_frames()
    if loop_tid is not None and loop_tid in frames:
        label = _frame_label(frames[loop_tid])
        counts[label] = counts.get(label, 0) + 1
    names = {t.ident: t.name for t in threading.enumerate()}
    for tid, frame in frames.items():
        if tid in (loop_tid, me):
            continue
        key = (names.get(tid, str(tid)), _frame_label(frame))
        others[key] = others.get(key, 0) + 1


class LoopLagWatchdog:
    def __init__(
        self,
        threshold: float = 0.5,
        on_stall: Callable[[StallReport], None] | None = None,
    ) -> None:
        self.threshold = threshold
        self._on_stall = on_stall or (lambda report: None)
        self._beat = time.monotonic()
        self._stop = threading.Event()
        self._loop_tid: int | None = None
        self._thread: threading.Thread | None = None
        self._task: asyncio.Task | None = None

    async def _heartbeat(self) -> None:
        while True:
            self._beat = time.monotonic()
            await asyncio.sleep(HEARTBEAT)

    def start(self) -> None:
        """Call from inside the running loop."""
        self._loop_tid = threading.get_ident()
        self._beat = time.monotonic()
        self._task = asyncio.get_running_loop().create_task(self._heartbeat())
        self._thread = threading.Thread(target=self._run, name="loop-lag", daemon=True)
        self._thread.start()

    async def stop(self) -> None:
        self._stop.set()
        if self._task is not None:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
        if self._thread is not None:
            self._thread.join(timeout=1.0)

    def _run(self) -> None:
        counts: dict[str, int] = {}
        others: dict[tuple[str, str], int] = {}
        stalled = False
        stall_beat = 0.0
        me = threading.get_ident()
        sample_from = max(2 * HEARTBEAT, self.threshold / 2)
        while not self._stop.wait(HEARTBEAT):
            try:
                lag = time.monotonic() - self._beat
                if lag > self.threshold:
                    stalled = True
                if lag > sample_from:
                    if not counts:
                        stall_beat = self._beat
                    _sample(self._loop_tid, me, counts, others)
                elif counts:
                    if stalled:
                        blocked = int((self._beat - stall_beat) * 1000)
                        self._report(counts, others, blocked)
                    counts, others, stalled = {}, {}, False
            except Exception:  # noqa: BLE001 - a watchdog must not die
                counts, others, stalled = {}, {}, False

    def _report(self, counts: dict, others: dict, blocked_ms: int) -> None:
        where, hits = max(counts.items(), key=lambda kv: (kv[1], kv[0]))
        other = None
        if others and _is_idle(where):
            (name, stack), _ = max(others.items(), key=lambda kv: (kv[1], kv[0]))
            other = f"{name}: {stack}"
        report = StallReport(blocked_ms, where, hits, sum(counts.values()), other)
        try:
            self._on_stall(report)
        except Exception:  # noqa: BLE001, S110
            pass


def top_places(places: collections.Counter, n: int = 3) -> list[tuple[str, int]]:
    """Stable top-N for a daily summary: count descending, then name."""
    return sorted(places.items(), key=lambda kv: (-kv[1], kv[0]))[:n]
