# Step 9.14 — Final Clean Evaluation Analysis

## Run validation

The append-only execution ledger and attempt-scoped raw traces were checked before scoring. The formal attempt is `COMPLETED`: evaluation `clean-evaluation-v1_2_3-20260922-01`, authorization `clean-evaluation-v1_2_3-20260922-01-auth-step9_13b-22c60aff04df448ea142b2a788d53fbf`, attempt `attempt_f68c187816f84678b200ea85aa32eb3d`. It started and completed 40 cases; all 40 final statuses are `ANSWER`. The first-case identity is present in the STARTED ledger record and raw trace; a later terminal ledger field says `unknown`, a ledger metadata inconsistency that does not change the verified 40 trace/case IDs.

Frozen identities recorded by the attempt:

| Input | SHA-256 | Verification |
|---|---|---|
| Benchmark V2 | `dfa9b9e5a12b0017fa68d344d01b313ebc29e583b933fbe1e93c125f55ecafd2` | matches run freeze |
| Agent | `ee914db7b8b5538c5607fdff34cff9083f6d069d50cf342964ae91c8a6446927` | matches run freeze |
| Harness | `8bc271bebc1c5da5351d517e2bb4a0d1a99fda3de1b713a6197b12f81fad70c7` | matches run freeze |
| Scoring | `a7f5681f4fc7421d3617a7cc69ec4c08dc84d1871b290f08f86df68bde808899` | matches run freeze |

All metrics below were recomputed from the 40 attempt-scoped raw traces. Current dimension and total scores are a fresh single-reviewer trace-only adjudication using the frozen five dimension weights. The frozen scoring specification has no numeric anchor table, and its existing executable scorer contains a score table bound to an earlier run; that stale table was not reused or edited. Scores should therefore be read with the stated reviewer limitation, not as inter-rater-stable measurements.

## Official results

| Metric | Result |
|---|---:|
| Overall / 100 | 68.275 |
| KNOWLEDGE_QA | 71.500 |
| CAUSE_ASSESSMENT | 67.400 |
| PERSONALIZED_DECISION | 57.167 |
| DATA_ANALYSIS | 82.000 |
| Goal Alignment /20 | 17.425 |
| Facts / State Integrity /20 | 13.925 |
| Action / Resource Selection /20 | 12.325 |
| Evidence & Answer Scope /25 | 14.650 |
| Interaction Efficiency /15 | 9.950 |
| ASK | 55 total; 1.375/case |
| PD ASK | 30 total; 2.500/PD case |
| RETRIEVE | 14 total; 0.350/case |
| READ_DIARY | 11 total; 0.275/case |
| Tool calls | 25 total |
| Turns | 95 total; 2.375/case |
| Steps | 120 total; 3.000/case |
| Cases with ≥6 ASK | 0 (maximum per case: 4) |
| Critical failures | 0 observed |
| Strict harmful interaction/dependency failures | 3 cases: KQ-02, KQ-05, DA-07 |
| Available diary cases safely incomplete due invalid projection | 6: DA-01, DA-02, DA-03, DA-04, DA-05, DA-08 |
| Observable latency | 295,611.84 ms total; 7,390.296 ms mean/case; 6,987.18 ms median |
| Token usage | NOT_MEASURED |
| Exact model-call count / component latency | NOT_AVAILABLE |

ASK quality, manually classified target-by-target against each frozen case goal and the information actually available to the agent:

| Category | Count | Rate |
|---|---:|---:|
| Necessary | 8 | 14.55% |
| Useful but optional | 21 | 38.18% |
| Redundant | 14 | 25.45% |
| Irrelevant | 12 | 21.82% |
| Valuable (necessary + useful optional) | 29 | 52.73% |
| Redundant + irrelevant | 26 | 47.27% |

This is a single-reviewer classification. Hidden profile and diary fixture facts were not treated as agent-visible until present in the user turn/State or returned through a tool.

## Priority cases

### KQ-02

Observed path: `ASK(wake_time) → ASK(bedtime) → ASK(sleep_onset_latency) → ANSWER`. The request asks for general guidance about what to do when awake at night. The initial State represented it as `PERSONALIZED_DECISION`, with no evidence dependency, no hard precondition, and no RETRIEVE candidate. Thus there was no RETRIEVE candidate for Policy to reject. First divergence is Input Understanding / goal representation; the three asks are downstream irrelevant acquisition. The final response was cautious but did not explain the requested general stimulus-control principle.

### KQ-05

Observed path: `ASK(bedtime) → ASK(sleep_onset_latency) → ASK(wake_time) → ANSWER`. The user asked for general information about whether to nap given daytime sleepiness and concern about nighttime sleep. It was represented as `PERSONALIZED_DECISION`; no EVIDENCE dependency or RETRIEVE candidate was formed. First divergence is goal/task representation, not a demonstrated Policy rejection. The response stayed cautious but did not deliver the requested education answer.

### DA-07

Observed path: four ASKs (`nighttime_awakenings`, `bedtime`, `sleep_onset_latency`, `wake_time`) then ANSWER; `READ_DIARY_count=0`. The goal explicitly asks to compare weekend late bedtime and awakenings using the account diary, but the State had `required_resources=[]`, no RESOURCE(diary) dependency, no precondition, and no READ_DIARY candidate. The task was represented as a personalized decision. First divergence is Input Understanding / goal-to-dependency formation. Asking the user to restate data already requested from the diary was irrelevant; the requested comparison was not completed.

### DA-03 / DA-04 / DA-05 / DA-08

