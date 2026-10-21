#!/usr/bin/env python3
"""PreToolUse(Bash) guard for a headless worker.

Turns the rules a worker is *told* ("never merge, never push to the default branch,
open PRs as drafts only") into rules it *cannot* break. Exit code 2 blocks the tool call
and feeds stderr back to the model, which then picks another path.

This is a regex over the command text, not a sandbox: it catches the honest mistake,
not an adversary who wraps the command in `bash -c` or builds it from variables.
(It also reads text literally: a heredoc that merely *contains* a blocked command is
blocked too.) Pair it with a low-privilege account and a token that cannot merge.

Configuration (environment, all optional):
  AGENT_OPS_PROTECTED   comma-separated protected branches      (default: main,master)
  AGENT_OPS_EXTRA_DENY  JSON list of [regex, reason] pairs      (default: none)
"""

import json
import os
import re
import sys

PROTECTED = [
    b.strip()
    for b in os.environ.get("AGENT_OPS_PROTECTED", "main,master").split(",")
    if b.strip()
]
_BRANCHES = "|".join(re.escape(b) for b in PROTECTED)

# One simple command = no newline, ';', '&' or '|' between the words we match on, so
# `git status; echo push main` is not mistaken for a push to main.
_SEG = r"[^\n;&|]*"

RULES = [
    (r"\bgh\s+pr\s+merge\b", "merging is the coordinator's job, after acceptance"),
    (
        r"\bgh\s+pr\s+ready\b",
        "marking a PR ready is the coordinator's call; keep it draft",
    ),
    (
        rf"\bgit\b{_SEG}\bpush\b{_SEG}(\s|:)(refs/heads/)?({_BRANCHES})(\s|$)",
        "pushing to a protected branch is forbidden; push your own branch",
    ),
    (
        rf"\bgit\b{_SEG}\bpush\b{_SEG}\s(-f|--force|--force-with-lease|--force-if-includes)(\s|=|$)",
        "force-push is forbidden",
    ),
    (
        rf"\bgit\b{_SEG}\bpush\b{_SEG}\s\+\S",
        "force-push via a '+refspec' is forbidden",
    ),
]
try:
    RULES += [
        (p, r) for p, r in json.loads(os.environ.get("AGENT_OPS_EXTRA_DENY", "[]"))
    ]
except (ValueError, TypeError):
    print(
        "guard_bash: AGENT_OPS_EXTRA_DENY is not a JSON list of pairs", file=sys.stderr
    )


def check(cmd: str):
    """Return the reason a command is blocked, or None."""
    for pattern, why in RULES:
        if re.search(pattern, cmd):
            return why
    if re.search(r"\bgh\s+pr\s+create\b", cmd) and not re.search(
        r"(\s--draft\b|\s-d\b)", cmd
    ):
        return "PRs are draft-only: add --draft"
    return None


def main() -> int:
    try:
        cmd = json.load(sys.stdin).get("tool_input", {}).get("command", "")
    except ValueError:
        return 0  # not our payload; never wedge the session on a parse error
    why = check(cmd or "")
    if why:
        print(f"BLOCKED by worker guard: {why}.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
