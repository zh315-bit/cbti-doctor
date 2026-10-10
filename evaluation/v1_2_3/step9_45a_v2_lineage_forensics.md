# Step 9.45a — Treatment-v2 Lineage Forensics

Read-only forensic step for the explicitly pinned treatment-v2 execution. Formal ledger, results, and traces were hash-checked before parsing and are never modified.

Evaluation `heldout-v4-step9_43-treatment-v2-20260928-01`; attempt `attempt-step9_44r1-cb362342ae31449aaffba8092c346864`; status **COMPLETED**. Formal results/traces: **40/40**. Task distribution: CAUSE_ASSESSMENT=10, DATA_ANALYSIS=10, KNOWLEDGE_QA=10, PERSONALIZED_DECISION=10.

Formal lineage ready=27; false=13. Recomputed lineage: COMPLETE=35, INCOMPLETE=5, INDETERMINATE=0.

Root classifications: NO_FAILURE=27, RUNNER_DERIVATION_BUG=8, TRUE_LINEAGE_FAILURE=5, INDETERMINATE=0.

Adjudication eligibility (not scoring): FULL=40, PARTIAL=0, NONE=0. Reviewer scores were not populated.

The deterministic derivation joins existing `final_state.action_history` IDs to persisted DECISION snapshots, dependencies, semantics, and lineage events. No candidate, dependency, or semantic identifier was generated, repaired, inferred, or guessed. Missing semantic roots remain missing.

No scoring, adjudication, aggregation, Overall, baseline comparison, rerun, model/Agent/RAG execution, or V5 access occurred. This report makes no performance or comparative claim.

Start-of-step hashes: case results `4648b8e320f535001922f13a969d1482433bfa15f88233cf9a7e70b06cafed6c`; raw traces `d7ddf2a9a47ba62a85a7d1b85f069cc9593fd8f46cc4a01c1f3c8a055698cec2`. The script rechecks both files against the starting bytes before exit.

## Shared frozen pin SHA-256 audit

- `evaluation/benchmarks/benchmark_v4_cases.yaml`: EXPECTED_SHA=`8b8c72092fcd7544e69d5d2ecd13610c7bb4c14210fca330698b3e5ab3f01d7f`; ACTUAL_SHA=`8b8c72092fcd7544e69d5d2ecd13610c7bb4c14210fca330698b3e5ab3f01d7f`; MATCH=`TRUE`
- `evaluation/v1_2_3/step9_13a_harness_freeze.json#new_harness_files`: EXPECTED_SHA=`8bc271bebc1c5da5351d517e2bb4a0d1a99fda3de1b713a6197b12f81fad70c7`; ACTUAL_SHA=`8bc271bebc1c5da5351d517e2bb4a0d1a99fda3de1b713a6197b12f81fad70c7`; MATCH=`TRUE`
- `evaluation/v1_2_3/step9_11_clean_freeze_manifest.json#scoring_files`: EXPECTED_SHA=`f742a8f8af7c8747818dadad81621c15d12d74f50538019913dfe18ab53bf59b`; ACTUAL_SHA=`f742a8f8af7c8747818dadad81621c15d12d74f50538019913dfe18ab53bf59b`; MATCH=`TRUE`
- `evaluation/benchmark_v1_1_scoring.md`: EXPECTED_SHA=`a7f5681f4fc7421d3617a7cc69ec4c08dc84d1871b290f08f86df68bde808899`; ACTUAL_SHA=`a7f5681f4fc7421d3617a7cc69ec4c08dc84d1871b290f08f86df68bde808899`; MATCH=`TRUE`
- `evaluation/v1_2_3/step9_26_v4_metric_registry.json`: EXPECTED_SHA=`de9f348cb1dff66410c03095abdaffcc256f53679718482870e4aa4d80c75056`; ACTUAL_SHA=`de9f348cb1dff66410c03095abdaffcc256f53679718482870e4aa4d80c75056`; MATCH=`TRUE`
- `evaluation/v1_2_3/step9_26_v4_one_shot_rules.md`: EXPECTED_SHA=`1c7ed4ef47865b117bc943f3e0ad9a859f4f74cfb4e8001f723ac5532af140d0`; ACTUAL_SHA=`1c7ed4ef47865b117bc943f3e0ad9a859f4f74cfb4e8001f723ac5532af140d0`; MATCH=`TRUE`
- `evaluation/v1_2_3/step9_34a_matched_comparison_protocol.json`: EXPECTED_SHA=`a71ba06090370b576fbba66bc4b005e519ddbabff3021a40c6546fc855f90265`; ACTUAL_SHA=`a71ba06090370b576fbba66bc4b005e519ddbabff3021a40c6546fc855f90265`; MATCH=`TRUE`

Input freeze: `step9_45a_v2_run_input_freeze.json`.