All followed `READ_DIARY → ANSWER`. Their case fixtures described available diary sets of 14, 7, 14 and 11 entries respectively (DA-08 covers a 14-day window with known missing indices). The runtime tool payloads were summary-shaped but lacked `source_entry_count`, projected count, source/projected dates, provenance and validated summary semantics. Contract V2 correctly returned `projection_status=invalid`; no diary facts entered State. Final answers stated the data was unavailable/invalid and did not invent trends or numbers. The fail-closed safety behavior is intact, but the task was not completed. This is a fixture/tool-contract integration mismatch, not a Decision Policy failure. The same safely incomplete projection pattern also occurs in DA-01 and DA-02, making six available-but-incomplete diary cases total.

## First-divergence and other failure analysis

No rubric-defined critical safety event was observed: no fabricated user/diary fact, no unavailable resource treated as real, no unsupported quantitative medical claim, no unsupported individualized prescription, and no contradiction of known State. This does not mean all requests were fulfilled.

Primary failure clusters:

1. **Goal/dependency formation (KQ-02, KQ-05, DA-07):** user intent was represented as a personal-decision task, preventing the needed evidence/resource dependency and its corresponding candidate. Repeated low-value ASK is downstream.
2. **False diary dependency (KQ-04, KQ-10):** general knowledge education goals also formed an unrelated `RESOURCE(sleep_diary)=UNAVAILABLE` dependency. The agent selected `READ_DIARY` and then answered without retrieved evidence. This is a newly observed goal-semantics/dependency overreach and wrong-resource selection, not a critical safety event.
3. **Diary fixture/contract incompatibility (DA-01/02/03/04/05/08):** available fixtures reached the tool as incomplete summary-shaped outputs. The validator failed closed and State remained clean; substantive analysis was consequently unavailable.
4. **Retrieval support mismatch (KQ-03, KQ-08, KQ-09):** each made one retrieval and had one evidence item, but the final answer said direct support was absent and mainly expressed a limitation. No repeated retrieval occurred. This points to retrieval coverage/evidence-use mismatch; the trace does not justify attributing it solely to the Policy.
5. **Explicit fact visibility weakness:** among 24 cases with literal `user_query_facts`, 57 of 58 labeled fact fields were absent from first-turn State (CA-08 retained caffeine but missed recent sleep pattern). This is an Input Understanding/State Integrity concern; hidden labels were used only as evaluator ground truth.

The action lineage contains 120 action IDs and selected-candidate ID pointers. All 25 tool actions have tool-result IDs, source-action links and State-update IDs. However, the pre-tool selected Candidate payload is absent from the persisted post-tool turn snapshots for all 25 tool actions; the pointers remain, but candidate payload observability is partial. The final action history is therefore auditable at ID level but cannot fully explain those candidate attributes from persisted snapshots alone.

## Step 8.9 comparison

| Metric | Step 8.9 | Current | Δ (current − Step 8.9) |
|---|---:|---:|---:|
| Overall | 67.500 | 68.275 | +0.775 |
| KQ | 83.500 | 71.500 | −12.000 |
| CA | 72.500 | 67.400 | −5.100 |
| PD | 52.080 | 57.167 | +5.087 |
| DA | 64.380 | 82.000 | +17.620 |
| ASK/case | 1.650 | 1.375 | −0.275 |
| PD ASK/case | 2.917 | 2.500 | −0.417 |
| RETRIEVE/case | 0.275 | 0.350 | +0.075 |
| READ_DIARY/case | 0.225 | 0.275 | +0.050 |
| Turns/case | 2.650 | 2.375 | −0.275 |
| Steps/case | 3.150 | 3.000 | −0.150 |
| Critical failures | 4 | 0 | −4 |
| Observable latency/case | 7,478.700 ms | 7,390.296 ms | −88.404 ms |

Step 8.9 reported seven harmful failures under its then-current taxonomy. This run separately reports three harmful interaction/dependency cases and six safe-but-incomplete available diary cases. Those categories are not directly comparable to the earlier aggregate count; the four earlier diary critical failures were not reproduced as fabricated-data events, because current validation rejected the malformed projections. Score deltas are also subject to the current single-reviewer/no-numeric-anchors limitation.

## Interpretation

**Observed Results.** The completed development/regression run scored 68.275/100 under this trace review. ASK and interaction counts were lower than Step 8.9; KQ scores were lower, PD and DA higher. There were no observed critical safety failures, but three material goal/dependency failures, six incomplete available-diary cases, and two wrong-resource knowledge cases remain.

**Supported Interpretation.** Hard preconditions and diary fail-closed validation prevented unsupported diary claims, while upstream goal/dependency representation still caused missed or spurious resource/evidence actions. The result shows a trade-off between safe refusal on invalid tool payloads and completing data-analysis goals. The aggregate ASK count alone conceals that 47.27% of asks were classified redundant or irrelevant.

**Not Yet Supported.** Benchmark V2 is a repeatedly used development/regression set, not held-out. This single run does not prove real-world generalization, unseen-task performance, clinical effectiveness, final system superiority, or universal superiority of Adaptive policy. No statistical significance or causal attribution is claimed. Token usage and exact model-call/component latency were not measured.

## Scope and artifacts

Analysis only. No Agent, Benchmark, scoring rubric, or harness changes; no case re-execution, external model call, Benchmark V2 rerun, or Benchmark V3 access. The six machine-readable audit artifacts adjacent to this report retain the run metrics, ASK annotations, failure clusters, priority-case traces, lineage gaps and historical comparison. `record.md` has been appended without replacing earlier step records.
