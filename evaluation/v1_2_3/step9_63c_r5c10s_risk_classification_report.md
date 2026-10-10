# Step 9.63c-r5c10s — B2 risk classification

This is a static, read-only review of the **remaining 11 modules**. No collection-only or test execution occurred in this step. The [module matrix](step9_63c_r5c10s_remaining_modules_dependency_matrix.json) records their current hashes, exact import routes, 174 static `def test_` definitions, collection-time behavior and execution risks. Those definitions are neither collected nor passed counts. The historical 12-module import failure and the r5c10r one-module success remain distinct observations.

Classification is about a **safe scoped collection patch**, not a promise that all methods will execute or pass:

- **A — 2:** `test_step9_63c_r3_parent_namespace_repair.py` and `test_step9_63c_r5c7b_diagnostics.py`. Each has a bounded, single-test-file import deferral that can expose independent methods. The former still has synthetic `parent.run`/case-start paths; the latter has four transport-dependent methods that should remain unexecuted without formal identity. These risks determine the next batch choice.
- **B — 0:** Static inspection did not prove that any module necessarily needs two non-frozen test files or a shared test helper changed. Zero is not a claim that all others are one-file-ready.
- **C — 1:** `test_step9_63a_r3_authorization_issuance.py` has the **frozen issuer** on its transitive import/runtime path. Method-local deferral may permit collection, but it cannot establish safe issuance-test execution. This category flags separate issuer-boundary review; it does not claim an issuer edit is unavoidable.
- **D — 8:** Global adapter-derived constants, shared helpers, all-method live identity setup, formal runner paths or r8/current preflight coupling make a test-only collection patch **unproven as a safe scoped repair**. Several can plausibly be made collectable within one file, but that is not yet verified or approved.

The common first trigger remains frozen adapter import → `load_identity_config(ROOT)` → missing formal r11 pointer. Import-time reading is not required for discovery, but the real identity, authorization, provenance and one-shot guards **must remain active at runtime**. A collected method may still be identity-blocked. None of these classes authorizes a fake r11 pointer, r10 fallback, skip/xfail, production/frozen edit or formal execution.

No direct write to the two named historical Trace paths was found in the 11 test files. Several write synthetic markers, journals, manifests or traces in `TemporaryDirectory`; `test_step9_63c_r5b_preflight_lifecycle.py` also reads a historical legacy preflight artifact. This static finding does not license running them; each future selected method needs a path/network/commit audit and before/after evidence check.
