"""Step 9.63c-r5c10ak: test_step9_58a_r1_namespace_allocator runs UNCHANGED on a temporary mirror of the repository.

The original module (archived as tests/retired/test_step9_58a_r1_namespace_allocator.py.retired) exercised production code whose default paths point
at the real activation state (ledger, run root, authorization manifests, namespace lock). Here it runs
inside a private copy (tests/legacy_isolation.py); the methods listed in RETIRED are not run, and their
properties are covered where the mapping says (evaluation/v1_2_3/step9_63c_r5c10ak_coverage_mapping.json).
"""
import legacy_isolation

RETIRED = {
    "NamespaceAllocatorTests.test_reserved_fresh_namespace_requires_transaction_for_post_first_case_guard": "tests/test_step9_63c_r5c10ak_legacy_rewrites.py::Rewritten58a.test_reserved_fresh_namespace_requires_transaction_for_post_first_case_guard (same body, synthetic temporary root)"
}

legacy_isolation.make_module(globals(), 'test_step9_58a_r1_namespace_allocator', retired=RETIRED)
