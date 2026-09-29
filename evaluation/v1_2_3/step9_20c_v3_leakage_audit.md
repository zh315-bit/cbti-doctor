# Step 9.20c — V3 Static Leakage and Quality Audit

Audit scope: only the V2/V3 YAML specifications and the frozen runner/tool input contract. No Agent output, Benchmark V2 execution, model call, or V3 execution was used.

| Check | Result |
| --- | --- |
| YAML parse | PASS |
| Required schema fields | 32/32 present |
| Unique V3 case IDs and query strings | 32/32 |
| V2 exact query duplicates | 0 |
| Task distribution | 8/8/8/8 for KQ/CA/PD/DA |
| Difficulty | easy 8, medium 13, hard 11 |
| Language | zh_brief 6, zh_colloquial 7, zh_distributed 7, mixed_zh_en 4, en 8 |
| Diary fixtures | 6 available entry-shaped, 26 unavailable (including non-diary tasks); all available entries have valid ISO dates and minute-unit duration values where provided |
| Evaluator leakage | No expected action, hidden user fact, or evidence injected by the runner; only declared initial session facts, actual follow-up answers and tool results can enter State |
| Duplicate-looking V3 scenarios | None found by manual goal/resource review; repeated broad CBT-I themes have distinct goals or available information |
| Impossible expected actions | None detected statically against the generic runner contract; alternative bounded paths are recorded where retrieval or diary data may be unavailable |
| Contradictory ground truth | None detected; unavailable diary has empty facts; entry counts and date coverage are derived from literal entries, not asserted separately |

Character-level `SequenceMatcher` screen across all 32×40 V3/V2 query pairs found no exact match. Highest ratio after pre-seal edits was **0.457** (`V3-PD-05` vs `V2-PD-01`): both mention personal bedtime, but V3 asks whether an otherwise stable schedule should be moved to 21:00 for abstract health reasons, whereas V2 asks whether a delayed-sleep-onset schedule should be moved later. This is neither a paraphrase nor the same decision. Other top ratios were 0.409, 0.398, 0.393 and 0.389; manual inspection found distinct goals. The highest within-V3 query ratio was 0.407, also with different decisions and input states. String similarity is only a screen, not proof of semantic independence.

Known limits: this is a static, single-author audit; it cannot prove that all case oracles are clinically complete or that another reviewer would assign identical scores. The frozen scorer has no numeric anchor table. Some tasks share unavoidable CBT-I vocabulary with V2. Neither overlap nor future score may be used to revise V3 after sealing. No case-specific Agent branch was added.
