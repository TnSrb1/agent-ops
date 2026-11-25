# The coordinator's own session: facts by script, not by memory

The worker is fenced by hooks. The coordinator was, for a long time, fenced only by its
instructions, and instructions are exactly what a long session forgets. This document
describes the hooks and habits that now guard the coordinator itself.

The principle behind all of them: **a rule that was broken once becomes a check, not a louder
line in the prompt.** Bold warnings in an instructions file were broken again and again; a hook
that blocks the command was not. When a new lesson arrives, the first question is "can a
machine check this?" If yes, it becomes a hook, a test or a gate step, and the instructions keep
only a one-line pointer to that check.

## Session start: facts collected by a script

A new session used to start by reading the state document and trusting it. The state document
is a hypothesis: it says what someone believed at the time of writing.

A start hook now runs before the first word and injects facts into the context, each command
with its own timeout so the start never waits more than about fifteen seconds:

- tool versions for the coordinator and the worker account (if they differ, update first);
- the live site's HTTP status, measured twice if the first answer is not 200 (one measurement
  once reported 502 during a restart and 200 a minute later), plus the age of the API container
  so a restart is not mistaken for an outage;
- whether automatic deployment is on, the current `main` commit and the database schema version;
- how many PRs are open and how many worker runs are alive;
- how long the login tokens of both accounts have left, and the usage window of each;
- the list of existing probe scripts, so the session reuses one instead of writing a new one;
- the start section of the handover from `main` (cut loudly, never silently, if it grows too
  long), and the top of the live handover file if it is newer.

What cannot be measured is printed as `?`, never guessed.

## Context guard

Re-reading a long context is the most expensive line in the whole loop: one coordinator window
cost several times what a worker run cost. A stop hook computes how full the context is and,
above a threshold, blocks the end of the turn with a reminder to write the handover. It fires
at most once every fifteen minutes per session, so it never becomes noise that people switch
off.

The window size is measured, not assumed: the first version took a constant from someone else's
README and reported "context 125%" on a healthy session.

## One session, one unit of work

A coordinator session does one thing: a diagnosis, OR a brief, OR an acceptance, OR a rollout.
At about 60% of the context it writes the handover and ends. Mixing units in one session is how
a long session ends up holding three half-finished things and no handover.

## Handover without touching `main`

The handover is written by the coordinator itself, automatically, after every merge, rollout,
run start or finish and decision by the owner, and never waits for a request. It contains facts
and pointers only.

While gates or the merge train are running, the coordinator does not push to `main`: a push
moves the base under a running gate, and the train rebuilds. The handover then goes into a live
file outside the repository; the start hook reads it if it is newer than the copy in the
repository. When the queue is empty, it is moved into the repository in one commit and the file
is deleted.

## Corrections are made out loud

When a note turns out to be wrong, the correction states the old claim, the fact and how it was
checked. A silent rewrite lets the next session inherit the error as a fact. A pending item
"waiting for the owner" must link the artifact the owner is supposed to approve; an item without
one is the coordinator's own unfinished work wearing someone else's name.

## The coordinator's own guard

The coordinator account has a pre-tool hook of its own. It blocks killing processes by pattern
(a pattern once matched the coordinator's own shell and killed it; only PIDs now), and liveness checks that cannot work across accounts: `kill -0` on another user's
process returns "operation not permitted", which a waiter once read as "dead" and exited at
once. Production writes are not run by the coordinator at all: it prepares a script file and the
owner runs it with one command, because a long pasted command breaks and a multi-line one gets
pasted as one piece.

## What this costs

Hooks are small shell scripts. The cost is discipline: every new lesson is first asked
whether it can be a check, and a check is added to the gate only if it does not go red on a
clean PR.
