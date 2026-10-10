# Step 9.63c-r5c10d — New runner freeze eligibility review

Status: `PASS_REVIEW_DRAFT_ONLY_NO_FREEZE_CREATED`. This is a read-only qualification review with a non-executable candidate inventory. It is **not** a new runner freeze, authorization, Mac-local preflight or formal V4 execution.

## Historical r10 and current member comparison

The historical r10 manifest remains at SHA-256 `d24244235e51e7bf6c8567880c654fe3fd73b87fa1bfe1ab0f10dfdc94db2693`; none of its 20 recorded member paths or hashes was edited. Comparing each member's current raw bytes against that manifest finds exactly **one** difference: `scripts/v3_execution_transaction.py` changed from r10 SHA-256 `f1a253730953abf51307f4e9404bf59d7856c15d2367b7a62d6809dbb64b2797` to working-copy SHA-256 `f0e74a49d152053b5455951c507edb8f7849a9e4708835711e5975a82e690e91`. The other 19 members match. The change is the approved `_find_identity()` journal-path classifier; no other production-code member changed.

Independent frozen-identity checks match r10 for the V3 Agent (`085d338ed95bbef7370c41cf97ca0d6653ffdfd2f1c924eef4b7123dfdea4607`), sealed benchmark and manifest, every harness/scoring file row and aggregate, rubric, metric registry, one-shot rules, tool adapter and dependency lock. All 55 historical pins match. No credential value was read. The prior committed transaction journal, its AppleDouble companion, old authorization manifest, r10 preflight and invocation registry retain their previously recorded SHA-256 values; the Step 9.58 provenance gap remains documented.

## Scanner and semantics review

The repaired scanner excludes a `._` file only after checking it is a regular non-symlink AppleDouble companion with magic `00051607` and a canonical ordinary journal. Non-JSONL files are not parsed. Canonical journals still use the unchanged `read_events()`/event sequence validator; invalid UTF-8, JSON, filenames, empty journals, symlinks, directories and duplicate authorization/attempt/namespace bindings fail closed. It examines every candidate before returning a collision result. The repair does **not** add an independent global uniqueness rule for `transaction_id`; that was not in the approved r5c10b scope. Existing exactly-once, duplicate-consumption and illegal-transition guards remain in place.

The `PREPARED → COMMITTING → COMMITTED` append order, lock, fsync and irreversible `COMMITTED` authority did not change. The authorization lifecycle module/contract and one-shot rules match their frozen hashes. A repeat offline run of 18 new scanner tests, 32 existing transaction tests and 14 selected temporary-root lifecycle tests passed: **64/64, 0 failures/errors/skips**. These tests did not read real production transaction journals or call network/model/Agent/RAG/V4 paths.

## Draft candidate and required rebindings

The version inventory contains historical runner freeze revisions r3 through r10; no r11 freeze or revision reference was found. Thus `r11` is the **proposed next unused identifier**, not an issued revision. The [candidate manifest](step9_63c_r5c10d_candidate_freeze_manifest.json) is explicitly `DRAFT_NOT_FROZEN_NOT_AUTHORIZED`, has 20 current working-copy member hashes and member-snapshot aggregate `024727dce3e0dfd8d939eaadfb2f4ead0cf396c4f55dddf80b929c8cafffefbb`. Its raw-file SHA-256 is `d00126ea3616bd1a51b0a8a33dc49a93bd7a142fdd46c98d8a1041069ccd04bc`; **this is the draft artifact hash, not the final r11 runner-freeze hash**, which is `NOT_DETERMINED`.

The snapshot intentionally still lists the historical r10 identity-pointer file, so it is not an executable r11 inventory. A later authorized freeze-construction step must create and bind a new r11 pointer, resolve freeze-builder/pointer ordering, repin the changed transaction module and dependent validators, and prove the Mac-local preflight producer works with r11 (the current producer has hardcoded r10 expectations). The unchanged adapter and formal-entry hashes do not themselves make the mixed working copy executable. Any new freeze must be independently rehashed after these rebindings; do not promote this draft in place.

The old r5c6 authorization's reducer state remains `ISSUED_EXECUTABLE`, consumed `NO`, count `0`, but the once-invoked r10 formal command is non-reusable. Before a new authorization, a separately approved exact-ID non-reuse determination and frozen-predicate retirement must succeed, or fail closed. Only after a valid new freeze and terminal handling of the old issuance may a separate audit consider globally fresh authorization, attempt and namespace IDs. A new authorization-bound Mac-local preflight follows issuance; the r10 preflight cannot be reused. Formal execution requires its own later gate. No such lifecycle action occurred here.

```makefile
STEP9_63C_R5C10D_STATUS = PASS_REVIEW_DRAFT_ONLY_NO_FREEZE_CREATED
R10_HISTORICAL_FREEZE_PRESERVED = YES
CHANGED_R10_FREEZE_MEMBER_COUNT = 1
SCANNER_REPAIR_SCOPE_VERIFIED = YES
TRANSACTION_SEMANTICS_PRESERVED = YES
AUTHORIZATION_LIFECYCLE_PRESERVED = YES
ONE_SHOT_RULES_PRESERVED = YES
CANDIDATE_RUNNER_FREEZE_REVISION = r11 (DRAFT_PROPOSED)
CANDIDATE_FREEZE_MEMBER_COUNT = 20
CANDIDATE_FREEZE_HASH = d00126ea3616bd1a51b0a8a33dc49a93bd7a142fdd46c98d8a1041069ccd04bc (DRAFT_ARTIFACT_SHA256)
NEW_RUNNER_FREEZE_CREATED = NO
NEW_AUTHORIZATION_ISSUED = NO
AUTHORIZATION_CONSUMED = NO
FORMAL_V4_CASE_EXECUTED = 0
READY_FOR_NEW_RUNNER_FREEZE_APPROVAL = YES_FOR_SEPARATE_FREEZE_CONSTRUCTION_ONLY
```
