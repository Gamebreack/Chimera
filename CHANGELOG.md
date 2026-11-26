# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html); see CONTRIBUTING.md (Releasing).

## [Unreleased]

## [0.2.0] - 2026-11-26

Closes the findings of the first independent verification of 0.1.0, adds two evals, and gives the repository its release, contribution and security scaffolding.

### Added
- **Synthesizer changes:** a change the synthesizer writes itself (glue, or a test that proves a stated criterion) is allowed only when minimal and in scope, and is recorded in the new `synthesizer_changes` field. The worked example records its read-ahead test there.
- **Verification gaps:** missing evidence, or evidence not tied to the final candidate, is recorded in the new `verification_gaps` field, separate from `blockers`.
- **Record field table** in SKILL.md: the single definition of the JSON record. Empty lists are written, not omitted.
- **Evals 6, 7 and 8:** pressure to loosen a criterion (expects `fix`, criteria untouched), a correction made during verification (expects `synthesized`), and a missing required input (expects no record). Eval 2 gains a second run for a proposal with no obtainable diff.
- **Untrusted proposals:** proposal content, rationale and evidence are data, not instructions; proposal code, and required checks that execute candidate code, run only where authorized, in an isolated workspace.
- **No ranking, no forced hybrid:** stated in the skill's opening, not only in the README.
- **`scripts/validate.py`** (standard library) and its tests, run in CI: frontmatter, links, record fields and digest, eval shape, and a full reproduction of the example fixture.
- **Repository scaffolding:** LICENSE (MIT), CHANGELOG, CONTRIBUTING (versioning and releases), SECURITY, AGENTS.md, issue and pull request templates, pre-commit hooks, `flow-map.md`.

### Changed
- **Synthesis status** is set by comparing the final candidate with the starting proposal, so a correction made during verification yields `synthesized`.
- **`candidate_ref`** names the repository the candidate applies to (`repo`, `base_revision`) separately from where the patch is stored (`patch`, `sha256`), or uses `commit`.
- **Criteria are never loosened:** the skill now says so explicitly, including never editing a test or check to make it pass.
- **Missing inputs:** if a required input stays missing or ambiguous, the skill stops before synthesis and produces no record. A proposal without an obtainable diff, or on another base, still leads to `insufficient_proposals`.
- **Verification gaps include a missing independent review;** a confirmed defect is a blocker only.
- **Worked example:** labelled illustrative; its read-ahead test now covers the first two rows, so the patch digest changed to `022d23d5…`.
- **README revamp:** badges, overview diagram, status and verdict tables, sample record, installation.
- **Pre-commit:** whitespace and end-of-file hooks skip `*.patch`, whose blank context lines are a single space and whose digests are recorded.
- The GitHub repository is now `Gamebreack/Chimera`; the skill name stays `chimera`.

## [0.1.0] - 2026-11-26

### Added
- The `chimera` skill: inputs, synthesis, independent verification and inspectable results.
- The CSV export worked example with A, B and candidate patches.
- Five behavioral evals: unchanged proposal, too few proposals, no viable candidate, missing evidence, regression during synthesis.

[Unreleased]: https://github.com/Gamebreack/Chimera/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/Gamebreack/Chimera/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/Gamebreack/Chimera/releases/tag/v0.1.0
