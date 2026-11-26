# agent-ops

An operating kit for one pattern: **a coordinator agent that briefs a headless worker, and
refuses to believe the worker's report until it has re-run it.**

It is extracted from the way the product at <https://nab.rs> is built: a Claude Code
session (the *coordinator*) writes atomic task briefs for `claude -p` runs (the *workers*);
each worker works in its own git worktree under hooks, and must hand back a pushed branch and
a draft PR. The coordinator reviews, approves an exact commit, and a merge train gates the
approved PRs together, so that `main` is always a tree that was tested as a whole. The owner
decides about money and about anything irreversible.

**For whom:** one person or a small team who wants an AI coding agent to ship pull requests
without being believed on its word. **Not for:** a team that wants a hosted platform or a
scheduler.

This is working tooling, not a framework. Everything here is a shell script, a hook or a
markdown file you can read in a few minutes.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/loop-dark.svg">
  <img alt="The loop: brief, worker, gate, review, merge, prod check, handover" src="assets/loop.svg">
</picture>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/train-dark.svg">
  <img alt="The merge train: approve on a sha, precheck, one gate, merge commits, main equals the tested tree" src="assets/train.svg">
</picture>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/watch-dark.svg">
  <img alt="Release watch: observe after roll-out, roll back on a sustained failure" src="assets/watch.svg">
</picture>

## What is in the box

| Path | What it is |
|---|---|
| `bin/run_worker.sh` | One-command launcher: validates the brief, makes a worktree, pushes the brief, starts `claude -p` detached with the API key unset, checks liveness. `DRY=1` validates only. |
| `hooks/guard_bash.py` | PreToolUse guard: blocks merge, "ready", non-draft PRs, pushes to protected branches, force-push, a test run piped into a commit, and commits that skip hooks with the no-verify flag. |
| `hooks/stop_gate.py` | Stop hook: the run cannot end until the tree is clean, the gate passes on HEAD, HEAD is pushed and a draft PR exists. |
| `hooks/settings.example.json` | How to wire both into Claude Code settings. |
| `prompts/BRIEF_PREAMBLE.md` | Rules every worker run starts with (hard-limit mode, evidence document with empty-implementation checks, quick check on a merge with fresh main, no questions, search for existing code first, probes against shared systems, exit after the PR, one kind of change per PR). |
| `prompts/TASK_TEMPLATE.md` | The shape of one brief. |
| `skills/check-value` | Decide whether a task is real before briefing; verdict in words and numbers. |
| `skills/launch-worker` | Brief, launch, watch and stop a worker; fix runs on the PR's own branch; a run without a start line did not start. |
| `skills/accept-worker-pr` | Accept a worker's PR: re-run evidence, wider tests than the worker ran, three independent reviewers (brief, previous behaviour, standards), approve the exact commit. |
| `skills/merge-deploy` | Who may merge what, approval pinned to a commit, the merge train, backups before migrations, how to confirm a release. |
| `skills/verify-traps` | Specific ways a check lies: accounts, aggregates, flags, tautological assertions, tests red only in the gate. |
| `skills/version-check` | Decide whether to update the tooling now. |
| `bin/watch_release.py` | Watch a release for N minutes after roll-out and roll back on a sustained failure. |
| `bin/loop_lag.py` | Stall watchdog for an asyncio event loop: sampled every tick, names the blocking line or "other thread". |
| `bin/wilson.py` | Alert on the lower bound of a failure rate, not the raw share. |
| `bin/pr_stats.py` | Counts and durations of a PR stream, published round-down with "+". |
| `docs/QUICKSTART.md` | A clean machine to a first accepted PR, about 15 minutes. |
| `docs/ACCEPTANCE.md` | How a PR is accepted: evidence, three reviewers, verdict as data. |
| `docs/RELEASE_WATCH.md`, `docs/OBSERVABILITY.md` | Production as a check after merge; what to alert on. |
| `docs/INCIDENTS.md` | 25 anonymised incidents: symptom, cause, rule, check. |
| `docs/CASE_TENDERSRB.md` | Measured numbers from the product this came from, with the method. |
| `docs/ARCHITECTURE.md` | The map and the invariants. |
| `docs/COORDINATOR_LOOP.md` | Essay: how a coordinator ships code with a headless worker. |
| `docs/VERIFYING_AI_PRS.md` | Essay: how to verify a PR written by an AI. |
| `docs/MEMORY_LAYERS.md` | When an observation may become a rule. |
| `docs/MERGE_TRAIN.md` | How approved PRs are merged in batches with one gate, so that `main` equals the tested tree. |
| `docs/COORDINATOR_SESSION.md` | Hooks that guard the coordinator itself: facts at session start, context guard, handover while gates run. |
| `docs/SHARED_MACHINE.md` | Several agents on one small machine: FIFO gate lock, slot limit, janitor, flaky tests with reasons. |
| `assets/` | The loop and the merge train as SVG, light and dark. |
| `tests/` | Tests for the hooks and the launcher; no network. |

