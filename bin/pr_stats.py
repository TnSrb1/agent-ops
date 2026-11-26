#!/usr/bin/env python3
"""Numbers about a stream of AI-written PRs, from the hosting service's own data.

    gh pr list --state all --limit 3000 \\
        --json number,state,createdAt,mergedAt,closedAt,headRefName > prs.json
    python3 bin/pr_stats.py prs.json --prefix worker/

Prints JSON. Every figure is a count or a duration taken from timestamps; nothing is
estimated. Publish a figure through `plus()` (round DOWN to a threshold and add "+"), so a
claim is never above the measurement.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from datetime import UTC, datetime


def _ts(value: str) -> datetime:
    return datetime.fromisoformat(value).astimezone(UTC)


def plus(value: int) -> str:
    """Round DOWN to a threshold and add '+': 987 -> '900+', 1038 -> '1,000+', 42 -> '40+'."""
    step = 10 if value < 100 else 100
    floor = value // step * step
    return f"{floor:,}+" if floor else str(value)


def percentile(sorted_vals: list[float], q: float) -> float:
    """Nearest-rank percentile of an ascending list (q in 0..1)."""
    if not sorted_vals:
        return 0.0
    rank = max(1, math.ceil(q * len(sorted_vals)))
    return sorted_vals[rank - 1]


def compute(prs: list[dict], prefix: str) -> dict:
    mine = [p for p in prs if p.get("headRefName", "").startswith(prefix)]
    merged = [p for p in mine if p.get("state") == "MERGED" and p.get("mergedAt")]
    closed = [p for p in mine if p.get("state") == "CLOSED"]
    opened = [p for p in mine if p.get("state") == "OPEN"]
    hours = sorted(
        (_ts(p["mergedAt"]) - _ts(p["createdAt"])).total_seconds() / 3600
        for p in merged
    )
    out: dict = {
        "prefix": prefix,
        "total": len(mine),
        "merged": len(merged),
        "closed_unmerged": len(closed),
        "open": len(opened),
    }
    if hours:
        first = min(_ts(p["mergedAt"]) for p in merged)
        last = max(_ts(p["mergedAt"]) for p in merged)
        days = (last.date() - first.date()).days + 1
        out.update(
            first_merge=first.date().isoformat(),
            last_merge=last.date().isoformat(),
            span_days=days,
            merged_per_day=round(len(merged) / days, 1),
            open_to_merge_hours_median=round(statistics.median(hours), 1),
            open_to_merge_hours_p90=round(percentile(hours, 0.9), 1),
            merged_within_24h_share=round(sum(h <= 24 for h in hours) / len(hours), 3),
        )
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("json_file")
    ap.add_argument("--prefix", default="worker/")
    a = ap.parse_args(argv)
    with open(a.json_file, encoding="utf-8") as fh:
        prs = json.load(fh)
    print(json.dumps(compute(prs, a.prefix), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
