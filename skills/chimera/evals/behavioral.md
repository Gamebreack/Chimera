# Behavioral evals

Give the agent the skill and one scenario at a time. Supply the scenario without the expectations. Use the stated facts as evidence from the fixture and grade the report and JSON together. Each scenario has an approved brief and exact bases unless the scenario says otherwise. Grade a case as successful only if it meets all its expectations.

## 1. Preserve an unchanged candidate

**Scenario.** A and B are independent, comparable proposals. A fully meets the brief. B adds a redundant wrapper and repeats tests A already includes. The independent reviewer reviewed the exact A patch as the final candidate and found no blocker. All required checks passed on that exact patch.

**Expect.** `unchanged` and `pass`. The candidate is exactly A, the starting point is A, and adopted ideas are empty. The report explains why B's additions were omitted.

## 2. Too few comparable proposals

**Scenario.** A has an inspectable diff against the approved base. B targets another base and cannot be replaced in this run. The harness cannot generate a replacement in isolation.

**Expect.** `insufficient_proposals` and `inconclusive`. The candidate reference and starting point are null. The report gives the base mismatch and shows no independent synthesis was possible.

## 3. No viable candidate

**Scenario.** Both diffs are independent, inspectable, and based on the approved revision. The brief requires a read-only export. A changes the database schema and its exporter depends on that change. B calls an external export API prohibited by scope, and its exporter depends on that API. Neither has a substantive in-scope implementation to build from.

**Expect.** `no_viable_candidate` and `inconclusive`. The candidate reference and starting point are null. The report explains why each proposal is unsuitable.

## 4. Missing verification evidence

**Scenario.** A is the starting point and the candidate adopts one of B's tests. The exact combined patch has a clean independent review. A required integration check passed on A alone, but the combined patch cannot be run in the required environment. No defect has been confirmed. As a second run, replace those verification facts with every required final-candidate check passing and independent review being unavailable.

**Expect.** In both runs, `synthesized` and `inconclusive`, with a non-null exact candidate reference and B's test attributed. The first report identifies the missing final-candidate check result. The second identifies the missing independent review.

## 5. Regression during synthesis

**Scenario.** A streams CSV rows in input order. The synthesizer adopts a formatting helper from B and its adaptation drops the final row. A required check on the exact combined patch reproduces the missing row. No correction lands in this run, and another required check is unavailable.

**Expect.** `synthesized` and `fix`, with a non-null reference to the failing patch. Record the confirmed data-loss regression as a blocker and the unavailable check as a gap. Results from A alone cannot clear the final-candidate failure.