## In numbers

Measured on 26 November 2026 from pull request data (method and gaps in
`docs/CASE_TENDERSRB.md`): 900+ worker PRs merged between 8 May and 26 November 2026, median
time from open to merge about 1 hour, 80+ % merged within a day. What could not be measured
(review blocker share, rollback rate) is listed there too, instead of guessed.

## What went wrong

The rules here are scars: 25 incidents, each with symptom, cause, rule and the check that now
catches it, in `docs/INCIDENTS.md`. Three that explain the design:

- A report said "GATE PASS" and an unformatted file was in the PR. The gate had run before the
  last commit. Now the stop hook stamps PASS per HEAD.
- A test run piped into `tail` before a commit took its exit code from `tail`: a commit on red
  tests. Test runs are never piped before a commit.
- Two green branches, one red `main`. Neither branch could see the conflict. The merge train
  gates the merged batch.

## Limitations

- **Not the product.** The service this was extracted from, its production scripts and its
  rollout procedure are not here.
- **The quick check is not shipped.** The stop hook runs `AGENT_OPS_GATE_CMD` (default: the
  full gate); point it at your own fast check if you have one.
- **The merge train is described, not shipped.** Its scripts are tied to one host; the design,
  the decisions and the incidents behind them are in `docs/MERGE_TRAIN.md`.
- **No supervisor.** There is no scheduler, no run database, no automatic relaunch. A
  supervisor that launches paid runs by itself would break the rule that spend needs a human
  word, so launching stays a command someone types.
- **The guard is a regex, not a sandbox.** It catches honest mistakes. It does not stop a worker
  that deliberately builds a command around it. Run workers under a low-privilege account with
  a token that cannot merge.
- **Runs with permission prompts disabled.** The launcher starts workers with
  `--dangerously-skip-permissions`, because a headless run cannot answer a prompt. The hooks
  and the account's limits are then the only barrier.
- **Claude Code 2.1 or newer** is assumed for the hook interface (`PreToolUse` exit code 2,
  `Stop` with `decision: block`). Verified on 2.1.327 only: `COMPATIBILITY.md`.
- **Defaults come from one setup.** Branch prefix, gate command and model name are
  configurable; the rest assumes a git host with the `gh` CLI, and a gate that is a single
  command.

## Quick start (about 15 minutes)

Step by step on a clean machine, with expected output: `docs/QUICKSTART.md`. In short:

1. Copy this directory, for example to `~/agent-ops`; merge `hooks/settings.example.json` into
   the worker account's `~/.claude/settings.json`, fixing the paths.
2. Set `AGENT_OPS_BRANCH_PREFIX` (default `worker/`), `AGENT_OPS_GATE_CMD` (default
   `bash scripts/gate.sh`; point it at a quick check if a merge train runs the full gate),
   `AGENT_OPS_PROTECTED` (default `main,master`).
3. Write a brief from `prompts/TASK_TEMPLATE.md`; keep `prompts/BRIEF_PREAMBLE.md` in your repo.
4. `DRY=1 bin/run_worker.sh my-task cheap path/to/brief.md` validates without side effects;
   drop `DRY` to launch. A model other than the cheap default needs `ALLOW_EXPENSIVE=1`, set
   only after the owner agreed to the spend.
5. Copy `skills/*` into the coordinator's `.claude/skills/`.

Tests: `python3 -m pytest -q tests`.

## Reading order

`docs/COORDINATOR_LOOP.md` for the story, `docs/ARCHITECTURE.md` for the map and the
invariants, `docs/VERIFYING_AI_PRS.md` if you review AI-written code, `docs/MERGE_TRAIN.md`
when more than one worker opens PRs, `docs/SHARED_MACHINE.md` if they share a host, and
`docs/MEMORY_LAYERS.md` and `docs/COORDINATOR_SESSION.md` if your agents keep notes between
sessions.

## Project files

`CHANGELOG.md`, `COMPATIBILITY.md` (what was verified, and on which version), `SECURITY.md`,
`CONTRIBUTING.md`. Planned first tag: `v1.0.0`.

## Pro edition

Pro edition and implementation help: link to follow.

## License

MIT. See `LICENSE`. Source: <https://github.com/TnSrb1/agent-ops>.
