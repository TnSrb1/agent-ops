# Several agents on one small machine

The whole loop runs on one virtual machine with four cores and eight gigabytes of memory: the
coordinator, two or three headless workers, their quick checks, the full gate of the merge train
and its throwaway database. This document lists what keeps such a machine alive. Each rule
came from a day when it was not.

## One heavy gate at a time, in order of arrival

The full gate runs the test suite in parallel processes against a throwaway database. Three or
four gates at once took the machine down completely.

So the heavy part of the gate takes a lock. A plain `flock -w` is not a queue: whoever happens
to ask at the moment of release wins, and a gate once waited about four hours while newer ones
overtook it. The lock is now a **FIFO of tickets**: each waiting gate writes a ticket named
`<epoch_ns>-<pid>` into a queue directory; the turn belongs to the owner of the oldest ticket
whose process is still alive, and dead tickets are removed on the fly. `flock` still provides
mutual exclusion; the tickets only decide the order.

Two consequences:

- **"Could not get the lock" is not a red gate.** The tests did not run. Callers grep for that
  marker and retry later instead of blaming the code.
- **A queue only works for those who know about it.** Until the ticket logic was in every
  branch, gates from older trees kept taking the bare lock and starved the queue. Plan the
  transition: land the lock change first, then rebase the rest.

The number of parallel test processes is chosen from free memory at start
(`min(3, (MemAvailable - 1.5 GB) / 0.7 GB)`), not fixed.

## A slot limit for workers

The launcher waits for a free slot before it starts a run: at most two worker runs at a time
since the machine was last resized. A worker's quick check takes no gate lock, so it can run
beside the train's gate.

## A janitor for orphans

A killed run does not kill what it started. Preview servers for screenshots, local HTTP servers
and throwaway databases outlived their runs and ate the memory. A janitor in cron removes:

- test stands and local servers of the worker account older than a few hours;
- throwaway database containers whose owning process no longer exists (the container name
  carries the owner's PID), and other unnamed database containers older than a few hours.

It never touches the production containers, and it is safe to run again. Compressed swap in
memory buys the time the janitor needs.

## A test that is red only in the background

Processes started in the background inherit SIGINT as ignored, and a non-interactive shell
cannot install a trap for a signal that was ignored on entry. A test that sent SIGINT to a child
shell was green in a terminal and red in every background gate, and four batches of the train
blamed an innocent PR before this was understood. Wrapping the reproduction in `timeout` hid the
effect, because `timeout` installs its own handler. Reproduce in the gate's environment:

```
python3 -c "import signal, subprocess, sys; signal.signal(signal.SIGINT, signal.SIG_IGN); \
sys.exit(subprocess.call(['python3', '-m', 'pytest', '-q', 'tests/test_x.py']))"
```

## Known flaky tests: a short list with reasons

The train keeps a hand-curated list of flaky tests. A batch whose only failures are on that list
gets one rerun of just those tests; green means PASS. Each entry carries the reason (the signal
case above; a two-second timeout that fails under gate load). A test does not go on the list to
make a red batch green: it goes on the list after its cause is known.

## Rules for every process on the machine

- Stop processes by PID, never by pattern. Other people's gates match your pattern.
- Long waits that must survive a session run detached (`setsid nohup`).
- Never edit a script that a live process is executing; write a new file and move it over.
- A probe inside a production container gets a unique file name, a timeout and cleanup on
  failure; a killed run does not kill its `docker exec`.
