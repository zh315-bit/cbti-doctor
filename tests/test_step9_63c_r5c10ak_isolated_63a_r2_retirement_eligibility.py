"""Step 9.63c-r5c10ak: test_step9_63a_r2_retirement_eligibility runs UNCHANGED on a temporary mirror of the repository.

The original module (archived as tests/retired/test_step9_63a_r2_retirement_eligibility.py.retired) exercised production code whose default paths point
at the real activation state (ledger, run root, authorization manifests, namespace lock). Here it runs
inside a private copy (tests/legacy_isolation.py); the methods listed in RETIRED are not run, and their
properties are covered where the mapping says (evaluation/v1_2_3/step9_63c_r5c10ak_coverage_mapping.json).
"""
import legacy_isolation

RETIRED = {
    "SupersededRetirementTests.test_active_authorization_count_becomes_zero": "tests/test_step9_63c_r5c10ai_final_form_and_tokens.py::FinalFormSequence (after activation the active set is exactly [the r11 authorization]); tests/test_step9_63c_r5c10ah_retire_entry.py::WriteTests.test_success_appends_exactly_one_approved_line_and_nothing_else",
    "SupersededRetirementTests.test_retired_auth_cannot_enter_prepared_committing_or_committed": "tests/test_step9_63c_r5c10ak_isolated_63a_r2_retirement_eligibility.py::test_SupersededRetirementTests__test_retired_auth_cannot_enter_new_transaction; tests/test_step9_63c_r5c10ak_isolated_r5c5b_lifecycle_reducer.py::test_LifecycleReducerTests__test_10_retirement_and_transaction_conflict_fail_closed"
}

legacy_isolation.make_module(globals(), 'test_step9_63a_r2_retirement_eligibility', retired=RETIRED)
