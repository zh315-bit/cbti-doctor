# Step 9.43a — Treatment-v2 Runner Identity Compatibility Repair

Status: `PASS_INFRASTRUCTURE_IDENTITY_COMPATIBILITY_ONLY`; precheck complete, authorization not issued.

The exact v1 coupling was in the Step 9.35a identity loader: it read `step9_33a_treatment_freeze.json` and `step9_34a_treatment_authorization_template.json`, then checked the v1 Agent SHA and fixed v1 evaluation ID against the v1 runner freeze. The parent runner's output path was already generic, but its accepted identity was not. No coupling was found in case loading, case ordering, tool/model/RAG use, trace/result shape, scoring, adjudication, aggregation, or claim semantics.

Added a small, separately frozen identity-contract adapter. It accepts only the exact v1 or v2 contract paths and their hashes in the new runner freeze; reads the named treatment freeze; recomputes its complete Agent inventory; verifies all shared evaluation identities; and requires an issued authorization manifest to bind the contract path/hash, freeze path/hash, Agent SHA, runner and runner-freeze hashes, evaluation/authorization/attempt IDs, and all frozen infrastructure pins. It rejects missing IDs, missing identity, mutable aliases, v1 fallback, wrong hashes, consumed/unissued authorization, prior attempts, and namespace collisions. It revalidates the full identity again at the parent runner's pre-first-case refresh point rather than handing over a stale identity snapshot.

Execution itself delegates to the byte-identical Step 9.35a runner and unchanged Step 9.28 production case path. No case, trace, result, scoring, or adjudication behavior changed. Step 9.35a runner/freeze remain untouched and retain their historical SHA. A v1 identity pair passes the synthetic identity-contract unit test; in the current workspace, the actual v1 Agent bytes are superseded by Step 9.42, so live inventory validation correctly rejects v1 while v2 is active. The v2 contract passes live freeze/inventory and all shared-pin checks.

Focused tests: 26 new identity-contract tests, 21 existing Step 9.35a runner tests, and 16 Step 9.42 synthetic Agent tests pass (63/63 combined). Full unittest regression: 359 passed, 0 failures, 0 errors. Tests use synthetic identities/inputs and guard fixtures; no V4 case was loaded or executed. Baseline Step 9.30a and treatment-v1 Step 9.36 run artifacts (ledger, case-results, raw-traces) match all six historical pins; all 22 Step 9.39 sources also match.

`TREATMENT_V2_RUNNER_READY = YES`  
`EXACTLY_ONCE_GUARD_READY = YES`  
`OUTPUT_NAMESPACE_ISOLATED = YES`; the new v2 namespace is absent and no prior v2 attempt exists.  
`AUTHORIZATION_STATUS = NOT_ISSUED`; the v2 authorization template is disabled, contains no IDs, and no command is generated.  
`READY_FOR_STEP9_44_TREATMENT_V2_AUTHORIZATION = YES` (eligibility only; Step 9.44 must separately audit and issue any authorization).  
`RESUME_DESCRIPTIVE_MATCHED_COMPARATIVE_CLAIM_ELIGIBLE = NO`  
`V4_CASE_EXECUTED = 0`; `V4_RERUN = NO`; `V5_CREATED = NO`; `V5_ACCESSED = NO`.

See `step9_43a_treatment_v2_runner_freeze.json` and `step9_43a_treatment_v2_preclearance_rerun.json`. The original Step 9.43 fail-closed artifacts are preserved unchanged.
