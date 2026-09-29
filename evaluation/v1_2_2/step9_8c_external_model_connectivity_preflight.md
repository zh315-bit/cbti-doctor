# Step 9.8c — External Model Connectivity Preflight

## Read-only configuration

| Setting | Observed value |
| --- | --- |
| Provider configuration | DeepSeek-compatible OpenAI endpoint |
| Model | `deepseek-flash` |
| Endpoint | `https://api.deepseek.com` |
| Model environment variables | `DEEPSEEK_MODEL`, `DEEPSEEK_BASE_URL` |
| Credential environment variable | `DEEPSEEK_API_KEY` |
| Credential | PRESENT (value not inspected or recorded) |

No model, provider, endpoint, or credential was changed.

## Preflight matrix

| Check | Result |
| --- | --- |
| Credential present | PASS |
| DNS resolution | FAIL |
| HTTPS connectivity | NOT_RUN |
| Endpoint reachable | NOT_RUN |
| Minimal real model probe | NOT_RUN |
| LLMInputUnderstander smoke | NOT_RUN |

## Blocking diagnosis

```text
FIRST_BLOCKING_POINT = DNS resolution for api.deepseek.com
ROOT_CAUSE_CLASS = DNS
Sanitized error = gaierror: [Errno 8] nodename nor servname provided, or not known
```

The DNS check used the configured endpoint's hostname and failed before any TCP
or HTTPS connection was attempted. Per protocol, no model request was sent, no
provider response was requested, and no Benchmark case or fixture was used.

## Preserved experiment history

* Step 9.8 remains `RUN_INITIALIZATION_FAILURE` (0/40 cases).
* Step 9.8b remains `RUN_ENVIRONMENT_FAILURE` (0/40 case results).

Neither record was changed, deleted, or reinterpreted. This preflight produces
no Benchmark score and does not authorize a Benchmark rerun.
