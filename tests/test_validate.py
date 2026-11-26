"""Tests for scripts/validate.py. Each test breaks one property in a temporary copy of the repository."""

import contextlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import validate  # noqa: E402

EXAMPLE = validate.EXAMPLE
SKILL = validate.SKILL
EVALS = validate.EVALS
PATCHES = EXAMPLE.parent / "csv-export"


def tracked_files():
    """Tracked files of the repository, or every file outside .git and docs without git."""
    try:
        out = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True,
                             check=True).stdout.decode()
        files = [Path(p) for p in out.split("\0") if p]
        if files:
            return files
    except (OSError, subprocess.CalledProcessError):
        pass
    return [p.relative_to(ROOT) for p in ROOT.rglob("*")
            if p.is_file() and not {".git", "docs", "__pycache__"} & set(p.relative_to(ROOT).parts)]


class ValidateTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        for rel in tracked_files():
            if (ROOT / rel).is_file():
                (self.root / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / rel, self.root / rel)

    def tearDown(self):
        self._tmp.cleanup()

    def edit(self, rel, old, new):
        path = self.root / rel
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text, f"fixture text not found in {rel}")
        path.write_text(text.replace(old, new, 1), encoding="utf-8")

    def errors(self, check):
        with contextlib.redirect_stdout(io.StringIO()):
            return check(self.root)

    def assertReports(self, check, fragment):
        errors = self.errors(check)
        self.assertTrue(any(fragment in e for e in errors), errors)

    def test_repository_passes(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual([], validate.validate(self.root))

    def test_main_exits_nonzero_on_failure(self):
        self.edit(SKILL, "(evals/behavioral.md)", "(evals/missing.md)")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(1, validate.main(["--root", str(self.root), "--skip-fixture"]))

    def test_main_exits_zero_on_success(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(0, validate.main(["--root", str(self.root), "--skip-fixture"]))

    def test_fixture_ignores_inherited_git_variables(self):
        outer = self.root / "outer"
        outer.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=outer, check=True)
        index = outer / ".git" / "index"
        before = index.read_bytes() if index.exists() else None
        saved = {k: os.environ.get(k) for k in ("GIT_DIR", "GIT_INDEX_FILE")}
        os.environ["GIT_DIR"] = str(outer / ".git")
        os.environ["GIT_INDEX_FILE"] = str(index)
        try:
            errors = self.errors(validate.check_fixture)
        finally:
            for key, value in saved.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
        self.assertEqual([], errors)
        self.assertEqual(before, index.read_bytes() if index.exists() else None)

    # frontmatter
    def test_missing_frontmatter(self):
        text = (self.root / SKILL).read_text(encoding="utf-8")
        (self.root / SKILL).write_text(text.replace("---\n", "", 2), encoding="utf-8")
        self.assertReports(validate.check_frontmatter, "missing YAML frontmatter")

    def test_wrong_skill_name(self):
        self.edit(SKILL, "name: chimera", "name: Chimera")
        self.assertReports(validate.check_frontmatter, "name is")

    def test_short_description(self):
        text = (self.root / SKILL).read_text(encoding="utf-8")
        start = text.index("description:")
        end = text.index("\n", start)
        (self.root / SKILL).write_text(text[:start] + "description: Synthesize." + text[end:],
                                       encoding="utf-8")
        self.assertReports(validate.check_frontmatter, "description")

    # links
    def test_broken_link(self):
        self.edit(SKILL, "(evals/behavioral.md)", "(evals/missing.md)")
        self.assertReports(validate.check_links, "broken link")

    # record
    def test_digest_mismatch(self):
        patch = self.root / PATCHES / "candidate.patch"
        patch.write_bytes(patch.read_bytes() + b"\n")
        self.assertReports(validate.check_record, "candidate_ref.sha256")

    def test_evidence_digest_mismatch(self):
        digest = validate.example_record(self.root)["candidate_ref"]["sha256"]
        self.edit(EXAMPLE, f'"candidate_sha256": "{digest}"', '"candidate_sha256": "0"')
        self.assertReports(validate.check_record, "evidence.candidate_sha256")

    def test_base_revision_mismatch(self):
        self.edit(EXAMPLE, '"base_revision": "00af', '"base_revision": "ffaf')
        self.assertReports(validate.check_record, "base_revision disagrees")

    def test_record_field_drift(self):
        self.edit(EXAMPLE, '"verification_gaps": []', '"gaps": []')
        errors = self.errors(validate.check_record)
        self.assertTrue(any("lacks fields ['verification_gaps']" in e for e in errors), errors)
        self.assertTrue(any("does not define ['gaps']" in e for e in errors), errors)

    def test_invalid_status(self):
        self.edit(EXAMPLE, '"synthesis_status": "synthesized"', '"synthesis_status": "hybrid"')
        self.assertReports(validate.check_record, "synthesis_status")

    def test_invalid_verdict(self):
        self.edit(EXAMPLE, '"independent_verdict": "pass"', '"independent_verdict": "approve"')
        self.assertReports(validate.check_record, "independent_verdict")

    def test_starting_point_not_a_proposal(self):
        self.edit(EXAMPLE, '"starting_point": "A"', '"starting_point": "C"')
        self.assertReports(validate.check_record, "starting_point")

    # evals
    def test_eval_without_verdict(self):
        self.edit(EVALS, "`unchanged` and `pass`", "`unchanged`")
        self.assertReports(validate.check_evals, "exactly one status and one verdict")

    def test_eval_with_two_statuses(self):
        self.edit(EVALS, "`unchanged` and `pass`", "`unchanged` or `synthesized` and `pass`")
        self.assertReports(validate.check_evals, "exactly one status and one verdict")

    def test_eval_without_scenario(self):
        self.edit(EVALS, "**Scenario.** A and B are independent", "A and B are independent")
        self.assertReports(validate.check_evals, "needs **Scenario.**")

    def test_no_evals(self):
        (self.root / EVALS).write_text("# Behavioral evals\n", encoding="utf-8")
        self.assertReports(validate.check_evals, "no evals found")

    def test_no_record_only_at_start(self):
        self.edit(EVALS, "**Expect.** `no_viable_candidate` and `inconclusive`.",
                  "**Expect.** Unsure, perhaps No record.")
        self.assertReports(validate.check_evals, "exactly one status and one verdict")

    def test_no_record_eval_naming_a_verdict(self):
        self.edit(EVALS, "No record: no synthesis status", "No record: `inconclusive`, no synthesis status")
        self.assertReports(validate.check_evals, "expects no record")

    # fixture
    def test_base_mismatch(self):
        self.edit(EXAMPLE, "import csv\nimport io\n", "import csv\nimport io  \n")
        self.assertReports(validate.check_fixture, "fixture: base is")

    def test_candidate_tests_failing(self):
        self.edit(PATCHES / "candidate.patch", '"first\\r\\n", next(chunks)', '"first\\n", next(chunks)')
        self.assertReports(validate.check_fixture, "unittest failed")

    def test_candidate_whitespace_error(self):
        self.edit(PATCHES / "candidate.patch", "+        consumed = []\n", "+        consumed = [] \n")
        self.assertReports(validate.check_fixture, "git diff failed")

    def test_candidate_export_differs_from_a(self):
        self.edit(PATCHES / "candidate.patch", "+    for row in rows:", "+    for row in list(rows):")
        self.assertReports(validate.check_fixture, "differs from A")

    def test_candidate_tests_do_not_catch_b(self):
        shutil.copy2(self.root / PATCHES / "A.patch", self.root / PATCHES / "B.patch")
        self.assertReports(validate.check_fixture, "should catch it")


if __name__ == "__main__":
    unittest.main()
