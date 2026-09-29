# Step 9.8e — Frozen Run Authorization State Fix (Design Only)

## Problem

The current guard treats a manifest as proof that a frozen run was consumed.
That is safe against accidental overwrite, but it conflates frozen-input
preparation with actual benchmark execution. Step 9.8 and Step 9.8b demonstrate
the ambiguity: both preserve valid manifests, while neither produced a case
result, trace record, or score.

This document is a design only. It authorizes no run and changes no code.

## Minimal boundary

Keep the existing manifests immutable and untouched:

- `step9_8_freeze_manifest.json`
- `step9_8b_freeze_manifest.json`

Add a separate, append-only attempt ledger (for example
`step9_8_execution_attempts.jsonl`). A manifest identifies frozen inputs; an
attempt record identifies what actually happened after authorization.

## Proposed attempt contract

Each append-only record should include:

```json
{
  "attempt_id": "unique immutable id",
  "manifest_reference": "path and SHA-256",
  "benchmark_sha256": "...",
  "rubric_sha256": "...",
  "authorization_reference": "human-approved run identifier",
  "status": "PREPARED | STARTED | COMPLETED | FAILED_BEFORE_FIRST_CASE | FAILED_DURING_FIRST_CASE_BEFORE_RESULT | FAILED_AFTER_PARTIAL_EXECUTION | BLOCKED_BY_MANIFEST_GUARD",
  "created_at": "UTC timestamp",
  "started_at": "UTC timestamp or null",
  "first_case_started_at": "UTC timestamp or null",
  "ended_at": "UTC timestamp or null",
  "completed_case_count": 0,
  "raw_trace_path": "path or null",
  "raw_trace_record_count": 0,
  "score_path": "path or null",
  "failure_reference": "sanitized exception/report reference or null"
}
```

The `FAILED_DURING_FIRST_CASE_BEFORE_RESULT` state is deliberate. It records
Step 9.8b more precisely than “before first case”: a request began, yet no
completed case result exists.

## State transitions and durability

```text
immutable manifest validated
        ↓
PREPARED (authorization recorded)
        ↓
STARTED (durably record attempt before first user turn)
        ↓
first_case_started_at recorded
        ↓
case result atomically written + trace flushed + completed_case_count incremented
        ↓
COMPLETED | FAILED_AFTER_PARTIAL_EXECUTION

No returned case result:
FAILED_BEFORE_FIRST_CASE | FAILED_DURING_FIRST_CASE_BEFORE_RESULT
```

The runner should write the `STARTED` event before sending input to the model,
then atomically persist each returned case result before advancing. This makes
partial execution unambiguous and prevents a crash from looking like an unused
manifest.

## Guard decision rule

The guard should inspect both the immutable frozen-input hashes and the
append-only attempt ledger:

1. Refuse if a prior attempt has `COMPLETED`, any `completed_case_count > 0`,
   a non-empty valid trace, or a valid score/result artifact.
2. Refuse if an attempt is still `STARTED`; require explicit human recovery,
   not automatic retry.
3. Permit a **new explicitly authorized attempt only** when all previous
   attempts have zero completed results/trace records/scores, are terminal
   failure or guard-block states, and benchmark/rubric hashes exactly match.
4. Persist the new `PREPARED`/`STARTED` records before any case starts.

This remains stricter than a normal retry loop: a new attempt needs a distinct
human authorization reference and cannot be created merely because an old
manifest exists. It neither deletes history nor permits arbitrary repeated
runs.

## Non-goals and invariants

- No Agent, tool, DependencyResolver, policy, model, or answer behavior changes.
- No Benchmark V2 or scoring-rubric change.
- No case-specific behavior.
- No change to frozen hashes.
- No deletion, overwrite, rename, or reinterpretation of historical manifests,
  reports, or the zero-byte raw-file container.

## Acceptance checks before any future implementation

1. Legacy manifest-only history is migrated by **adding** ledger entries, not
   editing manifests.
2. Step 9.8 is represented as `FAILED_BEFORE_FIRST_CASE`.
3. Step 9.8b is represented as
   `FAILED_DURING_FIRST_CASE_BEFORE_RESULT`, `completed_case_count=0`.
4. The user-reported local block is represented as
   `BLOCKED_BY_MANIFEST_GUARD`, `completed_case_count=0`, `MODEL_CALLS=0`.
5. A test proves a non-empty trace/result blocks a second run.
6. A test proves a zero-result terminal failure does not itself imply
   consumption, but still requires new explicit authorization.

