"""run_worker.sh: argument and brief validation (DRY mode has no side effects)."""

import os
import re
import signal
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "bin" / "run_worker.sh"


def launch(tmp_path, slug, model, brief_text, **env):
    brief = tmp_path / "brief.md"
    brief.write_text(brief_text)
    return subprocess.run(
        ["bash", str(LAUNCHER), slug, model, str(brief)],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        env={
            **os.environ,
            "DRY": "1",
            "AGENT_OPS_REPO": str(tmp_path),
            "AGENT_OPS_WT_ROOT": str(tmp_path),
            **env,
        },
    )


GOOD = "See BRIEF_PREAMBLE first.\n" + "x" * 300


def test_dry_run_ok_and_has_no_side_effects(tmp_path):
    r = launch(tmp_path, "demo", "claude-haiku-5-5", GOOD)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "DRY OK" in r.stdout and "branch worker/demo" in r.stdout
    assert not (tmp_path / "wt-demo").exists()


def test_cheap_alias(tmp_path):
    r = launch(tmp_path, "demo", "cheap", GOOD)
    assert r.returncode == 0 and "model claude-haiku-5-5" in r.stdout


def test_other_model_needs_explicit_spend_word(tmp_path):
    r = launch(tmp_path, "demo", "some-bigger-model", GOOD)
    assert r.returncode == 1 and "ALLOW_EXPENSIVE" in r.stdout
    r = launch(tmp_path, "demo", "some-bigger-model", GOOD, ALLOW_EXPENSIVE="1")
    assert r.returncode == 0


def test_rejects_bad_slug(tmp_path):
    assert launch(tmp_path, "Bad Slug", "cheap", GOOD).returncode == 1


def test_rejects_tiny_brief(tmp_path):
    r = launch(tmp_path, "demo", "cheap", "BRIEF_PREAMBLE")
    assert r.returncode == 1 and "bytes" in r.stdout


def test_rejects_brief_without_preamble(tmp_path):
    r = launch(tmp_path, "demo", "cheap", "y" * 400)
    assert r.returncode == 1 and "preamble" in r.stdout


def test_warns_when_worktree_exists(tmp_path):
    (tmp_path / "wt-demo").mkdir()
    r = launch(tmp_path, "demo", "cheap", GOOD)
    assert r.returncode == 0 and "WARN" in r.stdout


# --- live launch (no network): local bare origin + a fake `claude` on PATH -------------
#
# The fake is a bash script that prints one line (unless FAKE_SILENT is set) and then
# execs `sleep` under the argv0 "claude -p", so `pgrep -f '^claude -p'` finds it and its
# cwd is the worktree, just like the real worker.

FAKE_CLAUDE = """#!/usr/bin/env bash
[ -n "${FAKE_SILENT:-}" ] || echo "started"
exec -a "claude -p" sleep 300
"""

GIT_ID = {
    "GIT_AUTHOR_NAME": "ci",
    "GIT_AUTHOR_EMAIL": "ci@noreply.invalid",
    "GIT_COMMITTER_NAME": "ci",
    "GIT_COMMITTER_EMAIL": "ci@noreply.invalid",
}


def git(cwd, *args):
    subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        env={**os.environ, **GIT_ID},
    )


def live_sandbox(tmp_path):
    origin = tmp_path / "origin.git"
    repo = tmp_path / "repo"
    wts = tmp_path / "wts"
    fake_bin = tmp_path / "bin"
    for d in (wts, fake_bin):
        d.mkdir()
    git(tmp_path, "init", "-q", "--bare", str(origin))
    git(tmp_path, "init", "-q", "-b", "main", str(repo))
    (repo / "README.md").write_text("repo\n")
    git(repo, "add", "README.md")
    git(repo, "commit", "-qm", "init")
    git(repo, "remote", "add", "origin", str(origin))
    git(repo, "push", "-q", "origin", "main")
    claude = fake_bin / "claude"
    claude.write_text(FAKE_CLAUDE)
    claude.chmod(0o755)
    return repo, wts, fake_bin


def launch_live(tmp_path, repo, wts, fake_bin, **env):
    brief = tmp_path / "brief.md"
    brief.write_text(GOOD)
    return subprocess.run(
        ["bash", str(LAUNCHER), "demo", "cheap", str(brief)],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        env={
            **os.environ,
            **GIT_ID,
            "PATH": f"{fake_bin}{os.pathsep}{os.environ['PATH']}",
            "AGENT_OPS_REPO": str(repo),
            "AGENT_OPS_WT_ROOT": str(wts),
            "LIVENESS_WAIT": "2",
            **env,
        },
    )


def stop_pid_from(stdout):
    # Only the PID this test just started; never a pattern-based kill.
    m = re.search(r"pid=(\d+)", stdout)
    if m:
        try:
            os.kill(int(m.group(1)), signal.SIGTERM)
        except ProcessLookupError:
            pass


def test_live_launch_leaves_worktree_clean(tmp_path):
    repo, wts, fake_bin = live_sandbox(tmp_path)
    r = launch_live(tmp_path, repo, wts, fake_bin)
    try:
        assert r.returncode == 0, r.stdout + r.stderr
        wt = wts / "wt-demo"
        assert (
            subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=wt,
                capture_output=True,
                text=True,
                check=True,
            ).stdout
            == ""
        )
        log = Path(re.search(r"log=(\S+)", r.stdout).group(1))
        assert log.exists() and log.parent != wt
    finally:
        stop_pid_from(r.stdout)


def test_live_launch_fails_when_process_is_silent(tmp_path):
    # A live process with an empty log after LIVENESS_WAIT is not a working run.
    repo, wts, fake_bin = live_sandbox(tmp_path)
    r = launch_live(tmp_path, repo, wts, fake_bin, FAKE_SILENT="1")
    try:
        assert r.returncode == 1 and "FAIL" in r.stdout, r.stdout + r.stderr
    finally:
        stop_pid_from(r.stdout)
