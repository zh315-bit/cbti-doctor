# Step 9.63c-r5c5 — Fresh r9 Authorization Issue

**Status: `FAIL_CLOSED_ACTIVE_AUTHORIZATION_EXISTS`**

The r9 runner freeze and frozen evaluation identity checks passed, including all 19 member hashes, the 40-case count/set/order, task distribution, and all 55 historical pins. The Step 9.58 provenance gap remains `PRESENT_AND_DOCUMENTED`. The prior r8 authorization is correctly retired.

Issuance was blocked because a separate active authorization remains: `auth-step9_63a_r3-d53bbaa35b1e4522bc4a5f57d42c8ef7`, recorded in `evaluation/v1_2_3/step9_63a_r3_v3_authorization_manifest.json` (SHA-256 `1514438d0afe23a39de2a696e9ea5bd97faac4dd546a88cdbd7b91f450046345`). Its manifest still says `ISSUED_NOT_CONSUMED` / `ISSUED_NOT_EXECUTED`, consumed `false`, consumption count 0, with no retirement event or consumption event. Therefore `ACTIVE_EXECUTABLE_AUTHORIZATION_COUNT_BEFORE = 1`, not the required 0.

Fail-closed behavior was applied: no new authorization, attempt ID, or namespace ID was allocated; no authorization manifest or issuance lifecycle event was written; no attempt or namespace was created or reserved. No Mac-local preflight, connectivity probe, HTTP request, model/Agent/RAG call, or V4 case was run. No historical artifact or the outstanding authorization was changed.

No offline test manifest was produced because the issuance precondition failed before any issuance operation. Resolution of the still-active Step 9.63a-r3 authorization requires a separately authorized lifecycle decision; this step did not retire it.
