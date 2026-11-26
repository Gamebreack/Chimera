"""Tests for scripts/validate.py. Each test mutates a temporary copy of the repository."""

import contextlib
import io
import shutil
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


class ValidateTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        shutil.copytree(ROOT / "skills", self.root / "skills")
        shutil.copy(ROOT / "README.md", self.root / "README.md")

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

    def test_repository_passes(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual([], validate.validate(self.root))

    def test_wrong_skill_name(self):
        self.edit(SKILL, "name: chimera", "name: Chimera")
        self.assertTrue(any("name is" in e for e in self.errors(validate.check_frontmatter)))

    def test_broken_link(self):
        self.edit(SKILL, "(evals/behavioral.md)", "(evals/missing.md)")
        self.assertTrue(any("broken link" in e for e in self.errors(validate.check_links)))

    def test_digest_mismatch(self):
        patch = self.root / EXAMPLE.parent / "csv-export/candidate.patch"
        patch.write_bytes(patch.read_bytes() + b"\n")
        self.assertTrue(any("sha256" in e for e in self.errors(validate.check_record)))

    def test_record_missing_field(self):
        self.edit(EXAMPLE, '"verification_gaps": []', '"gaps": []')
        errors = self.errors(validate.check_record)
        self.assertTrue(any("lacks fields ['verification_gaps']" in e for e in errors))
        self.assertTrue(any("does not define ['gaps']" in e for e in errors))

    def test_invalid_status(self):
        self.edit(EXAMPLE, '"synthesis_status": "synthesized"', '"synthesis_status": "hybrid"')
        self.assertTrue(any("synthesis_status" in e for e in self.errors(validate.check_record)))

    def test_eval_without_verdict(self):
        self.edit(EVALS, "`unchanged` and `pass`", "`unchanged`")
        self.assertTrue(any("one verdict" in e for e in self.errors(validate.check_evals)))

    def test_candidate_tests_failing(self):
        self.edit(EXAMPLE.parent / "csv-export/candidate.patch",
                  '"first\\r\\n", next(chunks)', '"first\\n", next(chunks)')
        self.edit(EXAMPLE, validate.example_record(self.root)["candidate_ref"]["sha256"], "x")
        errors = self.errors(validate.check_fixture)
        self.assertTrue(any("unittest failed" in e for e in errors), errors)

    def test_candidate_export_differs_from_a(self):
        self.edit(EXAMPLE.parent / "csv-export/candidate.patch",
                  "+    for row in rows:", "+    for row in list(rows):")
        errors = self.errors(validate.check_fixture)
        self.assertTrue(any("differs from A" in e for e in errors), errors)


if __name__ == "__main__":
    unittest.main()
