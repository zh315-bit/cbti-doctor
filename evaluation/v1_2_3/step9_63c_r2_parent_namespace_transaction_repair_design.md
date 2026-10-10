# Step 9.63c-r2 — Parent namespace / transaction boundary repair design

Status: `PASS_DESIGN_ONLY_READY_FOR_R3_IMPLEMENTATION`. No production code, frozen input, authorization, attempt, transaction journal, namespace, result or trace was changed. The Step 9.63c invocation count remains one and rerun remains forbidden. The old transaction is `COMMITTED`, while case starts/completions and model/Agent/RAG calls remain zero, as frozen by Step 9.63c-r1.

## 1. Actual production order

| Order | Code | Operation | Class |
|---|---|---|---|
| 1 | `run_step9_63_v3_formal_execution.py:93-130` | Validate r7 formal entry, authorization/preflight shapes and CLI hashes; call adapter | READ_ONLY |
| 2 | `run_step9_53_v3_identity_adapter.py:650-666` | Derive `namespace_id` and `candidate_root`; validate frozen identity and parent authorization with explicit candidate root | READ_ONLY |
| 3 | `run_step9_53_v3_identity_adapter.py:675-703`, `v3_execution_transaction.py:187-228` | Revalidate under shared lock; append/fsync `PREPARED`, `COMMITTING`, `COMMITTED` | DURABLE_WRITE + AUTHORIZATION_STATE_CHANGE (irreversible identity burn at `COMMITTED`) |
| 4 | `run_step9_53_v3_identity_adapter.py:704-708`, `v3_namespace_allocator.py:61-115` | Require exact commit; exclusively create derived container and fsynced reservation marker | RESERVATION + DURABLE_WRITE |
| 5 | `run_step9_53_v3_identity_adapter.py:731-735` | Rebind `parent.OUT_ROOT` to `candidate_root`; call `parent.run` with transaction ID | READ_ONLY process-local binding |
| 6 | `run_step9_35a_matched_treatment.py:363-364,236-328` | First parent validation; `run_root` omitted, so definition-time global default is used; historical `run_root/evaluation_id` triggers collision | READ_ONLY; **actual failure** |
| 7 | `run_step9_35a_matched_treatment.py:370-405` | If step 6 passed: append `ATTEMPT_CLAIMED`, create inner output directory and exclusive attempt ledger; later append `AUTHORIZATION_CONSUMED` and `FIRST_EVALUATION_ACCESS` | DURABLE_WRITE + RESERVATION; not reached in failed run |
| 8 | `run_step9_35a_matched_treatment.py:443-488` | Verify exact committed transaction and case set; per case append transaction `CASE_STARTED`, then enter production `_case_result` | CASE_EXECUTION_BOUNDARY; not reached in failed run |

The authoritative transaction commit is step 3, **before** physical namespace reservation and parent validation. The parent collision check is step 6. The first case execution boundary is step 8, after the transaction `CASE_STARTED` event and attempt-ledger `STARTED` event. `COMMITTED` means the execution identity has been irrevocably claimed and authorization burned; it does **not** mean an attempt directory or ledger exists, a namespace reservation is complete, any case ran, or evaluation finished. This follows the frozen atomic commit contract's `commit_point` and `committed_pre_claim` rules. A future audit may display the explanatory label `EXECUTION_IDENTITY_COMMITTED`, but must retain the frozen `COMMITTED` event name and never rewrite old journals.

## 2. Identity and namespace semantics

