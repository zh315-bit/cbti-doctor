# Research Summary: Adaptive Information Acquisition for LLM Agents

## Research question

**When should an LLM agent acquire additional information, and when is the
current information sufficient to act?** CBT-I (cognitive behavioral therapy
for insomnia) is the application domain, rather than the central scientific
claim. The project studies information acquisition, sufficiency estimation, and
adaptive action selection in a multi-turn, evidence-constrained LLM agent.

## Motivation and system design

Many conversational systems either answer immediately or follow a fixed intake
sequence. Both can be inappropriate: a user may need one high-value question,
external evidence, a required resource such as a sleep diary, or no further
information at all. The design principle is **Missing Information ≠ Must Ask**:
the value of an action must be judged relative to the current goal, not field
completeness alone.

The frozen Adaptive Agent V1 follows:

```text
User Input → State → Requirements → Sufficiency → Candidate Actions
→ Decision Policy → ASK / RETRIEVE / READ_DIARY / ANSWER → State Update
```

State separates user facts, external evidence, resource status, provenance,
critical/secondary/decision-relevant missing information, and user/evidence
sufficiency. Requirements express goal-specific information and resource needs.
The policy chooses one concrete candidate at a time; tool results update State
and trigger re-evaluation. Answer generation is bounded by the goal, relevant
facts, relevant evidence, and answer scope; data-derived claims are separated
from evidence-grounded claims.

## Evaluation design

Two evaluations are intentionally distinct.

- **V1.1 Historical / Development Benchmark:** ten synthetic cases used during
  iterative system development and controlled Fixed-vs-Adaptive comparisons.
  The capability-matched V1 baseline was 86.3/100 on *n*=8; this is not an
  independent generalization result.
- **V2 Independent Evaluation:** a frozen, newly designed set of 40 synthetic
  cases (10 knowledge QA, 10 cause assessment, 12 personalized decisions, 8
  diary analyses), with language, difficulty, resource, multi-turn, and
  information-sufficiency diversity. It was not combined with V1.1 scores.

## V2 results

Frozen Adaptive V1 scored **63.85/100** on *n*=40. By task: KNOWLEDGE_QA
**91.5**, CAUSE_ASSESSMENT **65.4**, PERSONALIZED_DECISION **31.67**, and
DATA_ANALYSIS **75.62**. It made **2.775 ASK/case**; **72.1%** of asks were
classified as redundant, and **13 cases** reached the six-ASK limit. There were
**2 critical failures**. These results are single-run, synthetic-benchmark
observations; they do not establish statistical significance, real-world
clinical effectiveness, state-of-the-art performance, or general superiority.

## Failure analysis

The dominant independent-evaluation failure chain was:

```text
explicit user facts sometimes fail to enter State
→ sufficiency remains incorrectly low
→ repeated / redundant ASK
→ particularly severe in personalized decisions
```

This is not evidence that the Decision Policy alone is at fault: extraction and
state integrity are upstream contributors. V2 also revealed a separate diary
fixture/data-projection inconsistency: compressed diary representations were
miscounted in two final answers. It is attributed to tool/data projection and
claim provenance, not to Decision Policy. In contrast, unavailable diary data
was not treated as real data in the reviewed unavailable-resource case.

## Open research questions

1. How should sufficiency be estimated when state extraction itself is uncertain?
2. How should an agent trade expected information gain from another question
   against interaction cost and the risk of user burden?
3. How should provenance be maintained from user utterances and tool outputs,
   through State, to every final factual or quantitative claim?

The next research step should be a pre-specified, generalizable V1.1 change and
paired comparison against this frozen baseline—not case-specific optimization.
