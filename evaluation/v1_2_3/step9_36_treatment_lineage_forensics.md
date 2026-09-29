# Step 9.36 — Treatment Run Integrity Freeze & Lineage Audit

Attempt: `attempt-step9_35b-e469d82618d4c51d91d193bb439507e4`; comparison class: `POST_HOC_MATCHED_FROZEN_BASELINE`. All three formal run files were hashed and frozen. Input identities match the issued Step 9.35b authorization. Formal artifacts remain unchanged; no score, adjudication, aggregate, baseline comparison, model/Agent/RAG call, rerun, or V5 activity occurred.

Attempt status **COMPLETED**, cases **40/40**, result/trace coverage and order match. Formal lineage ready=27, false=13. Independent recomputation: COMPLETE=35, NOT_APPLICABLE=0, INCOMPLETE=5, INDETERMINATE=0.

False formal lineage cases: `V4-CA-02`, `V4-CA-04`, `V4-PD-01`, `V4-PD-03`, `V4-PD-04`, `V4-PD-05`, `V4-PD-09`, `V4-PD-10`, `V4-DA-01`, `V4-DA-03`, `V4-DA-06`, `V4-DA-09`, `V4-DA-10`.

Cause classification: runner derivation bug=8, true lineage failure=5, persistence bug=0, not-applicable misclassified=0, indeterminate=0. The eight derivation false negatives are deterministically reconstructable from existing IDs in raw traces; the five missing semantic roots remain incomplete and were not fabricated.

Derived sidecar complete=35; incomplete=5. Adjudication eligibility (not a score): FULL=40, PARTIAL=0, NONE=0. Incomplete lineage cases remain eligible only where all frozen rubric dimensions have trace evidence with the same caveats used in Step 9.30a.2.

Raw execution totals (descriptive only): ASK=13, RETRIEVE=31, READ_DIARY=10. Formal input freeze: `step9_36_treatment_run_input_freeze.json`. No outcome interpretation is made.
