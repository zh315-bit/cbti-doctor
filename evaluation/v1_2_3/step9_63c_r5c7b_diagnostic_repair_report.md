# Step 9.63c-r5c7b — Diagnostic instrumentation repair

**Status:** `PASS_DIAGNOSTIC_REPAIR_OFFLINE_VALIDATED`

The preflight retains fail-closed behavior and now emits a stable stage label,
exception type, and sanitized message. Stage tracking covers configuration,
project/venv, authorization/lifecycle, r10 and frozen identity checks,
historical pins, target collision, each DNS resolver, TCP, TLS/certificate
validation, serialization, and artifact writing. The transport helper only
adds an optional stage callback around its existing operations; it does not
send any additional request or change probe ordering.

The presence check now uses only `bool(os.environ.get("DEEPSEEK_API_KEY"))`.
The existing `load_dotenv(absolute_path, override=False)` configuration
behavior is retained if the preflight is run in a separately authorized later
step. `dotenv_values()` and direct `.env` reads are absent from this repair.
Exception sanitization covers credential assignments, Authorization/Bearer
tokens, common token/password/secret forms, URLs with userinfo, and complete
request-header blocks; no traceback or environment dump is produced.

Validation: 13 focused synthetic tests passed; 33 applicable offline regression
tests passed; `py_compile` passed. Tests mock resolver, TCP, TLS, and file-write
failures. An exploratory unfiltered regression run exposed one stale
pre-issuance assertion (`test_18_active_count_is_zero`) that expects zero active
authorizations despite the intentionally active r5c6 authorization; this test
was excluded from the final applicable selection and is documented in the
audit.

Neither changed preflight file is an r10 freeze member. All 20 frozen members
still match, so runner execution identity is unchanged and a runner re-freeze
is not required. The r5c6 authorization remains unconsumed; no attempt,
namespace, transaction, network request, inference, or V4 case was created or
run. The r5c7a process-boundary incident is recorded as
`DOTENV_VALUES_PARSED_DURING_READ_ONLY_FORENSICS`; no secret was printed,
persisted, or known to be disclosed.

No Mac-local preflight was rerun. This report does not authorize a retry or
formal execution.
