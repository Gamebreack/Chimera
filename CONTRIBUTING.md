# Contributing

## How to propose a change

1. For anything beyond a small fix, open an issue first and describe the problem.
2. Then open a pull request against `main`. Every change lands through a pull request.

## Branches

Work happens on feature branches, which stay local. They merge into `lesk`; only `lesk` is pushed and opened as a pull request against `main`. Branch protection is not available for this repository, so the model relies on discipline.

## Rules a change must keep

Every change keeps the rules in [AGENTS.md](AGENTS.md). They are not repeated here.

## Testing a change

Both checks must pass before merge; CI runs them on every push and pull request:

```bash
python3 scripts/validate.py
python3 -m unittest discover -s tests
```

`validate.py` rebuilds the worked example's fixture in a temporary directory, so it needs `git` and Python 3.9 or later. If you change a patch in the example, update its SHA-256 in the example record.

If a change alters skill behavior (statuses, verdict rules, record fields), update the evals and run the affected ones on at least one host. Note the host and the outcome in the pull request.

## Git hooks

This repo uses [pre-commit](https://pre-commit.com), which must be installed; then run `pre-commit install` once per clone; it installs both the commit and the push hooks. The commit hooks scan for secrets, reject `.env` files and a root `CONTEXT.md` (local planning stays local), fix whitespace and YAML hygiene, enforce the line limits, reject absolute home paths, and run the validator. The push hook (`scripts/hooks/pre_push.sh`) rejects tracked `.env` files, a root `CONTEXT.md` and absolute home paths across all tracked files and in the commits of the pushed branch (pre-commit passes one range per push), then re-runs the line limits, the validator and the tests. Run the commit hooks on everything with `pre-commit run --all-files`, and never bypass them with `--no-verify`.

## Versioning

Versions follow SemVer, applied to the skill's behavior:

- **Patch:** wording and fixes that do not change statuses, verdicts or the record.
- **Minor:** new or changed behavior, rules, record fields or evals.
- **Major:** a breaking change to the statuses, verdicts or record format.

## Releasing

1. In a pull request, move the `[Unreleased]` entries in `CHANGELOG.md` under `## [X.Y.Z] - YYYY-MM-DD` and update the compare links.
2. Run pre-release verification on that pull request while it is up to date with `main`: a fresh verifier run plus an independent review panel (for example the `verify` skill). Merge only with no open BLOCKER or SHOULD-FIX finding. If anything else lands on the pull request or on `main` afterwards, run it again.
3. Only with the operator's approval, which covers this step and the next: after the pull request merges, create the annotated tag `vX.Y.Z` on the merge commit and push it.
4. Create the GitHub release with that version's changelog section as its notes: `gh release create vX.Y.Z --verify-tag --title "vX.Y.Z — <summary>" --notes-file <section>`. `--verify-tag` stops the release if the tag from step 3 is not on the remote.
