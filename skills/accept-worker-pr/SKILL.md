---
name: accept-worker-pr
description: Accept a headless worker's pull request before merging - re-run its evidence, run your own gate with a HEAD check, review the diff in two passes, verify test expectations against facts, then merge. Use when a worker has returned a report and opened a PR, or when deciding whether a worker branch can be merged.
---

# Accept a worker's PR

The worker's report, the PR description and any tool's output are **hypotheses**. The fact is
your own run, the database, and the rendered live system. This procedure exists because a
report once said "GATE PASS" while an unformatted test file was in the PR, and because the
coordinator's own gate once failed on formatting in code the coordinator had written.

## When not to use

- Paths your project marks as high-risk (migrations, auth, billing, CI config): run the same
  acceptance, but the merge needs the owner's word. Stop before step 9.
- Docs-only changes: reading the diff is enough.

## Steps

0. **Find out whether the PR exists and is already merged.**
   `gh pr list --state all --head <branch> --json number,state,mergedBy`: always
   `--state all`. An auto-merge once merged a PR on its own; the coordinator looked at
   `--state open`, saw an empty list, read it as "no PR" and opened a duplicate. An empty
   result is not proof that the thing does not exist.

1. **Read the worker's report from its transcript, not only from the log.** The transcript
   survives even if the coordinator's session was cut off; take the text of the last
   assistant message.

2. **Open the testing document and repeat its commands.** It must start with a RED section: a
   command that reproduced the symptom before the change. No red, or "could not reproduce",
   means the fix is not shown to fix the stated problem; that blocks the merge like a red
   gate. A command that cannot be repeated verbatim (no path, no user, "something like")
   counts as unchecked. Read the "not checked" section whole: a gap named aloud is an input
   to steps 5-6, not a formality. Matching output does not close steps 3-6: the worker may have
   checked the wrong thing.

3. **Your own gate, in a worktree of its own, with a HEAD check on both sides.**
   Use a separate `git worktree add --detach <path> <sha>` so nothing else can move the
   checkout under you. Before the run, prove where the code resolves from
   (`python3 -c "import pkg; print(pkg.__file__)"` must print a path inside the worktree;
   an editable install can silently test another branch). Then make the command expose
   itself:
   `echo "HEAD before: $(git rev-parse --short HEAD)"` -> `gate > log 2>&1` ->
   `echo "EXIT=$? HEAD after: $(git rev-parse --short HEAD)"`.
   Both HEADs must equal the branch tip. Once, a periodic `git reset --hard` in a shared
   clone moved the branch between checkout and pytest, and the gate reported
   "passed, EXIT=0" about someone else's commit. No pipe into `tail` - it eats the exit code.

4. **Red gate: baseline first, verdict second.** Only a failure that is absent on a clean
   `origin/main` blocks the merge. Run the same gate on main in the same checkout, compare
   the LISTS of failing test names, not the counts. In the branch only: a regression, the
   worker fixes it. On both: pre-existing debt; file it separately and do not make the
   worker fix someone else's problem.

5. **Review the diff in two passes, in this order.**
   - *5a, spec compliance:* `git diff --stat origin/main...origin/<branch>`. Is every point
     of the brief done, and nothing beyond it? Do not move to 5b until 5a passes.
   - *5b, code quality:* the core of the change, by eye: project invariants, error
     handling, tests, security. Files outside the brief are not a violation by default;
     check why. Hand fixes back as a table "file:line -> was -> replace with", and re-review
     the fix in the same order. An author's self-check does not replace review.

6. **Check the tests' expectations against facts, not logic.** Two kinds of green test prove
   nothing: an assertion computed from the same catalogue/template the code reads
   (`assert render(key) in output`), and a test on mocks whose name promises a check of a
   query the mock never executes. Both go red under mutation - which is why "the mutation
   went red" does not mean "the expectation is right". For each new test ask: *which literal
   taken from a real run is asserted here?* If none, rewrite the expectation. Call the route,
   count in the database, render the page; compare with the assertion.

7. **See the result with your own eyes.** UI: screenshot and look at it. Delivery or
   rendering: execute the production code path on safe data. A metric that is clean while
   the page is broken is still a broken page.

8. **Boundaries and litter.** No task briefs in the tree; migration numbers free and a
   single head; new files actually in the index (export the tree from the index, not from
   the disk, because tests see untracked files and production does not).

9. **Merge** (non-high-risk) and then, after a *series* of merges, run the gate once more on
   the merged main before releasing. Three branches that were each green produced a red main
   once: a semantic conflict with no textual one.

## Failure modes

| Symptom | What it usually is | Action |
|---|---|---|
| gate fails on the formatter | formatting, including your own code | run the formatter before committing, rerun |
| red test | read the traceback, do not guess | run that single test, read the assertion |
| red test not in the diff | pre-existing debt or a time dependency | step 4: baseline on main |
| report says PASS, gate says FAIL | the report was written before the last commit | trust your run |
