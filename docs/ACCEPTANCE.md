# Acceptance: why a PR from an AI is read three times and tested twice

The procedure is in `skills/accept-worker-pr/SKILL.md`. This page is the reasoning behind
its four less obvious parts, so you can keep them when you adapt the rest.

## 1. The report is a hypothesis; your own run is the fact

A worker's report says what the worker believes. Twice the report said "gate passed" and it
had not: the gate had run before the last commit, and a shared clone had been reset under a
test run. So acceptance repeats the worker's commands in a worktree the coordinator owns,
prints the `HEAD` before and after the run, and requires both to equal the branch tip.

The testing document that comes with each PR starts with a **red** section: a command that
reproduces the symptom *before* the change, with its real output. No red section means the
fix is not shown to fix the stated problem, and the PR is sent back like a red gate.

## 2. Mutation check: a new test must fail without the fix

A test that was never red proves nothing. For every new test:

1. Remove the fix, or replace the body of the changed function with an empty result of its
   type (`return None`, `[]`, `0`).
2. The new test **must** fail. Keep the failing output in the testing document, and make sure
   the assertion line is the *expected* one, not an import error.
3. Restore the change. Do it through version control, and only after the work is
   committed: `git checkout -- file` restores from the index, so an unstaged mutation
   revert can erase the work itself. Stage first, then mutate.

Two kinds of green test survive this check and still prove nothing, so the reviewer asks one
more question: **which literal, taken from a real run, does this test assert?**

- an expectation computed from the same catalogue or template the code reads
  (`assert render(key) in output`): both sides change together;
- a test on mocks that is named after a check the mock never performs.

## 3. Three readers, three questions

One reviewer reading "the diff" finds what the diff shows. The defects that reached `main`
were found by asking different questions, so the review is three independent read-only
runs with a clean context each:

| Reader | Question | Finds |
|---|---|---|
| Brief | What was asked, what is missing, what was added beyond it? | gaps, scope creep |
| **Previous behaviour** | For every path the diff touches: what did the user get *before*, what do they get *after*? | regressions that follow the brief to the letter |
| Standards | Do the project's written invariants hold for the touched paths? | rule violations |

The middle reader earned its place by one case: a brief asked to improve a search, was
followed exactly, and a search for the number of an expired record stopped opening its card.
The brief described the new behaviour and was silent about the old one. Only a reader asked
"what happened before?" could see it.

Every reader also gets the log from the merge base to `main`, with the instruction to check
for **overlap in meaning**: three of nine blockers in one shift came from a change merged
after the branch was cut, which the branch's own diff cannot show.

A reviewer's blocker is itself a hypothesis. Re-check it with your own command before you
send it back, and hand fixes back as a table of `file:line`, what it is now, what it should
be.

## 4. A violated rule becomes a check

When a worker breaks a rule that was written in the preamble, the reflex is to reword the
rule. That does not work: the next run reads the preamble the same way. The remedy is to turn
the rule into something that cannot be broken silently:

| The rule that was only words | The check that replaced the wording |
|---|---|
| "open PRs as drafts" | the guard hook blocks a non-draft PR |
| "do not merge" | the guard hook blocks the merge command |
| "run the gate before you finish" | the stop hook runs it on `HEAD` and blocks the stop |
| "do not weaken existing tests" | a precheck compares the test diff and demands a declared section |
| "keep file names short" | a precheck on the basename length |
| "the type-checker debt must not grow" | a ratchet in the gate, in both directions |
| "search for existing code first" | a line in the report, and a reviewer who rejects its absence |

The last row shows the limit: some rules cannot be automated, and then the cure is a
reviewer's blocker with a named rule, not a longer preamble. The order of preference is a
hook, then a test, then a review question, then a sentence.

The promotion of an observation to a rule follows `MEMORY_LAYERS.md`: by evidence of the
failure, not by how often it was mentioned.

## 5. What acceptance does not do

It does not decide whether the task was worth doing (see `skills/check-value`), and it does
not replace the full gate on the merged batch (`MERGE_TRAIN.md`). A green gate is not
acceptance either: several defects that reached review had a green gate.

## Record the verdict as data

End every review with one line a script can count: `VERDICT: OK` or `VERDICT: BLOCKER <n>`,
followed by the evidence. Post it as a PR comment. The share of PRs with a blocker is then
`gh pr list` plus a grep, instead of a number nobody can reconstruct.
