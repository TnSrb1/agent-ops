# Case: the product this kit was extracted from

One service, built since May 2026 by a coordinator session and headless workers, with a
human owner who decides about money and anything irreversible. This page lists only what was
measured, how, and what could **not** be measured.

## Numbers

Measured on 26 November 2026 from the hosting service's own pull request data. Published
figures are rounded down to a threshold and marked "+" (`plus()` in `bin/pr_stats.py`), so a
claim is never above the measurement.

| What | Published | Measured |
|---|---|---|
| Worker PRs merged (branch prefix `claude/`) | 900+ | 999 |
| Worker PRs closed without merge | 30+ | 33 |
| Worker PRs open at the time | | 14 |
| Period of the first to the last merge | 200+ days | 203 days (8 May to 26 November) |
| Merged per calendar day, average | 4+ | 4.9 |
| Open to merge, median | about 1 hour | 1.2 h |
| Open to merge, 90th percentile | about 1 day | 25.1 h |
| Merged within 24 hours of opening | 80+ % | 89.7 % |

Reading: a worker PR is usually merged within a couple of hours of being opened. The tail is
the PRs that waited for the owner (money, access, irreversible changes) or for a re-review.

## Not measured

- **Share of PRs with a review blocker.** No record exists. Reviews were written as comments
  and handover notes, not as a field: a search of the PR comments for the verdict line finds it
  in 2 PRs out of about 1,000, so there is no uniform record to count. A figure here would be
  invented, so there is none. `docs/ACCEPTANCE.md` now asks for
  the verdict as a fixed line, so the next count can be taken from data.
- **Automatic rollbacks.** The roll-out log that records "rollback: none/done" starts on
  18 November 2026. It holds four roll-outs and no rollbacks. Four is too few to say anything
  about a rate; it shows that the mechanism ran, not that it is rare.
- **Cost per PR.** Spend is tracked per account, not per PR.
- **Defects that reached production.** Not counted in a uniform way.

## Method (repeat it)

```bash
gh pr list --state all --limit 5000 \
  --json number,state,createdAt,mergedAt,closedAt,headRefName > prs.json
python3 bin/pr_stats.py prs.json --prefix claude/
```

- Use `--limit` with a large number and filter the prefix on the client. The search form
  (`--search "head:claude/"`) is capped at 1,000 results by the hosting service and returned
  998 merged PRs on the day, which would have understated the count by one.
- Durations are `mergedAt - createdAt` of merged PRs; the median and the percentile use the
  nearest-rank method.
- "Merged per day" divides by the days from the first merge to the last, inclusive.
- Merge-train PRs are counted like any other PR; the train does not change the counting.

## What the numbers do not say

They describe throughput and latency of a process, not the quality of what it produced.
Quality is what `docs/VERIFYING_AI_PRS.md` and `docs/INCIDENTS.md` are about: 25 recorded
failures of the process itself, each with the rule that now catches it.
