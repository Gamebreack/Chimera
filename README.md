# Chimera

Chimera is a standalone Agent Skill that compares independent proposals for an approved software change and produces one candidate patch. It can preserve the starting proposal exactly when the alternatives offer no improvement.

## Usage

1. Load [the skill](skills/chimera/SKILL.md) in a harness that supports Agent Skills, or give its instructions to an agent directly.
2. Supply the approved brief, exact base revision for each repository, scope limits, acceptance criteria, and required checks. Provide two or more independent proposal diffs or immutable commit references if you have them. Include proposal IDs and any evidence available.
3. Give the agent access to inspect the proposals and prepare the candidate. Arrange independent review of the final candidate and provide any check results collected outside the harness.

A sample request:

> Use Chimera to synthesize proposals A and B against the repository revisions in the approved brief. Use the supplied diffs and check logs, stay within the brief's scope, and return the final patch, synthesis report, and verification verdict.

## Limitations

Chimera relies on the available harness, tools, or people for workspace isolation, proposal generation, test execution, and independent review. Independently prepared handoffs work with a single agent handling synthesis. Coverage and verdicts depend on the evidence available for the exact final candidate. A `pass` is a technical verification result. Release decisions stay with the authorized owner.

- [Worked CSV export example](skills/chimera/examples/csv-export.md)
- [Behavioral evals and grading expectations](skills/chimera/evals/behavioral.md)
