---
name: grounded_answer
description: Select a supported answer
---

# Select a supported answer

Input: question and dated evidence. Select at most four verbatim quotations with source identifiers. Include exceptions that change the answer. Return abstain true with no claims when support is absent. Never manufacture a quote or infer a secret value.

## Success condition
The output meets the contract and keeps its original provenance.

## Failure behavior
Return an explicit failure or abstention; never guess.
