# BRIEF_PREAMBLE: rules for every worker run

Every task brief points here. Read this file first. The run is headless: nobody answers
questions, and the process can be cut at any moment (usage limit, crash).

## 1. Hard limit mode: assume you will be cut off

Work that is not on the pushed branch is lost.

1. First action: create your branch from a fresh `origin/main` and push an empty marker
   commit (`git commit --allow-empty -m "wip: start <task>"`, `git push -u`).
2. After EVERY logical step (one change plus its check): `git add -A && git commit && git push`.
3. `git add` new files the moment you create them. Untracked files do not appear in
   `git diff` and are the first thing lost.
4. Keep `docs/reports/REPORT_<task>.md` incrementally: after each step, one line with the
   fact that proves it.
5. Do the most valuable step first, not the preparation.
6. If answers start getting cut off, commit and push what you have and write
   "cut off at step N, next: X" in the report.

## 2. Evidence document: `docs/reports/TESTING_<task>.md`

"Done, tests green" cannot be re-checked. So keep a testing document in the branch. Without
it the PR is not merged.

1. **Red first.** The first entry is a command that reproduces the symptom BEFORE your
   change, with its real output. If you could not reproduce it, say so and why.
2. **Every check is a command that can be repeated verbatim**: working directory, file,
   expected output or exit code. "Ran the tests" is not a check.
3. **Mutation check of each new test**: remove the fix, show the test going red, restore.
   Confirm the mutation actually applied (the diff is not empty).
   **3a. Empty implementation.** Replace the body of a changed function with an empty result of
   its type (`return None`, `[]`, `0`). The new test MUST go red; show the output. A test that
   stays green on an empty implementation checks a mock or its own catalogue: rewrite its
   expectation as a literal taken from a real run.
   **3b. Red for the expected reason.** Quote the assertion line or the traceback, not only the
   word FAILED. A red test that fails for an unrelated reason proves nothing.
4. **A separate section: what was NOT checked, and why.** A gap named aloud costs less than
   a gap found in production.
5. **Verdict in 2-3 lines**: is it correct, minimal, safe to merge.

A command that cannot be repeated (no path, no user, "something like") counts as unchecked.

## 3. Quick check and PR in the foreground

A headless run ends when you end your answer, and it KILLS anything you left running in the
background. A worker once started the gate in the background to "wait for it" and exited:
the gate died, no PR existed.

0. **You do not run the full gate.** The coordinator runs it once per batch of approved PRs on
   the merged tree (the merge train). Full gates started by workers held the shared lock for
   20+ minutes each and slowed every batch.
1. Before the final check, merge fresh `main` into your branch
   (`git fetch origin && git merge --no-edit origin/main`) and resolve conflicts by meaning.
   Regenerate generated files with their generator; never resolve them by hand.
2. Run the quick check in the foreground only, output to a file, and wait for the exit code:
   `bash <quick-check> > /tmp/qc_<task>.log 2>&1; echo "EXIT=$?"`. It lints the changed files,
   runs the tests selected by the change and the cheap guards, and runs on a merge with fresh
   `main` if your branch is behind. The stop hook requires its PASS on the current HEAD; "gate
   PASS after the last commit" in a brief means this PASS.
3. Your last action is `gh pr create --draft`. Always a draft, even if the brief says
   otherwise. Put the PR link in the report. Do not end the run before the PR exists, or
   the report says why it does not.
4. Never pipe a test run into `tail` before a commit: the pipeline returns the exit code of
   `tail`, not of the tests.

## 4. Autonomy: do not ask questions

An interactive question in a headless run is never answered; a worker once sat for an hour
on "which option do you prefer?".

1. A fork not covered by the brief: take the safest option inside the brief's boundaries,
   write the choice and the alternative in the testing document, and finish the PR.
2. An unmet acceptance criterion is not a reason to withhold the PR. Put the numbers and the
   list in the report and open the draft; the coordinator decides at acceptance.
