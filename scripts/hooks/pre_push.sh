#!/usr/bin/env bash
# Pre-push checks: the same gates CI runs, plus whole-repo guards that the commit
# hooks (staged files only) cannot see. Does not call pre-commit (avoids recursion).
#
# Guards run on the current checkout and, when pre-commit exports the pushed range
# (PRE_COMMIT_FROM_REF and PRE_COMMIT_TO_REF, pre-commit 4.x, pre-push stage), also on
# the commits being pushed: .env paths, a root CONTEXT.md and added home-path lines
# anywhere in that range.
# A new branch has no usable from-ref, so the range is the commits not reachable from
# any remote-tracking ref. Without the variables (manual run) only the checkout is checked.
# Merge commits are included (--cc: changes made by the merge itself, e.g. conflict
# resolution; --cc rather than -m so lines merely brought in from another parent, which
# are scanned as their own commits or already on the remote, are not re-flagged).
# Every git call whose output is parsed passes --no-color (forced colour would break parsing).
# The range scans use plumbing (rev-list | diff-tree), not porcelain log: its output depends on
# user config (log.showSignature prints signature text into the stream).
# All regex and NUL-separated path matching lives in guard_scan.py (git + Python 3 only,
# no PCRE, no GNU grep), so quoted (core.quotePath) names match too and macOS works.
#
# CHIMERA_PRE_PUSH_GUARDS_ONLY=1 stops after the guards (the hook tests use it so they
# do not recurse into the real suite). Unset, the full run happens.
set -euo pipefail

# Resolve the helper before the cd so manual runs from any directory work.
SCAN="$(CDPATH= cd -- "$(dirname -- "$0")" >/dev/null && pwd)/guard_scan.py"
cd "$(git rev-parse --show-toplevel)"

# Same exclusions as the no-absolute-home-path hook in .pre-commit-config.yaml.
EXCLUDES=(':!.pre-commit-config.yaml' ':!scripts/hooks/pre_push.sh')

tmp=$(mktemp)
trap 'rm -f "$tmp"' EXIT

# Feeds "$tmp" to the Python helper in the given mode and prints its hits.
# Helper exit codes: 0 hit, 1 no hit, 2 or other = error (a crash exits 2, never 1).
# Returns 0 on hit, 1 on no hit, exits on any other result (fail closed).
scan() {
  local rc=0
  python3 "$SCAN" "$1" <"$tmp" || rc=$?
  case "$rc" in
    0) return 0 ;;
    1) return 1 ;;
    *) echo "guard_scan.py $1 failed (rc=$rc)" >&2; exit 1 ;;
  esac
}

# Range of commits being pushed, as rev-list arguments; empty when unknown.
RANGE=()
from="${PRE_COMMIT_FROM_REF:-}"
to="${PRE_COMMIT_TO_REF:-}"
if [ -n "$from" ] && [ -n "$to" ]; then
  if [[ "$from" =~ ^0+$ ]] || ! git rev-parse --verify --quiet "${from}^{commit}" >/dev/null; then
    RANGE=("$to" --not --remotes)
  else
    RANGE=("${from}..${to}")
  fi
fi

echo "== tracked .env files and root CONTEXT.md =="
git ls-files -z >"$tmp"
if scan paths; then
  echo ".env files and a root CONTEXT.md must not be tracked" >&2
  exit 1
fi

if [ "${#RANGE[@]}" -gt 0 ]; then
  echo "== .env files and root CONTEXT.md in pushed commits =="
  git rev-list "${RANGE[@]}" |
    git diff-tree --stdin --root -r -z --no-commit-id --name-only --no-renames --cc --diff-filter=ACMRT --no-color >"$tmp"
  if scan paths; then
    echo ".env files and a root CONTEXT.md must not be pushed (present in the pushed commits)" >&2
    exit 1
  fi
fi

echo "== absolute home paths =="
# git grep only pre-filters (POSIX ERE); the lookbehind is applied by the helper.
rc=0
git grep --no-color -n -I -z -E '(/home/|/Users/)[A-Za-z0-9._-]+' -- . "${EXCLUDES[@]}" >"$tmp" || rc=$?
case "$rc" in
  0|1) ;;
  *) echo "home-path check could not run (git grep rc=$rc)" >&2; exit 1 ;;
esac
if scan grep; then
  echo "absolute home paths found" >&2
  exit 1
fi

if [ "${#RANGE[@]}" -gt 0 ]; then
  echo "== absolute home paths in pushed commits =="
  git rev-list "${RANGE[@]}" |
    git diff-tree --stdin --root -r --no-commit-id -p --cc -U0 --no-renames --no-ext-diff --no-textconv --no-color -- . "${EXCLUDES[@]}" >"$tmp"
  # Added lines only; merge commits are scanned with --cc (see guard_scan.py).
  if scan added; then
    echo "absolute home paths found in the pushed commits" >&2
    exit 1
  fi
fi

if [ "${CHIMERA_PRE_PUSH_GUARDS_ONLY:-}" = "1" ]; then
  exit 0
fi

echo "== doc line limits =="
scripts/check-doc-length.sh

echo "== validator =="
python3 scripts/validate.py

echo "== tests =="
python3 -m unittest discover -s tests
