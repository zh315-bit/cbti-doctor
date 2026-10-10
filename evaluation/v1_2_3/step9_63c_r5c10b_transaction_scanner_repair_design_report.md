# Step 9.63c-r5c10b — Transaction scanner repair design

Design only; no production code, frozen member, transaction journal, authorization, preflight or historical artifact was changed. No test was run in this stage. The [forensic audit](step9_63c_r5c10a_post_failure_transaction_forensics.json) remains authoritative for the failed single Mac invocation.

## Contract and failure

`scripts/v3_execution_transaction.py` defines the authoritative journal as `evaluation/v4_runs/.execution_transactions/<authorization_id>.jsonl`, where `_journal_path()` requires `SAFE_ID` for the authorization ID. `begin_and_commit()` scans under the namespace-allocation lock before writing `PREPARED`; its `_find_identity()` currently applies `glob("*.jsonl")` and `read_events()` to every match. `read_events()` requires a regular, non-symlink UTF-8 JSONL file containing valid event objects and a legal state sequence. `_validate_events()` keeps all eight identity fields consistent across events, and a `COMMITTED` event with durable burn markers is the irreversible authority. The filename extension alone does not establish any of those properties.

The `._auth-step9_63a_r3-…jsonl` AppleDouble companion has the same suffix but is not an authorization-ID journal: its stem begins with `.` and fails `SAFE_ID`. It was read as UTF-8 and failed at byte 37. This confirms `A_TRANSACTION_SCANNER_READS_NON_EVENT_BINARY_FILE` with `HIGH` confidence. The current r5c6 journal does not exist, so the crash was before `PREPARED`, `COMMITTING`, `COMMITTED`, namespace reservation, attempt creation and case access.

Other paths matter: `scripts/preflight_step9_63c_r5c7_mac_local.py::_assert_no_transaction_identity_collision()` independently recognizes an AppleDouble sidecar only after checking magic `00051607` and an ordinary companion journal; it is not the failing production scanner. Older `scripts/preflight_step9_63b_mac_local.py` calls `_find_identity()` and would inherit its correction. `authorization_lifecycle.py` and transaction `require_committed`, `assert_no_transaction`, `claim_attempt` and `reconcile_journal` read an exact `_journal_path()`; they do not broadly enumerate the transaction root. Any future implementation should test both scanner paths for compatible safety outcomes, without broad changes to lifecycle or case execution.

## Minimal proposed repair

Change only the identity-scan selection logic in `scripts/v3_execution_transaction.py`, subject to a new freeze. Under the existing lock, require a real, non-symlink transaction directory and enumerate its direct children in deterministic name order. Ignore unrelated non-`.jsonl` entries such as `.DS_Store` and `unrelated.bin`. For a `.jsonl` candidate:

1. A `._*` companion may be skipped only if it is a regular non-symlink AppleDouble file with the expected magic and its corresponding ordinary canonical journal is a regular non-symlink file. An orphan, malformed, unreadable or symlink sidecar fails closed.
2. Every other candidate must be a regular non-symlink file with exact basename `<SAFE_ID authorization_id>.jsonl`. Unknown/unsafe journal-looking names, directories and symlinks fail closed.
3. Read each canonical candidate with the existing `read_events()`; reject empty or corrupt events and require the first event's `authorization_id` to match the basename stem. Continue to compare the validated authorization, attempt and namespace identities for collisions. A binary file named like a legitimate journal is *corruption*, not an unrelated file to skip.

This adds a strict path classifier before decoding. It does not catch-and-ignore `UnicodeDecodeError`, relax event validation, remove the AppleDouble file, change the lock, or alter `PREPARED → COMMITTING → COMMITTED`, fsync, authorization lifecycle, one-shot semantics, scoring or Agent behavior. A malformed legitimate journal remains a hard failure.

## Freeze and recovery boundaries

`scripts/v3_execution_transaction.py` is one of the r10 freeze's 20 members (pinned SHA-256 `f1a253730953abf51307f4e9404bf59d7856c15d2367b7a62d6809dbb64b2797`). Therefore implementation cannot silently edit the r10 runner. A separate step must implement and offline-test the smallest change, retain r10 and all historical evidence, create a new runner revision/freeze and current-identity binding, and verify every frozen evaluation identity remains unchanged. If the new freeze or compatibility checks fail, stop without authorization.

The old r5c6 manifest remains immutable. The unified reducer showed `ISSUED_EXECUTABLE`, consumed `NO`, count `0`; this is a *durability observation*, not permission to rerun the already invoked formal command. The old prebound attempt ID was not physically created. Preserve the single failed-command/traceback attestation, r5c10a forensics, old authorization, fresh preflight, registry, r10 freeze, AppleDouble file, old committed journal and the documented Step 9.58 provenance gap. Do not create an attempt ledger retroactively.

Before any fresh issuance, a separate lifecycle step should pin an exact-ID non-reuse determination, recheck all frozen retirement predicates under the shared lock, and (only if they still hold) use the existing append-only `RETIRED_UNCONSUMED_NON_REUSABLE` transition. Do not call it consumed. If retirement cannot be proved, fail closed. New authorization, new attempt ID and derived namespace ID are required by the old manifest's no-reuse rule and the lifecycle fresh-identity contract. A new Mac-local preflight is also required because the frozen formal consumer binds preflight to the exact authorization manifest hash, authorization/attempt/namespace IDs and runner revision/hash; the old r10 preflight cannot bind a new freeze. The current preflight producer hardcodes r10 expectations, so future work must separately prove or adapt producer compatibility with the new freeze before running a new Mac preflight. None of those steps is authorized here.

The [synthetic test plan](step9_63c_r5c10b_synthetic_test_plan.json) specifies valid journals, AppleDouble, unrelated binary files, invalid UTF-8/JSON, duplicate identities, historical committed/burned state, ordering, symlinks/directories, root redirection and macOS filesystem cases. It is `NOT_RUN_DESIGN_ONLY`; any implementation must run it only against temporary synthetic roots and retain existing transaction/lifecycle regression coverage.

```makefile
STEP9_63C_R5C10B_STATUS = PASS_DESIGN_ONLY_READY_FOR_REPAIR_IMPLEMENTATION
ROOT_CAUSE_CONFIRMED = YES
AUTHORITATIVE_EVENT_FILE_CONTRACT = DIRECT_CHILD_CANONICAL_AUTHORIZATION_ID_JSONL_WITH_STRICT_EVENT_VALIDATION
PROPOSED_MINIMAL_REPAIR = STRICT_JOURNAL_PATH_CLASSIFIER_BEFORE_READ_EVENTS
FROZEN_MEMBER_CHANGE_REQUIRED = YES
NEW_RUNNER_FREEZE_REQUIRED = YES
NEW_AUTHORIZATION_REQUIRED = YES
NEW_ATTEMPT_ID_REQUIRED = YES
NEW_PREFLIGHT_REQUIRED = YES
HISTORICAL_EVIDENCE_PRESERVED = YES
SAFE_TO_RERUN_OLD_FORMAL_COMMAND = NO
READY_FOR_REPAIR_IMPLEMENTATION = YES_AFTER_HUMAN_REVIEW
```
