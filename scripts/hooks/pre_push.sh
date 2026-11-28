#!/usr/bin/env bash
# Pre-push checks: the same gates CI runs, plus whole-repo guards that the commit
# hooks (staged files only) cannot see. Does not call pre-commit (avoids recursion).
#
# Guards run on the current checkout and, when pre-commit exports the pushed range
# (PRE_COMMIT_FROM_REF and PRE_COMMIT_TO_REF, pre-commit 4.x, pre-push stage), also on
# the commits being pushed: .env paths, a root CONTEXT.md and added home-path lines anywhere in that range.
# A new branch has no usable from-ref, so the range is the commits not reachable from
# any remote-tracking ref. Without the variables (manual run) only the checkout is checked.
# Paths are NUL-separated throughout, so quoted (core.quotePath) names match too.
#
# CHIMERA_PRE_PUSH_GUARDS_ONLY=1 stops after the guards (the hook tests use it so they
# do not recurse into the real suite). Unset, the full run happens.
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

# .env files anywhere, and a root CONTEXT.md (local planning entry point, never committed).
ENV_RE='(^|/)\.env(\..*)?$|^CONTEXT\.md$'
# Same regex and exclusions as the no-absolute-home-path hook in .pre-commit-config.yaml.
HOME_RE='(?<![A-Za-z0-9._~-])(/home/|/Users/)[A-Za-z0-9._-]+'
EXCLUDES=(':!.pre-commit-config.yaml' ':!scripts/hooks/pre_push.sh')

tmp=$(mktemp)
trap 'rm -f "$tmp"' EXIT

# Runs grep with the given args on "$tmp"; prints matches (NULs shown as newlines).
# Returns 0 on match, 1 on no match, exits on any other grep error (fail closed).
scan() {
  local rc=0 out
  out=$(grep "$@" "$tmp" | tr '\0' '\n'; exit "${PIPESTATUS[0]}") || rc=$?
  case "$rc" in
    0) printf '%s\n' "$out"; return 0 ;;
    1) return 1 ;;
    *) echo "scan failed (grep rc=$rc)" >&2; exit 1 ;;
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
if scan -zE "$ENV_RE"; then
  echo ".env files and a root CONTEXT.md must not be tracked" >&2
  exit 1
fi

if [ "${#RANGE[@]}" -gt 0 ]; then
  echo "== .env files and root CONTEXT.md in pushed commits =="
  git log -z --format= --name-only --no-renames --diff-filter=ACMR "${RANGE[@]}" >"$tmp"
  if scan -zE "$ENV_RE"; then
    echo ".env files and a root CONTEXT.md must not be pushed (present in the pushed commits)" >&2
    exit 1
  fi
fi

echo "== absolute home paths =="
set +e
git grep -n -I -P "$HOME_RE" -- . "${EXCLUDES[@]}"
rc=$?
set -e
case "$rc" in
  0) echo "absolute home paths found" >&2; exit 1 ;;
  1) ;;
  *) echo "home-path check could not run (git grep -P unavailable?)" >&2; exit 1 ;;
esac

if [ "${#RANGE[@]}" -gt 0 ]; then
  echo "== absolute home paths in pushed commits =="
  git log --format= -p -U0 --no-color --no-ext-diff --no-renames "${RANGE[@]}" -- . "${EXCLUDES[@]}" >"$tmp"
  # Added lines only; '+++ b/path' diff headers are not content.
  if scan -nP "^\\+(?!\\+\\+ (b/|/dev/null)).*?${HOME_RE}"; then
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
