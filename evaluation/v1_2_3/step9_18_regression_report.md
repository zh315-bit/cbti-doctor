# Step 9.18 — Regression Report

## Results

- New information-value gate tests: **17 passed / 0 failed**.
- Combined focused suite (information value, policy, sufficiency, dependency, projection, grounding, lineage, authorization): **115 passed / 0 failed**.
- Full non-Benchmark unittest discovery: **217 passed / 0 failed / 0 skipped** (`.venv/bin/python -m unittest discover -s tests`).
- `tests.test_model_configuration` ran in its existing mocked/offline form; no live provider request was made.

The full suite's argparse usage text is expected output from negative CLI-argument tests; the tests themselves passed.

## Freeze and scope audit

- Step 9.11 manifest SHA-256 remains `ab1720e0f481c301a2436786d8e2390df2ebfd885ff2b60b5df8f64c17c1aa5c`; not modified.
- Step 9.17 candidate freeze remains intact and is the direct parent for the new candidate.
- New post-Step-9.18 candidate Agent aggregate: `0dfdbac361d68dfeb577433107395b50f4c2fa8ca59f3e1d226fbd9271a839a7` (26 inventoried files; matches current content using the repository's freeze hash verifier, including its directory/runtime fingerprint rules).
- Benchmark aggregate remains `723ab458f5808d7d8ea542e519ddbf19afe59463e0b355700b1b537f942bb4f6`.
- Harness remains bound to the accepted Step 9.13a harness freeze `8bc271bebc1c5da5351d517e2bb4a0d1a99fda3de1b713a6197b12f81fad70c7`; this step did not modify harness code.
- Scoring aggregate remains `f742a8f8af7c8747818dadad81621c15d12d74f50538019913dfe18ab53bf59b`.
- No Benchmark V2 run; no Benchmark V3 access; no live model/RAG requests.

## Status

Regression gate: **PASS**. This is mechanism/regression evidence only, not a Benchmark performance claim.
