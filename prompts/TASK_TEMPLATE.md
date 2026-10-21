# TASK: <slug> - <one line: the outcome, not the activity>

Preamble `prompts/BRIEF_PREAMBLE.md` is mandatory (BRIEF_PREAMBLE). Branch `worker/<slug>`,
draft PR. Write ONLY inside: <list of paths>. Do NOT touch: <list of paths>.

## Why
Two or three sentences: who needs this, what they see today. Facts, not adjectives.

## Diagnosis (facts)
Each line is marked **verified** (with the command that produced it) or **NOT verified -
check it first**. A brief's premise is a hypothesis; the worker re-checks anything marked
unverified before building on it.

- <fact> - verified: `<command>` -> <number or output>
- <fact> - NOT verified

## Addresses
`path/to/file.py:123` + the selector or function name. Scope by predicate
(`grep -nP "<pattern>"`) with a counterfactual on main, not by a list of literals.
Exact addresses save more than choosing a bigger model.

## Steps (most valuable first; commit + push after each)
1. <one change and the check that proves it>
2. ...

## Boundaries and invariants
Write the project invariants out in full - do not say "see the contributing guide".
- <invariant>: <prohibition> -> <reason> -> <how to check>

## Required evidence
- red reproducing command BEFORE the change, with output
- mutation check of every new test, with proof the mutation applied
- a read-only check against the real system, with numbers
- what was NOT checked

## Done when
- `<command>` prints `<exact expected output>`
- gate passes on the final HEAD (run after the last commit)
- draft PR exists; link in the report
