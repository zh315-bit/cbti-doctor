# Step 9.8 — Local Execution Instructions

## Why local execution is required

The current Work environment cannot resolve either `example.com` or
`api.deepseek.com`. A real-model Benchmark V2 run therefore needs a local
terminal with working DNS and outbound HTTPS. This document does not alter the
Agent, Benchmark, scoring, provider, or runner.

## Preconditions

1. Copy the project to a separate local directory. Keep the current workspace
   untouched so its Step 9.8 / 9.8b failure records remain preserved.
2. Use Python 3.12 and the existing project virtual environment/dependencies.
3. Ensure the copied project's `.env` provides, without printing it:
   `DEEPSEEK_API_KEY`, optionally `DEEPSEEK_MODEL`, and optionally
   `DEEPSEEK_BASE_URL`.
4. Confirm local DNS and HTTPS can reach `api.deepseek.com` before running.

## Prepare an isolated local output directory

The Step 9.8b runner intentionally refuses a second run in an output directory
that already has a frozen-run manifest. In the copied checkout, archive the
copied evaluation output rather than deleting it:

```zsh
cd /path/to/local/cbti-doctor-main
mv evaluation/v1_2_2 evaluation/v1_2_2_work_history
mkdir -p evaluation/v1_2_2
```

This does not alter the original workspace or its historical records.

## Verify local configuration without exposing credentials

```zsh
.venv/bin/python - <<'PY'
import os, socket
from pathlib import Path
from urllib.parse import urlparse
from dotenv import load_dotenv
load_dotenv(Path('.env'))
endpoint = os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')
host = urlparse(endpoint).hostname
print('credential=' + ('PRESENT' if os.getenv('DEEPSEEK_API_KEY') else 'MISSING'))
print('model=' + os.getenv('DEEPSEEK_MODEL', 'deepseek-flash'))
print('endpoint=' + endpoint)
print('dns=' + ','.join(sorted({x[4][0] for x in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)})))
PY
```

Do not print the API key. If this check fails, stop; do not use a mock, proxy,
fallback provider, or modified endpoint.

## One authorized local frozen run

Only after the local DNS preflight succeeds, run exactly once:

```zsh
.venv/bin/python -m scripts.run_step9_8_frozen_evaluation
```

Expected inputs are unchanged:

* Benchmark: `evaluation/benchmarks/benchmark_v2_cases.yaml`
* Scoring rubric: `evaluation/benchmark_v1_1_scoring.md`
* Runner: `scripts/run_step9_8_frozen_evaluation.py`
* Maximum turns: 6
* Model variables: `DEEPSEEK_API_KEY`, `DEEPSEEK_MODEL`,
  `DEEPSEEK_BASE_URL`

Expected evaluation directory: `evaluation/v1_2_2/`. The runner writes a
`step9_8b_freeze_manifest.json` and a raw trace after case execution. Do not
re-run after any case result is produced; preserve incomplete artifacts if the
run fails.

## Post-run handling

Do not modify Agent, Benchmark, scoring, or cases based on results. Copy the
generated `evaluation/v1_2_2/` directory back alongside the original workspace
as a separately named artifact only after preserving its local manifest and
trace. The existing Work records remain historical environment failures, not
Benchmark observations.
