#!/usr/bin/env python3
"""Stop hook for a headless worker: refuse to end the run until the work is shippable.

On a worker branch (prefix below) the run may only finish when
  1. the working tree is clean,
  2. the gate command passes on the CURRENT HEAD,
  3. HEAD is pushed to the remote,
  4. a draft PR exists for the branch.

It exists because a worker once started its gate in the background, ended its turn, and
the headless run killed the gate with it: no PR. And because a non-draft PR was picked
up by auto-merge before anyone reviewed it.

A blocked stop is reported as {"decision": "block", "reason": ...}: the model reads the
reason and keeps working. To avoid paying for an endless loop, at most MAX_BLOCKS
blocks are issued per session; after that the stop is allowed and the skip is logged.

Configuration (environment, all optional):
  AGENT_OPS_BRANCH_PREFIX  branches this applies to        (default: worker/)
  AGENT_OPS_GATE_CMD       gate command, run in the repo   (default: bash scripts/gate.sh)
  AGENT_OPS_GATE_TIMEOUT   seconds before the gate is cut  (default: 840)
  AGENT_OPS_REMOTE         remote name                     (default: origin)
  AGENT_OPS_MAX_BLOCKS     blocks per session              (default: 3)
  AGENT_OPS_STATE_DIR      counters, gate stamps, log      (default: ~/.local/state/agent-ops)
"""

import json
import os
import subprocess
import sys
import time

PREFIX = os.environ.get("AGENT_OPS_BRANCH_PREFIX", "worker/")
GATE_CMD = os.environ.get("AGENT_OPS_GATE_CMD", "bash scripts/gate.sh")
GATE_TIMEOUT = int(os.environ.get("AGENT_OPS_GATE_TIMEOUT", "840"))
REMOTE = os.environ.get("AGENT_OPS_REMOTE", "origin")
MAX_BLOCKS = int(os.environ.get("AGENT_OPS_MAX_BLOCKS", "3"))
STATE = os.path.expanduser(
    os.environ.get("AGENT_OPS_STATE_DIR", "~/.local/state/agent-ops")
)


def main() -> int:
    os.makedirs(STATE, exist_ok=True)
    payload = json.load(sys.stdin)
    cwd = payload.get("cwd") or os.getcwd()
    sid = payload.get("session_id", "x")

    def run(*argv, shell=False, timeout=None):
        return subprocess.run(
            argv[0] if shell else list(argv),
            shell=shell,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

    def git(*args):
        return run("git", *args).stdout.strip()

    def log(msg):
        with open(f"{STATE}/stop.log", "a") as f:
            f.write(f"{time.strftime('%F %T')} {sid[:8]} {cwd} {msg}\n")

    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    if not branch.startswith(PREFIX):
        return 0  # not a worker branch: coordinator and humans are never gated

    counter = f"{STATE}/{sid}.n"
    n = int(open(counter).read()) if os.path.exists(counter) else 0
    if n >= MAX_BLOCKS:
        log(f"SKIP after {MAX_BLOCKS} blocks, branch {branch}")
        return 0

    def block(reason):
        with open(counter, "w") as f:
            f.write(str(n + 1))
        log(f"BLOCK {n + 1}: {reason[:120]}")
        print(
            json.dumps(
                {
                    "decision": "block",
                    "reason": f"Worker stop gate ({n + 1}/{MAX_BLOCKS}): {reason} "
                    "If the task is blocked, still commit a report stating why, "
                    "push, and open a draft PR.",
                }
            )
        )
        return 0

    dirty = git("status", "--porcelain")
    if dirty:
        return block(
            f"uncommitted changes:\n{dirty[:500]}\nCommit (or remove) and push."
        )

    head = git("rev-parse", "HEAD")
    stamp = f"{STATE}/gate_pass_{head}"
    if not os.path.exists(stamp):
        try:
            r = run(GATE_CMD, shell=True, timeout=GATE_TIMEOUT)
        except subprocess.TimeoutExpired:
            return block(f"gate timed out after {GATE_TIMEOUT}s on {head[:7]}.")
        if r.returncode != 0:
            tail = (r.stdout + r.stderr)[-1500:]
            return block(f"gate FAILED on {head[:7]}. Tail:\n{tail}\nFix and commit.")
        if git("rev-parse", "HEAD") != head:
            return block("HEAD moved while the gate ran; run it again.")
        with open(stamp, "w") as f:
            f.write(branch)

    run("git", "fetch", "-q", REMOTE)
    if git("rev-parse", f"{REMOTE}/{branch}") != head:
        return block(f"HEAD {head[:7]} is not pushed: git push -u {REMOTE} {branch}.")

    listing = run(
        "gh",
        "pr",
        "list",
        "--state",
        "all",
        "--head",
        branch,
        "--json",
        "number,isDraft,state",
    )
    prs = json.loads(listing.stdout.strip() or "[]")
    if not prs:
        return block(f"no PR for {branch}: gh pr create --draft, report in the body.")
    if prs[0]["state"] == "OPEN" and not prs[0]["isDraft"]:
        return block(f"PR {prs[0]['number']} is not a draft: undo its ready state.")
    log(f"OK {branch} {head[:7]} PR {prs[0]['number']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
