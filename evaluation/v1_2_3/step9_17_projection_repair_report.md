# Step 9.17 — Tool → State Projection Repair Report

## Change summary

Implemented a verified projection boundary for the currently wired tools. Diary inputs now retain explicit payload shape and are validated before any diary facts enter State. Entry-shaped inputs must prove count, per-entry dates, unique date coverage, and provenance. Summary-shaped inputs must prove source cardinality, date coverage, provenance and summary semantics; they are stored under a separate `diary_summary` fact and cannot masquerade as raw day entries. Unavailable and invalid are now distinct states. Invalid/unavailable reads clear any prior diary-sourced projection so an old result cannot be mistaken for the new tool result.

Valid entries preserve the source rows and add deterministic aggregates: diary-day count, average numeric sleep duration with contributor count, exact-clock bedtime/wake variation, time-in-bed by date, and per-day sleep efficiency only when sufficient exact inputs exist. Approximate/range clocks remain approximate/ranges and are not used for exact variation or efficiency. All claims derived from diary data carry projection IDs, source count, dates, provenance and validation status. Answer generation filters diary-sourced facts unless the active projection is valid.

Retrieval now records the same generic projection envelope (`EVIDENCE_LIST`) and propagates source/result IDs into State evidence and evidence-grounded claim provenance. This supplies a reusable pattern for future tools without pretending that all tools have diary semantics.

## Modules and data flow

1. `DiaryTool.read(requirements) → DiaryResult`: returns facts, availability, explicit kind and source metadata; no automatic provenance is synthesized.
2. `apply_diary_result(state, result) → state`: validates payload shape and source metadata, creates projection/tool/state lineage, fails closed on invalid input, and writes only validated facts.
3. Deterministic projection derives statistics from validated entry rows only; values keep their source projection in `fact_sources`.
4. `LLMAnswerGenerator.answer(state) → answer`: builds a filtered fact view, excludes diary facts unless projection status is valid, provides deterministic claims and lineage, then applies the existing answer grounding/scope checks.
5. Retrieval follows the same result → projection event → State evidence → evidence claim lineage pattern.

## Verification

- New synthetic projection matrix: **20 passed / 0 failed**.
- Focused combined suites (projection, Diary Contract, V1.2.1 mechanism/preconditions, answer grounding, Agent Loop, policy refinement, Step 9.4/9.6 integration): **93 passed / 0 failed**.
- Full discovered unittest suite: **200 tests; 198 passed, 2 failed, 0 skipped**. The two failures are `test_step9_13a_authorization_infrastructure` assertions that the current Agent still matches the historical Step 9.11 Agent freeze. Step 9.17 intentionally changed Agent source within its authorized Tool→State boundary, so this historical identity assertion is now stale; the historical freeze was not rewritten. These failures are not projection correctness failures, but the full regression gate is therefore reported **FAIL (2 expected freeze-identity mismatches)**, not PASS.
- `tests.test_model_configuration`: included in discovery and passed (its network/model operations are mocked; no live call made).
- No benchmark cases were run, no external model/RAG requests were made, and no Benchmark V3 files were accessed.

## Limits and follow-up

- Summary provenance is validated structurally (non-empty metadata plus explicit summary semantics), not cryptographically authenticated against an upstream database. Future real adapters should supply source IDs or signed/versioned provenance.
- Current entry schema expects valid ISO `date` per entry and exact normalized clock strings for variation/efficiency. More date formats or measurement units need explicit adapters, not permissive guessing.
- The two freeze-identity regression failures should be handled as a separate evaluation-infrastructure/version-freeze decision; this step preserves old freeze artifacts and does not bless a new baseline.
- This repair does not resolve low-value ASK behavior; that remains the next priority, but should proceed only after review of these projection results.
