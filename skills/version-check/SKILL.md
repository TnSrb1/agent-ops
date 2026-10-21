---
name: version-check
description: Decide whether to update the Claude Code CLI on the coordinator and worker NOW - version gap, changelog gap, complaint clusters after a release, and whether a reported regression applies to this machine. Use when the two installs have drifted, a new release is out, the worker misbehaves after an update, or before launching a batch of tasks.
---

# Should we update Claude Code now?

"Versions drift silently; `claude update` fixes it" answers *how*, not *when*. Updating in the
middle of a usage-limited window, or right before a batch of tasks, can cost a whole window if
the release is broken.

## When not to use

- A run is in progress: do not update at all. Check for worker processes and transcript
  growth (a grep inside a shell started for the check matches itself).
- You only need to know which version is installed - that is one command.

## Steps

1. **The gap: what is installed vs what is published.** `claude --version` for each install
   (coordinator, worker) and the published dist-tags. `stable` is not an LTS and can be
   BEHIND an install that is already on `latest`; "install stable" can be a downgrade.

2. **The changelog between installed and latest.** Look for "Fixed ... regression": a release
   that mostly repairs a noisy one is usually a safe landing point.

3. **A cluster of complaints, not single ones.** List open bug issues created since the
   release, sorted by reactions. One issue with 0-1 reactions is permanent noise; a *batch* of
   highly-reacted issues filed right after a release is the signal.

4. **Does the reported regression apply to THIS machine?** This step decides. A cluster once
   proved real (eleven issues, segfault on start) but was tied to one specific libc version,
   and the host ran an older one. Every complaint has a condition (distribution, libc, IDE,
   provider, OS). Until the condition is compared with your environment, a cluster is a
   question, not a prohibition.

5. **The strongest evidence is a second install on the same machine.** If the coordinator
   already runs the candidate version here, that proves it starts here - stronger than any
   outside report. Update the one whose downtime is cheaper first (the coordinator), the
   worker second.

6. **After updating, verify by fact, not by assumption:**
   the version; the settings file checksum (model and hooks still in place); the auth status
   (`claude auth status`: logged in, which plan); and a real run
   `env -u ANTHROPIC_API_KEY claude -p "Reply with one word: working"`.
   The account e-mail stored in the local config does NOT prove the session is alive - it
   stays in place when the tokens are dead. Once the config showed the right account and the
   settings checksum matched, while the credentials file held empty tokens whose refresh
   expiry was days in the past; every run would have failed to authenticate. Check the
   refresh-token expiry directly. Re-login is a human, interactive act (never switch to
   API-key billing to "fix" it). And note that a short probe run succeeds even when the plan's
   limit is exhausted: it proves the binary works, not that quota remains.

## Verdict

One line: **update / wait / do not touch**, with the reason and a number (versions, cluster
size, your condition check). "Looks quiet" is not a verdict.

## What this was proven on

A worker two patch versions behind `latest` and one above `stable`; a segfault cluster that
did not apply (host libc older than the affected one) while the coordinator already ran the
candidate on the same host. The update went through and settings survived. An earlier note
"the worker's session survived" was WRONG: it rested on the e-mail field and a matching
checksum, without a real run; the refresh token had expired days earlier.
