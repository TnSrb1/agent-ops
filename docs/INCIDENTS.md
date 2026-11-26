# Incidents

Every rule in this kit is a scar. Each entry has the same four fields: **Symptom** (what
was seen), **Cause** (what it really was), **Rule** (what changed), **Check** (what now
catches it without anyone remembering). Entries are anonymised: no product names, no
addresses, no people. Numbers are the ones recorded at the time.

Entries 1 to 6 and 25 are new in 1.0; 7 to 24 are the list the README carried before.

## Roll-out and production

### 1. Processes killed by their own supervisor during start-up
- **Symptom:** a few minutes after a roll-out, a burst of 502 responses and the log line
  "child process died". The smoke test had passed.
- **Cause:** the multi-process server's supervisor pings each process twice a second and
  kills one that does not answer within a timeout (5 s by default). The answer comes from a
  thread inside the process and needs the interpreter lock. Start-up under load (four
  processes sharing the CPU, a warm-up of templates and routes) held the lock longer than 5 s,
  so healthy processes were killed as "hung" and restarted cold in the middle of live
  requests.
- **Rule:** a supervisor's health timeout must exceed the worst start-up you can observe,
  not the typical one. The timeout became a setting, default 60 s.
- **Check:** the release watch (`RELEASE_WATCH.md`) counts the "died" line; two in the
  window roll the release back.
- **Honest note:** the worker assigned to reproduce the restart loop on a test bench did not
  reproduce it and stopped with that statement instead of inventing a cause. The setting
  follows from reading the supervisor's code and the start-up timings; the watch is what
  would show a recurrence.

### 2. A smoke test cannot see a failure that starts two minutes later
- **Symptom:** the roll-out reported success; users saw errors minutes afterwards.
- **Cause:** a smoke test samples one moment. Supervisor kills and 502 bursts fall outside it.
- **Rule:** a roll-out ends after a watched window, not at the first healthy answer.
- **Check:** `bin/watch_release.py`: ten minutes, rollback on thresholds. Whether it has
  rolled anything back in production is stated in `CASE_TENDERSRB.md`, with its date.

### 3. The watchdog named an innocent line
- **Symptom:** "event loop stalled at line X" for weeks; the code at X was fine.
- **Cause:** the watchdog took one stack sample when it noticed the stall. By then the loop
  had been blocked for a while, and the sample showed whatever was running at that moment.
  In other cases the loop's own frame was just "waiting": another thread held the lock.
- **Rule:** sample on every tick of a stall and report the most frequent frame with
  `samples=N/M`; when the loop frame is idle, report the busiest other thread.
- **Check:** `tests/test_tools.py` blocks the loop with a named function and asserts that
  the report names it, from several samples.

### 4. A rollback that redeploys the broken head
- **Symptom (found in review, before it happened):** the roll-out script starts with
  `git fetch` and `git reset --hard origin/main`. Called as the rollback, it would fetch
  and reset to the broken commit.
- **Rule:** the rollback runs the same script with `git` shimmed: `fetch` does nothing,
  `reset` goes to the previous commit; migration files are kept only when the database
  revision is unknown to the old tree.
- **Check:** the roll-out's own tests cover the shim and both migration cases.

### 5. A timer that resets the checkout wiped uncommitted work
- **Symptom:** files an agent had just written were gone.
- **Cause:** an automatic roll-out timer runs `git reset --hard` in the main clone every
  few minutes of eligibility. Work left uncommitted there is destroyed.
- **Rule:** agents work only in their own worktree; commit and push after every logical
  step. The reflog and an immediate push are the recovery.
- **Check:** hard-limit mode in the preamble: first action is an empty marker commit and a
  push; every step ends with a commit and a push.

### 6. Reverting a mutation erased the work
- **Symptom:** after a mutation check, three new files were gone.
- **Cause:** `git checkout -- <file>` restores from the *index*. The work was not staged, so
  "undo the mutation" restored the old content over the new.
- **Rule:** stage (or commit) first, mutate second, revert third.
- **Check:** `ACCEPTANCE.md`, section 2; the testing-document template names the order.

## The worker and its guards

### 7. A report said "GATE PASS" and an unformatted file was in the PR
- **Cause:** the gate had run before the last commit.
- **Rule / check:** the gate runs after the final commit; the stop hook stamps PASS per
  `HEAD`; the coordinator re-runs it.

