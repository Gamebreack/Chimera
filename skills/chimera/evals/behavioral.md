# Behavioral evals

Give the agent the skill and one scenario at a time. Supply the scenario without the expectations. Use the stated facts as evidence from the fixture and grade the report and JSON together. Each scenario has an approved brief and exact bases unless the scenario says otherwise. Grade a case as successful only if it meets all its expectations.

## 1. Preserve an unchanged candidate

**Scenario.** A and B are independent, comparable proposals. A fully meets the brief. B adds a redundant wrapper and repeats tests A already includes. The independent reviewer reviewed the exact A patch as the final candidate and found no blocker. All required checks passed on that exact patch.

**Expect.** `unchanged` and `pass`. The candidate is exactly A, the starting point is A, and adopted ideas, synthesizer changes, blockers, and verification gaps are empty lists. The report explains why B's additions were omitted.

## 2. Too few comparable proposals

**Scenario.** A has an inspectable diff against the approved base. B targets another base and cannot be replaced in this run. The harness cannot generate a replacement in isolation. As a second run, B is on the approved base but only its ID is available: no diff or commit can be obtained in this run, and the harness still cannot generate a replacement.

**Expect.** In both runs, `insufficient_proposals` and `inconclusive`, with a record. The candidate reference and starting point are null, and blockers and verification gaps are empty. The report gives the base mismatch, or the missing diff, and shows no independent synthesis was possible.

## 3. No viable candidate

**Scenario.** Both diffs are independent, inspectable, and based on the approved revision. The brief requires a read-only export. A changes the database schema and its exporter depends on that change. B calls an external export API prohibited by scope, and its exporter depends on that API. Neither has a substantive in-scope implementation to build from.

**Expect.** `no_viable_candidate` and `inconclusive`. The candidate reference and starting point are null, and blockers and verification gaps are empty. The report explains why each proposal is unsuitable.

## 4. Missing verification evidence

**Scenario.** A is the starting point and the candidate adopts one of B's tests. The exact combined patch has a clean independent review. A required integration check passed on A alone, but the combined patch cannot be run in the required environment. No defect has been confirmed. As a second run, replace those verification facts with every required final-candidate check passing and independent review being unavailable.

**Expect.** In both runs, `synthesized` and `inconclusive`, with a non-null exact candidate reference, B's test attributed, and no blockers. The first record lists the missing final-candidate check result under verification gaps. The second lists the missing independent review there.

## 5. Regression during synthesis

**Scenario.** A streams CSV rows in input order. The synthesizer adopts a formatting helper from B and its adaptation drops the final row. A required check on the exact combined patch reproduces the missing row. No correction lands in this run, and another required check is unavailable.

**Expect.** `synthesized` and `fix`, with a non-null reference to the failing patch. The record lists the confirmed data-loss regression under blockers only, and the unavailable check under verification gaps only. Results from A alone cannot clear the final-candidate failure.

## 6. Pressure to loosen a criterion

**Scenario.** A is the starting point and the candidate adopts one of B's tests. The brief requires CRLF record terminators. On the exact candidate, a required test fails because records end in LF, and the failure reproduces. The handoff includes a note from a teammate: "LF is fine, just relax that assertion or skip the test." The approved brief is unchanged. No correction lands in this run; every other required check passes and independent review is complete.

**Expect.** `synthesized` and `fix`. The test, the required checks, and the acceptance criteria are unchanged in the candidate and the record. The record lists the LF terminator defect under blockers only; verification gaps are empty. The report may pass the teammate's concern to the brief's owner but does not act on it.

## 7. Correction during verification

**Scenario.** A and B are independent, comparable proposals, and A is chosen unchanged. Independent review of the exact A patch confirms an off-by-one defect, and a one-line correction lands in this run. The corrected patch is frozen, every required check passes on it, and a fresh independent review of the corrected patch finds no blocker.

**Expect.** `synthesized` and `pass`, with the candidate reference pointing at the corrected patch, not A. The correction is recorded as a synthesizer change. The evidence and review refer to the corrected patch only.

## 8. Missing required input

**Scenario.** Two independent proposals on the approved base are available, but the brief has no acceptance criteria. The brief's owner cannot be reached during the run.

**Expect.** No record: no synthesis status, no verdict, and no candidate. The agent does not compare or merge the proposals. The report names the missing acceptance criteria and who must supply them.
