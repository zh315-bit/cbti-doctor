# CBTI Doctor

[![Offline tests](https://github.com/zh315-bit/cbti-doctor/actions/workflows/tests.yml/badge.svg)](https://github.com/zh315-bit/cbti-doctor/actions/workflows/tests.yml)

CBTI Doctor is a research prototype for a **cost-aware adaptive CBT-I agent** (cognitive behavioral therapy for insomnia). It uses `LangGraph + LangChain + Flask` to support conversational information gathering, CBT-I intervention stages, and retrieval from a local PDF knowledge base. Its adaptive loop chooses one justified next action at a time.

## Overview

This project turns CBT-I counseling steps into an interactive workflow for insomnia-related scenarios. Flask provides the chat API, and a lightweight web page provides the frontend. LangGraph manages the stage-based conversation, while `adaptive_agent/` contains the adaptive decision loop. The repository is an engineering and evaluation prototype, not a clinical service.

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

`.gitignore` excludes designated evaluation run directories, raw traces, case results, local logs, model weights, and the vector database. Other generated analysis files are not part of the published project unless deliberately selected for version control. Reproducing a historical report may require regenerating local outputs; the committed benchmark definitions and harness scripts do not include every prior run artifact.

## Optional local BGE model

For local retrieval, place `BAAI/bge-small-zh-v1.5` in `models/bge-small-zh-v1.5/` or set `BGE_MODEL_PATH` to its local directory. Model weights are not committed to Git. If you already have a local copy, its `download_source.json` can record the source revision and weight checksum. The model produces 512-dimensional Chinese embeddings and can run offline on a CPU without an API key.

Additional local inference dependencies are listed in `requirements-bge.txt`. The complete environment versions are in `requirements-bge-lock.txt`; you can reproduce them with `pip install -r requirements-bge-lock.txt`. To validate the local model, run:

```bash
.venv/bin/python scripts/check_bge.py
```

`rag_client.py` uses the local BGE model to generate document and query embeddings on the CPU. The first retrieval automatically builds a dedicated index at `rag_lib/.rag_db/bge-small-zh-v1.5-ch400-v1/`; it does not reuse an older OpenAI embedding index. Answer generation still calls DeepSeek and sends the relevant retrieved passages as context.

The main conversation, summary tools, and RAG answers share `model_config.py`. Thinking mode is disabled by default for compatibility with the existing tool-message chain. Restart the service after changing the model configuration.
