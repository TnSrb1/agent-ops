---
name: launch-worker
description: Write a task brief, launch a headless worker run, watch it, and stop it - one wrapper, a dry run first, a slot limit, spend only on the owner's word, fix runs on the PR's own branch, and the checks that tell a run that started from one that did not. Use when writing a brief, launching, waiting for, or stopping a worker.
---

# Launch a worker

A worker run costs quota, holds a slot on a shared machine and can be cut at any moment.
Everything below exists because a run once started without anyone noticing it had failed, ran
twice under two names, or sat for hours waiting for something nobody would ever give it.

## When not to use

- A one-line change cheaper than its brief.
- A task whose value has not been checked: run `check-value` first.

## Launching

1. **One wrapper, dry first.** `DRY=1 bin/run_worker.sh <slug> <model> <brief>` validates the
   brief and the model without side effects; then the same command without `DRY`. The wrapper
   creates the worktree, pushes the brief, starts `claude -p` detached with the API key unset,
   and checks liveness. Never launch by hand when the wrapper exists: the wrapper cannot forget.

2. **Spend needs the owner's word.** If the plan can bill past its limit, a run past the limit
   is real money and the usage counters may not show it. Launch only after the owner has said
   there is budget. The default model is the cheapest that can do the job; a stronger one needs
   an explicit flag and a reason in the report.

3. **Respect the slot limit.** A small machine runs at most two or three workers and one full
   gate; more ended in out-of-memory kills and a frozen host. Make the wrapper wait for a free
   slot under a lock (a count of running `claude -p` processes) instead of racing for it. The
   launcher in `bin/` does not do this yet: with it, the limit is you.

4. **A fix to an existing PR runs on that PR's branch.** Use the PR branch name, without the branch prefix, as the slug. A fix
   launched under a new slug made its own branch; the stop hook demanded a PR from it, and the
   result was two duplicate PRs and two runs looping on the hook.

5. **One slug, one live run.** A waiting launcher left by an earlier session once raced a new
   one for the same branch. The launcher in `bin/` refuses any slug whose worktree already
   exists.

6. **The launcher must not destroy work.** A cut-off run leaves new, uncommitted files. A
   launcher that reuses worktrees must refuse one with untracked files: an earlier version
   checked only tracked files, removed the worktree with force, and lost a run's work.

## Watching

7. **A run whose launch log has no `OK pid=` line did not start.** Two launches once failed
   on a push key and nobody noticed for eight hours. After a queue of launches, grep the launch
   logs for the start line and for errors.

8. **Liveness is two measurements:** the process exists AND its transcript grows. Silence for
   a long while usually means a long test run (or, if workers run the full gate, the gate
   lock queue), not that it is stuck.

9. **The run ending is not the task ending.** Look up the PR with `--state all` by branch. No PR:
   the worker probably left the gate in the background and exited. Run the check yourself and
   open the PR, or relaunch with "continue from step N".

10. **Do not wait for a worker inside your session.** Use a detached waiter; your session's
    context is the most expensive thing in the loop.

## Stopping

11. **Stop by PID or with the stop script, never by pattern.** Other people's gates and runs share
    the machine; `pkill -f gate` once killed two foreign gates. Before stopping, snapshot the
    work in progress (diff plus untracked files) so a relaunch can continue.

12. **Clean up orphans.** A killed run does not kill what it started: preview servers, throwaway
    databases, a probe inside a container holding a transaction. A periodic janitor removes
    test stands older than a few hours and throwaway databases whose owner process is gone.

## Writing the brief

- **Facts, marked.** Each claim in the diagnosis is marked "verified (how)" or "not verified,
  check it". Your premise is a hypothesis: check it with the same predicate you ask the worker
  to use; for an external source, make one live request before writing the brief.
- **Addresses, not descriptions.** `file:line` and a selector; the scope as a predicate with a
  counter-check on `main`, not a list of literals you happened to find.
- **Read the open PRs that touch the same files first.** A brief that depends on another PR is
  written after that PR is merged, against the merged code.
- **What must stay as it is.** A brief describes the new; it is silent about what already works.
  List the old behaviours on the touched paths that must not change.
- **One kind of change per PR:** schema, or collector, or screen. Around fifteen changed code
  files is the ceiling; above it the worker writes a plan for splitting and stops after step one.
  One mixed PR of schema, collector and delivery needed five fix rounds.
- **The coordinator assigns the migration number** and the wrapper checks it is free; the worker
  never picks its own.
- **Fix briefs ask for the quick check, not the full gate.** Three full gates started by fix
  workers once ran beside the train's gate on four cores; every batch took 45 minutes.
- **Point at the preamble, do not paste it.** Check that the brief is not empty before pushing.

## Failure modes

| Symptom | What it usually is | Action |
|---|---|---|
| run exited, no PR | gate left in the background, or the run was cut | check with `--state all`; finish the PR yourself or relaunch to continue |
| two PRs for one fix | fix launched under a new slug | close the duplicate; relaunch on the PR branch |
| launch log without a start line | failed before start (keys, slot, brief) | read the log; do not wait for it |
| run "hangs" for an hour | a long test run or the gate lock queue | check the transcript and the lock queue before killing anything |
| run polls its PR every 30 minutes | the brief or preamble did not say "exit after the PR" | the preamble now does |
