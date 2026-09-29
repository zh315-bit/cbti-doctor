# Step 9.30a — V4 frozen-rubric adjudication infrastructure

## Frozen formal run

The one-shot V4 attempt is `COMPLETED` with 40 cases started/completed and `valid_raw_results=true`. The ledger, result file, and raw trace file were frozen with repository-relative path, SHA-256, byte size, and line count in `step9_30a_v4_run_input_freeze.json`. AppleDouble `._*` files were excluded. Result/trace case coverage is 40/40, case IDs are unique, and all result rows remain `PENDING_FROZEN_RUBRIC_REVIEW`.

The result and raw trace files are unchanged after infrastructure work. Hashes remain:

- attempts ledger: `5fe1b11cbe0c28ccdfd056e3141862748897dc3b419ff6f05eb3ad8cb847b59f` (83 lines)
- case results: `77042ae9f5a5a75f7f7efd068e3c182e5725fa709e4f68ae63e58f0bbad0d2ea` (40 lines)
- raw traces: `e1aac03f4dbedf567c625694e084fa23155c8bfc2db1d43c4dffbce158734189` (40 lines)

## Frozen scoring contract

The rubric SHA-256 is `a7f5681f4fc7421d3617a7cc69ec4c08dc84d1871b290f08f86df68bde808899`, matching the V4 Metric Registry. Registry SHA-256 is `de9f348cb1dff66410c03095abdaffcc256f53679718482870e4aa4d80c75056`. The V3 Step 9.21 score artifact was inspected only to understand prior review-field provenance; no V3 score, label, or rationale was copied into V4.

## Schema, template, validator, and aggregation

The machine-readable schema separates immutable execution facts, reviewer judgments, review provenance, and source-line provenance. The deterministic template contains one row per formal case, with execution facts copied from the result and trace files. It includes no answer text. Every reviewer judgment, reviewer identity, and review timestamp remains null. Source path, line number, and line SHA-256 allow each fact to be traced back to the frozen file.

The validator has `--template` and `--completed` modes. It checks exact case coverage, duplicate/unknown cases, immutable facts and provenance, rubric/registry identities, dimension ranges and total arithmetic, completion/validity values, ASK denominator and category sum, target-denominator arithmetic, tool-action classifications, critical/harmful fields, evidence, and reviewer provenance. Completion is never inferred from `final_status`.

The aggregation contract only accepts records that pass completed-mode validation. It defines the preregistered descriptive quality, acquisition, safety, attribution, efficiency, and latency summaries. It creates no composite pass threshold. No aggregate was run on the real V4 template.

Focused deterministic tests: 13/13 passed. Template validation: PASS, 40 rows. No completed V4 adjudication or score was produced.

## Lineage limitation

The formal records do not satisfy the requested all-cases-lineage-ready condition: 28/40 result rows have `lineage_ready=true`, while 12 have `false`. The affected case IDs are V4-CA-02, V4-CA-04, V4-DA-01, V4-DA-03, V4-DA-06, V4-DA-09, V4-DA-10, V4-PD-03, V4-PD-04, V4-PD-05, V4-PD-06, and V4-PD-10. Their recorded values and traces were preserved exactly; no synthetic lineage was added.

The infrastructure and blank template are ready, but `READY_FOR_STEP9_30B_HUMAN_ADJUDICATION = NO` until the 12 lineage exceptions receive an explicit handling decision. This stage made no V4 rerun, Agent/model/RAG call, human judgment, aggregate score, or Overall score.
