---
name: chimera
description: Synthesize independent implementation proposals for the same authorized software change into one candidate patch. Use when asked to compare actual diffs, preserve a sound proposal or adopt specific improvements, and hand the final candidate off for independent verification.
---

# Chimera

Produce one coherent candidate for the approved change. Preserve a sound proposal verbatim if the other proposals offer no improvement.

## 1. Establish the inputs

- Obtain the approved brief, repository identities and exact base revisions, scope limits, acceptance criteria, and required checks or other evidence. Resolve missing approvals, ambiguous bases, or conflicting criteria before proceeding. Keep these constraints fixed throughout the run.
- Accept independently supplied proposals. Require an ID and an inspectable diff or commit for each proposal, and collect any available check results, rationale, and known risks. Confirm that each proposal addresses the same brief and criteria and is based on the specified revision of every repository it touches. Establish independence from the handoff and report any uncertainty that prevents confirming it.
- If needed, ask the available harness for two independent attempts. Give each author identical inputs and a separate workspace at the specified base revisions. Withhold competing work, including drafts, diffs, and results, until both handoffs. Use only isolation and delegation capabilities that are available and authorized.
- If fewer than two independent, comparable proposals are available, return `insufficient_proposals` with the reason and a null candidate reference. A poor implementation can still be comparable. An unavailable diff or mismatched base can prevent comparison.

## 2. Synthesize

- Read the actual diffs against the specified bases. Compare behavior, scope, interactions, and evidence against the brief. Treat proposal check results as evidence about those proposals.
- Choose a coherent starting point. Inspect interactions before adapting an idea, and adopt it only if it improves the candidate within scope. Record the source proposal ID, the adopted idea, and why it helps. Explain material omissions, including ideas that conflict with the design, scope, or criteria.
- Return `unchanged` if the candidate is the starting proposal's exact patch and `synthesized` if you changed that patch during synthesis. If no proposal is a suitable starting point for a coherent in-scope candidate, return `no_viable_candidate` with reasons and a null candidate reference.
- Freeze the result as an exact, inspectable patch or commit. For multiple repositories, identify the complete set of exact patch or commit references and their repository and base revision mappings.

## 3. Hand off for verification

- Give a reviewer who did not author or synthesize the candidate the approved brief, scope, acceptance criteria, bases, required checks, and exact frozen candidate. Ask for blockers with supporting evidence. Keep the synthesis rationale out of the initial handoff so the reviewer can form an independent judgment.
- Run the required checks on that exact candidate. Record each check's result and evidence reference, tied to the candidate identity. Record review evidence the same way. If the candidate changes, freeze the new revision, rerun required checks, and obtain independent review of the new candidate. Keep the approved criteria intact.
- Apply these verdict rules in order:
  1. `fix` when evidence confirms an unresolved defect in the final candidate. A confirmed defect takes precedence over missing evidence.
  2. `inconclusive` when there is no candidate, completed independent review is unavailable, or any required evidence is missing or cannot be tied to the final candidate. Use it if a check failure or potential review blocker remains unconfirmed.
  3. `pass` only when every required check passes on the exact final candidate, all other required evidence is present, and independent review finds no blocker.
- Treat the verdict as a verification result. Leave the candidate for review within the authorization granted for the task.

## 4. Return inspectable results

Return the exact candidate reference and a short synthesis report. Identify the bases, proposal IDs, starting point, adopted ideas with reasons, material omissions, verification evidence, and blockers or verification gaps. Include a JSON record alongside the report. Keep `synthesis_status` and `independent_verdict` as separate fields. Set `candidate_ref` and `starting_point` to null when no candidate exists.

See [the CSV export example](examples/csv-export.md) for a report and JSON record. See [behavioral evals](evals/behavioral.md) for expected outcomes at the decision boundaries.
