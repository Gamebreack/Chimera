#!/usr/bin/env python3
"""Validate the Chimera skill repository. Standard library only.

Checks:
  frontmatter  SKILL.md has `name: chimera` (matching its directory) and a description.
  links        every relative Markdown link in tracked files resolves.
  record       the worked example's JSON record has exactly the fields SKILL.md defines,
               valid status and verdict values, and a candidate digest that matches the patch.
  evals        every eval states a scenario and an expectation with one status and one verdict.
  fixture      the example fixture reproduces: base revision, patches apply, required checks
               pass on the candidate, the candidate keeps A's export.py, and its tests fail on B.

Usage: python3 scripts/validate.py [--root PATH] [--skip-fixture]
Exit status is 0 when every check passes, 1 otherwise.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL_DIR = Path("skills/chimera")
SKILL = SKILL_DIR / "SKILL.md"
EXAMPLE = SKILL_DIR / "examples/csv-export.md"
EVALS = SKILL_DIR / "evals/behavioral.md"
STATUSES = {"synthesized", "unchanged", "insufficient_proposals", "no_viable_candidate"}
VERDICTS = {"pass", "fix", "inconclusive"}
FIXTURE_DATE = "2026-01-01T00:00:00Z"

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
FIELD_ROW_RE = re.compile(r"^\| `([a-z_0-9]+)` \|", re.MULTILINE)
CODE_BLOCK_RE = re.compile(r"`([^`\n]+)`\n\n```(\w+)\n(.*?)```", re.DOTALL)


def read(root: Path, rel: Path) -> str:
    return (root / rel).read_text(encoding="utf-8")


def tracked_markdown(root: Path) -> list[Path]:
    """Tracked .md files, or every .md file outside hidden and planning dirs without git."""
    try:
        out = subprocess.run(
            ["git", "ls-files", "-z", "*.md"], cwd=root, capture_output=True, check=True
        ).stdout.decode()
        files = [Path(p) for p in out.split("\0") if p]
        if files:
            return files
    except (OSError, subprocess.CalledProcessError):
        pass
    skip = {".git", "docs"}
    return [
        p.relative_to(root)
        for p in root.rglob("*.md")
        if not any(part in skip or part.startswith(".") for part in p.relative_to(root).parts[:-1])
    ]


def check_frontmatter(root: Path) -> list[str]:
    text = read(root, SKILL)
    match = re.match(r"---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        return [f"{SKILL}: missing YAML frontmatter"]
    fields = dict(
        line.split(":", 1) for line in match.group(1).splitlines() if ":" in line
    )
    errors = []
    name = fields.get("name", "").strip()
    if name != SKILL_DIR.name:
        errors.append(f"{SKILL}: name is {name!r}, expected {SKILL_DIR.name!r}")
    if len(fields.get("description", "").strip()) < 40:
        errors.append(f"{SKILL}: description is missing or too short")
    return errors


def check_links(root: Path) -> list[str]:
    errors = []
    for rel in tracked_markdown(root):
        path = root / rel
        if not path.is_file():
            continue
        for target in LINK_RE.findall(path.read_text(encoding="utf-8")):
            if re.match(r"^[a-z]+:", target) or target.startswith("#"):
                continue
            file_part = target.split("#", 1)[0]
            if not (path.parent / file_part).exists():
                errors.append(f"{rel}: broken link {target}")
    return errors


def example_record(root: Path) -> dict:
    text = read(root, EXAMPLE)
    match = re.search(r"```json\n(.*?)```", text, re.DOTALL)
    if not match:
        raise ValueError(f"{EXAMPLE}: no JSON record")
    return json.loads(match.group(1))


def skill_fields(root: Path) -> list[str]:
    return FIELD_ROW_RE.findall(read(root, SKILL))


def check_record(root: Path) -> list[str]:
    try:
        record = example_record(root)
    except (ValueError, json.JSONDecodeError) as exc:
        return [str(exc)]
    errors = []
    fields = skill_fields(root)
    if not fields:
        return [f"{SKILL}: no record field table found"]
    missing = sorted(set(fields) - set(record))
    extra = sorted(set(record) - set(fields))
    if missing:
        errors.append(f"{EXAMPLE}: record lacks fields {missing}")
    if extra:
        errors.append(f"{EXAMPLE}: record has fields SKILL.md does not define {extra}")
    if record.get("synthesis_status") not in STATUSES:
        errors.append(f"{EXAMPLE}: invalid synthesis_status {record.get('synthesis_status')!r}")
    if record.get("independent_verdict") not in VERDICTS:
        errors.append(f"{EXAMPLE}: invalid independent_verdict {record.get('independent_verdict')!r}")
    ref = record.get("candidate_ref")
    if not isinstance(ref, dict):
        return errors + [f"{EXAMPLE}: candidate_ref must be an object in the worked example"]
    if ref.get("repo") not in record.get("base_revisions", {}):
        errors.append(f"{EXAMPLE}: candidate_ref.repo is not in base_revisions")
    elif ref.get("base_revision") != record["base_revisions"][ref["repo"]]:
        errors.append(f"{EXAMPLE}: candidate_ref.base_revision disagrees with base_revisions")
    patch = (root / EXAMPLE).parent / str(ref.get("patch"))
    if not patch.is_file():
        return errors + [f"{EXAMPLE}: candidate patch {ref.get('patch')} not found"]
    digest = hashlib.sha256(patch.read_bytes()).hexdigest()
    if ref.get("sha256") != digest:
        errors.append(f"{EXAMPLE}: candidate_ref.sha256 does not match {ref['patch']} ({digest})")
    if record.get("evidence", {}).get("candidate_sha256") != digest:
        errors.append(f"{EXAMPLE}: evidence.candidate_sha256 does not match the patch")
    if record.get("starting_point") not in record.get("proposal_ids", []):
        errors.append(f"{EXAMPLE}: starting_point is not a proposal id")
    return errors


def check_evals(root: Path) -> list[str]:
    text = read(root, EVALS)
    sections = re.split(r"^## ", text, flags=re.MULTILINE)[1:]
    if not sections:
        return [f"{EVALS}: no evals found"]
    errors = []
    for section in sections:
        title = section.splitlines()[0]
        expect = section.split("**Expect.**", 1)
        if "**Scenario.**" not in section or len(expect) != 2:
            errors.append(f"{EVALS}: '{title}' needs **Scenario.** and **Expect.**")
            continue
        words = set(re.findall(r"`([a-z_]+)`", expect[1]))
        if len(words & STATUSES) != 1 or len(words & VERDICTS) != 1:
            errors.append(f"{EVALS}: '{title}' must expect exactly one status and one verdict")
    return errors


def git_env() -> dict:
    # Drop inherited GIT_* variables: inside a git hook, GIT_DIR and GIT_INDEX_FILE
    # would point the fixture's git commands at the enclosing repository.
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(
        GIT_CONFIG_NOSYSTEM="1",
        GIT_CONFIG_GLOBAL=os.devnull,
        GIT_AUTHOR_DATE=FIXTURE_DATE,
        GIT_COMMITTER_DATE=FIXTURE_DATE,
        PYTHONDONTWRITEBYTECODE="1",
    )
    return env


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, env=git_env(), capture_output=True, text=True)


def build_base(root: Path, work: Path) -> tuple[Path | None, list[str]]:
    """Write the fixture files from the example and commit them as the base."""
    text = read(root, EXAMPLE)
    files = {name: body for name, lang, body in CODE_BLOCK_RE.findall(text) if lang == "python"}
    if set(files) != {"export.py", "test_export.py"}:
        return None, [f"{EXAMPLE}: expected export.py and test_export.py fixture blocks"]
    work.mkdir()
    for name, body in files.items():
        (work / name).write_text(body, encoding="utf-8", newline="\n")
    steps = [
        ["git", "init", "-q", "--object-format=sha1"],
        ["git", "-c", "core.autocrlf=false", "add", "--chmod=-x", "export.py", "test_export.py"],
        ["git", "-c", "user.name=Chimera Example", "-c", "user.email=chimera@example.invalid",
         "-c", "commit.gpgsign=false", "commit", "-q", "-m", "CSV fixture base"],
    ]
    for step in steps:
        result = run(step, work)
        if result.returncode:
            return None, [f"fixture: {' '.join(step)} failed: {result.stderr.strip()}"]
    return work, []


def check_fixture(root: Path) -> list[str]:
    record = example_record(root)
    expected_base = record["base_revisions"][record["candidate_ref"]["repo"]]
    patches = (root / EXAMPLE).parent / "csv-export"
    errors: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        trees = {}
        for name in ("A", "B", "candidate"):
            work, errs = build_base(root, tmp_path / name)
            if errs:
                return errs
            head = run(["git", "rev-parse", "HEAD"], work).stdout.strip()
            if head != expected_base:
                return [f"fixture: base is {head}, record says {expected_base}"]
            patch = patches / f"{name}.patch"
            for cmd in (["git", "apply", "--check", str(patch)], ["git", "apply", str(patch)],
                        ["git", "diff", "--check"]):
                result = run(cmd, work)
                if result.returncode:
                    errors.append(f"fixture {name}: {' '.join(cmd[:2])} failed: "
                                  f"{(result.stdout + result.stderr).strip()}")
            trees[name] = work
        if errors:
            return errors
        tests = run([sys.executable, "-m", "unittest", "-v"], trees["candidate"])
        if tests.returncode:
            errors.append(f"fixture candidate: unittest failed:\n{tests.stderr.strip()}")
        if (trees["candidate"] / "export.py").read_bytes() != (trees["A"] / "export.py").read_bytes():
            errors.append("fixture: candidate export.py differs from A's")
        (trees["B"] / "test_export.py").write_bytes((trees["candidate"] / "test_export.py").read_bytes())
        if run([sys.executable, "-m", "unittest"], trees["B"]).returncode == 0:
            errors.append("fixture: candidate tests pass on B's export.py; they should catch it")
    return errors


CHECKS = [
    ("frontmatter", check_frontmatter),
    ("links", check_links),
    ("record", check_record),
    ("evals", check_evals),
    ("fixture", check_fixture),
]


def validate(root: Path, skip_fixture: bool = False) -> list[str]:
    errors = []
    for name, check in CHECKS:
        if skip_fixture and name == "fixture":
            continue
        try:
            found = check(root)
        except (OSError, KeyError, ValueError, TypeError) as exc:
            found = [f"{name}: {type(exc).__name__}: {exc}"]
        errors.extend(found)
        print(f"{'FAIL' if found else 'ok  '} {name}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--skip-fixture", action="store_true")
    args = parser.parse_args(argv)
    errors = validate(args.root.resolve(), args.skip_fixture)
    for error in errors:
        print(f"  - {error}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
