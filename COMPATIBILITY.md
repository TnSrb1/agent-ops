# Compatibility

What was actually run, not what should work.

| Component | Verified with | How |
|---|---|---|
| Claude Code | 2.1.327 | `claude --version` on the machine that ran the tests, 26 November 2026 |
| Python | 3.12 (CI); 3.10+ expected | the tools use the standard library only |
| git | 2.30+ | worktrees and `merge-base --is-ancestor` |
| `gh` CLI | any recent release | draft PR creation and `gh pr list --json` |
| OS | Linux (Debian/Ubuntu family) | the launcher uses `setsid`; macOS is untested |

## Claude Code interface the hooks rely on

- `PreToolUse` hook: exit code 2 blocks the call and sends stderr to the model.
- `Stop` hook: JSON `{"decision": "block", "reason": ...}` keeps the run going.
- `claude -p` headless mode with `--dangerously-skip-permissions`.

If a new Claude Code release changes any of these, `tests/test_hooks.py` still passes because
it tests the scripts, not the client. After every Claude Code update, run Part A of
`docs/QUICKSTART.md` and one real worker with a trivial brief before trusting a batch.

## Not verified

- Claude Code versions other than 2.1.327.
- Windows and macOS.
- Part B of the quickstart (a real worker and a real PR) is written from the launcher's code
  and tests; Part A is a recorded run.
