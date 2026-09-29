# Step 9.44-r1 — Treatment-v2 Regression Authorization

**Authorization status: `ISSUED_NOT_EXECUTED`.** Authorization was issued only for the frozen regression-only treatment-v2 V4 run. The command below is saved for a human operator and was not executed.

The Step 9.43a treatment-v2 agent/freeze, adapter and runner freeze, parent runner, benchmark and manifest, harness, scoring/rubric, Metric Registry, One-shot Rules, matched protocol, claim policy, model/tool/RAG configuration, dependency lock, case count/order, and execution limits all revalidated against their frozen identities. Historical checks passed: the baseline run files match Step 9.30a freeze, treatment-v1 run files match Step 9.36 freeze, and all 22 source hashes plus all three outputs from Step 9.39 match. The preclearance remains `PASS_PRECHECK_ONLY_NOT_AUTHORIZED`; before this issuance there was no v2 authorization, attempt, namespace, ledger, case-results file, or raw-trace file.

The evaluation ID is the unique treatment-v2/V4 regression namespace already pinned by the frozen Step 9.43a contract, `heldout-v4-step9_43-treatment-v2-20260928-01`. It had not been formally used and its output namespace was absent. The validator requires this exact pinned ID, so it is retained rather than mutating frozen infrastructure. New unique authorization and attempt IDs were issued and bound to it.

The adapter binding validator and frozen parent runner's pre-execution authorization validator both passed read-only validation. The three focused test modules passed 63/63. They cover correct identity acceptance and rejection of wrong Agent (including v1/baseline), freeze, benchmark, harness, scoring, registry, one-shot, protocol/order, IDs, missing/unissued authorization, duplicates, output collision, mutable aliases, and namespace mismatch. The actual issued manifest also passed both validators. Validation did not consume the authorization or create an attempt.

Authorization manifest: `step9_44_r1_treatment_v2_authorization_manifest.json` (SHA-256 `cb26164b3af3953c73bdebb42da3517e45848f036ea72f78552da389131825e0`).

Authorized command: `step9_44_r1_treatment_v2_authorized_command.txt` (SHA-256 `72ec47275b27cd2be74efd1cb9f83a99943ebf68644d0d9f1d6a722ae0739612`). Its flags and identities were reread and matched against the manifest. **Do not infer execution from authorization:** command execution, authorization consumption, formal attempt creation, V4 case execution, scoring, adjudication, aggregation, comparison, and V5 activity all remain absent. `RESUME_DESCRIPTIVE_MATCHED_COMPARATIVE_CLAIM_ELIGIBLE=NO`.

The earlier Step 9.44 fail-closed audit is preserved unchanged as historical audit history; this rerun records the authorization decision under new append-only artifact names.
