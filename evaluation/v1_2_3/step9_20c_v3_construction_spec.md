# Step 9.20c — Benchmark V3 Construction Specification

## Identity and separation

Benchmark V3 is a new 32-case held-out evaluation set, independent of the 40-case V2 development/regression set. It has eight cases in each of KNOWLEDGE_QA, CAUSE_ASSESSMENT, PERSONALIZED_DECISION and DATA_ANALYSIS. No V2 case text was copied or paraphrased into a new case; common domain concepts are allowed, but each V3 question has a distinct user intent or information state. This set was authored before any V3 Agent execution. It must not be edited after sealing in response to future Agent outputs.

## Schema and visibility

The YAML extends the V2 case schema. The frozen Step 9.20a runner consumes only its generic fixture contract: `case_id`, `user_query`, `task_type`, `diary_facts`, `follow_up_facts`, and optional `initial_session_facts`. Evaluator-only fields (`goal`, `user_query_facts`, `evidence`, requirement/resource expectations, acceptable/unacceptable paths, answer scope, and failure criteria) are never injected into Agent State. The `follow_up_facts` map releases only the field actually requested by ASK. Diary fixture facts are only made visible by `READ_DIARY`. All synthetic dates and health-related details are fictional.

Available diary fixtures use entry-shaped `recent_sleep_pattern` lists of ISO-dated dictionaries, compatible with the existing `SessionDiaryTool` contract. Numeric `total_sleep_time` values are **minutes**, not hours; clock strings are local `HH:MM`. There are no fabricated summary metadata fields or implicit missing-day values. Unavailable fixtures have empty `facts`. The single direct-input DATA_ANALYSIS case needs no diary resource and explicitly tests `Missing Information ≠ Must Ask` and resource non-acquisition.

## Coverage and acceptable paths

The 32 cases vary language (brief/colloquial/distributed Chinese, mixed Chinese-English, English), difficulty, known facts, follow-ups, initial session facts, evidence needs, diary availability, and answer scope. They exercise direct bounded ANSWER, ASK then bounded ANSWER, RETRIEVE then ANSWER, READ_DIARY then ANSWER, and optional mixed paths. An `expected_actions` sequence is a reference, not an exact-match requirement: the frozen rubric evaluates whether each acquisition materially serves the goal and whether an alternative path stays within the answer scope. In particular, missing secondary fields never automatically require ASK.

Eight knowledge cases require external CBT-I evidence; one cause-assessment case requires evidence for its explanatory claim. Seven data-analysis cases require diary data, six with available entry-shaped fixtures and one unavailable; the remaining analysis case uses explicit user-provided values. Five personalized/cause cases explicitly request USER_FACTS, and one personalized case requires both user facts and evidence for a specific treatment-rule discussion. Optional evidence/resource use is adjudicated by actual answer scope, not rewarded automatically.

## Construction boundary

Only benchmark data and Step 9.20c documentation/manifest are created. Agent behavior, frozen runner, scoring, metric registry, one-shot rules, and V2 remain unchanged. No Agent or model call, V2 rerun, or V3 evaluation is part of construction. After static QA, the file's SHA-256 is recorded as its immutable identity. Any later byte change is a new dataset identity, not an in-place correction to this sealed one.
