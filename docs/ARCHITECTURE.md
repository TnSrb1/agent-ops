# Architecture

This document describes how the pieces in this repository fit together and, more usefully,
which rules the design refuses to break. It is the map; `COORDINATOR_LOOP.md` is the story.

## Bird's Eye View

Two Claude Code sessions with different jobs share one repository.

The **coordinator** is an interactive session. It does not write product code. It decides
what is worth doing, writes an atomic task brief, launches the worker, accepts or rejects the
result, merges, rolls out, and hands over to the next session.

The **worker** is a headless `claude -p` run. It gets one brief, works in its own git
worktree on its own branch, under hooks that make the dangerous commands impossible, and
must end with a pushed branch and a draft pull request. It cannot merge and cannot ask
questions.

A **human owner** sits above both. The owner decides about money (which model, which paid
quota), about high-risk paths (migrations, auth, billing, CI configuration) and about
anything irreversible.

```
 idea -> check-value -> brief -> run_worker.sh -> worker (worktree + hooks)
                                                      |
                              draft PR  <-------------+  stop hook: clean tree,
                                 |                       gate PASS on HEAD, pushed, draft PR
                                 v
        accept-worker-pr: re-run evidence -> own gate (HEAD checked) -> two-pass review
                                 |
                                 v
                  merge (coordinator, or the owner for high-risk paths)
                                 |
                                 v
                  rollout -> check the LIVE system -> handover / memory layers
```

The loop is drawn in `assets/loop.svg`. Everything in it is a plain file or a shell command;
there is no orchestration service to run.

## Components

### `bin/run_worker.sh` - the launcher
One command starts one run. It validates the brief (not empty, points at the preamble),
refuses a non-default model unless `ALLOW_EXPENSIVE=1` is set, creates the worktree, commits
and pushes the brief into the branch, starts `claude -p` detached with `ANTHROPIC_API_KEY`
unset, and then checks liveness. `DRY=1` runs only the validation. It replaces a list of
manual rules with a script that cannot forget them.

### `hooks/guard_bash.py` - the PreToolUse guard
A regex over the Bash command the worker is about to run. Merge, marking a PR ready,
non-draft PR creation, push to a protected branch and any force-push exit with code 2; the
reason goes back to the model. Protected branches and extra deny rules are configurable.

### `hooks/stop_gate.py` - the Stop hook
On a worker branch the run cannot end until the tree is clean, the gate passes on the current
HEAD, HEAD is on the remote and a draft PR exists. A PASS is stamped per commit, so a new
commit is gated again. After a few blocks per session it lets go, so a stuck worker cannot
burn money in a loop.

### `prompts/` - what the worker reads
`BRIEF_PREAMBLE.md` carries the rules that never change (hard-limit mode, evidence document,
foreground gate, autonomy, findings go to issues). `TASK_TEMPLATE.md` is the shape of one
brief: diagnosis marked verified or not, addresses, boundaries, required evidence, done-when.

### `skills/` - the coordinator's procedures
Three Claude Code skills in executable form: `check-value` (before the brief),
`accept-worker-pr` (after the PR), `version-check` (before touching the tooling).

### `docs/` - the reasoning
`COORDINATOR_LOOP.md`, `VERIFYING_AI_PRS.md` and `MEMORY_LAYERS.md` explain the why.

## Invariants

These are the rules the design is built around. Each one has a reason, and each one has a
way to check it.

**Invariant:** a worker never merges.
Merging is the point where an unreviewed change becomes the product. The guard blocks the
merge command, the token the worker runs under should not be able to merge, and the stop hook
requires the PR to be a draft. Check: ask the worker's account to merge a throwaway PR.

**Invariant:** a report is a hypothesis until it is re-run.
A worker report, a PR description and any tool's output are claims. The coordinator repeats
the commands from the evidence document and runs its own gate. Check: the acceptance notes
contain the coordinator's own exit code and commit hash, not a quote.

**Invariant:** one worktree = one operation.
A shared checkout moves under you: a periodic reset, another run, a branch switch. Every run
and every acceptance gate gets its own worktree, and a gate prints the HEAD it started and
ended on. Check: both hashes equal the branch tip.

**Invariant:** spend needs an explicit human word.
The default model is the cheapest one that can do the job; anything else needs a deliberate
flag, and workflows that call a paid API from CI stay off until the owner turns them on.
Check: the launcher refuses a non-default model without the flag.

**Invariant:** the gate must pass on the final HEAD.
A gate result belongs to one commit. A report that says PASS was written before the last
commit and proves nothing about it. Check: the stop hook stamps PASS per HEAD hash.

**Invariant:** a headless run is autonomous.
Nobody answers a question, so a worker that asks has stopped. Forks are resolved inside the
brief's boundaries and recorded; unmet criteria go into the report, not into silence.
Check: the preamble forbids questions and the stop hook enforces a PR instead.

**Invariant:** a worker pushes after every step.
A run can be cut at any moment. Unpushed work is lost work. Check: the branch history shows
one commit per step, not one at the end.

**Invariant:** findings outside the brief become issues, not edits.
Scope creep hides review comments about the real change. Check: the diff stat touches only
paths the brief listed.

**Invariant:** the record is corrected out loud.
When a note turns out to be wrong, the correction says what was claimed, what the fact is and
how it was checked. A silent rewrite lets the next session inherit the error as fact.
Check: the corrected entry names the old claim.

**Invariant:** knowledge is promoted by proof, not by frequency.
An observation becomes a rule only when something re-checks it (see `MEMORY_LAYERS.md`).
Check: every rule names the incident or the measurement that justifies it.

**Invariant:** a metric does not replace the eye.
A tool can miss a defect and can invent one. A conclusion that matters comes from an action -
a click, a request, a rendered page - and a false positive is fixed in the tool at once.
Check: acceptance includes a screenshot that someone looked at.

## Cross-cutting concerns

**Where the guard stops.** The hooks are a guard rail, not a jail. They are regexes and
file checks, they assume a worker that makes honest mistakes, and they assume the worker's
credentials are limited. A run started with permission prompts disabled is only as safe as
those two assumptions.

**Where the loop is cut.** The hard-limit preamble is a design response to a real constraint:
usage limits end runs without warning. The state of a run therefore lives in the branch (code,
the evidence document, a small machine-readable state file), never in the conversation.

**What is deliberately absent.** No scheduler, no database of runs, no automatic restart. A
supervisor that launches paid workers by itself breaks the spend invariant, so launching stays
a human-approved command.
