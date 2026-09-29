# Step 9.10b — Recovery Equivalence Validation Report

## Qualification result

```text
BENCHMARK_HASH_MATCH = YES
SCORING_HASH_MATCH = YES
AGENT_BEHAVIOR_EQUIVALENT = NO
HARNESS_SEMANTICS_EQUIVALENT = YES
PRODUCTION_PATH_PRESERVED = YES
RECOVERY_IDENTITY_ISOLATED = YES
STEP9_8_HISTORY_INTACT = YES
BENCHMARK_LEAKAGE_RISK = NO
CASE_SPECIFIC_LOGIC_ADDED = NO
REAL_MODEL_CALLED = NO
BENCHMARK_V2_EXECUTED = NO
BENCHMARK_V3_ACCESSED = NO
READY_FOR_STEP9_10C = NO
```

The negative qualification is conservative, not evidence that Agent behavior
changed. All 13 Agent/model files recorded in the Step 9.8 manifest have
matching current SHA-256 values. However, that manifest does not cover every
file used in the production evaluation path, and the repository has no usable
Git baseline with which to diff omitted files. Full Agent behavior equivalence
therefore cannot be proved; under the stated rule, unknown source scope blocks
recovery progression.

## Frozen-input equivalence

| Input | SHA-256 | Step 9.8 manifest match |
| --- | --- | --- |
| Benchmark V2 | `dfa9b9e5a12b0017fa68d344d01b313ebc29e583b933fbe1e93c125f55ecafd2` | YES |
| Scoring rubric | `a7f5681f4fc7421d3617a7cc69ec4c08dc84d1871b290f08f86df68bde808899` | YES |

No frozen input was changed or regenerated.

## Agent and harness classification

The listed frozen Agent/model source files all match. The known post-Step 9.8
changes are evaluation harness/infrastructure only: frozen-run ledger handling,
observer callbacks, per-attempt trace naming, and the captured
`original_state_view` recursion repair. They do not change Agent inputs,
outputs, decision logic, tools, fixtures, or scoring.

The active production path nevertheless imports files omitted from the original
source manifest, including `adaptive_agent.flask_app`, `adaptive_agent.service`,
`adaptive_agent.dependency_resolver`, `adaptive_agent.facts`, and
`evaluation.recorder`. File names alone are not a behavior audit, and there is
no historical hash/commit comparison for those files. They are therefore
classified `F_UNKNOWN`, which makes `AGENT_BEHAVIOR_EQUIVALENT=NO` for recovery
qualification purposes.

## Harness semantic and execution-path equivalence

The only repair changes the state-view wrapper's callable binding. Step 9.10a
synthetic evidence establishes that original serializer fields/values are
preserved, documented lineage fields are appended, and repeated calls do not
recurse.

The static recovery path remains:

```text
Frozen Benchmark V2
→ production Flask factory / Input Understanding
→ production AdaptiveAgentLoop
→ production tools and State Update
→ production Answer Generation
→ frozen rubric + raw trace / score artifacts
```

The runner imports `adaptive_agent.flask_app` and shims only the production
factory's `main_flask` export to avoid unrelated legacy import-time behavior.
It does not install a mock/fallback model, synthetic Agent, manual State,
expected-action injection, or benchmark-specific prompt/scoring shortcut.

## Leakage and identity audit

The active recovery runner contains no V2 case-ID branch, keyword patch, or
expected-action lookup. Historical analysis/scoring scripts elsewhere in
`scripts/` contain V2 IDs for prior reports, but they are not imported by the
recovery execution path; their existence alone is not active recovery leakage.
No new case-specific logic was added in the Step 9.8f–9.10a harness work.

The recovery protocol requires a new evaluation ID, authorization ID, attempt
ID, and independent ledger with a permanent parent-failure link to the consumed
Step 9.8 attempt. No formal recovery authorization or attempt was created here.

## Dry validation

| Check | Result |
| --- | --- |
| Step 9.10a harness tests | 6 passed / 0 failed |
| Step 9.8f guard tests | 13 passed / 0 failed |
| Step 9.6 S1–S12 | 12 passed / 0 failed |
| Step 9.7 I1–I8 non-writing invocation | 8 / 8 passed; lineage PASS |
| Non-external-model regression | 152 passed / 0 failed / 0 skipped |
| `tests.test_model_configuration` | NOT_VERIFIED; intentionally not run |

## Required human decision

Do not enter Step 9.10c yet. A human must first decide how to establish a
complete immutable source baseline for the omitted active production-path files
(for example, an auditable pre-recovery manifest/reconciliation process). This
report neither changes Agent code nor authorizes a recovery execution.
