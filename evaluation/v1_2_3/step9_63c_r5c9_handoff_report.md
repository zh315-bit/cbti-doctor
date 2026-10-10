# Step 9.63c-r5c9 — Fresh Mac-local preflight handoff verification

Status: `PASS_READ_ONLY_HANDOFF_READY_FOR_SINGLE_ATOMIC_FORMAL_EXECUTION`.

The exact Mac-local artifact exists at the reported authorization scoped path and has SHA-256 `fbb2f3dfe964bbe500459c4ba58e016f7318bd2ca61c439d902030fd3cb2f35a`. Its embedded preflight ID is `preflight-step9_63c_r5-r5c8b-e3406012dcd4446fa793b097105cdf1d`. The append-only registry parses strictly and contains one initialization row plus exactly one claim for this ID, with no duplicates. Authorization issuance predates the claim, which predates artifact creation.

The current frozen `validate_preflight_evidence()` was invoked directly and accepted the artifact, explicit ID, path and SHA. The runner's earlier payload guard fields also match: both status representations, authorization/attempt/r10 binding, unconsumed/no-attempt/no-namespace state and DNS/TCP/TLS readiness. The consumer accepted the recorded DNS, TCP, TLS and certificate evidence without a new network check. The artifact's case set/order/distribution and nested evaluation identities match the authorization, and the production preflight snapshot reverified the underlying frozen identities.

The current r10 freeze matches all 20 members; V3 Agent and frozen evaluation identities match, the case count remains 40 with 10 per task, all 55 historical pins match, and the documented Step 9.58 provenance gap is preserved. The unified lifecycle reducer reports one active executable authorization, `ISSUED_EXECUTABLE`, unconsumed/count 0, with no attempt, namespace, reservation or transaction. The preflight artifact and registry were not changed in this audit.

`READY_FOR_SINGLE_ATOMIC_FORMAL_EXECUTION = YES` at this read-only handoff. The frozen CLI accepts the explicit authorization ID, preflight file, preflight ID and SHA flags, plus the seven required frozen hash flags. The following is the sole next-stage manual command. It has not been executed here. Because the authorization is one-shot, any execution failure must be preserved and assessed before another action; do not rerun automatically.

```sh
cd /Volumes/Elements/cbti-doctor-main && .venv/bin/python scripts/run_step9_63_v3_formal_execution.py \
  --execute-formal-v4 \
  --evaluation-id heldout-v4-step9_55a-treatment-v3-20260930-01 \
  --authorization-id auth-step9_63c_r5c6-aff5c4b96bb74278a14d3fd08bf8a84e \
  --attempt-id attempt-step9_63c_r5c6-3401b701486c4fdeb4019b461d024bd4 \
  --authorization-file evaluation/v1_2_3/step9_63c_r5c6_r10_v3_authorization_manifest.json \
  --preflight-file evaluation/v1_2_3/step9_63c_r5_auth-step9_63c_r5c6-aff5c4b96bb74278a14d3fd08bf8a84e_preflight-step9_63c_r5-r5c8b-e3406012dcd4446fa793b097105cdf1d_mac_local_preclearance.json \
  --preflight-id preflight-step9_63c_r5-r5c8b-e3406012dcd4446fa793b097105cdf1d \
  --preflight-sha256 fbb2f3dfe964bbe500459c4ba58e016f7318bd2ca61c439d902030fd3cb2f35a \
  --treatment-agent-sha256 085d338ed95bbef7370c41cf97ca0d6653ffdfd2f1c924eef4b7123dfdea4607 \
  --benchmark-sha256 8b8c72092fcd7544e69d5d2ecd13610c7bb4c14210fca330698b3e5ab3f01d7f \
  --harness-sha256 8bc271bebc1c5da5351d517e2bb4a0d1a99fda3de1b713a6197b12f81fad70c7 \
  --scoring-sha256 f742a8f8af7c8747818dadad81621c15d12d74f50538019913dfe18ab53bf59b \
  --metric-registry-sha256 de9f348cb1dff66410c03095abdaffcc256f53679718482870e4aa4d80c75056 \
  --one-shot-rules-sha256 1c7ed4ef47865b117bc943f3e0ad9a859f4f74cfb4e8001f723ac5532af140d0 \
  --matched-protocol-sha256 a71ba06090370b576fbba66bc4b005e519ddbabff3021a40c6546fc855f90265
```
