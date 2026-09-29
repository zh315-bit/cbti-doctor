# Step 9.20c — Benchmark V3 Provenance Correction

This is an additive correction; no earlier artifact is rewritten. Historical Step 8.2 stated “Benchmark V3 was not created or inspected”; the Step 9.19 manifest recorded `heldout_set.status=SEALED_NOT_ACCESSED` while also recording `hash_recorded=false` and `content_read=false`. Step 9.20/9.20a preparation and Step 9.20b authorization audit did not locate or bind a concrete dataset; the unsigned template kept `benchmark_path=null`.

Therefore the **pre-construction** status should be understood as `PLANNED_HELDOUT_NOT_YET_CONSTRUCTED`, not as proof that a sealed dataset existed somewhere. The old `SEALED_NOT_ACCESSED` phrase was a planned evaluation status, not an artifact identity. This correction does not imply that earlier audit statements about *not viewing* V3 were false: there was no V3 file to view.

Step 9.20c creates `evaluation/benchmarks/benchmark_v3_cases.yaml` and seals its bytes using `step9_20c_v3_manifest.json`. From this point forward `SEALED_NOT_ACCESSED` has a real, narrow meaning: **the constructed dataset was read during design/static QA, but has not been accessed by the Agent or the formal evaluation runner**. The formal runner's `V3_FIRST_ACCESS` event will mark first *evaluation* access, not first-ever human or construction access. This distinction is required for truthful provenance.

The Step 9.19 Agent/Harness/Scoring/Metric/One-shot freezes remain unchanged. Step 9.20b was blocked and issued no authorization; its earlier `benchmark_path=null` is preserved as historical evidence. Any future authorization must bind both the repository-relative V3 path and the Step 9.20c dataset SHA-256, and must receive separate human review. This document does not authorize a run.
