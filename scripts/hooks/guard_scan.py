#!/usr/bin/env python3
"""Matching helper for scripts/hooks/pre_push.sh (standard library only).

All regex and NUL handling lives here so the hook needs only git and Python 3:
no PCRE and no GNU-only grep. Input is read from stdin as bytes.
Inputs come from plumbing (`git ls-files -z`, `git grep -z`, `git rev-list | git diff-tree`),
never porcelain `git log`: its output depends on user config (for example log.showSignature
prints signature text into the stream), which would corrupt parsing.

Modes (exit 0 = hit, printed to stdout; 1 = no hit; 2 = usage error or any crash, fail closed):
  paths  NUL-separated paths (`git ls-files -z`, or `git diff-tree --name-only -z`): print the
         forbidden ones (a .env file anywhere, or a root CONTEXT.md).
  grep   `git grep -n -I -z -E <candidate regex>` output (path NUL line NUL text LF):
         print hits where the home-path lookbehind also holds.
  added  `git diff-tree -p --cc` patch text: print added lines that hold a home path.
         In a combined (merge) diff a line counts as added only when it is added
         against every parent (all '+' columns), i.e. introduced by the merge itself.
"""
import re
import sys

# Same rule as the no-absolute-home-path hook in .pre-commit-config.yaml.
HOME = re.compile(rb"(?<![A-Za-z0-9._~-])(/home/|/Users/)[A-Za-z0-9._-]+")
FORBIDDEN = re.compile(rb"(^|/)\.env(\..*)?$|^CONTEXT\.md$", re.DOTALL)


def forbidden_paths(data):
    return [p for p in data.split(b"\0") if p and FORBIDDEN.search(p)]


def grep_hits(data):
    hits = []
    for m in re.finditer(rb"([^\0]*)\0(\d+)\0([^\n]*)\n", data):
        if HOME.search(m.group(3)):
            hits.append(b":".join(m.groups()))
    return hits


def added_hits(data):
    hits, cols = [], 0
    for line in data.split(b"\n"):
        if line.startswith(b"diff "):
            cols = 0
        m = re.match(rb"(@@+) ", line)
        if m:
            cols = len(m.group(1)) - 1  # one column per parent
            continue
        if cols and len(line) >= cols and line[:cols] == b"+" * cols:
            if HOME.search(line[cols:]):
                hits.append(line)
    return hits


def main(argv):
    modes = {"paths": forbidden_paths, "grep": grep_hits, "added": added_hits}
    if len(argv) != 2 or argv[1] not in modes:
        sys.stderr.write("usage: guard_scan.py paths|grep|added < input\n")
        return 2
    try:
        hits = modes[argv[1]](sys.stdin.buffer.read())
        for h in hits:
            sys.stdout.buffer.write(h + b"\n")
        sys.stdout.buffer.flush()
    except BaseException as exc:  # an uncaught exception would exit 1 = "no hit"
        sys.stderr.write("guard_scan.py: %s: %s\n" % (type(exc).__name__, exc))
        return 2
    return 0 if hits else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
