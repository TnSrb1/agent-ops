"""Tests for bin/watch_release.py, bin/wilson.py, bin/loop_lag.py, bin/pr_stats.py.
No network, no real sleeping beyond a few hundred milliseconds."""

import asyncio
import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "bin" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod  # dataclasses need the module registered
    spec.loader.exec_module(mod)
    return mod


wr = load("watch_release")
wilson = load("wilson")
loop_lag = load("loop_lag")
pr_stats = load("pr_stats")


# ---- watch_release ---------------------------------------------------------------------


def S(died=0, bad=0, total=0):
    return {"died": died, "bad": bad, "total": total}


L = wr.Limits(died_max=2, bad_pct=2.0, bad_min=20)


@pytest.mark.parametrize(
    "sample, rolls",
    [
        (S(died=1), False),
        (S(died=2), True),  # >= for deaths
        (S(bad=2, total=100), False),  # exactly 2 % is not "more than 2 %"
        (S(bad=3, total=100), True),
        (S(bad=19, total=19), False),  # below the minimum number of responses
        (S(bad=1, total=20), True),  # 5 % of 20
        (S(), False),
    ],
)
def test_evaluate_thresholds(sample, rolls):
    assert (wr.evaluate(sample, L) is not None) is rolls


@pytest.mark.parametrize(
    "text, want",
    [
        ('{"died":0,"bad":1,"total":10}', S(0, 1, 10)),
        ('noise\n{"died":1,"bad":0,"total":5}\n', S(1, 0, 5)),
        ("", None),
        ("not json", None),
        ('{"died":0,"bad":11,"total":10}', None),  # more bad than total: nonsense
        ('{"died":-1,"bad":0,"total":10}', None),
        ('{"died":0,"bad":0}', None),
    ],
)
def test_parse_sample(text, want):
    assert wr.parse_sample(text) == want


class Clock:
    def __init__(self):
        self.t = 1000.0

    def now(self):
        return self.t

    def sleep(self, s):
        self.t += s


def run_watch(samples, window=100, interval=30, grace=10):
    clk = Clock()
    it = iter(samples)
    seen = []

    def probe(since):
        seen.append(since)
        return next(it)

    reason, last = wr.watch(
        probe, L, window, interval, grace, clk.now, clk.sleep, log=lambda s: None
    )
    return reason, last, seen


def test_healthy_window_runs_to_the_end_and_counts_after_grace():
    reason, _last, seen = run_watch([S(0, 0, 10)] * 10)
    assert reason is None
    assert len(seen) == 4  # 30, 60, 90, 120 s: the first tick after 100 s ends it
    assert seen[0] == 1010.0  # counting starts after the grace period


def test_rolls_back_at_the_first_bad_step():
    reason, _, seen = run_watch([S(0, 0, 5), S(died=2), S(0, 0, 5)])
    assert "died x2" in reason
    assert len(seen) == 2


def test_unreadable_probe_is_not_a_reason_to_roll_back():
    reason, last, _ = run_watch([None, None, None, None])
    assert reason is None
    assert last == S()


