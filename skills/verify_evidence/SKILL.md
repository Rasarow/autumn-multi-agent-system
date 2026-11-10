---
name: verify_evidence
description: Verify evidence before release
---

# Verify evidence before release

Input: candidate and original sources. Check source existence, exact normalized quotation match, validity date, relevance, and coverage. An unsupported or irrelevant answer must be withheld. Repair at most once through the supervisor; never add tools or raise the budget.

## Success condition
The output meets the contract and keeps its original provenance.

## Failure behavior
Return an explicit failure or abstention; never guess.
