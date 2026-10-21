"""Tests for the worker hooks. No network: git remotes are local bare repos and `gh`
is a stub script on PATH."""

import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / "hooks" / "guard_bash.py"
STOP = ROOT / "hooks" / "stop_gate.py"


def run_guard(cmd, env=None):
    return subprocess.run(
        [sys.executable, str(GUARD)],
        input=json.dumps({"tool_input": {"command": cmd}}),
        capture_output=True,
        text=True,
        env={**os.environ, **(env or {})},
    )


@pytest.mark.parametrize(
    "cmd",
    [
        "gh pr merge 12 --squash",
        "gh pr ready 12",
        "git push origin main",
        "git push origin HEAD:main",
        "git push -u origin master",
        "git push origin refs/heads/main",
        "git -C repo push origin main",
        "git push --force origin worker/x",
        "git push -f origin worker/x",
        "git push --force-with-lease origin worker/x",
        "git push origin +worker/x",
        "gh pr create --title t --body b",
        "cd repo && gh pr merge 3",
    ],
)
def test_guard_blocks(cmd):
    r = run_guard(cmd)
    assert r.returncode == 2, cmd
    assert "BLOCKED" in r.stderr


@pytest.mark.parametrize(
    "cmd",
    [
        "git push -u origin worker/feature",
        "git push origin HEAD",
        "git status; echo push main",
        "git log main..HEAD",
        "gh pr create --draft --title t --body b",
        "gh pr create -d --title t",
        "gh pr list --state all --head worker/x",
        "pytest -q",
        "git push origin worker/main-page",
    ],
)
def test_guard_allows(cmd):
    r = run_guard(cmd)
    assert r.returncode == 0, (cmd, r.stderr)


def test_guard_ignores_garbage_payload():
    r = subprocess.run(
        [sys.executable, str(GUARD)], input="not json", capture_output=True, text=True
    )
    assert r.returncode == 0


def test_guard_protected_branches_configurable():
    assert run_guard("git push origin trunk").returncode == 0
    r = run_guard("git push origin trunk", env={"AGENT_OPS_PROTECTED": "trunk"})
    assert r.returncode == 2


def test_guard_extra_deny():
    extra = json.dumps([["rm\\s+-rf\\s+/", "no recursive deletes from root"]])
    r = run_guard("rm -rf /", env={"AGENT_OPS_EXTRA_DENY": extra})
    assert r.returncode == 2 and "recursive" in r.stderr


# --- stop gate ---------------------------------------------------------------


def git(cwd, *args):
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path):
    """A clone with a local bare `origin`, on branch worker/t, one pushed commit."""
    bare = tmp_path / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", str(bare)], check=True)
    work = tmp_path / "work"
    subprocess.run(["git", "clone", "-q", str(bare), str(work)], check=True)
    git(work, "config", "user.email", "noreply@test.invalid")
    git(work, "config", "user.name", "t")
    (work / "a.txt").write_text("a\n")
    git(work, "add", "a.txt")
    git(work, "commit", "-qm", "init")
    git(work, "checkout", "-qb", "worker/t")
    git(work, "push", "-q", "-u", "origin", "worker/t")
    return work


@pytest.fixture
def stubs(tmp_path):
    """A `gh` stub whose PR list is read from $GH_PRS_FILE."""
    bindir = tmp_path / "bin"
    bindir.mkdir()
    gh = bindir / "gh"
    gh.write_text('#!/bin/sh\ncat "$GH_PRS_FILE"\n')
    gh.chmod(gh.stat().st_mode | stat.S_IEXEC)
    prs = tmp_path / "prs.json"
    prs.write_text("[]")
    return bindir, prs


def run_stop(repo, tmp_path, stubs, gate="true", sid="s1", extra=None):
    bindir, prs = stubs
    env = {
        **os.environ,
        "PATH": f"{bindir}:{os.environ['PATH']}",
        "GH_PRS_FILE": str(prs),
        "AGENT_OPS_STATE_DIR": str(tmp_path / "state"),
        "AGENT_OPS_GATE_CMD": gate,
        **(extra or {}),
    }
    r = subprocess.run(
        [sys.executable, str(STOP)],
        input=json.dumps({"cwd": str(repo), "session_id": sid}),
        capture_output=True,
        text=True,
        env=env,
    )
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout) if r.stdout.strip() else None


def test_stop_ignores_non_worker_branch(repo, tmp_path, stubs):
    git(repo, "checkout", "-q", "-b", "feature/x")
    assert run_stop(repo, tmp_path, stubs, gate="false") is None


def test_stop_blocks_dirty_tree(repo, tmp_path, stubs):
    (repo / "dirty.txt").write_text("x")
    out = run_stop(repo, tmp_path, stubs)
    assert out["decision"] == "block" and "uncommitted" in out["reason"]


def test_stop_blocks_failing_gate(repo, tmp_path, stubs):
    out = run_stop(repo, tmp_path, stubs, gate="echo boom; exit 1")
    assert out["decision"] == "block"
    assert "gate FAILED" in out["reason"] and "boom" in out["reason"]


def test_stop_blocks_unpushed_head(repo, tmp_path, stubs):
    (repo / "b.txt").write_text("b")
    git(repo, "add", "b.txt")
    git(repo, "commit", "-qm", "b")
    out = run_stop(repo, tmp_path, stubs)
    assert out["decision"] == "block" and "not pushed" in out["reason"]


def test_stop_blocks_without_pr(repo, tmp_path, stubs):
    out = run_stop(repo, tmp_path, stubs)
    assert out["decision"] == "block" and "no PR" in out["reason"]


def test_stop_blocks_non_draft_pr(repo, tmp_path, stubs):
    stubs[1].write_text(json.dumps([{"number": 7, "isDraft": False, "state": "OPEN"}]))
    out = run_stop(repo, tmp_path, stubs)
    assert out["decision"] == "block" and "not a draft" in out["reason"]


def test_stop_allows_when_everything_holds(repo, tmp_path, stubs):
    stubs[1].write_text(json.dumps([{"number": 7, "isDraft": True, "state": "OPEN"}]))
    assert run_stop(repo, tmp_path, stubs) is None
    log = (tmp_path / "state" / "stop.log").read_text()
    assert "OK worker/t" in log


def test_stop_gate_runs_on_new_head_only(repo, tmp_path, stubs):
    """A PASS is stamped per HEAD: a new commit must be gated again."""
    stubs[1].write_text(json.dumps([{"number": 7, "isDraft": True, "state": "OPEN"}]))
    marker = tmp_path / "ran"
    gate = f"echo x >> {marker}"
    assert run_stop(repo, tmp_path, stubs, gate=gate) is None
    assert run_stop(repo, tmp_path, stubs, gate=gate) is None
    assert marker.read_text().count("x") == 1  # second stop reused the stamp
    (repo / "c.txt").write_text("c")
    git(repo, "add", "c.txt")
    git(repo, "commit", "-qm", "c")
    git(repo, "push", "-q")
    assert run_stop(repo, tmp_path, stubs, gate=gate) is None
    assert marker.read_text().count("x") == 2


def test_stop_gives_up_after_max_blocks(repo, tmp_path, stubs):
    for i in range(3):
        out = run_stop(repo, tmp_path, stubs, gate="exit 1")
        assert out["decision"] == "block" and f"({i + 1}/3)" in out["reason"]
    assert run_stop(repo, tmp_path, stubs, gate="exit 1") is None  # loop breaker
    assert "SKIP" in (tmp_path / "state" / "stop.log").read_text()
