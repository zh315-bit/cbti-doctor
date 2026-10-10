# Step 9.63c-r5c10m — 12 module-import blockers

All 12 observed import placeholders share one earliest failing production call: `scripts/run_step9_53_v3_identity_adapter.py:25` calls `load_identity_config(ROOT)` during module import. `scripts/v3_runner_identity.py:11–13,27–30` requires the exact formal r11 pointer; its absence correctly fails closed. The adapter is an unchanged r10 frozen member. No test method in a blocked module was collected, so downstream outcomes remain unknown.

| Blocked test module | Static import route to adapter | Boundary classification |
|---|---|---|
| `test_step9_53_v3_identity_adapter.py` | direct test import, line 7 | Fixture isolation conceivable; not yet proven |
| `test_step9_55a_namespace_lifecycle.py` | direct, line 8 | Same |
| `test_step9_58a_r1_namespace_allocator.py` | direct, line 8 | Same |
| `test_step9_59a_auth_identity_binding.py` | direct, line 9 | Same |
| `test_step9_63a_r1_production_integration.py` | direct, line 15 | Same |
| `test_step9_63a_r2_retirement_eligibility.py` | direct, line 13 | Same |
| `test_step9_63a_r3_authorization_issuance.py` | test line 10 → frozen `scripts/issue_step9_63a_r3_authorization.py:17` → adapter | Test-only fixture may be insufficient if issuer import validates the live root |
| `test_step9_63b_mac_local_preflight.py` | test line 12 → frozen `scripts/preflight_step9_63b_mac_local.py:30` → adapter | Same transitive risk |
| `test_step9_63c_r3_parent_namespace_repair.py` | direct, line 19 | Fixture isolation conceivable; not yet proven |
| `test_step9_63c_r5_mac_local_preflight.py` | test line 12 → frozen r8 preflight wrapper → current preflight; also transport import line 12 → adapter | Transitive path is present before synthetic fixtures execute |
| `test_step9_63c_r5b_preflight_lifecycle.py` | test line 15 → transport → adapter; also direct formal runner import | Same |
| `test_step9_63c_r5c7b_diagnostics.py` | test line 11 → transport → adapter; r10 preflight later imports adapter at lines 305–306 | Same |

**Classification:** None has been proven solvable by test-only fixture isolation. No distinct unfrozen-infrastructure defect has been demonstrated. If pre-import temporary fixture setup cannot safely isolate the historical version, moving the eager read in the frozen adapter to its invocation boundary would require a separate frozen-member/identity-contract approval and revalidation; it is not authorized here. No r10 fallback, fake formal r11 pointer, or weakened SHA/provenance guard is acceptable. The exact count of additional method-level failures after collection is **unknown**, not zero.

The current producer's `scripts/preflight_step9_63c_current_mac_local.py:30–35` imports the adapter when validating an authorization, rather than at module import; this is not evidence that the frozen adapter is safe to change. The current formal runner imports it at execution validation stages (`scripts/run_step9_63_v3_formal_execution.py:222,270,417`). A prospective lazy-resolution design must independently prove missing/invalid r11 identity still fails before authorization consumption, transaction creation, or `adapter.run()`.
