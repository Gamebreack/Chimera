# Security policy

## Supported versions

| Version | Supported |
|---|---|
| 0.2.x | yes |
| < 0.2 | no |

Only the latest minor release receives fixes.

## Reporting a vulnerability

Report privately through GitHub: **Security → Report a vulnerability** on [Gamebreack/Chimera](https://github.com/Gamebreack/Chimera/security/advisories/new). Do not open a public issue for a security problem.

Include the skill version, the host you ran it in, the inputs that trigger the problem (with secrets and private paths redacted), and what happened. You will get an acknowledgement within 7 days. Fixes ship as a patch release, credited in the changelog unless you ask otherwise.

## What counts

Chimera is instructions, not code: it runs only through the agent and harness that load it. A security issue here is wording that leads a compliant agent to an unsafe action, for example:

- **Instruction injection through proposals:** text inside a proposal diff, rationale or check log that the skill causes the agent to obey. Proposal content is data (SKILL.md, section 1).
- **Unisolated execution:** guidance that runs proposal code outside an isolated, authorized workspace.
- **False assurance:** a path through the verdict rules that yields `pass` without every required check on the final candidate and an independent review.
- **Scope escape:** guidance that lets synthesis broaden the approved scope, push, deploy or approve a release.

`scripts/validate.py` runs `git ls-files` read-only in the repository, then rebuilds the example fixture in a temporary directory and runs `git` and Python's `unittest` there. The Python it runs comes from the example page and its patches, so a change to `skills/chimera/examples/` is a change to code that runs in CI and in the pre-commit hook: review it as code.

## Out of scope

Vulnerabilities in a host, harness or model, and secrets that users paste into their own proposals. Report those to the relevant vendor.
