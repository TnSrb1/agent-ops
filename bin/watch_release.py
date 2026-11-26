#!/usr/bin/env python3
"""Watch a release for a few minutes after the roll-out, and roll back by itself.

A smoke test looks at one point in time. The failures that hurt show up two to five
minutes later: a supervisor kills a "hung" process, a proxy returns 502 in the middle of
a request. This tool keeps counting for a window and runs your rollback command when a
threshold is crossed.

You supply two shell commands:

  --probe     prints ONE JSON object on stdout: {"died": N, "bad": N, "total": N}
              counted from the epoch in $WATCH_SINCE until now
                died  = processes killed or restarted by the supervisor
                bad   = responses with status >= 500
                total = all responses
  --rollback  puts the previous release back (your own script)

Rules (all configurable, defaults in brackets):
  * died >= --died-max [2]                                   -> roll back
  * total >= --bad-min [20] and bad/total > --bad-pct [2] %  -> roll back
  * a probe that fails or prints garbage is NOT a reason to roll back: a broken
    measuring tool is not a broken release. It is logged and the step is skipped.
  * the first --grace [10] seconds are not counted (the old processes are still dying).

Exit code: 0 healthy, 3 rolled back, 4 rollback command failed, 2 bad usage.
Stdlib only. The decision is a pure function (`evaluate`), so it is tested without a clock.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class Limits:
    died_max: int = 2
    bad_pct: float = 2.0
    bad_min: int = 20


def parse_sample(text: str) -> dict[str, int] | None:
    """Probe output -> counters, or None if it is not usable. Never raises."""
    for line in reversed(text.strip().splitlines()):
        try:
            raw = json.loads(line)
            out = {k: int(raw[k]) for k in ("died", "bad", "total")}
        except (ValueError, KeyError, TypeError):
            continue
        if min(out.values()) >= 0 and out["bad"] <= out["total"]:
            return out
    return None


def evaluate(sample: dict[str, int], limits: Limits) -> str | None:
    """The reason to roll back, or None. Strictly greater than for the percentage."""
    if sample["died"] >= limits.died_max:
        return f"died x{sample['died']} (limit {limits.died_max})"
    if (
        sample["total"] >= limits.bad_min
        and sample["bad"] * 100 > limits.bad_pct * sample["total"]
    ):
        return f"5xx {sample['bad']}/{sample['total']} (> {limits.bad_pct:g}%)"
    return None


def run_probe(cmd: str, since: float, timeout: float = 30.0) -> dict[str, int] | None:
    env = {**os.environ, "WATCH_SINCE": str(int(since))}
    try:
        done = subprocess.run(
            cmd,
            shell=True,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None
    if done.returncode != 0:
        return None
    return parse_sample(done.stdout)


def watch(
    probe: Callable[[float], dict[str, int] | None],
    limits: Limits,
    window: float,
    interval: float,
    grace: float,
    clock: Callable[[], float] = time.time,
    sleep: Callable[[float], None] = time.sleep,
    log: Callable[[str], None] = lambda s: print(s, file=sys.stderr),
) -> tuple[str | None, dict[str, int]]:
    """Poll until the window ends. Returns (reason or None, last good sample)."""
    start = clock()
    since = start + grace
    last = {"died": 0, "bad": 0, "total": 0}
    tick = 0
    while True:
        sleep(interval)
        tick += 1
        sample = probe(since)
        if sample is None:
            log(f"watch #{tick}: probe unreadable, step skipped")
        else:
            last = sample
            log(
                f"watch #{tick}: died {sample['died']}, "
                f"5xx {sample['bad']}/{sample['total']}"
            )
            reason = evaluate(sample, limits)
            if reason:
                return reason, last
        if clock() >= start + window:
            return None, last


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--probe", required=True)
    ap.add_argument("--rollback", required=True)
    ap.add_argument("--window", type=float, default=600)
    ap.add_argument("--interval", type=float, default=30)
    ap.add_argument("--grace", type=float, default=10)
    ap.add_argument("--died-max", type=int, default=2)
    ap.add_argument("--bad-pct", type=float, default=2.0)
    ap.add_argument("--bad-min", type=int, default=20)
    a = ap.parse_args(argv)
    if a.window <= 0 or a.interval <= 0:
        print("window and interval must be positive", file=sys.stderr)
        return 2
    limits = Limits(a.died_max, a.bad_pct, a.bad_min)
    reason, last = watch(
        lambda since: run_probe(a.probe, since), limits, a.window, a.interval, a.grace
    )
    print(json.dumps({"rolled_back": bool(reason), "reason": reason, "last": last}))
    if reason is None:
        return 0
    rc = subprocess.run(a.rollback, shell=True, check=False).returncode
    return 3 if rc == 0 else 4


if __name__ == "__main__":
    sys.exit(main())
