---
name: verify-traps
description: Specific traps when checking a fact - liveness, which account a complaint came from, the first pass of a new source, enabling a flag, an empty log, aggregates, counterfactuals, tautological assertions, docstrings about the security context, monotonic grants, nondeterministic picks, and tests that are red only in the gate. Use when checking a complaint, a flag, a source, an aggregate, a test, or a tool's output.
---

# Verification traps

The core rule lives elsewhere: a report, a doc and a tool's output are hypotheses; the fact is
your own run, the database and the rendered live system. This skill lists the specific ways
that rule was broken anyway. Each line is one incident.

## When not to use

- You already see the defect on the live system: go straight to diagnosis.

## Runs and processes

- **Liveness takes two measurements:** process present AND output growing. Take time from one
  clock in UTC; file listings and `uptime` may use another time zone.
- **A substring search finds itself** and the text of files that mention the pattern. Match
  the exact process or the exact line.
- **An error at the end of a script does not mean the action failed.** Check the data and the
  audit trail first. One-off scripts must be idempotent so a re-run is safe.

## Complaints and accounts

- **First: which account?** One address can map to several tenants. Diagnose that account, not
  the one you assumed.
- **First: which channel?** A service bot that only sends alerts stays silent on commands by
  design. Check that the message reached the right bot before debugging the handler.
- **Statements for a customer rot like docs.** Each claim in a reply is a predicate over code or
  data, and each number carries its date.

## Data

- **An aggregate over the whole table lies.** Slice it by time, and split it by entity type:
  "141 records lost a day" became "all present" once the publications were split by document
  type. Then ask "should this record exist here at all?"
- **Before "the data is not there", search the adjacent tables.**
- **A counterfactual that did not go red does not close the question.** Measure the share with
  a predicate.
- **`LIMIT 1` without `ORDER BY` is a random row**, including in code that was "only moved".
- **A foreign number is a hypothesis.** A threshold copied from someone's README once made a
  context gauge report 125%.

## Flags and sources

- **Before enabling a flag, ask what the FIRST cycle will do.** It may send a backlog, in the
  wrong language, to everyone. Trace the flag from the environment file to the running process.
- **A new source whose first pass found zero new records:** compare with the live API. A
  first-pass lookback of zero plus a server-side "modified since" filter silently drops
  everything that was already open.
- **"The log is empty" is not a defect** until you have found the event that should have
  written to it and confirmed that it happened.
- **"Does A behave like B?" compares mechanisms**, not results: B may look right by accident of
  data.

## Tests

- **An assertion computed from the same catalogue or template as the code is a tautology.** The
  expected value is a literal taken from a real run. "The mutation went red" does not mean "the
  expectation is right".
- **A test that pins the wrong contract is worse than no test.** Take the expectation from the
  live behaviour (call the route), not from the code under test.
- **A docstring about the security context is the most expensive hypothesis.** "This runs as the
  owner role" was false; check by running the path inside the real container on safe data.
- **"Extend by N days" must be monotonic.** A grant that sets instead of extends can shorten
  access; shortening is a separate, explicit operation.

## Red only in the gate

- **Reproduce in the gate's environment, not in your terminal.** A process started in the
  background inherits SIGINT as ignored, and a non-interactive shell cannot trap it. A signal
  test was green by hand and red in every background gate; four batches blamed an innocent PR.
  Wrapping the check in `timeout` hid it, because `timeout` installs its own handler.
- **Red in the full parallel run, green alone:** a neighbour on the same parallel worker poisons
  shared state. Replay the gate's per-worker order (verbose output, random order off), then
  bisect the file list. One leaked dependency override took 15 minutes to find this way, after
  six fixes aimed at the wrong cause.
- **Your own reproducer needs a control run on `main`.** A reproducer that is also red on `main`
  is noise, not evidence about the PR.
- **The same test red for different PRs is a defect of `main`.** Fix it once, there.
