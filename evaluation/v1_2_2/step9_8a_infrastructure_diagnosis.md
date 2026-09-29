# Step 9.8a — Run Infrastructure Preflight Diagnosis

## First blocking point

The failed Step 9.8 attempt stopped **before case 1** during import-time module
initialization:

```text
benchmark runner
→ import main_flask
→ import rag_client
→ langchain_core.tools lazy import
→ langchain_core.runnables / callbacks module load
```

A five-second `faulthandler` sample located the active stack at
`rag_client.py:6`, importing `langchain_core.tools`, which was loading
`langchain_core.callbacks.manager` and `langchain_core.runnables.base`.
No Flask factory, Adaptive service construction, model invocation, RAG query,
vector-store load, benchmark case, or network request had begun. The first
blocking point is therefore **import-time legacy RAG/LangChain dependency
loading**, not Agent runtime behavior.

## Infrastructure change

Created `adaptive_agent/flask_app.py`, an import-light production factory that
exports the same `create_app()` route and lazy
`_create_adaptive_chat_service()` construction. `main_flask.py` now imports
that factory for its production `create_app` export. The benchmark harness
imports the factory directly, avoiding unrelated legacy workflow and RAG module
imports at benchmark startup.

This does not add another Agent implementation: the factory uses the existing
`AdaptiveChatService`, `AdaptiveAgentLoop`, input understander, RAG tool,
diary tool, answer generator, State Update, DependencyResolver and Policy.
Model/RAG construction remains lazy and unchanged.

## Preflight

The non-Benchmark synthetic smoke ran through the actual import-light
production Flask test client and `/api/chat` route:

```text
knowledge goal with wrong task signal
→ EVIDENCE
→ RETRIEVE
→ SATISFIED
→ ANSWER
```

It produced State history, dependencies, semantic provenance, candidate/action
IDs, and tool-to-State lineage. See `step9_8a_preflight_trace.json`.

`_create_adaptive_chat_service()` also constructed an `AdaptiveChatService`,
`AdaptiveAgentLoop`, and `RagRetrievalTool` without invoking a model or RAG
query. The separate model configuration test remains NOT_VERIFIED.

## Equivalence conclusion

The change is initialization/evaluation infrastructure only. Agent behavior,
Benchmark V2, scoring, and case handling did not change; no case-specific logic
was introduced. The current runner is ready for **one explicitly authorized**
Step 9.8 frozen run. No Benchmark case was run in this preflight.