| Identity/path | Producer → consumer | Collision rule and lifecycle | Uniqueness scope |
|---|---|---|---|
| `evaluation_id` | Frozen V3 contract → CLI, adapter, parent | Names the same 40-case evaluation across attempts; reuse of this *family label* is not itself a collision | Evaluation family, not an attempt |
| `authorization_id` | Fresh issuer → manifest, transaction journal, lifecycle/parent | Prior retirement, journal or use is terminal; this ID is burned by durable `COMMITTED` | Globally unique authorization |
| `attempt_id` | Fresh issuer → manifest, journal, reservation, ledger/results | Any prior claim, reservation or ledger use fails closed | Globally unique attempt |
| `namespace_id` | `derive_namespace_id(evaluation_id, authorization_id, attempt_id)` → journal, allocator, adapter, parent | Existing container, marker or journal binding fails for a **new** attempt; after commit only the exact matching transaction may own it | Attempt-scoped under `evaluation/v4_runs` |
| Parent `run_root` | Legacy default at function definition is global `evaluation/v4_runs`; adapter later rebinds `parent.OUT_ROOT` | Parent checks `run_root/evaluation_id`; this wrongly treats an old evaluation family directory as the fresh attempt's output | Currently global (defect) |
| Transaction namespace | Allocator → adapter/parent | `evaluation/v4_runs/<namespace_id>` is exclusive and reservation marker binds exact auth/attempt/transaction; never clean up old failed container | One attempt |
| Case output path | Parent → attempt ledger, result/trace writer | `evaluation/v4_runs/<namespace_id>/<evaluation_id>/`; inner directory and files use exclusive creation and no overwrite | One attempt within its container |

`GLOBAL_RUN_ROOT_COLLISION_SEMANTICS=YES` in the current parent validator. `ATTEMPT_SCOPED_NAMESPACE_SEMANTICS=YES` in the current r7 transaction/allocator. Both coexist, causing the bug: the fresh derived namespace did not collide, but `validate_authorization(run_root=OUT_ROOT)` retained the definition-time global `OUT_ROOT`. Rebinding the module variable later does not change that default argument. Thus the guard tested the September 30 historical `evaluation/v4_runs/<evaluation_id>` directory, **not** the newly reserved `evaluation/v4_runs/<namespace_id>/<evaluation_id>` path. The transaction did not create the path that raised this exception.

## 3. Machine-checkable invariant and authority

For each *new* formal attempt, compute `N = derive_namespace_id(E, A, T)` once with the frozen allocator. Require `A` and `T` globally fresh; no prior journal for `A`, no marker/ledger for `A` or `T`, and no `evaluation/v4_runs/N` before commit. Under the shared transaction lock, commit `(transaction_id, A, T, N, runner, Agent, evaluation, case_set)` exactly once. After commit, all parent calls must require that exact journal tuple; reservation marker must bind the same tuple, and parent `run_root` must equal the canonical `evaluation/v4_runs/N`. The **only** parent collision target is `run_root/E`. It must not exist before exclusive creation, and ledger/results/traces must each use exclusive creation. An existing `evaluation/v4_runs/E` belonging to a historical attempt is irrelevant unless it is the current canonical `run_root/E` (which it is not).

Formal predicate, with `R = canonical(global_root/N)`: `precommit_fresh(A,T,N) ∧ commit_exact(tx,A,T,N,pins) ∧ marker_exact(R,tx,A,T,N) ∧ parent_root == R ∧ ¬exists(R/E) ∧ no_current_attempt_ledger_or_outputs(A,T)`. After the parent creates `R/E`, revalidation must use a phase-aware guard that accepts only the **same** transaction's directory and ledger, never an arbitrary pre-existing path. Each `CASE_STARTED` remains append-only, ordinal/ID unique, and requires `COMMITTED` plus `ATTEMPT_CLAIMED`. Symlinks, missing/corrupt markers, mismatched owner identities, duplicate commit or output paths fail closed. No guard is disabled.

The transaction journal is the authority for the committed identity and burn decision; the allocator marker is its exact physical reservation evidence; the parent consumes **that** resolved path and performs the final exclusive inner-directory/output check. The parent must not choose an independent global namespace. The lifecycle manifest's `consumed=false` is not sufficient to restore executability after a journal exists.

## 4. Repair options

| Option | Correctness / exactly-once | Crash recovery / history | Scope / risk |
|---|---|---|---|
| **A. Explicit transaction-resolved parent root (recommended)** | Parent validates journal+marker tuple and uses exactly `R`; retains exclusive directory/file and case guards | Preserves frozen commit ordering, burned identities and all old paths | Focused parent + adapter integration changes; must refreeze runner/entry and use fresh authorization |
| B. Parent delegates every collision check to a new transaction API | Can centralize policy but risks hiding final filesystem/output overwrite checks | New API/state semantics enlarge recovery proof | More code and wider validation surface |
| C. Delay commit until after parent validation | A precommit validation already exists and passed in the failed run; without root alignment it changes nothing | Alters frozen commit point and crash matrix; dangerous window before durability | High protocol and refreeze risk; not recommended |
| D. Disable parent collision check / clear historical directory | Breaks overwrite and one-shot protection | Destroys or weakens evidence | Forbidden |

