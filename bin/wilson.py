#!/usr/bin/env python3
"""Alert on the lower bound of a rate, not on the raw rate.

"share of failures > 20 %" fires on 1 failure out of 3 (33 %) — a single unlucky event on a
tiny sample. The Wilson score interval answers a different question: "even on the optimistic side of the
noise, is the rate above the threshold?" Alert only when the LOWER bound is above it.

  python3 bin/wilson.py <failures> <total> <threshold>     # e.g. 1 3 0.2 → ok; 12 30 0.2 → ALERT
Prints the bound and ALERT or ok; exit code 1 on ALERT, 0 on ok.
"""

from __future__ import annotations

import math
import sys


def wilson_lower(k: int, n: int, z: float = 1.96) -> float:
    """Lower bound of the Wilson score interval for k successes out of n (z=1.96: 95 %)."""
    if n <= 0:
        return 0.0
    if not 0 <= k <= n:
        raise ValueError("need 0 <= k <= n")
    p = k / n
    z2 = z * z
    centre = p + z2 / (2 * n)
    spread = z * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n))
    return max(0.0, (centre - spread) / (1 + z2 / n))


def should_alert(k: int, n: int, threshold: float, z: float = 1.96) -> bool:
    return wilson_lower(k, n, z) > threshold


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 3:
        print(__doc__)
        return 2
    k, n, thr = int(args[0]), int(args[1]), float(args[2])
    low = wilson_lower(k, n)
    alert = low > thr
    print(
        f"rate {k}/{n} lower bound {low:.4f} threshold {thr:g}: {'ALERT' if alert else 'ok'}"
    )
    return 1 if alert else 0


if __name__ == "__main__":
    sys.exit(main())
