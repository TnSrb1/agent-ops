---
name: accept-worker-pr
description: Accept a headless worker's pull request before merging - re-run its evidence, run your own gate with a HEAD check, review the diff on three independent axes, verify test expectations against facts, then approve the exact commit for the merge train. Use when a worker has returned a report and opened a PR, or when deciding whether a worker branch can be merged.
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
   With a merge train, the train's single gate on the merged batch replaces this full run;
   before approving, run only the targeted and wider checks below in such a worktree.

4. **Red gate: baseline first, verdict second.** Only a failure that is absent on a clean
   `origin/main` blocks the merge. Run the same gate on main in the same checkout, compare
   the LISTS of failing test names, not the counts. In the branch only: a regression, the
   worker fixes it. On both: pre-existing debt; file it separately and do not make the
   worker fix someone else's problem.

4b. **Empty implementation and stubs.** In your own checkout of the PR branch, replace the body of
   one changed function with an empty result of its type (`return None` / `[]` / `0`). The new test
   must go red, and the output goes into the testing document. Then search the diff for fallbacks
   that hide a failure:
   `git diff origin/main...HEAD | grep -nE '^\+.*(except.*:|or \[\]|or ""|\.get\([^)]*,)'`.
   A new `except` without a re-raise, or a fallback sitting exactly where the reported symptom
   happened, without a traceback taken BEFORE the fix in the testing document, is a stub,
   not a fix. Treat it as a blocker.

4c. **Run wider than the worker did.** The worker's quick check selects tests by the change;
   it is blind to tests that never name the file they cover. A template or a translation
   catalogue changed: run the whole render-test directory. Four of nine PRs approved on targeted
   tests were red on the full suite; one reported "QUICK PASS" with fifteen red render tests.

5. **Review on three axes, by three fresh readers.** Run three read-only reviewer subagents in
   parallel, each with a clean context and one question. Do not merge their findings into one
   list before reading them: one axis hides another.
   - *Brief:* what was asked and is missing, what was added beyond the brief, what is done
     wrong - each with a quote from the brief and a `file:line`.
   - *Previous behaviour:* for every path the diff touches, what did the user get BEFORE this
     PR and what do they get AFTER? A brief describes the new and is silent about what already
     worked. A PR that followed its brief literally stopped opening the record card when a user
     searched for the number of an expired tender; the earlier release had opened it.
   - *Standards:* the project's invariants and rules files for the touched paths.
   Give every reviewer the **delta since the branch point**: `git log --oneline
   $(git merge-base origin/main <sha>)..origin/main`, with the instruction "check for overlap in
   meaning". Three of nine blockers in one shift came from a change merged into `main` after the
   branch was cut; the branch's own diff could not show them. Compute a fix's delta with
   `git diff origin/main...<sha>` or `git range-diff`, not `git diff <old> <new>`, which drags in
   everything merged from `main`. A reviewer's blocker is a hypothesis too: re-check it with
   your own command before you send it back. Hand fixes back as a table
   "file:line -> was -> replace with", and review the fix the same way.

6. **Check the tests' expectations against facts, not logic.** Two kinds of green test prove
   nothing: an assertion computed from the same catalogue/template the code reads
   (`assert render(key) in output`), and a test on mocks whose name promises a check of a
   query the mock never executes. Both go red under mutation - which is why "the mutation
   went red" does not mean "the expectation is right". For each new test ask: *which literal
   taken from a real run is asserted here?* If none, rewrite the expectation. Call the route,
   count in the database, render the page; compare with the assertion.

   6b. **If the repository is exported or mirrored somewhere (a public snapshot, a vendored copy),
   run the new tests inside that export too.** A test that reads a registry, a file or a
   setting that the export replaces is green at home and red in the copy: one worker's tests
   failed the public repository's CI while the private gate passed.

   6c. **Parallel PRs: one PR's constant is another PR's literal.** Before merging, `git grep`
   the old value on the neighbouring branch. One PR raised a cap from 12 to 30 while another,
   written the same day, mirrored 12 in a public page and its test: each was green, main went
   red. Merge the source of the value first; the second PR is reworked after `merge origin/main`.

   6d. **A public export must not grow by accident.** If part of the repository is published,
   export the PR's commit and list what the export contains. A new module the export's exclude
   list does not know about is published by default; a content scan that only looks for secrets
   and addresses will not notice a whole new internal integration.

   6e. **Pre-mortem before a high-risk merge.** Ask: "the release went out, a day later a user
   complains - about what?" Write two or three concrete scenarios (a user path, a background
   worker, a migration) and the command or render that rules each out. Then the second order:
   the fix is right, but what does it cost elsewhere? A correct one-line fix added a correlated
   subquery to a list query; on production data it hit the statement timeout and returned 500.
   New SQL on a hot list gets an `EXPLAIN ANALYZE` against production-sized data before merge.

7. **See the result with your own eyes.** UI: screenshot and look at it. Delivery or
   rendering: execute the production code path on safe data. A metric that is clean while
   the page is broken is still a broken page.

8. **Boundaries and litter.** No task briefs in the tree; migration numbers free and a
   single head; new files actually in the index (export the tree from the index, not from
   the disk, because tests see untracked files and production does not).

9. **Approve the commit, not the PR, and let the train merge it** (`docs/MERGE_TRAIN.md`,
   `skills/merge-deploy`). The approval names the sha you reviewed; new commits by the worker
   make it stale. Without a train: merge (non-high-risk), and after a *series* of merges run the
   gate once more on the merged main before releasing. Three branches that were each green
   produced a red main once: a semantic conflict with no textual one.

## Failure modes

| Symptom | What it usually is | Action |
|---|---|---|
| gate fails on the formatter | formatting, including your own code | run the formatter before committing, rerun |
| red test | read the traceback, do not guess | run that single test, read the assertion |
| red test not in the diff | pre-existing debt or a time dependency | step 4: baseline on main |
| report says PASS, gate says FAIL | the report was written before the last commit | trust your run |
| blocker appears only after the merge | a change merged into main after the branch point | give reviewers the merge-base..main log |
| gate FAIL: lock not taken | the tests did not run | retry later; not a verdict on the PR |
