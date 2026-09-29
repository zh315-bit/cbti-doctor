# Step 9.20c — Benchmark V3 Sealing Report

**Sealed dataset:** `evaluation/benchmarks/benchmark_v3_cases.yaml`  
**SHA-256:** `44ca089a6efa6d734815b17fc73753e8411fcfc31c4f5792342644ed54b2821f`  
**Schema/version:** `v2-compatible-1` / `3.0-heldout`  
**Cases:** 32 (8 per task type)  
**Seal timestamp:** `2026-09-24T14:47:16Z`  
**Status:** `SEALED_NOT_ACCESSED` = constructed and statically audited, **not yet accessed by Agent/formal evaluation**.

The prior Step 9.19 phrase `SEALED_NOT_ACCESSED` is corrected in a separate additive provenance artifact to mean `PLANNED_HELDOUT_NOT_YET_CONSTRUCTED` before this step. Historical manifests and reports were not rewritten. The Step 9.20b missing-path blocker now has a real, sealed path and hash; this report itself is **not** authorization. The earlier unsigned template remains unsigned. The existing local preflight artifact predates dataset construction and should be reassessed as part of any later authorization audit.

Static checks passed: YAML parsing, all 32 required-field sets, unique IDs/queries, no exact V2 query duplicate, valid dated entry fixtures and positive minute-unit durations, unavailable fixtures empty, and manual review of closest V2/V3 query similarities. The audit and its limitations are recorded separately. No Agent execution on V3, DeepSeek call, V2 rerun, scoring modification, or one-shot attempt occurred.

Future handling: compare the file's bytes to the sealed SHA-256 before formal access; bind the path and hash to a newly human-reviewed authorization. Do not alter the dataset based on model performance. If data quality issues are later found, record them as limitations; do not silently edit this sealed file or replace the primary result.
