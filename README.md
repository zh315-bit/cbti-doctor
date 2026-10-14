# CBTI Doctor

[![Offline tests](https://github.com/zh315-bit/cbti-doctor/actions/workflows/tests.yml/badge.svg)](https://github.com/zh315-bit/cbti-doctor/actions/workflows/tests.yml)

CBTI Doctor is a research prototype for a **cost-aware adaptive CBT-I agent** (cognitive behavioral therapy for insomnia). It uses `LangGraph + LangChain + Flask` to support conversational information gathering, CBT-I intervention stages, and retrieval from a local PDF knowledge base. Its adaptive loop chooses one justified next action at a time.

## Overview

This project turns CBT-I counseling steps into an interactive workflow for insomnia-related scenarios. Flask provides the chat API, and a lightweight web page provides the frontend. LangGraph manages the stage-based conversation, while `adaptive_agent/` contains the adaptive decision loop. The repository is an engineering and evaluation prototype, not a clinical service.

## Research Focus

- **Adaptive agent decision-making:** When information is incomplete, how should an agent choose among answering, asking a question, retrieving evidence, and reading a diary, given the cost of each action?
- **Agent reliability and evidence-grounded behavior:** Can explicit requirements, dependency checks, and state updates help the agent avoid unsupported answers and unnecessary information gathering?
- **Reliability of LLM-based evaluation:** How much do case-level judgments and aggregate conclusions change when the AI reviewer changes?

## Architecture

The adaptive loop processes each user turn in this order:

```text
User query
  -> Input understanding
  -> Goal and user facts
  -> Requirements and dependencies
  -> User-information and evidence sufficiency
  -> Candidate actions and acquisition gate
  -> Decision policy
  -> One action: ASK / RETRIEVE / READ_DIARY / ANSWER
  -> State update and re-evaluation
```

`adaptive_agent/runner.py` coordinates the loop. The input-understanding, requirements, dependency, sufficiency, information-value, candidate, policy, acquisition-gate, and state-update modules provide the corresponding steps. Retrieval and diary reads can update state before the policy chooses again; an `ASK` returns control to the user.

## Core principles

- **Missing information does not always require an ASK.** The policy weighs relevance, information value, available resources, and acquisition cost.
- **Task type does not directly determine the next action.** The current goal, requirements, evidence, and state determine the candidates.
- **User information and external evidence are separate.** Retrieved material does not become a user fact merely because it was found.
- **One action at a time.** The loop records each decision and re-evaluates after new information arrives.
- **Goal alignment.** Candidate actions should address the user's current goal and its effective requirements.
- **No fabricated user facts.** Answers should use stated or validated facts and represent unresolved information as a limitation.

## Features

- **Information gathering:** Asks about sleep timing, nighttime awakenings, bedtime behavior, daytime habits, stressors, and thoughts related to insomnia.
- **Summary and feedback:** Analyzes possible contributing factors and identifies cognitive patterns from the conversation.
- **Cognitive restructuring:** Identifies negative thoughts and helps develop alternative thoughts.
- **Integrated intervention:** Recommends CBT-I modules such as stimulus control, sleep restriction, and sleep education based on the user's situation.
- **RAG retrieval:** Loads CBT-I PDFs from `rag_lib/pdfs/`, builds a local vector database, and answers domain questions.
- **Web chat:** The frontend communicates with the backend through `/api/chat` and supports basic session management.
- **CLI mode:** Runs the conversation in a terminal for debugging.

## Getting started

### 0. Install dependencies and configure API keys

Use Python 3.12. From the project root, run:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-bge-lock.txt
```

The current configuration uses DeepSeek V4.1 Flash and a local BGE model. `requirements-bge-lock.txt` includes the dependencies for local inference. `requirements.txt` lists the base dependency ranges, while `requirements-lock.txt` preserves versions for the base environment. The project uses the LangChain 0.3 APIs; do not upgrade LangChain to 1.x independently.

If `.env` does not exist, copy `.env.example` to `.env` and edit these values locally:

| Environment variable | Purpose |
| --- | --- |
| `DEEPSEEK_API_KEY` | The only required API key; used for the main conversation and RAG answers. |
| `DEEPSEEK_MODEL` | Defaults to `deepseek-flash`, corresponding to DeepSeek V4.1 Flash. |
| `DEEPSEEK_BASE_URL` | Defaults to `https://api.deepseek.com`. |
| `BGE_MODEL_PATH` | Defaults to `models/bge-small-zh-v1.5`, relative to the project root. |
| `ENABLE_WEB_SEARCH` | Defaults to `false`; no Tavily key is needed. |
| `TAVILY_API_KEY` | Required only when web search is explicitly enabled. |

Git ignores `.env`. Do not put API keys in source code or commit them to the repository. A virtual environment does not include a service account or API credits, so real conversations still require a valid key.

### 1. Start the Flask backend

From the project root, run:

```bash
.venv/bin/python main_flask.py
```

The backend starts at `http://localhost:5001` by default. To use another available port, set `PORT=5002` in `.env` and update `CBTI_API_PORT` in `public/index.html` to match.

### 2. Start the frontend

The frontend files are in `public/`. You can serve them with a simple static server:

```bash
.venv/bin/python -m http.server 8000 --bind 127.0.0.1 --directory public
```

Then open `http://localhost:8000`.

### 3. Use CLI mode

For terminal-based interaction, run:

```bash
RUN_MODE=cli .venv/bin/python main_flask.py
```

## Notes

- This is a research prototype. It cannot replace a physician, licensed therapist, professional diagnosis, or emergency care. Do not use it as a substitute for urgent medical help.
- On the first run, the application processes the PDFs in `rag_lib/pdfs/` and builds a vector database. This may take some time.
- Web sessions retain the current stage, full message history, and tool results. You can reset a session after it ends. Sessions are currently stored in process memory: restarting the server clears them, and they cannot be shared across multiple processes.

## Offline regression tests

```bash
DEEPSEEK_API_KEY=ci-placeholder-no-network .venv/bin/python -m unittest discover -s tests -v
```

The value above is a non-secret sentinel for frozen configuration checks; the tests do not send it to an external service. The session tests use the real application factory with mocked Flask, message, and graph objects. They cover stage recovery, preservation of tool results, session isolation, reset behavior, invocation failures, and session completion. Model configuration tests also check the DeepSeek settings, BGE query prefix, and index file validation. These tests do not call external APIs and do not replace real Flask/LangGraph integration tests.

The full local suite also checks historical evaluation contracts against generated run artifacts and freeze records that are not all committed to Git. A clean checkout cannot run those artifact-bound modules without the original local outputs. The `Offline tests` GitHub Actions workflow runs every repository-contained test module and lists the eight artifact-bound modules it excludes. It does not alter their assertions or the evaluation harness.

## Evaluation and reproducibility

The repository contains offline regression tests in `tests/`, evaluation harness scripts in `scripts/`, and fixed benchmark definitions under `evaluation/`. Historical freeze records and reports document evaluation setups, including heldout evaluation. The reports describe specific runs; they are not claims of clinical efficacy or general performance.

Use Python 3.12 and the dependency files above to reproduce the software environment. `requirements-lock.txt` pins the core application dependencies used by the offline tests. `requirements-bge-lock.txt` includes the optional local BGE inference stack. The offline unit tests use mocks and do not require downloaded model weights, a real API key, or paid model calls. Actual RAG and model-backed conversations require their separate local model and API configuration.

`.gitignore` excludes designated evaluation run directories, raw traces, case results, local logs, model weights, and the vector database. Selected r11 run evidence was [archived](evaluation/v1_2_3/step9_63c_r11_run_archive/MANIFEST.json) with [SHA-256 checksums](evaluation/v1_2_3/step9_63c_r11_run_archive/SHA256SUMS), but some historical raw traces and evaluation artifacts are absent from the public repository. The committed benchmark and scripts alone cannot reproduce every historical result; artifact-bound tests may require the original local outputs.

## Evaluation Methodology

**Frozen benchmark and artifacts.** The V4 benchmark contains 40 fixed cases: 10 each in `KNOWLEDGE_QA`, `CAUSE_ASSESSMENT`, `PERSONALIZED_DECISION`, and `DATA_ANALYSIS`. It was originally sealed for the [Step 9.28 held-out run](evaluation/v1_2_3/step9_28_v4_execution_protocol.md). Subsequent v3 repairs consulted V1/V2 case-level behavior and frozen scores on these same V4 cases, so the later v3 comparison is development and postmortem evidence, not an unseen test of generalization. A [frozen rubric](evaluation/v1_2_3/step9_63c_r11_blind_review_packet/rubric/benchmark_v1_1_scoring.md) guides case-level review. Execution traces and case results record action paths, tool use, and final states; the [run archive](evaluation/v1_2_3/step9_63c_r11_run_archive/MANIFEST.json), [adjudication freeze](evaluation/v1_2_3/step9_63c_r11_adjudication_freeze.json), and SHA-256 manifests identify the reviewed bytes.

**Preregistered primary evaluation.** The [FINAL scoring plan](evaluation/v1_2_3/step9_63c_r11_scoring_preregistration_final.json) was locked before the main v3 review. It specifies five primary measures: low-value `ASK` rate (M1), completion (M2), harmful-failure rate (M3), necessary-`ASK` preservation (M4), and critical-failure rate (M5). Total and task-category scores are descriptive. One Claude AI reviewer assessed v3; the 9.28 comparator retained its earlier, locked Codex AI review. Records were frozen before the unchanged aggregation formula was applied. The [primary report](evaluation/v1_2_3/step9_63c_r11_scoring_report.md) presents a matched development comparison, not a causal estimate of an architecture change.

**Cross-reviewer sensitivity analysis.** A separate [2×2 plan](evaluation/v1_2_3/step9_63c_r11_reviewer_sensitivity_preregistration.json) was registered after the primary result was available but before two new reviews. It adds a fresh Claude AI review of 9.28 (B) and a Codex AI review of v3 (A) to the unchanged primary v3 result and locked 9.28 baseline. The new records were [frozen before aggregation](evaluation/v1_2_3/step9_63c_r11_sensitivity_freeze.json). This design probes reviewer dependence; it does not isolate the causal effect of agent design changes.

## Reviewer Sensitivity

M4 is the number of oracle-marked necessary information targets acquired through a semantically equivalent `ASK`, divided by the four oracle-marked targets. The cells below are separate reviews of the indicated run, not interchangeable scores.

| AI reviewer | v3: M4 necessary-`ASK` preservation | 9.28: M4 necessary-`ASK` preservation |
| --- | ---: | ---: |
| Claude | 0/4 (primary review) | 0/4 (B) |
| Codex | 0/4 (A) | 1/4 (locked baseline)¹ |

¹ Disclosure only; no value in this table is changed. The locked baseline's `1/4` comes from a single label (V4-PD-03, `bedtime` acquired). The 9.28 trace shows a different `ASK` target and an "unknown" reply for that case, and the other three cells record `0` for it. See the [erratum](evaluation/v1_2_3/step9_63c_r11_erratum_M4_baseline.md).

The primary comparison therefore fails its preregistered requirement that M4 not fall below the locked baseline. The [sensitivity report](evaluation/v1_2_3/step9_63c_r11_sensitivity_report.md) finds lower M1 and M3 on both reviewer paths, while the directions for completion, validity, M4, and critical failures are reviewer-dependent or uncertain.

The following counts are exact per-case agreement on the recorded boolean `validity_judgment` and `critical_failure.present` fields; they do not establish agreement on clinical correctness.

| Same run | AI reviews compared | Validity agreement | Critical-failure agreement |
| --- | --- | ---: | ---: |
| v3 | Claude primary vs Codex A | 35/40 | 37/40 |
| 9.28 | Codex locked baseline vs Claude B | 24/40 | 40/40 |

The 9.28 agreement is descriptive: its locked baseline used an earlier review procedure, and the Codex model version was not recorded. No cell is selected in preference to another.

## Research Limitations

V4 was initially a sealed held-out evaluation, but prior exposure to its results makes later v3 analyses development evidence. Each cell has one LLM-based evaluator, not a human clinical expert, and reviewer disagreement limits the interpretation of scores. The locked 9.28 baseline also used an earlier review procedure. Some raw evaluation artifacts are not publicly available, so a clean checkout cannot reproduce every historical result. No statistical significance, clinical efficacy, or overall superiority is claimed; the evidence also does not identify the causal effect of an agent architecture change.

## Optional local BGE model

For local retrieval, place `BAAI/bge-small-zh-v1.5` in `models/bge-small-zh-v1.5/` or set `BGE_MODEL_PATH` to its local directory. Model weights are not committed to Git. If you already have a local copy, its `download_source.json` can record the source revision and weight checksum. The model produces 512-dimensional Chinese embeddings and can run offline on a CPU without an API key.

Additional local inference dependencies are listed in `requirements-bge.txt`. The complete environment versions are in `requirements-bge-lock.txt`; you can reproduce them with `pip install -r requirements-bge-lock.txt`. To validate the local model, run:

```bash
.venv/bin/python scripts/check_bge.py
```

`rag_client.py` uses the local BGE model to generate document and query embeddings on the CPU. The first retrieval automatically builds a dedicated index at `rag_lib/.rag_db/bge-small-zh-v1.5-ch400-v1/`; it does not reuse an older OpenAI embedding index. Answer generation still calls DeepSeek and sends the relevant retrieved passages as context.

The main conversation, summary tools, and RAG answers share `model_config.py`. Thinking mode is disabled by default for compatibility with the existing tool-message chain. Restart the service after changing the model configuration.
