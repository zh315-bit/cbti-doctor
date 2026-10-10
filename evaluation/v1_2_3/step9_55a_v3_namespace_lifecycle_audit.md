# Step 9.55a — V3 Runner Namespace Lifecycle Repair

Status: `PASS_INFRASTRUCTURE_REPAIR_ONLY`

## Root cause and lifecycle

The frozen parent runner validates authorization and requests `current_frozen_bindings()` before it creates the attempt namespace. It then creates the namespace and exclusive ledger, durably records `PREPARED`, `AUTHORIZATION_CONSUMED`, and `FIRST_EVALUATION_ACCESS`, reads and verifies the benchmark case set/order, records `CASE_SET_AND_ORDER_VERIFIED`, and requests fresh bindings once more immediately before constructing the production service and starting case 1.

The identity adapter previously treated both binding requests as pre-attempt checks. Its namespace-absence guard is correct before attempt creation (collision prevention), but incorrect at the parent's second callback, when the exact authorized attempt namespace is supposed to exist. The one-shot ledger and old consumed authorization show Step 9.55 stopped at this boundary: no case started and no result/trace files were created.

## Repair

The adapter now uses phase-aware checks:

- `PRE_ATTEMPT`: namespace must be absent; fresh authorization/attempt IDs must be paired, valid, unconsumed, bound to the evaluation identity, and unused in other ledgers.
- `POST_ATTEMPT_CREATION_PRE_FIRST_CASE`: namespace must be a real directory, with the exact current authorization and attempt identity; the ledger must contain exactly the parent-created four-event prefix; all ledger identities and frozen hashes must match; case counters remain zero; no result/raw-trace or other output exists; no completion or duplicate identity exists.

The adapter's parent callback sequencing is explicit: its first call validates `PRE_ATTEMPT`; its second validates `POST_ATTEMPT_CREATION_PRE_FIRST_CASE`. Exactly-once and namespace collision checks remain enabled. The original Step 9.53 r2 freeze and contract were not edited. Step 9.55a introduces a compact future-identity overlay and a new freeze, superseding r2 only for a future identity; the consumed old authorization and failed attempt cannot be reused.

## Verification

- Synthetic lifecycle coverage: all 12 required conditions covered, PASS.
- Focused standard-library unittest regression: 51/51 PASS (`Step 9.55a lifecycle`, including callback phase order; `Step 9.53 identity adapter`, `Step 9.35a runner`, `Step 9.50 traceability`).
- Identity-only preflight: all frozen hashes, parent lineage, model configuration identity and lifecycle checks PASS; authorization remains `NOT_ISSUED`.
- V3 Agent inventory SHA-256 before and after: `085d338ed95bbef7370c41cf97ca0d6653ffdfd2f1c924eef4b7123dfdea4607`.
- Historical failed Step 9.55 ledger SHA-256 remains `57967d950a3a4c700f3187e3d495ca39b4e01d5700ef31a9ebe36c3380450de6`; the authorization manifest/audit/report/freeze hashes are unchanged.
- No Agent, benchmark, parent runner, harness, scoring/rubric, metric registry, one-shot rules, or evaluation semantics changed.

No authorization or attempt was issued/created. No V4 case was executed; no formal model/Agent/RAG case call, result, trace, score, adjudication, aggregation, comparison, or V5 access occurred. A separate authorization step is required before any future formal attempt.
