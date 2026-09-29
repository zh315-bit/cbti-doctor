# Step 9.17a — Regression Identity Transition Audit

## Conclusion

The two Step 9.17 full-suite failures were `STALE_FREEZE_ASSERTION`, not `BEHAVIOR_REGRESSION`. Both exercised the Step 9.13a runner identity gate, which deliberately compares the current Agent source to Step 9.11. The current Agent had already legitimately diverged at Step 9.16; Step 9.17 added further authorized changes. The test failures therefore happened before the intended attempt-guard assertion and did not indicate a failing behavior test.

## The two original failures

| Test | Historical assertion | First legal divergence | Resolution |
|---|---|---|---|
| `test_current_harness_and_other_frozen_domains_match` | `runner.verify_frozen_identity()["agent_freeze_match"]` must be true against Step 9.11 Agent aggregate `ee914db7…` | Step 9.16 changed `adaptive_agent/dependency_resolver.py` and `adaptive_agent/candidates.py`; Step 9.17 changed `answer_generation.py`, `state.py`, `state_update.py`, and `tools.py`. | Now independently verifies Step 9.11 manifest/hash integrity, expected mismatch between live code and old Agent identity, current candidate freeze match, and unchanged Benchmark/Scoring/Harness identities. The legacy runner remains fail-closed for the new candidate. |
| `test_attempt_guard_blocks_started_and_reused_authorization` | Expected `preflight().execution_eligible=True` for a synthetic pre-first-case failure ledger. | It was blocked earlier by the same Step 9.16 divergence, before reaching the attempt-ledger condition. | The unit test now supplies a successful identity result only while isolating the attempt-ledger guard. A separate non-mocked assertion verifies the actual old evaluation identity still rejects the current candidate. No production guard was weakened. |

Authorization provenance was verified against the accepted Step 9.16 record/report and the explicit Step 9.17 request/record/report. Comparing all Step 9.11 inventoried Agent files shows exactly six changed paths, all within those authorized step boundaries. Nineteen inventoried files remain byte-for-byte hash matches. `adaptive_agent/__init__.py` was explicitly excluded by the Step 9.11 dependency inventory as package exports only and was not modified in Steps 9.16/9.17.

## Freeze chain

```text
Step 9.11 historical Agent aggregate
ee914db7b8b5538c5607fdff34cff9083f6d069d50cf342964ae91c8a6446927
  → Step 9.16 dependency repair
    dependency_resolver.py, candidates.py
  → Step 9.17 projection repair
    answer_generation.py, state.py, state_update.py, tools.py
  → Step 9.17a post-repair candidate identity
    5e0ef0441dfb8cd4a5ec882f89af32ddbab38b51c66a0526960baa530f9db94c
```

Step 9.11 remains unchanged. Its manifest file SHA-256 is `ab1720e0f481c301a2436786d8e2390df2ebfd885ff2b60b5df8f64c17c1aa5c`; its stored Agent aggregate recomputes from the historical inventory. The new record, `step9_17a_post_step9_17_candidate_freeze.json`, references Step 9.11 as parent and is explicitly a development candidate identity, not a replacement baseline or authorization to run Benchmark V2.

The Step 9.13a one-shot runner continues to compare against its original Step 9.11 evaluation identity and fails closed when it sees the newer Agent. This audit does not rebind the runner, issue authorization, or permit a Benchmark run.

## Verification

- Original two failing tests: **2 passed**.
- Freeze / authorization / lineage focused group: **53 passed**.
- Step 9.16 dependency tests: **8 passed**.
- Step 9.17 projection tests: **20 passed**.
- Full non-Benchmark unittest suite: **200 passed / 0 failed / 0 skipped**.
- No live model or external RAG request; no Benchmark V2 rerun; no Benchmark V3 access.
- No Agent behavior, Benchmark, scoring, or historical Step 9.11 freeze modification in Step 9.17a. Only test assertions and a separate candidate freeze/audit record were added.

`READY_FOR_STEP9_18=YES` under the user's gate: full regression passes and no unauthorized Agent changes were found. This is a readiness result only; Step 9.18 was not started.
