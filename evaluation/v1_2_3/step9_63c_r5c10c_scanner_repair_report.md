# Step 9.63c-r5c10c — Transaction scanner repair implementation

Status: `PASS_OFFLINE_SCANNER_REPAIR_UNFROZEN`. This is a working-copy infrastructure repair, **not** a frozen or executable runner. No formal V4 execution, old-command rerun, Mac-local preflight, authorization issuance/consumption, attempt, namespace or transaction was performed.

## Implemented scope

Only `scripts/v3_execution_transaction.py::_find_identity()` changed in production code. Before `read_events()`, it now requires a real transaction root and classifies sorted direct-child entries. Files without `.jsonl` do not enter event parsing. A `.jsonl` candidate must be a regular non-symlink file with a `SAFE_ID` authorization stem. A `._` companion is excluded only when it is regular, has AppleDouble magic `00051607`, and has a real canonical non-symlink companion journal. Orphan/malformed sidecars, unsafe names, directories and symlinks fail closed. Canonical candidates still go through the unchanged `read_events()` and event sequence validator; empty journals and filename-to-first-event authorization mismatches fail closed. The scan checks every candidate before returning a collision result, so an earlier identity match cannot hide later corruption.

No `UnicodeDecodeError` is caught-and-ignored. A canonical journal with invalid UTF-8 still raises and blocks the transaction. The fix does not alter `begin_and_commit`'s lock, `PREPARED → COMMITTING → COMMITTED` writes, fsync durability or irreversible commit point; it changes only the admission scan. Authorization lifecycle and one-shot implementation/contract files remain byte-identical.

## Offline verification

64 tests passed, 0 failures, 0 errors and 0 skips: 18 new synthetic scanner tests, 32 existing transaction tests and 14 selected synthetic lifecycle tests. The new tests cover each r5c10b design scenario, including a verified AppleDouble companion, unrelated binary files, corrupt canonical UTF-8/JSON, duplicate identities, a historical committed journal and burned authorization, deterministic all-file scanning, symlink/directory rejection, macOS metadata and case-insensitive alias collision. Existing transaction tests confirm state transitions, commit markers, collision rejection, crash outcomes and exactly-once guards. The lifecycle tests used only temporary synthetic roots. Production-journal-reading cases from the older lifecycle suite were deliberately excluded under this step's test boundary. See [test matrix](step9_63c_r5c10c_test_matrix.json).

The direct read-only current-authorization check still reports `ISSUED_EXECUTABLE`, consumed `NO`, count `0`; the exact r5c6 transaction journal and namespace remain absent. That is not permission to reuse the already-invoked command. No real production transaction journal was read or modified by tests.

## Freeze boundary and next gate

The original r10 freeze remains SHA-256 `d24244235e51e7bf6c8567880c654fe3fd73b87fa1bfe1ab0f10dfdc94db2693`. Exactly one of its 20 members now differs in the working copy: `scripts/v3_execution_transaction.py`, frozen SHA-256 `f1a253730953abf51307f4e9404bf59d7856c15d2367b7a62d6809dbb64b2797`, current SHA-256 `f0e74a49d152053b5455951c507edb8f7849a9e4708835711e5975a82e690e91`. Thus `CURRENT_RUNNER_MATCHES_R10_FREEZE = NO` and `CURRENT_RUNNER_NO_LONGER_MATCHES_R10_FREEZE = YES`. No new freeze was created. r10 manifest, old authorization, journal, AppleDouble file, preflight, invocation registry and historical audit artifacts remain untouched.

`READY_FOR_NEW_RUNNER_FREEZE_REVIEW = YES` means only that this offline repair may be reviewed for a **separate** new-freeze step. It does not authorize retirement, fresh issuance, preflight or formal execution. The old formal command remains unsafe to rerun.

```makefile
STEP9_63C_R5C10C_STATUS = PASS_OFFLINE_SCANNER_REPAIR_UNFROZEN
SCANNER_REPAIR_IMPLEMENTED = YES
APPLEDOUBLE_EXCLUDED = YES
VALID_JOURNAL_CORRUPTION_FAIL_CLOSED = YES
TRANSACTION_SEMANTICS_UNCHANGED = YES
AUTHORIZATION_LIFECYCLE_UNCHANGED = YES
ONE_SHOT_RULES_UNCHANGED = YES
OFFLINE_TESTS_PASSED = 64
OFFLINE_TESTS_FAILED = 0
CHANGED_R10_FREEZE_MEMBER_COUNT = 1
CURRENT_RUNNER_MATCHES_R10_FREEZE = NO
NEW_RUNNER_FREEZE_CREATED = NO
NEW_AUTHORIZATION_ISSUED = NO
AUTHORIZATION_CONSUMED = NO
FORMAL_V4_CASE_EXECUTED = 0
READY_FOR_NEW_RUNNER_FREEZE_REVIEW = YES
```
