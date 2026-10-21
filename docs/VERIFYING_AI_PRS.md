# Verifying pull requests written by an AI

An agent's pull request arrives with a confident report and green checks. Neither is
evidence. This is the set of habits that turned acceptance from reading into measuring. Each
one comes from a PR that would have shipped a defect without it.

## 1. Start from a red you can reproduce

Before reading any code, get one command that fails on the symptom and passes on the fix. If
the failure is not deterministic, run it N times and count. The worker is required to put that
command first in its evidence document, with real output, *before* its change.

If the document says "could not reproduce", the fix is not shown to fix the stated problem.
That blocks a merge exactly like a failing gate. It sounds harsh and it removes a whole class
of PRs that change code near a bug and declare victory.

Corollary: three failed fixes in a row mean the problem is in the structure, not in the next
patch. Do not order a fourth; ask the owner a question about the design.

## 2. Run your own gate, and make it testify against itself

"GATE PASS" in a report is a statement about some commit at some time. Run the gate yourself,
in a worktree nobody else touches, and make the command expose what it ran:

```
git checkout <sha> && echo "HEAD before: $(git rev-parse --short HEAD)"
bash scripts/gate.sh > /tmp/gate.log 2>&1
echo "EXIT=$? HEAD after: $(git rev-parse --short HEAD)"
```

Both hashes must equal the branch tip. This was added after a gate returned "passed, exit 0"
twice in a row about a commit that was not the one under review: a timer in the shared clone
had reset the branch to main between checkout and test run. Also check where the code is
imported from (`python -c "import pkg; print(pkg.__file__)"`); an editable install can quietly
test another branch.

And never pipe the test run: `pytest | tail && git commit` takes its exit code from `tail`,
and a commit once landed on top of red tests.

## 3. Read the tests for tautologies

A green test proves only that code and assertion agree. Two common shapes prove nothing:

- **The assertion computed from the same source as the code.**
  `assert translate("ru", key).format(days=5) in text` compares the output with the catalogue
  it was built from. It stays green when the catalogue loses the expiry date, which was
  precisely what the customer had asked for. Another asserted that a text "contains the letter
  e-with-diaeresis", which a word elsewhere in the sentence satisfied.
- **A mock test whose name promises more than it checks.** A test called "expired beyond the
  grace window sends nothing" fed the worker an empty list from a fake session; the query it
  claimed to test never ran. The test was renamed to say what it does, and the window was
  proven separately against a real database.

The fix is a question to ask of every new test: *which literal taken from a real run is
asserted here?* The expectation should be a number, a string, a status code that you obtained
by calling the route or counting in the database - written out, not derived.

## 4. A mutation that did not apply proves nothing

Mutation checking is how you learn that a test is connected to the code: remove the fix, the
test must go red, restore the fix. Two ways it lies:

- **The mutation never took.** A copy of the file under a name that was already taken did not
  get created, the "restore" overwrote the work, and the "red" was a leftover. Confirm the
  diff is non-empty before you trust the red.
- **The mutation tooling hid the tests.** Stashing the change also stashes the new tests when
  they are uncommitted, so the run goes green on the old pair. Commit the tests first, mutate
  the code, restore through version control.

A third caveat is the reverse: a test that goes red under mutation is connected to the code,
but is its expectation *right*? One assertion said a link without a profile id was normal;
the route required one, and 100 rows on a page returned 404. Mutation could not see it. Call
the route.

## 5. A metric is not an eye, and neither is your own tool

Measurements both miss and invent defects. A tool reported a 13-by-13 checkbox that
"blocked registration"; a click showed it worked. A pixel measurement was clean while the page
was 30,000 pixels tall and two thirds of the cards showed raw markup. An alarm about
"141 lost records a day" disappeared when the aggregate was split by document type.

So conclusions come from an action: click it, request it, render it and look at the image.
When your own tool lied, fix the tool the same day, or it will invent the next defect and the
reports will stop being read.

## 6. Diff in two passes

First: does the diff do what the brief asked, and nothing else? Second: is the code good?
Never mix them. A style comment in the same pile as a scope problem hides the scope problem.
Files outside the brief are not a violation by default - ask why - but they must be explained.

## 7. After a series, gate the whole

Three branches, each green, merged one after another, produced a red main: one branch changed
shared behaviour that another had pinned with an assertion. No text conflict, so no tool in a
branch could see it. After any series of merges, run the gate once on the merged tip before
rollout, and when it is red, fix the *expectation* from a fact, not the behaviour to fit the
old assertion.

## The short version

Treat the report as a claim. Reproduce the red. Run the gate yourself and print the commit.
Read tests for the literal they assert. Make sure the mutation applied. Look at the result.
Then merge.
