# Step 9.27 — V4 Leakage Audit

The audit was static only. Historical V2/V3 IDs and query text were used solely for ID/exact-text/surface-similarity checks; evaluator expected paths, evidence, Agent outputs, and scores were not used to construct answer keys. Shared CBT-I topic areas are not treated as leakage by themselves.

| Check | Result |
|---|---:|
| V2 normalized exact query duplicates | 0 |
| V3 normalized exact query duplicates | 0 |
| Reused V2/V3 case IDs | 0 |
| V4↔V2/V3 query pairs with normalized `SequenceMatcher` ratio ≥ 0.52 | 0 |
| V4 case IDs or dataset lookup in `adaptive_agent/` and `configs/` | None found |
| Production `expected_actions` lookup | None found |
| Agent-specific case branch | None found |

The sequence ratio is a surface screen, not a semantic plagiarism detector. The case text was also reviewed for direct copying or simple paraphrase; no such case was identified. The evaluator-only metadata is isolated under each case's `evaluation` key and is excluded by the generic runtime fixture contract.

V3 remains consumed historical evidence. Its case content was consulted only as permitted for the static leakage audit; no V3 output/result was used as a construction target. No Agent/model evaluation occurred.
