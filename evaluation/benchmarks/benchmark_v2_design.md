# Benchmark V2 Evaluation Set — Design

## Status and scope

Benchmark V2 is an independent, unrun 40-case evaluation set. It does not edit, supersede, or combine scores with frozen Benchmark V1.1. It is designed to assess generalization after future authorized changes to Adaptive Agent V1, not to select changes now.

All cases use evaluator-owned synthetic data. `user_query_facts` are an evaluator oracle for review only: they do not enter Agent State unless Input Understanding extracts them from literal user text. `follow_up_facts` are released only after an actual ASK. Diary entries are evaluator-owned and enter only after `READ_DIARY`; evidence begins empty and must come through `RETRIEVE`.

## Dataset composition

| Task type | Cases | IDs |
|---|---:|---|
| KNOWLEDGE_QA | 10 | V2-KQ-01–10 |
| CAUSE_ASSESSMENT | 10 | V2-CA-01–10 |
| PERSONALIZED_DECISION | 12 | V2-PD-01–12 |
| DATA_ANALYSIS | 8 | V2-DA-01–08 |
| **Total** | **40** | — |

Difficulty is deliberately semantic/decision-based, not jargon-based: **easy 10**, **medium 20**, **hard 10**.

## Diversity design

| Language style | Count | Design use |
|---|---:|---|
| 简短中文 | 10 | Compact but interpretable user questions |
| 口语中文 | 9 | Everyday phrasing without medical labels |
| 信息分散中文 | 7 | Facts distributed across clauses or uncertainty statements |
| 中英混合 | 5 | Natural borrowed sleep vocabulary without implementation-keyword targeting |
| 英文 | 9 | Equivalent CBT-I tasks in ordinary English |

The cases include multi-fact one-sentence reports, vague but understandable timing, explicit conflicts, more information than the goal needs, and a multi-turn data-analysis focus clarification. They do not use a fixed field order or attempt to trigger named V1 Failure Set fields.

## Information-sufficiency coverage

Coverage labels overlap where a real task has more than one property; they are not numerical probability claims.

| Coverage condition | Representative cases |
|---|---|
| Information already sufficient for a bounded answer | CA-01, CA-05, CA-10, PD-01, PD-03, PD-10 |
| One critical fact missing | CA-04, CA-08, CA-09, PD-05, PD-07, PD-08 |
| Multiple critical facts missing | CA-02, CA-03, CA-07, PD-02, PD-04, PD-06, PD-12 |
| Only secondary information missing | CA-01, CA-05, CA-10, PD-01, PD-10 |
| Evidence missing at start | All 40 cases; evidence may only arrive via RETRIEVE |
| Diary required | DA-01–08 |
| Diary optional or explicitly not authorized | PD-11 |
| Diary unavailable | DA-06, PD-12 |
| User provides more than necessary | PD-10 |
| Conflicting/incomplete facts | CA-06, PD-09, DA-08 |

The intended interpretation remains **Missing Information ≠ Must Ask**. Cases with secondary gaps, extra user information, or an answer-ready limited scope explicitly permit direct answer/retrieval paths rather than requiring field completion.

## Action-path coverage

Expected paths and alternatives intentionally include more than one successful strategy:

| Path form | Representative cases |
|---|---|
| ANSWER | CA-07 (limited response) |
| RETRIEVE → ANSWER | KQ-01–10, CA-01, PD-01 |
| ASK → ANSWER | PD-09; CA-07 alternative |
| ASK → RETRIEVE → ANSWER | CA-02/03/04, PD-02/05/06/08/12 |
| READ_DIARY → ANSWER | DA-01/02/05/06/08 |
| READ_DIARY → RETRIEVE → ANSWER | DA-03/04 |
| ASK → READ_DIARY → ANSWER | DA-07 |

An acceptable alternative path is never invalid merely because it uses a different high-value ASK order. Unacceptable paths are defined around absent information value, resource misuse, fabrication, unsafe individual prescriptions, and scope drift rather than action-string mismatch.

## Separation from V1.1

V1.1 remains the historical/development benchmark. V2 is a new evaluation set with new identifiers, user framing, goals and fixture contracts. Future reports must separately state:

```text
V1.1 historical/development performance
V2 evaluation performance
```

They must not form a combined score without an explicitly approved new protocol.
