# Observability that an agent can act on

A coordinator that ships many small changes needs to know two things quickly: did the last
release make things worse, and where. Dashboards answer neither for a small team. What
works is a few cheap signals that name a *place in the code* and a daily summary that a
worker can be briefed from.

Three tools in this kit, from the smallest.

## 1. A stall watchdog for an asyncio event loop (`bin/loop_lag.py`)

**Symptom it exists for:** the service is up, health checks pass, and some requests take
three seconds. Something blocks the event loop for a moment. Logs show nothing, because the
blocked code cannot log while it blocks.

**How it works.** The loop writes a heartbeat every 100 ms. A separate thread checks the
heartbeat every 100 ms. When the heartbeat is older than the threshold, the thread takes a
stack sample of the loop thread. When the loop recovers, one line is reported: how long it
was blocked and where.

Two decisions turned a toy into something that finds culprits:

1. **Sample on every tick of the stall, not once at its start.** The first sample is often
   an innocent bystander: the loop was already blocked when the thread noticed. The code that
   holds the loop is the frame where it spent the *most* ticks. The report says
   `samples=7/9`, so you can see how sure it is.
2. **When the loop's own frame is just "waiting", look at the other threads.** If the most
   frequent frame is the event loop's selector, the loop is not busy; it is starved. Another
   thread holds the GIL: a synchronous library call in an executor, a JSON dump of a big
   object, a regular expression with catastrophic backtracking. The report then names the
   most frequent frame among the other threads, as `other-thread=<name>: <stack>`.

```python
from loop_lag import LoopLagWatchdog

wd = LoopLagWatchdog(threshold=0.5, on_stall=lambda r: log.warning(
    "loop stalled %d ms at %s samples=%d/%d other=%s",
    r.blocked_ms, r.where, r.samples, r.total, r.other_thread))
wd.start()          # inside the running loop, e.g. in the startup hook
...
await wd.stop()
```

Limits: the resolution is the 100 ms period; the callback must be quick (it runs on the
watchdog thread); the report carries code locations only, never request data.

## 2. A daily summary from the stalls

Writing a log line per stall is not enough: nobody reads logs. The project this was
extracted from keeps hourly counters (count, total milliseconds, maximum) and a per-place
counter, with a three-day expiry, and a daily job turns them into a short message: stalls
in the last 24 hours, the worst one, the top three places.

Two details that keep the summary useful:

- **Collapse service frames.** A stack ends in the event loop, the server and the thread
  pool. Only the first frames of *application* code say anything, so the place label drops
  the rest. Without it every place looks the same.
- **Count per place, rank by count then name.** Stable order, so two days of summaries can
  be compared by eye. `top_places` in `bin/loop_lag.py` is that ranking.

The summary is also the cheapest brief for a worker: "this place stalls the loop 40 times a
day, find out why" is a task with a number in it.

## 3. Alert on the lower bound of a rate (`bin/wilson.py`)

"Alert when more than 20 % of items fail" fires on one failure out of three (33 %): a single
unlucky event on a tiny sample pages a person. On 1 of 3 the lower bound is 6 %, below the
threshold — no alert; on 12 of 30 (40 %) it is 25 % — alert. The bound never exceeds the raw
rate, so it does not make a large sample more sensitive; it only stops small samples from
crying wolf.

The lower bound of the Wilson score interval answers the question a person asks:
*"even on the optimistic side of the noise, is this rate above the threshold?"* Alert when
the lower bound is above it.

```text
$ python3 bin/wilson.py 1 3 0.2        # 1 failure of 3, threshold 20 %
rate 1/3 lower bound 0.0615 threshold 0.2: ok
$ python3 bin/wilson.py 400 1200 0.2   # same raw 33 %, 400 times the evidence
rate 400/1200 lower bound 0.3072 threshold 0.2: ALERT
```

Exit code `1` on ALERT, so it drops into a cron job or a gate. For small samples it is
quiet; for large ones it is nearly the raw rate. Use it wherever a share is compared with a
threshold and the denominator varies from hour to hour.

## How the three fit with the release watch

| Question | Tool | Reaction |
|---|---|---|
| Did the new release kill processes or return 5xx? | `watch_release.py`, 10 minutes | rollback, automatic |
| Does the loop stall, and where? | `loop_lag.py` + daily summary | a brief for a worker |
| Is a failure *share* really above its limit? | `wilson.py` | an alert to a human |

Stalls are deliberately **not** a rollback reason: they exist before the release too. The
watch compares the window after with a baseline from the window before, and reports both.
