# Changelog

Format: newest first. Versions follow semantic versioning for the files you copy (hooks,
launcher, tools): a change in a hook's exit codes or an environment variable's meaning is
a major change.

## 1.0.0 (planned tag; the tag is set at publication)

Added
- `bin/watch_release.py`: watch a release for N minutes after roll-out and roll back
  automatically on a sustained failure (`docs/RELEASE_WATCH.md`).
- `bin/loop_lag.py`: stall watchdog for an asyncio event loop, sampling every tick and
  reporting stalls caused by other threads (`docs/OBSERVABILITY.md`).
- `bin/wilson.py`: alert on the lower bound of a failure rate instead of the raw share.
- `bin/pr_stats.py`: counts and durations of a PR stream from the host's own data, with
  round-down "+" publication.
- Docs: `QUICKSTART`, `ACCEPTANCE`, `RELEASE_WATCH`, `OBSERVABILITY`, `INCIDENTS` (25 entries
  in four fields each), `CASE_TENDERSRB` (measured numbers with the method).
- Project files: `CHANGELOG`, `COMPATIBILITY`, `SECURITY`, `CONTRIBUTING`.
- `MERGE_TRAIN`: a section on the dispatcher's batching, stale approvals and locks.

Changed
- README rewritten as a product page: audience, quick start, contents, limits. The incident
  list moved to `docs/INCIDENTS.md`.

Unchanged
- Hooks, launcher, prompts and skills keep their interface; nothing was removed.

## 0.x

Pre-release snapshots published from November 2026 (hooks, launcher, prompts, six skills,
seven docs, two diagrams).
