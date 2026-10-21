#!/usr/bin/env bash
# Launch one headless worker run with a single command.
#
#   bin/run_worker.sh <slug> <model> <brief-file>
#
# What it does, in order:
#   1. validates the arguments and the brief (not empty, references the preamble);
#   2. creates a dedicated git worktree and branch <prefix><slug> (or continues the
#      branch if it already exists on the remote);
#   3. commits and pushes the brief into the branch, so the run can be resumed;
#   4. starts `claude -p` detached (setsid) with ANTHROPIC_API_KEY unset;
#   5. after LIVENESS_WAIT seconds checks the process is alive, its log is non-empty,
#      and the log does not report a usage limit. The log goes next to the worktree.
#
# What it does NOT do: decide whether the run is worth paying for, or pick the model for
# you. Anything other than the cheap default model needs ALLOW_EXPENSIVE=1, so spend is
# always an explicit human act.
#
# Environment:
#   AGENT_OPS_REPO          main clone (default: current directory's git toplevel)
#   AGENT_OPS_WT_ROOT       where worktrees go             (default: parent of the clone)
#   AGENT_OPS_BRANCH_PREFIX branch prefix                  (default: worker/)
#   AGENT_OPS_CHEAP_MODEL   default model id               (default: claude-haiku-5-5)
#   AGENT_OPS_PREAMBLE_MARK text the brief must contain    (default: BRIEF_PREAMBLE)
#   ALLOW_EXPENSIVE=1       permit a model other than the cheap one
#   LIVENESS_WAIT           seconds before the liveness check (default: 60)
#   DRY=1                   validate only; no worktree, no push, no process
set -euo pipefail

slug=${1:?usage: run_worker.sh <slug> <model> <brief-file>}
model=${2:?model}
brief=${3:?brief file}

cheap=${AGENT_OPS_CHEAP_MODEL:-claude-haiku-5-5}
prefix=${AGENT_OPS_BRANCH_PREFIX:-worker/}
mark=${AGENT_OPS_PREAMBLE_MARK:-BRIEF_PREAMBLE}
repo=${AGENT_OPS_REPO:-$(git rev-parse --show-toplevel)}
wt_root=${AGENT_OPS_WT_ROOT:-$(dirname "$repo")}
wait_s=${LIVENESS_WAIT:-60}

[[ "$slug" =~ ^[a-z0-9-]+$ ]] || { echo "FAIL: slug must match [a-z0-9-]+"; exit 1; }
[ -f "$brief" ] || { echo "FAIL: no such brief: $brief"; exit 1; }

# "cheap" is an alias for the default; anything else is an explicit, paid-for choice.
[ "$model" = cheap ] && model=$cheap
if [ "$model" != "$cheap" ] && [ "${ALLOW_EXPENSIVE:-}" != 1 ]; then
    echo "FAIL: model '$model' is not the default '$cheap'; set ALLOW_EXPENSIVE=1 once the owner has agreed to the spend"
    exit 1
fi

size=$(wc -c < "$brief")
[ "$size" -gt 200 ] || { echo "FAIL: brief is $size bytes (an empty or truncated brief starts a run that guesses)"; exit 1; }
grep -q "$mark" "$brief" || { echo "FAIL: brief does not reference $mark; workers must be pointed at the preamble"; exit 1; }

wt="$wt_root/wt-$slug"
br="$prefix$slug"
task="tmp/TASK_$slug.md"

if [ "${DRY:-0}" = 1 ]; then
    echo "DRY OK: brief $size bytes, model $model, branch $br, worktree $wt"
    [ -e "$wt" ] && echo "WARN: $wt already exists"
    exit 0
fi

# One worktree = one operation. Refuse to reuse a directory that may hold a live run.
[ -e "$wt" ] && { echo "FAIL: $wt exists - a run is live or the worktree was not cleaned up"; exit 1; }

cd "$repo"
git fetch -q origin
if git ls-remote --exit-code --heads origin "$br" > /dev/null; then
    base="origin/$br"   # continue an interrupted branch
else
    base="origin/main"
fi
git worktree add -q -B "$br" "$wt" "$base"
(
    cd "$wt"
    mkdir -p tmp
    cp "$brief" "$task"
    git add -f "$task"
    git commit -qm "tmp: TASK $slug"
    git push -q -u origin "$br"
    echo "branch $br from $base, tip $(git rev-parse --short HEAD)"
)

# Detached from this shell; API key unset so the run bills the subscription, not the API.
# The log lives next to the worktree, not inside it: an untracked log in the worktree
# blocks the worker's stop hook ("uncommitted changes") and gets swept up by `git add -A`.
ts=$(date -u +%m%d%H%M)
log="$wt_root/run_${slug}_$ts.log"
(
    cd "$wt"
    setsid nohup env -u ANTHROPIC_API_KEY claude -p --verbose \
        --dangerously-skip-permissions --model "$model" \
        "Read the file $task and carry out the task completely." \
        > "$log" 2>&1 < /dev/null &
)

# Liveness is two measurements, both taken after LIVENESS_WAIT seconds:
#   1. a process whose cwd is the worktree is alive (a grep for a substring would match
#      its own command line, so the cwd is what identifies the run);
#   2. the log is non-empty. The log starts empty at launch, so "grew since launch" and
#      "non-empty" are the same check; a silent live process is not a working run.
sleep "$wait_s"
pid=""
for p in $(pgrep -f '^claude -p' || true); do
    if [ "$(readlink "/proc/$p/cwd" 2> /dev/null)" = "$wt" ]; then pid=$p; break; fi
done
if [ -z "$pid" ]; then
    echo "FAIL: no worker process after ${wait_s}s. Log tail:"
    tail -5 "$log"
    exit 1
fi
if [ ! -s "$log" ]; then
    echo "FAIL: worker pid=$pid is alive but its log is empty after ${wait_s}s, see $log"
    exit 1
fi
if grep -qi "hit your" "$log"; then
    echo "FAIL: usage limit reached, see $log"
    exit 1
fi
echo "OK pid=$pid model=$model worktree=$wt log=$log"
