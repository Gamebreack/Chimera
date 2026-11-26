# Worked example · CSV export

## Approved brief

Stream CSV records from a finite or lazy row iterable in order. Yield one complete record per chunk without reading the next row before yielding the current record. Preserve the standard library's default CSV dialect, including commas, quotes, embedded newlines, and CRLF terminators. Empty input yields zero chunks. Scope is `export.py` and `test_export.py`, with standard-library dependencies only. Required checks are `git diff --check` and `python -m unittest -v`.

The fixture repository `csv-fixture` has exact base `00af1155d107255636168b658d0fad6520cf5f3a`. A and B are illustrative handoffs representing two blind attempts from that base.

## Synthesis report

This example is illustrative. The fixture, the three patches, and both required checks reproduce with the script at the end; the independent review is described, not recorded.

[A's patch](csv-export/A.patch) uses a CSV writer that returns each encoded record directly. [B's patch](csv-export/B.patch) buffers the whole export, then splits on line breaks. B adds tests for empty input and fields containing commas, quotes, and newlines.

Start with A. Adapt B's tests to assert chunk boundaries as well as CSV output. Empty input must yield zero chunks, and a quoted field containing a newline must stay in a single chunk. Neither proposal tests the brief's no-read-ahead rule, so the synthesizer adds one test that fails if the exporter consumes the next row before yielding the current record; it is recorded as a synthesizer change. Omit B's buffering because it reads ahead and can split a quoted record across chunks. The candidate's `export.py` is A's, byte for byte.

The [final patch](csv-export/candidate.patch) applies to the `csv-fixture` base and is identified by its SHA-256 digest in the record below. The four tests and the whitespace check passed on that patch. An independent reviewer applied the same patch to the exact base, repeated both checks, and found no blockers. The reviewer also confirmed default CSV formatting on additional inputs and one-row-at-a-time consumption from an infinite iterable. No required evidence is missing, so the record has no verification gaps.

## Result

```json
{
  "base_revisions": {
    "csv-fixture": "00af1155d107255636168b658d0fad6520cf5f3a"
  },
  "proposal_ids": ["A", "B"],
  "starting_point": "A",
  "synthesis_status": "synthesized",
  "candidate_ref": {
    "repo": "csv-fixture",
    "base_revision": "00af1155d107255636168b658d0fad6520cf5f3a",
    "patch": "csv-export/candidate.patch",
    "sha256": "022d23d56268f752f494e5acce96f9a784b4d89359171f2248e83a9274937767"
  },
  "adopted_ideas": [
    {
      "proposal_id": "B",
      "idea": "Adapt empty-input and special-character tests",
      "reason": "Check zero chunks for empty input and one complete CSV record for a quoted field containing a newline."
    }
  ],
  "synthesizer_changes": [
    {
      "change": "Add test_reads_one_row_per_chunk",
      "reason": "The brief forbids reading the next row before yielding the current record, and neither proposal tests it."
    }
  ],
  "material_omissions": [
    {
      "proposal_id": "B",
      "idea": "Buffer and split the export",
      "reason": "Reads later rows before yielding and splits quoted multiline fields across chunks."
    }
  ],
  "independent_verdict": "pass",
  "evidence": {
    "candidate_sha256": "022d23d56268f752f494e5acce96f9a784b4d89359171f2248e83a9274937767",
    "checks": [
      {"check": "git diff --check", "result": "pass", "detail": "Exit 0"},
      {"check": "python -m unittest -v", "result": "pass", "detail": "4 tests passed"}
    ],
    "independent_review": {"result": "no_blockers", "detail": "Reviewed the exact patch against the brief, reran both checks, and checked additional CSV inputs and lazy iteration."}
  },
  "blockers": [],
  "verification_gaps": []
}
```

## Reproduce the fixture

In a fresh directory, save these two files using LF line endings and a final newline.

`export.py`

```python
import csv
import io


def csv_chunks(rows):
    output = io.StringIO(newline="")
    csv.writer(output).writerows(rows)
    yield output.getvalue()
```

`test_export.py`

```python
import unittest

from export import csv_chunks


class ExportTests(unittest.TestCase):
    def test_simple_rows(self):
        self.assertEqual("a,1\r\nb,2\r\n", "".join(csv_chunks([["a", 1], ["b", 2]])))
```

Create the base commit and verify its revision. Set `patch_path` to the absolute path of the linked final patch before applying it.

```sh
set -e
git init --object-format=sha1
git -c core.autocrlf=false add --chmod=-x export.py test_export.py
GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null \
GIT_AUTHOR_DATE=2026-01-01T00:00:00Z GIT_COMMITTER_DATE=2026-01-01T00:00:00Z \
  git -c user.name='Chimera Example' -c user.email=chimera@example.invalid \
  -c commit.gpgsign=false commit -m 'CSV fixture base'
test "$(git rev-parse HEAD)" = 00af1155d107255636168b658d0fad6520cf5f3a
git apply --check "$patch_path"
git apply "$patch_path"
git diff --check
python -m unittest -v
```
