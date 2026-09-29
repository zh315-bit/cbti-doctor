# CBTI Doctor

CBTI Doctor is a conversational CBT-I (cognitive behavioral therapy for insomnia) assistant built with `LangGraph + LangChain + Flask`. It guides users through sleep information gathering, problem summaries, cognitive restructuring, and integrated interventions. It also uses RAG to answer questions from a local PDF knowledge base.

## Overview

This project turns core CBT-I counseling steps into an interactive agent workflow for insomnia-related scenarios. Flask provides the chat API, and a lightweight web page provides the frontend. LangGraph manages the main agent flow, with separate subgraphs for different treatment stages.

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

- This project is intended for learning, research, and prototype validation. It should not replace diagnosis or treatment advice from a physician or mental health professional.
- On the first run, the application processes the PDFs in `rag_lib/pdfs/` and builds a vector database. This may take some time.
- Web sessions retain the current stage, full message history, and tool results. You can reset a session after it ends. Sessions are currently stored in process memory: restarting the server clears them, and they cannot be shared across multiple processes.

## Offline regression tests

```bash
.venv/bin/python -m unittest discover -s tests -v
```

The session tests use the real application factory with mocked Flask, message, and graph objects. They cover stage recovery, preservation of tool results, session isolation, reset behavior, invocation failures, and session completion. Model configuration tests also check the DeepSeek settings, BGE query prefix, and index file validation. These tests do not call external APIs and do not replace real Flask/LangGraph integration tests.

## Downloaded local BGE model

`BAAI/bge-small-zh-v1.5` is stored in `models/bge-small-zh-v1.5/`, which is not committed to Git. See `download_source.json` in that directory for the source revision and weight checksum. The model produces 512-dimensional Chinese embeddings and can run offline on a CPU without an API key.

Additional local inference dependencies are listed in `requirements-bge.txt`. The complete environment versions are in `requirements-bge-lock.txt`; you can reproduce them with `pip install -r requirements-bge-lock.txt`. To validate the local model, run:

```bash
.venv/bin/python scripts/check_bge.py
```

`rag_client.py` uses the local BGE model to generate document and query embeddings on the CPU. The first retrieval automatically builds a dedicated index at `rag_lib/.rag_db/bge-small-zh-v1.5-ch400-v1/`; it does not reuse an older OpenAI embedding index. Answer generation still calls DeepSeek and sends the relevant retrieved passages as context.

The main conversation, summary tools, and RAG answers share `model_config.py`. Thinking mode is disabled by default for compatibility with the existing tool-message chain. Restart the service after changing the model configuration.
