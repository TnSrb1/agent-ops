# Memory layers

A coordinator agent forgets between sessions, so the project keeps its memory in files. The
hard question is not where to put a note but **when an observation is allowed to become a
rule**. This document is the answer we use.

The four-layer shape (raw, atom, scenario, core) is borrowed from published agent-memory
work. We did not adopt the service. We kept the shape and changed the promotion rule.

> **The difference.** Systems like that promote knowledge by *frequency*: mentioned often,
> therefore remembered. Here knowledge moves up only by *proof*. Automatic "remember it
> because we talked about it a lot" is a factory for phantom tasks: six tasks in a row once
> came from notes nobody had checked against the facts, and a coordinator once wrote a defect
> into the state file that a single click disproved.

## The layers

| Layer | What it is | Where it lives | Lifetime |
|---|---|---|---|
| **L0 - raw** | transcripts, gate logs, command output, screenshots, measurement JSON | scratch directories, session transcripts | until the session ends |
| **L1 - atom** | ONE verified fact, with the way it was verified | state file, facts registry, coordinator memory | until refuted |
| **L2 - scenario** | a repeatable procedure | runbook sections, skills, scripts | until the design changes |
| **L3 - core** | an invariant that must never be broken | the project rules file and the rules loaded by path | until the owner decides otherwise |

## Promotion rules

**L0 to L1.** An observation becomes an atom only if it was checked against reality and the
check is recorded with it: a number from the database, the status code of a route you called,
a row in the catalogue, a rendered page. "I saw it in a report", "the worker wrote it" and
"the doc says so" are still L0. A worker's report, a PR description and any tool's output are
L0, and so is an instrument finding: a measurement shows element size, but only an action
(click, request, run) shows whether it works.

**L1 to L2.** An atom becomes a procedure if either holds:
- it reproduced **twice** (the second time shows it is not an accident of the environment);
- the cost of a mistake is high even once: money, delivery to users, authentication, data loss.

A procedure is written as steps with a check on each, not as a story.

**L2 to L3.** A procedure becomes an invariant when breaking it has **already caused a
defect in production**, or when it guards security, money or tenant isolation. An invariant
must state three things: **prohibition, reason, how to check**. Without the third it cannot
be verified, and it will rot unnoticed.

## Technique 1: compress the handover by layer

**The problem.** At one point a cold start required reading about 110 KB: the project rules,
the runbook, the state file and the previous handover, and the handover retold parts of the
other three. Retelling is not only expensive, it *drifts* from the original and starts to lie.

**The rule: a handover carries only L1 and pointers. L2 and L3 are never copied into it.**

| What | Goes to | In the handover |
|---|---|---|
| deployed commit, schema head, what is live, worker state, open PRs | L1 | as a number and a fact |
| task queue with diagnosis and `file:line` addresses | L1 | a table, one or two lines per task |
| a procedure (rollout, acceptance, UI measurement) | L2 | a link to the skill or runbook section |
| an invariant | L3 | a link to the rules, not a copy |
| logs, transcripts, last shift's screenshots | L0 | a path, if it will be needed |

Three questions before a paragraph goes into a handover:
1. Is it a fact with a number, or a retelling? Retellings are dropped in favour of a link.
2. Will it be stale within a day? Then it is L1 and belongs in the state file, not in the rules.
3. Will the reader know what to do FIRST? If not, the handover is not doing its job.

Keep the lessons of a shift to five at most, and only those that change the next action;
the rest are already in L2 or L3. Each lesson is one line with the price of the mistake.

## Technique 2: a versioned skill is L2 in executable form

A procedure that reached L2 is written as a skill with these fields beyond the vendor
minimum: `version`, `updated`, `layer`, `promoted_from` (what proved it), `owner`, and
`verify` (how to tell the skill is still alive).

- `version`: 1.0 to 1.1 is a clarified step; to 2.0, the design changed. The reader can tell
  whether their habit is out of date.
- **Do not copy an invariant into a skill.** It lives in the rules file; the skill links to
  it. A copy is two sources of truth that will diverge.
- **`verify` is mandatory.** A skill with no check rots silently and starts doing harm.
- Another project's skill catalogue gives you the *form*, not the *content*. Adopt the shape,
  but write the evidence from your own incidents and rewrite the body for your own tools;
  the original was written for a different agent's tool names and does not run as is. In
  `promoted_from`, name both the source of the form and your own incident.

## Demotion and death (more important than promotion)

- **Refuted by fact: correct it OUT LOUD.** "Entry X was wrong; the fact is Y; checked like
  this." A silent rewrite lets the next session inherit the error with the status of a fact.
- **A debt closed in code: remove its entry in the same change.** A stale entry costs a
  worker run: a brief written from two such entries came back BLOCKED.
- **Record a removed phantom with numbers** ("closed as stale: 0 of 47,788") or it returns.
- **State is never promoted above L1.** "Production is at commit X" and "the worker is at its
  limit" go stale in hours and have no place in the runbook or the rules.

## What never gets promoted

- Circumstances of one session: which file was open, in what order commands ran.
- Impressions without a measurement ("looks better", "feels faster").
- A retelling of code that `grep` finds in seconds. The design lives in the code; the docs
  carry only what the code does NOT show: the reason for a decision, the price of a mistake,
  the way to check.

## Testing the model on itself

Every few shifts, take a random invariant and a random skill and ask: how is it checked right
now, does the phenomenon still exist, does the skill's `version` match how we actually work?
An invariant with no check is a candidate for demotion to L2 or removal. And beware a guard
that asserts the existence of a hole: it is green only while the system is broken (a real
case: the hole was closed and main went red).