Recommended A is **not** a one-line suppression. The parent transaction branch must require an explicitly resolved attempt root equal to the committed `namespace_id`, verify matching reservation ownership, and pass that root through both validator calls and all physical output writes. The adapter passes the same root rather than relying on `parent.OUT_ROOT` rebinding; its independent binding-loader override may remain only for frozen identity validation. Precommit checks continue to reject any fresh-ID collision. Postcommit checks are phase-aware for the exact current transaction. The direct parent CLI must either resolve the same committed root or fail closed, never fall back to global output. An implementation that merely changes a default parameter without proving the output-write path and journal tuple match fails acceptance.

## 5. Failure atomicity and disposition design

| Point | Authorization / transaction | Attempt / namespace | Rerun? | Recovery and future identity |
|---|---|---|---|---|
| F1 before any durable journal or physical reservation | Manifest `ISSUED_NOT_CONSUMED`; no transaction | No attempt; namespace absent | No automatic rerun | Read-only audit; any future formal execution after an invoked/failed command requires a separately justified fresh auth/attempt/namespace |
| F1a after `PREPARED` or `COMMITTING`, before reservation | Journal exists; frozen contract distinguishes abortable `PREPARED` from `COMMITTING` that must be resolved to commit | No physical attempt/namespace yet | **No** | Preserve journal; manual, contract-governed reconciliation only in a separately authorized phase; neither state permits silently reusing the same ID |
| F1b after `COMMITTED` but before reservation | Manifest may still say unconsumed; journal burned | No marker or attempt | **No** | Preserve journal; manual fail-closed disposition, no old-ID reuse; fresh identity after repair/authorization decision |
| F2 after reservation before commit | **Unreachable in current/recommended commit-before-reserve order**; if observed, protocol violation | Orphan marker | **No** | Manual forensic classification; never delete marker to rerun; fresh identity only after a separate decision |
| F3 after commit, before parent validation (current incident's window) | `COMMITTED` and irreversibly burned | Matching marker may exist; no attempt ledger/case | **No** | Preserve both artifacts; do not execute old transaction even if generic reconciler labels it ready; repair code then fresh authorization and IDs |
| F4 after parent validation, before first case | `COMMITTED`; possibly `ATTEMPT_CLAIMED` and durable consumption event | Inner directory/ledger may be partial; no `CASE_STARTED` | **No** | Preserve partial state; deterministic read-only classification; no automatic continuation or deletion |
| F5 during case execution | `COMMITTED`; per-case `CASE_STARTED` | Append-only ledger/results/traces may be partial | **No** | Preserve partial artifacts and mark failure; no case retry or overwrite |
| F6 all cases finished, before final result event | `COMMITTED`; all case events may exist, final `COMPLETED` uncertain | Preserve full/partial output | **No** | Read-only completeness audit; any append-only finalization needs separately proven frozen authority, never a case rerun |

For F3–F6, a fresh authorization is **necessary but not sufficient** for any future *new* formal execution: a separate protocol decision must first establish that the case set may legitimately be evaluated again. The old Step 9.63c authorization `auth-step9_63a_r3-d53bbaa35b1e4522bc4a5f57d42c8ef7`, attempt `attempt-step9_63a_r3-3b66e84b7b1f4f538e87156c85b0e7dd`, committed journal and reserved namespace remain immutable historical failure evidence. `OLD_AUTHORIZATION_REUSED=NO`, `OLD_ATTEMPT_ID_REUSED=NO`, `OLD_TRANSACTION_DELETED=NO`, `OLD_NAMESPACE_DELETED=NO`. No reconciliation is authorized in this design step.

## 6. Minimal implementation boundary for Step 9.63c-r3

| File | Function | Current responsibility | Required change | Risk |
|---|---|---|---|---|
| `scripts/run_step9_35a_matched_treatment.py` | `validate_authorization`, `run` | Validate transaction/authorization and check/create output | Require transaction-resolved `run_root` for transaction execution; prove it equals journal `namespace_id` and marker owner; use it for both validations, exclusive `out` creation and fsync/output paths; keep collision guard | Highest: path escape/overwrite if root check is weak |
| `scripts/run_step9_53_v3_identity_adapter.py` | `run` | Derive/reserve namespace, invoke parent | Pass the exact committed/reserved candidate root explicitly to parent; remove reliance on mutable `parent.OUT_ROOT` for output selection | Moderate: adapter/parent binding drift |
| `scripts/run_step9_63_v3_formal_execution.py` (or a new versioned entry) | formal entry identity pin | Bind frozen runner revision and preflight | Point **future** execution to a new repaired runner freeze and fresh preflight/authorization; old r7 entry remains unavailable for this committed attempt | Moderate: identity/version mismatch if old pin retained |

No Agent, V4 dataset, scoring, rubric, metric-registry, RAG, model, case set/order or evaluation-semantic change is required. `V3_AGENT_MODIFICATION_REQUIRED=NO`, `V4_MODIFICATION_REQUIRED=NO`, `SCORING_MODIFICATION_REQUIRED=NO`, `METRIC_REGISTRY_MODIFICATION_REQUIRED=NO`. Changed runner/parent/entry hashes necessarily supersede r7 for **future** execution: create a new infrastructure freeze and fresh candidate/authorization binding per protocol, never claim the old r7 freeze still matches or migrate/burn-reuse the old authorization. Preserve old journal/marker and all historical artifact hashes.

## 7. Synthetic regression design (do not run in this step)

1. Historical global `evaluation/v4_runs/E` exists; fresh `(A,T,N)` resolves `R/N/E` absent → parent precommit and postcommit checks accept; old directory unchanged.
2. Same `attempt_id` appears in journal/marker/ledger → fail closed before new commit or output.
3. Same `namespace_id` directory or marker already exists → fail closed, no overwrite.
4. Same `authorization_id` has any journal state or retirement → fail closed, even if manifest still says unconsumed.
5. Two concurrent contenders for the same `(A,T)` → exactly one COMMITTED winner; loser creates no attempt/case output.
6. Two distinct fresh attempts in one historical evaluation family → no false global-root collision; each isolated under a different derived namespace.
7. COMMITTED with zero `CASE_STARTED` (including the observed marker-only shape) → immutable burned disposition; no silent reuse or automatic resume.
8. Existing result directory or file under current `R/N/E` → fail closed; bytes and historical outputs unchanged.
9. Crash at/after reservation with matching/mismatching marker → deterministic classification; no marker deletion or automatic case restart.
10. Crash after COMMITTED before first case, with absent or partial attempt ledger → deterministic fail-closed disposition; old auth/attempt remain non-reusable.
11. Every parent validator/output call resolves the same `R/N` as the journal, allocator and marker; wrong `run_root`, symlink, or foreign owner fails.
12. Static/synthetic call-graph test: no direct parent/adapter/CLI path reaches case execution without committed journal, claimed attempt, exact marker/root and per-case `CASE_STARTED`.

## 8. Acceptance gate

Step 9.63c-r3 may claim implementation readiness only after synthetic tests pass with zero failures/errors and a new runner freeze pins the repaired code. Required assertions: `TRANSACTION_PARENT_NAMESPACE_SEMANTICS_ALIGNED=YES`, `GLOBAL_HISTORICAL_ROOT_FALSE_COLLISION=NO`, `FRESH_ATTEMPT_NAMESPACE_REQUIRED=YES`, `FRESH_AUTHORIZATION_REQUIRED=YES`, `EXACTLY_ONCE_GUARD_PRESERVED=YES`, `CRASH_RECOVERY_PRESERVED=YES`, `HISTORICAL_ARTIFACTS_PRESERVED=YES`, `V3_AGENT_UNCHANGED=YES`, `V4_UNCHANGED=YES`, `EVALUATION_SEMANTICS_UNCHANGED=YES`. Also require no case-specific branch, no guard weakening, no old-ID reuse, all historical pins match, and old COMMITTED journal/namespace remain byte-for-byte unchanged. Only then may a separate lifecycle/authorization decision begin; this design neither issues it nor grants permission to run V4.
