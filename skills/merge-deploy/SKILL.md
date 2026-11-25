---
name: merge-deploy
description: Merge accepted worker PRs and roll them out - who may merge what, approval pinned to a commit, the merge train, gates in their own worktree, backups before migrations, and how to tell that a release actually happened. Use before any merge, gate run, rollout or migration.
---

# Merge and roll out

Merging is the moment an unreviewed change would become the product, and with automatic
deployment there is no gap between "merged" and "released". This skill collects the rules that
were each paid for by an incident. It assumes the review in `accept-worker-pr` is done.

## When not to use

- You have not reviewed the PR yet: run `accept-worker-pr` first.
- Docs-only change outside any deployed path: merge after reading the diff.

## Authority

1. **High-risk paths** (migrations, deploy configuration, auth, billing, CI workflows, the
   decision records) need the owner's word, unless the owner has delegated them in writing.
   Delegation does not remove acceptance; a migration additionally needs a fresh database
   backup with exit code 0 before the merge.
2. **Everything else** the coordinator merges after its own review.
3. **Spend is not a merge decision.** Workflows that call a paid API stay off until the owner
   turns them on, even if a PR adds one.

## Steps

1. **PRs arrive as drafts.** If one is not a draft, turn it back into one before anything
   else. A ready PR can be picked up by automation within minutes, before review.

2. **Approve a commit, not a PR.** Record "PR N at sha S". If the worker pushes again after S,
   the approval is stale and the new commits need review. A live fix worker once kept pushing
   report-only commits after review; anything keyed on "the PR" would have merged unread code.

3. **Prefer the merge train for anything that is not a one-off** (`docs/MERGE_TRAIN.md`): cheap
   prechecks, one full gate on the merged batch, bisect on failure, merge commits, and a final
   comparison of `tree(main)` with the tested tree. Branches that are each green can make a red
   `main`; only a gate on the merged tree sees that.

4. **If you gate by hand:** a fresh worktree on the exact commit
   (`git worktree add --detach <path> <sha>`), never the shared clone, which a periodic reset
   can move under you. Prove the code resolves from that worktree (an editable install can
   test another branch). Print the HEAD before and after; both must equal the sha you approved.
   No pipe into `tail`.

5. **Read a red gate before you blame the PR.**
   - "Could not get the lock", a killed process, out of memory: the tests did not run. Retry
     once, later; this is not a red result.
   - The same test red for different PRs: a defect of `main`, not of the PR.
   - Red only in the full gate, green alone: suspect the environment (signals ignored in a
     background run, test-order pollution under parallel workers) before ordering fixes.
     See `verify-traps`.

6. **Migrations.** Backup first, exit code checked; no backup, no merge. Check for long-running
   transactions before the schema change; a forgotten probe holding one transaction for two
   hours once blocked a migration and, behind it, delivery. If you roll code back after a
   migration, keep the migration files, or the next migrate fails.

7. **Do not push to `main` while gates or a train are running.** The train notices that `main`
   moved and rebuilds; a long run never finishes. Hand over in a side file until the queue is
   empty, then move it into the repository in one commit.

8. **A merge is a release.** With automatic deployment, confirm the release by facts, in this
   order: the deployed checkout contains the merge commit; the service restarted after it; for
   a migration, the database's schema version equals the new head (the service being up proves
   nothing about the schema); then render the changed page or run the changed path on safe data.
   A 502 right after a restart is the service coming up: poll for 200 before you judge.

9. **Never edit a shell script that a live process is executing.** Bash reads the file by
   offset; an in-place edit shifted the bytes under a running merge chain and would have ended
   it in a syntax error. Write a new file and `mv` it over (new inode), or use a new name.

10. **Waits that must outlive your session run detached** (`setsid nohup`), not as a background
    task of the session: a session's background tasks die with it, and a gate can wait 45
    minutes for the lock.

## Failure modes

| Symptom | What it usually is | Action |
|---|---|---|
| "conflicting" right after a neighbour merged | stale status on the hosting side | re-read the status after a few minutes before redoing anything |
| train says "main is not the tested tree" | partial merge: a later PR was refused | re-approve the remaining PR; do not hand-merge it |
| gate FAIL with no failing test names | infrastructure (lock, memory) | retry once; check the machine, not the code |
| release "done" but old behaviour on the page | deploy waited for its window, or migration not applied | check the deployed commit and the schema version |
| merged PR keeps a run busy | a worker still waiting for its own gate | stop it by its PID, not by pattern |
