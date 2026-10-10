# Step 9.63c-r5c7d — Mac-local import-context repair

**Status:** `PASS_IMPORT_CONTEXT_REPAIR_OFFLINE_VALIDATED`

The reported error is explained by direct-script import resolution. In the
failed invocation, Python placed the `scripts/` directory at `sys.path[0]`,
not the repository root. The first failing statement was
`from scripts import authorization_lifecycle as lifecycle` in
`_snapshot` (line 198 at the failed revision). Because the parent directory of
the `scripts` namespace package was not on the path, Python raised
`ModuleNotFoundError: No module named 'scripts'` before freeze validation.

The project convention is direct script execution with a deterministic
repository-root bootstrap inside the entrypoint. The formal V3 runner, V3
identity adapter, and Step 9.63b preflight all derive the root from `__file__`
and add it to `sys.path`. The r5c7 wrapper now uses that same minimal bootstrap.
Module invocation from repository root would also supply an import context, but
was not adopted because it differs from the established convention.

Two focused offline tests passed. They reproduce the direct-script `sys.path`
shape, verify `scripts` helper imports and read-only R10 freeze validation, and
compare module/direct-bootstrap identity snapshots. Eighteen related offline
regression tests passed and `py_compile` passed. The tests do not call the
preflight main, network, HTTP, model, Agent, RAG, or V4.

Two files changed (preflight wrapper and test); neither belongs to the 20
members in the r10 freeze. All frozen members still match, so execution
identity did not change and a runner re-freeze is not required. The failed
r5c7c preflight identity remains retired from use; any later preflight must use
a new invocation ID. This audit does not claim a real Mac-local preflight
passed and does not authorize formal execution.