def test_cli_rolls_back_and_runs_the_rollback_command(tmp_path):
    marker = tmp_path / "rolled"
    probe = 'echo \'{"died": 3, "bad": 0, "total": 0}\''
    done = subprocess.run(
        [
            sys.executable,
            str(ROOT / "bin" / "watch_release.py"),
            "--probe",
            probe,
            "--rollback",
            f"touch {marker}",
            "--window",
            "5",
            "--interval",
            "0.1",
            "--grace",
            "0",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 3, done.stderr
    assert marker.exists()
    assert json.loads(done.stdout)["rolled_back"] is True


def test_cli_healthy_does_not_run_rollback(tmp_path):
    marker = tmp_path / "rolled"
    done = subprocess.run(
        [
            sys.executable,
            str(ROOT / "bin" / "watch_release.py"),
            "--probe",
            'echo \'{"died": 0, "bad": 0, "total": 50}\'',
            "--rollback",
            f"touch {marker}",
            "--window",
            "0.3",
            "--interval",
            "0.1",
            "--grace",
            "0",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    assert not marker.exists()


def test_cli_reports_a_failed_rollback_with_its_own_code():
    done = subprocess.run(
        [
            sys.executable,
            str(ROOT / "bin" / "watch_release.py"),
            "--probe",
            'echo \'{"died": 5, "bad": 0, "total": 0}\'',
            "--rollback",
            "exit 1",
            "--window",
            "5",
            "--interval",
            "0.1",
            "--grace",
            "0",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 4


def test_probe_gets_the_window_start_in_its_environment():
    out = wr.run_probe(
        'echo "{\\"died\\": $WATCH_SINCE, \\"bad\\": 0, \\"total\\": 0}"', 1234
    )
    assert out == S(died=1234)


# ---- wilson ----------------------------------------------------------------------------


def test_wilson_literals():
    # Values computed independently (z = 1.96).
    assert wilson.wilson_lower(1, 3) == pytest.approx(0.0615, abs=1e-3)
    assert wilson.wilson_lower(400, 6000) == pytest.approx(0.0606, abs=1e-3)
    assert wilson.wilson_lower(0, 100) == 0.0
    assert wilson.wilson_lower(0, 0) == 0.0


def test_small_sample_does_not_alert_but_large_one_does():
    # The same 33 % raw rate: 1 of 3 is noise, 400 of 1200 is not.
    assert wilson.should_alert(1, 3, 0.2) is False
    assert wilson.should_alert(400, 1200, 0.2) is True
    # Raw "rate > 5 %" would fire on 1/3; the lower bound is 6 % there, so use 10 %.
    assert wilson.should_alert(1, 3, 0.10) is False


def test_wilson_rejects_impossible_counts():
    with pytest.raises(ValueError):
        wilson.wilson_lower(5, 3)


def test_wilson_cli_exit_codes():
    exe = [sys.executable, str(ROOT / "bin" / "wilson.py")]
    ok = subprocess.run(
        [*exe, "1", "3", "0.2"], capture_output=True, text=True, check=False
    )
    bad = subprocess.run(
        [*exe, "400", "1200", "0.2"], capture_output=True, text=True, check=False
    )
    assert (ok.returncode, bad.returncode) == (0, 1)
    assert "ALERT" in bad.stdout


# ---- loop_lag --------------------------------------------------------------------------


def blocker():
    time.sleep(0.9)  # blocks the loop thread


def test_watchdog_names_the_blocking_function():
    reports = []

    async def scenario():
        wd = loop_lag.LoopLagWatchdog(threshold=0.3, on_stall=reports.append)
        wd.start()
        await asyncio.sleep(0.3)
        blocker()
        await asyncio.sleep(0.5)  # let the loop recover and the report fire
        await wd.stop()

    asyncio.run(scenario())
    assert len(reports) == 1
    r = reports[0]
    assert "blocker" in r.where
    assert 600 <= r.blocked_ms <= 1500
    assert r.samples >= 2  # sampled on several ticks, not once


def test_watchdog_is_silent_for_a_healthy_loop():
    reports = []

    async def scenario():
        wd = loop_lag.LoopLagWatchdog(threshold=0.3, on_stall=reports.append)
        wd.start()
        for _ in range(8):
            await asyncio.sleep(0.05)
        await wd.stop()

    asyncio.run(scenario())
    assert reports == []


def test_a_raising_callback_does_not_kill_the_watchdog():
    calls = []

    def bad(report):
        calls.append(report)
        raise RuntimeError("boom")

    async def scenario():
        wd = loop_lag.LoopLagWatchdog(threshold=0.3, on_stall=bad)
        wd.start()
        await asyncio.sleep(0.2)
        blocker()
        await asyncio.sleep(0.4)
        blocker()
        await asyncio.sleep(0.4)
        await wd.stop()

    asyncio.run(scenario())
    assert len(calls) == 2


def test_idle_frame_detection():
    assert loop_lag._is_idle("selectors.py:select:468")
    assert not loop_lag._is_idle("app.py:handler:12")


# ---- pr_stats --------------------------------------------------------------------------


def pr(state, created, merged=None, ref="worker/x"):
    return {
        "state": state,
        "createdAt": created,
        "mergedAt": merged,
        "headRefName": ref,
    }


def test_plus_rounds_down():
    assert pr_stats.plus(988) == "900+"
    assert pr_stats.plus(1038) == "1,000+"
    assert pr_stats.plus(42) == "40+"
    assert pr_stats.plus(7) == "7"


def test_percentile_nearest_rank():
    assert pr_stats.percentile([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 0.9) == 9
    assert pr_stats.percentile([5], 0.9) == 5
    assert pr_stats.percentile([], 0.9) == 0.0


def test_compute_counts_and_durations():
    prs = [
        pr("MERGED", "2026-05-01T00:00:00Z", "2026-05-01T01:00:00Z"),
        pr("MERGED", "2026-05-02T00:00:00Z", "2026-05-02T03:00:00Z"),
        pr("MERGED", "2026-05-03T00:00:00Z", "2026-05-05T00:00:00Z"),  # 48 h
        pr("CLOSED", "2026-05-03T00:00:00Z"),
        pr("OPEN", "2026-05-04T00:00:00Z"),
        pr("MERGED", "2026-05-01T00:00:00Z", "2026-05-01T00:30:00Z", ref="human/y"),
    ]
    out = pr_stats.compute(prs, "worker/")
    assert (out["total"], out["merged"], out["closed_unmerged"], out["open"]) == (
        5,
        3,
        1,
        1,
    )
    assert out["open_to_merge_hours_median"] == 3.0
    assert out["open_to_merge_hours_p90"] == 48.0
    assert out["merged_within_24h_share"] == pytest.approx(0.667, abs=1e-3)
    assert out["span_days"] == 5


def test_compute_with_no_merges_has_no_durations():
    out = pr_stats.compute([pr("OPEN", "2026-05-01T00:00:00Z")], "worker/")
    assert "open_to_merge_hours_median" not in out
