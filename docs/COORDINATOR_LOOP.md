# How a coordinator agent ships code with a headless worker

A production service I run is built almost entirely by two Claude Code sessions. One of them
never writes product code. This is what that arrangement looks like after a few months of
using it daily, including the parts that broke.

## The split

The **coordinator** is interactive. It reads the repository, decides what is worth doing,
writes a brief, launches a worker, checks the result and merges. The **worker** is
`claude -p`: headless, one brief per run, its own git worktree, no one to answer a question.
A human owner holds the decisions that cost money or cannot be undone.

The reason for the split is not elegance, it is cost and context. The coordinator's session is
long and carries the history of the project; every action it takes re-reads that history. A
worker starts cold and reads only the brief, so the same piece of code costs several times
less when the worker writes it. The rule that came out of this is blunt: code goes to the
worker, always. When the coordinator "does it itself" it pays more and the work is not
cheaper. The coordinator's own subagents are for review, audit and reading.

## Step one: is the task real?

The cheapest run is the one never started. Before a brief exists, an idea goes through
`check-value`: split it into questions that could each kill it, most likely killer first, and
check each against real data. Is the phenomenon in the data? Does the user actually see it?
Is it our layer? The result is a verdict - confirmed, partial or phantom - written down with
numbers.

This step earned its place in one day, when six queued tasks were removed by fact. A fallback
for "missing title" fired on zero of tens of thousands of records. A "winner not stated"
placeholder fired on zero of two thousand. A field was not in the source at all. A cache
already existed. A phantom is recorded as carefully as a confirmation, because an unrecorded
negative result comes back next session as a fresh task.

## Step two: the brief

A brief is atomic and puts the most valuable step first, because the run can be cut off
without warning. It states the diagnosis as facts, and marks each fact *verified* (with the
command) or *not verified - check it first*. The coordinator's own premise is a hypothesis
too: a brief once asserted something about an external source that one live request would
have disproved, and the worker built on it.

It gives addresses (`file:line` plus a selector) rather than prose, writes the project's
invariants out in full, lists the paths the worker may and may not touch, and names the
evidence it must return: a red reproducing command, a mutation check of every new test, a
read-only check against the real system, and a list of what was *not* checked. Exact
addresses save more than a bigger model.

The rules that never change live in one shared preamble the brief points at, not pasted
into each brief.

## Step three: launch

Launching is a script, `run_worker.sh`, because every manual rule it replaces was once
forgotten. It checks the brief is non-empty and references the preamble, creates a separate
worktree, pushes the brief into the branch so the run is resumable, unsets the API key so the
run bills the subscription and not the API, detaches the process from the coordinator's shell,
and verifies after a minute that a process exists with the worktree as its working directory.
The model is the cheapest one by default. Anything else needs a flag a human sets, because
spend is the human's decision.

Two hooks make the worker's rules physical. A pre-tool guard blocks merging, marking ready,
non-draft PRs, pushes to the default branch and force-pushes. A stop hook refuses to let the
run finish until the tree is clean, the gate passes on the current HEAD, HEAD is pushed and a
draft PR exists. Both exist because of incidents: a worker started its gate in the
background and exited, killing it, and no PR was opened; a non-draft PR was picked up by
auto-merge before anyone looked at it.

## Step four: acceptance

The worker's report is a hypothesis. The coordinator opens the evidence document and repeats
its commands, starting with the red one - if the symptom was never reproduced before the
change, the fix is not shown to fix anything. It then runs its own gate in its own worktree,
printing the HEAD before and after. That detail was bought: a periodic reset in a shared
clone once moved a branch mid-run, and the gate reported success about someone else's commit.

A red gate gets a baseline before a verdict: run the same gate on a clean main and compare
*lists* of failing tests. Only a failure absent on main blocks the merge; the rest is existing
debt, filed separately.

The diff is reviewed in two passes in a fixed order, brief compliance first and code quality
second, because a style note in the same pile hides the fact that the scope drifted. Then the
test expectations are checked against facts (see `VERIFYING_AI_PRS.md`), and the result is
seen with eyes: a screenshot for UI, the real code path for rendering.

## Step five: merge, rollout, and what comes after

High-risk paths (migrations, auth, billing, CI configuration) are merged by the owner; the
rest by the coordinator after acceptance. After a *series* of merges, one more gate runs on the
merged main before rollout, because branches that are each green can make a red main - a
semantic conflict has no textual one. After rollout the coordinator checks the live system, not
the pipeline's exit code.

Then the handover. The next session starts cold, so the handover carries only verified facts
and pointers to procedures, not copies of them; `MEMORY_LAYERS.md` describes the rule. The
coordinator writes it itself, after every merge, rollout and decision, not when asked.

## What went wrong along the way

- A report said "GATE PASS" while an unformatted file was in the PR. Now the gate runs after
  the last commit, and the coordinator reruns it.
- An empty list of open PRs was read as "no PR" - auto-merge had already merged it, and a
  duplicate was opened. Searches use every state.
- A killed run left its container process behind, which held a database transaction and
  blocked a migration. Probes now run under a timeout, one transaction per unit of work.
- A worker finished with a question and waited an hour. Headless runs get a rule: pick the
  safe option inside the brief, record it, finish the PR.
- Two parallel gates took down a throwaway database; the rule is gates in series, and a red
  database test is rerun alone before it is believed.
- A cleanup command matched by pattern killed someone else's gate. Processes are stopped by
  the PID you started.

## What I would tell someone starting

Do not start with the agents; start with the verdict step and the evidence document. A worker
that can write code is easy to get. A loop that can tell whether the code is right, without
trusting the one who wrote it, is the product. Put the guards in hooks instead of prompts,
make every claim carry the command that produced it, and correct your own wrong notes out
loud. The rest is plumbing.
