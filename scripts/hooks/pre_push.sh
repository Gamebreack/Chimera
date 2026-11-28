#!/usr/bin/env bash
# Pre-push checks: the same gates CI runs, plus whole-repo guards that the commit
# hooks (staged files only) cannot see. Does not call pre-commit (avoids recursion).
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "== tracked env files =="
if git ls-files | grep -E '(^|/)\.env(\..*)?$'; then
  echo ".env files must not be tracked" >&2
  exit 1
fi

echo "== absolute home paths =="
# Same regex and exclusions as the no-absolute-home-path hook in .pre-commit-config.yaml.
set +e
git grep -n -I -P '(?<![A-Za-z0-9._~-])(/home/|/Users/)[A-Za-z0-9._-]+' -- . ':!.pre-commit-config.yaml' ':!scripts/hooks/pre_push.sh'
rc=$?
set -e
case "$rc" in
  0) echo "absolute home paths found" >&2; exit 1 ;;
  1) ;;
  *) echo "home-path check could not run (git grep -P unavailable?)" >&2; exit 1 ;;
esac

echo "== doc line limits =="
scripts/check-doc-length.sh

echo "== validator =="
python3 scripts/validate.py

echo "== tests =="
python3 -m unittest discover -s tests
