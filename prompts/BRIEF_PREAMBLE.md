# BRIEF_PREAMBLE — rules for every worker run

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
4. **A separate section: what was NOT checked, and why.** A gap named aloud costs less than
   a gap found in production.
5. **Verdict in 2-3 lines**: is it correct, minimal, safe to merge.

A command that cannot be repeated (no path, no user, "something like") counts as unchecked.

## 3. Gate and PR in the foreground

A headless run ends when you end your answer, and it KILLS anything you left running in the
background. A worker once started the gate in the background to "wait for it" and exited:
the gate died, no PR existed.

1. Run the gate in the foreground only, output to a file, and wait for the exit code:
   `bash scripts/gate.sh > /tmp/gate_<task>.log 2>&1; echo "EXIT=$?"`.
2. Your last action is `gh pr create --draft`. Always a draft, even if the brief says
   otherwise. Put the PR link in the report. Do not end the run before the PR exists, or
   the report says why it does not.
3. Never pipe a test run into `tail` before a commit: the pipeline returns the exit code of
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

## 5. Findings outside the task

Do not fix them and do not write them into docs. File an issue with the label `finding`:
what, where (`file:line` or the query and the numbers), how to reproduce, what you did NOT
check. List the issue numbers in the report.

## 6. Hooks: do not route around them

A pre-tool hook blocks: merging, marking a PR ready, creating a non-draft PR, pushing to the
default branch, force-pushing. A stop hook will not let the run end until the tree is clean,
the gate passes on the current HEAD, HEAD is pushed and a draft PR exists. A block with a
reason means "continue the work", not "find a way around".

## 7. Other people's processes

Never `pkill`/`killall`/`kill` by pattern (`pkill -f gate`): other gates and runs share the
machine. Stop only the process YOU started in this run, by its PID.

Run logs (gate, pytest, mutation output) are not committed. Carry the commands and the
numbers into the testing document instead.
