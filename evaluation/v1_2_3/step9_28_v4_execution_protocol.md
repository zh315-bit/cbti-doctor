# Step 9.28 — V4 execution protocol

The runner is prepared but not authorized. Its only production execution path creates `AdaptiveChatService`, invokes the production `/api/chat` route, leaves the existing Agent Loop and real tool adapters unchanged, captures the recorder trace, and persists raw traces and unscored case results. It has no V4 case-ID branch, expected-action lookup, or benchmark policy.

Formal execution requires a separate human-issued authorization with new `evaluation_id`, `authorization_id`, and `attempt_id`. Before any case read it verifies the final Agent, harness, scoring, metric registry, one-shot rules, runner, manifest, and sealed-dataset hashes; validates a passing local real preflight; and confirms that no V4 attempt ledger exists. Any mismatch fails closed.

On the only permitted run, the runner creates an exclusive append-only ledger, fsyncs `PREPARED`, then fsyncs `FIRST_EVALUATION_ACCESS` before reading the dataset. It fsyncs each per-case `STARTED`, raw trace, unscored result, and completion event. An interruption retains the ledger and partial artifacts. A ledger blocks automatic rerun.

The local preflight may hash the sealed bytes and check the generic schema, but never creates a session from a V4 case, invokes `/api/chat` with V4 input, calls the model for V4, writes an attempt ledger, generates a V4 answer, or produces a V4 score.
