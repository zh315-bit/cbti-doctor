# Step 9.63c-r5c10y — Single-file collection isolation

Status: **FAIL_CLOSED_COLLECTION_UNVERIFIED_PYTEST_UNAVAILABLE**. The narrowly approved test-only patch is present, but the required pytest collection could not begin because pytest is absent from the project virtual environment. The system and bundled Python environments checked also lack it. No substitute discovery run, package installation, network request, test method, or full regression was attempted.

## Exact modification

Only `tests/test_step9_63b_mac_local_preflight.py` was edited. It was already **untracked** in Git before this step, so ordinary `git diff --` was empty both before and after. Its pre-edit bytes were retained in a shell variable and compared with the edited file using `git diff --no-index` through a file descriptor. The content diff consists solely of removing the top-level `preflight_step9_63b_mac_local` import and inserting the identical import at the beginning of each of the eight methods that uses it. The no-index diff also displays a pseudo-file mode difference caused by `/dev/fd/3`; this does not establish a target mode change. No assertion, fixture, expected result or test call was changed.

Target SHA-256: `0a81c59db2969fc6b4fb7f09a5b4ed04b24422dd5f633620f49a4d61934ef191` before; `bcf9b8289336d575a184bf3dfb4cd2b6583f05a2f7d205ed4c6d852c06784052` after. A static AST parse passed and found eight `test_` definitions, eight method-local transport imports and no top-level `scripts` import. These are **static counts, not pytest collection results**. See [diff and hash audit](step9_63c_r5c10y_diff_hash_audit.json).

## Collection attempt and boundary

Command attempted:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest --collect-only -q -p no:cacheprovider tests/test_step9_63b_mac_local_preflight.py
```

It exited before loading the test file with `No module named pytest`. Thus `COLLECTION_SUCCEEDED = NO`, while `TESTS_COLLECTED`, test-module import errors and collection exceptions are **NOT_MEASURED**. No method was executed. [Collection result](step9_63c_r5c10y_collection_result.json).

The target is outside the 20-member r10 freeze inventory. The historical r10 manifest and current 20-member path/hash aggregate match their pre-edit observations; both affected historical Trace files retain their forward SHA-256 baselines. This does not establish their original content integrity, which remains `CONTENT_INTEGRITY_UNPROVEN`. The formal r11 pointer and freeze remain absent, and the production identity guard was neither changed nor bypassed. [Boundary audit](step9_63c_r5c10y_boundary_audit.json).

The patch should be reviewed as a **pending, unverified collection isolation**. A separately prepared environment with pytest must run the same target-file collection-only command before collection success or next-scope readiness can be claimed. Do not execute methods, create a fake r11 identity, or extend the patch to another module.

```makefile
STEP9_63C_R5C10Y_STATUS = FAIL_CLOSED_COLLECTION_UNVERIFIED_PYTEST_UNAVAILABLE
PATCHED_FILE_COUNT = 1
TARGET_FILE = tests/test_step9_63b_mac_local_preflight.py
COLLECTION_SUCCEEDED = NO
TESTS_COLLECTED = NOT_MEASURED
IMPORT_ERRORS = NOT_MEASURED_TEST_MODULE_NOT_IMPORTED
TEST_METHODS_EXECUTED = 0
IDENTITY_GUARD_BYPASSED = NO
FROZEN_MEMBER_CHANGED = NO
HISTORICAL_TRACE_MODIFIED = NO
NEW_R11_FREEZE_CREATED = NO
NEW_AUTHORIZATION_ISSUED = NO
FORMAL_V4_CASE_EXECUTED = 0
READY_FOR_NEXT_SCOPE_REVIEW = NO_COLLECTION_VERIFICATION_PENDING
```