### 8. A gate "passed" about someone else's commit
- **Cause:** a periodic reset in a shared clone moved the branch between checkout and test.
- **Rule / check:** every gate runs in its own worktree and prints `HEAD` before and after.

### 9. A commit landed on top of red tests
- **Cause:** `pytest | tail && git commit` takes its exit code from `tail`.
- **Rule / check:** never pipe a test run before a commit; the guard hook blocks the
  pattern.

### 10. A worker ran its gate in the background and exited
- **Cause:** a headless run kills what it left running; no PR was opened.
- **Rule / check:** the gate runs in the foreground; the stop hook demands a PR.

### 11. A non-draft PR was merged by automation before anyone looked
- **Rule / check:** drafts only, enforced by the guard, not requested by a prompt.

### 12. An empty "open PRs" list was read as "no PR"
- **Cause:** auto-merge had already merged it; the lookup used `--state open`; a duplicate
  was opened.
- **Rule / check:** lookups use `--state all`.

### 13. A fix run made duplicate PRs
- **Cause:** launched under a new name, it made its own branch, and its stop hook demanded a
  PR from that branch.
- **Rule / check:** a fix runs on the PR's own branch (`skills/launch-worker`).

## Verification

### 14. Green tests that asserted nothing
- **Cause:** an expectation computed from the same catalogue as the code; a mock test named
  after a check the mock never ran.
- **Rule / check:** expectations are literals from a real run; the mutation must be shown
  to have applied (`ACCEPTANCE.md`).

### 15. Phantom tasks
- **Symptom:** six queued tasks removed in one day.
- **Cause:** the supposed defect was in zero rows, or not in the source, or already handled.
- **Rule / check:** a verdict step before every brief (`skills/check-value`); a removed
  phantom is written down with its numbers, or it comes back next session.

### 16. Two green branches, one red main
- **Cause:** one PR raised a cap from 12 to 30; a parallel PR mirrored the old 12 in a page
  and its test.
- **Rule / check:** search the old value across neighbouring branches before merging; the
  train gates the merged tree.

### 17. A brief was followed to the letter and something that worked broke
- **Cause:** a search for the number of an expired record stopped opening its card.
- **Rule / check:** a separate reviewer for "before and after" (`ACCEPTANCE.md`).

### 18. Three of nine review blockers were invisible in the branch
- **Cause:** a change merged into `main` after the branch point.
- **Rule / check:** reviewers get the log from the merge base to `main`.

### 19. "Quick pass" with fifteen red tests
- **Cause:** the quick check selected tests by file name; render tests never name their
  template.
- **Rule / check:** selection also uses a coverage map, and a template change runs the whole
  render-test directory. The full gate on the train stays the proof.

## The gate and the train

### 20. The gate became the bottleneck
- **Cause:** every PR went through the full gate three or four times, behind one lock.
- **Rule / check:** workers run a quick check; one gate runs on a batch (`MERGE_TRAIN.md`).

### 21. A batch merged only its first PR, again and again
- **Cause:** squashing each PR left `main` without the earlier batch commit; a generated
  file carrying a commit hash conflicted on the second PR. 54 train stops in eleven days.
- **Rule / check:** merge commits; the train compares the tree of `main` with the tested
  tree.

### 22. The gate lock was not a queue
- **Cause:** a bare `flock` lets newcomers overtake; one gate waited about four hours, and
  "could not get the lock" looked like a red gate.
- **Rule / check:** a FIFO of tickets; lock and memory failures are retried, not blamed on
  a PR.

### 23. An innocent PR was blamed four times
- **Cause:** a signal test was red only in background gates, because a background process
  inherits SIGINT as ignored. Reproductions under `timeout` looked green.
- **Rule / check:** reproduce in the gate's environment; the same test failing for different
  PRs is a defect of `main`.

### 24. Six fixes for the wrong cause
- **Cause:** a database test was red only in the full parallel run; a neighbour on the same
  parallel worker leaked a dependency override.
- **Rule / check:** replay the gate's per-worker order and bisect the file list; found in 15
  minutes the seventh time.

### 25. A dropped PR was picked up again every two minutes
- **Cause:** a PR that left the batch on a conflict kept its approval; 178 starts and an
  alert storm.
- **Rule / check:** a drop is a state file newer than the approval; only a fresh approval
  clears it.
