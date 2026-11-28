# Chimera — repo rules

This repo holds the `chimera` Agent Skill (synthesis of independent implementation proposals into one verified candidate) and a standard-library validator for it.

## Hard rules

- No commits, pushes, tags, releases or remote changes without explicit operator authorization. Workers never commit or push. Before committing, run the pre-commit hooks; never use `--no-verify`.
- Feature branches merge into `lesk`; only `lesk` is pushed and PRed to `main`.
- The skill under `skills/chimera/` stays host-agnostic: no host, harness, agent-type, model or provider names, and no runner or adapter.
- The skill name stays lowercase `chimera` (Agent Skills naming). The project and repository are called Chimera.
- One home per fact: the record fields live in the SKILL.md table, the release procedure in CONTRIBUTING.md. Link instead of copying.
- Reference docs stay under 200 lines (`scripts/check-doc-length.sh`).
- Secrets, credentials, personal endpoints and machine-specific paths never enter the repo.
- When the example patch changes, recompute its SHA-256 in the example record; the validator enforces it.

## Required checks

These must pass before merge and before release:

```bash
python3 scripts/validate.py
python3 -m unittest discover -s tests
```

## Planning

If a git-ignored `CONTEXT.md` exists at the root, read it first; local planning files are never committed. Releases: see [CONTRIBUTING.md](CONTRIBUTING.md).
