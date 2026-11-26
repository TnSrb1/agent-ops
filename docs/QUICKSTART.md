# Quickstart: from a clean machine to a first accepted PR

About 15 minutes. Part A needs no network and no paid run, and it proves that the guards
work. Part B starts a real worker and accepts its PR.

Part A was run step by step in an empty directory before this page was published. Part B
needs a GitHub account and a Claude Code login, so it is written from the launcher's code
and its tests, not from a recorded run; see `COMPATIBILITY.md` for what is verified.

## Prerequisites

| Tool | Check | Why |
|---|---|---|
| `git` 2.30+ | `git --version` | worktrees, `merge-base` |
| `python3` 3.10+ | `python3 --version` | hooks and tools use the standard library only |
| `gh` (GitHub CLI), logged in | `gh auth status` | draft PRs (Part B only) |
| `claude` (Claude Code) 2.1+ | `claude --version` | the worker (Part B only) |

Optional: `pytest`, to run this kit's own tests.

## Part A. Install and prove the guards (no network)

```bash
# 1. Get the kit.
git clone https://github.com/TnSrb1/agent-ops ~/agent-ops
cd ~/agent-ops && python3 -m pytest -q tests        # expect: all passed

# 2. A playground repository with a local "remote" and a trivial gate.
mkdir -p ~/ops-demo && cd ~/ops-demo
git init -q -b main work && git init -q --bare remote.git
cd work
git config user.name demo && git config user.email demo@noreply.invalid
git remote add origin ../remote.git
mkdir -p scripts && printf '#!/usr/bin/env bash\necho GATE PASS\n' > scripts/gate.sh
git add -A && git commit -qm "init" && git push -q -u origin main

# 3. The guard blocks what a worker must not do. Exit code 2 = blocked.
G=~/agent-ops/hooks/guard_bash.py
echo '{"tool_input":{"command":"gh pr merge 5 --squash"}}' | python3 $G; echo "exit=$?"
echo '{"tool_input":{"command":"git push origin main"}}'   | python3 $G; echo "exit=$?"
echo '{"tool_input":{"command":"git status"}}'             | python3 $G; echo "exit=$?"
# expect: exit=2, exit=2, exit=0
```

The first two print a reason on stderr; the model reads it and picks another path.

```bash
# 4. Validate a brief without side effects.
cp ~/agent-ops/prompts/TASK_TEMPLATE.md /tmp/brief.md
cat ~/agent-ops/prompts/BRIEF_PREAMBLE.md >> /tmp/brief.md   # the brief must reference the preamble
DRY=1 ~/agent-ops/bin/run_worker.sh hello cheap /tmp/brief.md
# expect: DRY OK: brief ... bytes, model claude-haiku-5-5, branch worker/hello, worktree .../wt-hello
```

```bash
# 5. The release watch, on a fake probe: healthy, then broken.
cd ~/agent-ops
python3 bin/watch_release.py --window 1 --interval 0.2 --grace 0 \
  --probe 'echo "{\"died\":0,\"bad\":0,\"total\":50}"' --rollback 'echo ROLLBACK'; echo "exit=$?"
python3 bin/watch_release.py --window 5 --interval 0.2 --grace 0 \
  --probe 'echo "{\"died\":3,\"bad\":0,\"total\":50}"' --rollback 'echo ROLLBACK'; echo "exit=$?"
# expect: exit=0 (healthy); then ROLLBACK and exit=3
```

If steps 1 to 5 print what is expected, the install is sound.

## Part B. A real worker and a first acceptance

Use a throwaway repository on GitHub that you own. Give the worker account a token that
**cannot merge** (see `SECURITY.md`).

```bash
# 6. Wire the hooks into the WORKER account's Claude Code settings.
mkdir -p ~/.claude
cp ~/agent-ops/hooks/settings.example.json ~/.claude/settings.json   # if you have one, merge by hand
export AGENT_OPS_GATE_CMD='bash scripts/gate.sh'        # the stop hook runs this on HEAD

# 7. Write a small brief (copy prompts/TASK_TEMPLATE.md, fill it in) and launch.
cd /path/to/your/repo
~/agent-ops/bin/run_worker.sh hello cheap /tmp/brief.md
# expect: "branch worker/hello from origin/main" ... "OK pid=... worktree=... log=..."
```

The launcher made a worktree, pushed the brief into the branch and started `claude -p`
detached. Follow the log it printed. The stop hook will not let the run end before the tree
is clean, the gate passes on HEAD, HEAD is pushed and a draft PR exists.

```bash
# 8. Accept it. Never trust the report; re-run it.
gh pr list --state all --head worker/hello           # --state all: an empty list is not "no PR"
git fetch -q origin && git worktree add -q ../wt-accept origin/worker/hello
cd ../wt-accept && bash scripts/gate.sh              # your own gate, in your own worktree
git log --oneline origin/main..HEAD                  # what exactly is in it
```

Then read the diff against the brief and against the *previous* behaviour, and for each new
test remove the fix and watch the test go red (`skills/accept-worker-pr/SKILL.md`, and
`docs/ACCEPTANCE.md` for the reasons). Only then do the merge yourself, pinned to the commit
you read:

```bash
gh pr ready <N>
gh pr merge <N> --merge --match-head-commit "$(git rev-parse HEAD)"
```

If the worker pushed again after you read the diff, the pinned merge is refused.

## When something goes wrong

| Symptom | Look at |
|---|---|
| `run_worker.sh` says the brief does not reference the preamble | add the word `BRIEF_PREAMBLE`, and copy the file into the repo |
| No worker process after 60 s | the log it printed; usually auth or a usage limit |
| The worker cannot end the run | the stop hook's reason in the log: the gate is red or the PR is missing |
| A guard blocks a harmless command | `docs/ARCHITECTURE.md` (the guard), or set `AGENT_OPS_EXTRA_DENY` |
