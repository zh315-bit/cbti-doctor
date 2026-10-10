# Step 9.63c-r5c10n — remaining blockers and decision boundary

- The two trace files have no trusted pre-r5c10l byte hashes. Their current hashes are preservation pins only; original content integrity remains `CONTENT_INTEGRITY_UNPROVEN`. A test-output redirect cannot retroactively repair that provenance gap.
- The proposed two-file patch has not been implemented or tested. Its temporary-root guard, test result semantics and protected-root no-write behavior still need offline verification after separate approval.
- Twelve historical modules still fail import before method collection because the unchanged frozen adapter resolves the missing formal r11 pointer at import time. This plan does **not** modify that adapter or create a fake pointer. Whether all 12 can be isolated in non-frozen tests remains unproven.
- The six-cluster fixes are separate from the two trace-writer patch. C1/C3/C5 are candidate test-only repairs, C4/C6 require archival/current contract decisions, and C2 could require a new frozen-member scope decision. No full-regression green claim or r11 freeze readiness follows from this patch plan.
- A future broad regression run requires a prior write-path inventory. The existing Step 9.51a selector explicitly excludes the two historical writer modules, but that narrow selector is not the requested full regression.

Decision offered for human review: approve only the two non-frozen test-file redirects and scoped offline validation, with historical trace bytes protected. Do not approve production/frozen code changes, authorization operations, preflight or V4 under this plan.