3. If the gate fails on a database-backed test with "connection refused", run it ONCE more:
   another run may have been using the same machine.
4. **Two fixes in a row fail the same test: stop.** Do not write a third. Write one sentence
   in the testing document with the premise both fixes shared ("I assumed X"), and check that
   premise with one command. If the premise is false, open the draft PR with that conclusion.
5. **Do not hide a failure.** A new `try/except` without a re-raise, or a fallback such as
   `or []`, `or ""` or `.get(key, default)` placed on the path where the symptom occurs, is not a
   fix. It is allowed only when the testing document holds the traceback taken BEFORE the change
   and a reason why the fallback is correct.

## 5. Findings outside the task

Do not fix them and do not write them into docs. File an issue with the label `finding`:
what, where (`file:line` or the query and the numbers), how to reproduce, what you did NOT
check. List the issue numbers in the report.

## 6. Hooks: do not route around them

A pre-tool hook blocks: merging, marking a PR ready, creating a non-draft PR, pushing to the
default branch, force-pushing, piping a test run into a commit, and any commit that skips the
hooks with the no-verify flag. A stop hook will not let the run end until the tree is clean,
the quick check passes on the current HEAD, HEAD is pushed and a draft PR exists. A block with a
reason means "continue the work", not "find a way around".

Always open the PR as a draft. Automation picks up a ready PR within minutes, before anyone
has reviewed it.

## 7. Other people's processes

Never `pkill`/`killall`/`kill` by pattern (`pkill -f gate`): other gates and runs share the
machine. Stop only the process YOU started in this run, by its PID.

Run logs (gate, pytest, mutation output) are not committed. Carry the commands and the
numbers into the testing document instead.

## 8. Look for existing code first

Before you write a new module, function, helper or template, search for one that already
exists: `git grep` by name and by meaning, and a fresh map of the modules if the repository
keeps one. The report gets a line `Analogs: <what you found, and why it did not fit>` or
`Analogs: none, searched <what you searched for>`. A duplicate placed next to an existing
implementation blocks acceptance.

## 9. Probes against shared systems

A probe against a shared database, a container or a live data source can run longer than the
task and hold locks the others need.

1. Keep a transaction to one unit of work (one record, one batch). Never keep one open across a
   long loop over the network.
2. Wrap every remote command in `timeout <seconds>` and write the expected duration in the report.
3. Give a script that runs inside a container a unique name (`/tmp/<task>_$$.py`), and remove it
   when the run ends, including after a failure. Copy the results out of the container before it
   restarts, because a restart erases them.
4. Do not repeat a rate-limited live request if the data is already collected. Keep the window
   as short as the output needs.

## 10. After the draft PR and the report: exit

Do not watch the PR, do not schedule a wake-up, a loop or a sleep, do not wait for review or CI.
A fix worker once polled its PR every 30 minutes for two hours and held a slot the whole time.
The last action is the report; then end the run.

## 11. One kind of change per PR

1. A PR is ONE kind of change: a schema migration, OR a collector, OR a screen and its text. If
   the brief asks for two, do the first and describe the rest in the report as "next PR". One
   PR that mixed a schema, a collector and delivery needed five rounds of fixes.
2. About fifteen changed code files (not counting docs and tests) is the ceiling. Above it, stop:
   write a plan for splitting into the report and no code beyond the first step.
3. A migration number comes only from the brief ("Migration: NNNN"), assigned by the
   coordinator. Do not pick your own. If it is already taken on `main` when you start, stop and
   report.

## 12. Exported copies: run their guards before you push

If the repository is mirrored or published in part, its export guards (a content scan for
secrets and addresses, a translation memory for non-English text, generated diagrams that
count things) run in the gate too. Run them before you push any new text, test string or
migration. Three PRs in one day failed the batch gate on the same export guard that a
one-minute run would have caught.
