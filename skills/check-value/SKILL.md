---
name: check-value
description: Check whether a task is worth doing BEFORE writing the brief - break the idea into killer questions, test each against real data, and record an explicit verdict (confirmed, partial, phantom). Use when an idea, a customer complaint, a line in a doc or a tool finding might become a task and you must decide whether to brief a worker or drop it.
---

# Check the value of a task before briefing

A worker run costs quota and time, and a brief built on an unchecked premise comes back
BLOCKED or "fixes" a defect that does not exist. This skill exists because six tasks in a
row turned out to be phantoms, and because a defect can be invented not only by a stale doc
but by your own measurement.

One rule: **every idea gets a verdict, in words and numbers.** A task without a recorded
verdict returns next session as a new task.

## When not to use

- A direct instruction from the owner: do it, do not litigate value.
- A defect you can already see on the live system (a 500, an empty page, a mail that did
  not arrive): it is already a fact; go straight to diagnosis.
- A change cheaper than its check (a typo in a string).

## Steps

1. **Split the idea into 2-5 killer questions** - not subtasks; each one can end the task
   alone. Form: "Given ... when ... then ..." with the expected observation. **Order them by
   risk: the question most likely to kill the idea goes first.** Checking the easy one first
   pays for verifying something you might not need.

2. **Question 1 - is the phenomenon in the DATA?** Use a predicate, not a hand-picked sample;
   a sample never finds what you did not think of.
   An aggregate over a whole table lies: slice it by time. An aggregate without a split by
   entity type invents defects: "we lose 141 records a day" became "all 146 are present" once
   the 478 publications were broken down by document type. Before concluding "the data is not
   there", search the adjacent tables - a field missing from announcements was present in the
   decisions register.

3. **Question 2 - does the CLIENT see it?** Not "is it in the code" but what the live system
   returns. For rendering, take a screenshot and LOOK at it: a clean metric coexisted with a
   page 30,000 px tall and raw `###` on two thirds of the cards. "Does not work" must come from
   an ACTION (call the route, click, render), not from a number in a tool's report. For a
   customer complaint, first find out which account they used - one address can map to several
   tenants - then diagnose.

4. **Question 3 - is it OUR layer, and should it exist at all?** What is absent in the source
   cannot be fixed in code, and some absences are by design. Check ALL sources, not two of three.

5. **Record the verdict** as one of three words, with numbers and the method:

   | Verdict | Meaning | What the coordinator does |
   |---|---|---|
   | **CONFIRMED** | phenomenon exists, client sees it, our layer | write the brief; the numbers go into it as the diagnosis |
   | **PARTIAL** | reproduces under conditions X, Y | write the conditions into the brief; scope is only them |
   | **PHANTOM** | no phenomenon / client does not see it / not our layer | note "closed as stale" with the numbers; close the task |

   Record a phantom as carefully as a confirmation. An unrecorded negative result comes back
   as a new task.

6. **Fix a false positive in the TOOL, immediately.** A measurement that invented one defect
   will invent the next; a report demanding fixes for something that is fine stops being read.

## Failure modes

| Symptom | What it usually is | Action |
|---|---|---|
| "there is a defect, I saw it in the docs" | a doc is a hypothesis; main and the live system are facts | check before briefing |
| "the tool says 13x13" | element size is not click-target size | click it and observe the state |
| "141 mismatches in the database" | an aggregate with no split by type | split by type, ask "should this exist here?" |
| "found zero rows" | maybe your own query is broken | run it as a counterfactual on data known to exist |
| the check costs more than the fix | not a job for this skill | just make the change |

## What this was proven on

Six phantoms removed by fact in one day (zero rows with the supposed missing title out of
tens of thousands; a "winner not stated" fallback that fired on zero of two thousand records;
a field absent from the source; a cache that already existed). A checkbox "that blocks
registration" was disproved by a click. A "lost records" alarm was disproved by splitting the
aggregate by type.
