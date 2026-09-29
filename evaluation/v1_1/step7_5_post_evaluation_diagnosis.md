# Step 7.5 Post-Evaluation Diagnosis

Date: 2026-09-20

## Scope

This is an offline analysis of the frozen Step 7.4 artifacts only. No Agent,
prompt, Benchmark V2 case, rubric, or model run was changed or rerun.

## ASK Quality

V1.1 produced 112 ASK actions (2.800/case): necessary 21 (18.8%), useful-but-optional 9 (8.0%), redundant 39 (34.8%), and irrelevant 43 (38.4%). Frozen V1 had 111 ASK, 2.775/case, and 72.1% redundant. Thus V1.1 did not reduce ASK quantity and its redundant rate is lower under the same trace-only classification, but its irrelevant rate is higher; ASK quality improved only partially.

## Per-Task Diagnosis

| Task | Score V1 → V1.1 | ASK/case V1 → V1.1 | V1.1 redundant ASK rate | V1.1 six-ASK cases | V1.1 critical failures |
|---|---:|---:|---:|---:|---:|
| KNOWLEDGE_QA | 91.50 → 78.10 | 0.900 → 1.000 | 0.0% | 1 | 0 |
| CAUSE_ASSESSMENT | 65.40 → 71.00 | 3.100 → 3.200 | 50.0% | 0 | 0 |
| PERSONALIZED_DECISION | 31.67 → 34.17 | 5.417 → 5.333 | 35.9% | 9 | 0 |
| DATA_ANALYSIS | 75.62 → 87.50 | 0.750 → 0.750 | 0.0% | 1 | 0 |

PD remains the main bottleneck: it has the highest repeated-ASK concentration and most six-ASK paths. Lower ASK burden cannot be inferred from its score because the V1.1 run still repeatedly asks for broad requirement fields after State extraction failures.

## Six-ASK Limit

The 11 cases and every ASK target with the State before the ASK are recorded in
`step7_5_ask_quality_analysis.json`. The frozen trace shows selected ASK actions
were present in the persisted candidate list, but it does not persist rejected
candidate reasons; exact “gate blocked” counts are therefore not observable.
The dominant observed clusters are extraction failure and sufficiency/requirement
over-collection, not a proven policy-only regression.

## Step Effectiveness

- **Step 7.1:** diary projection contradictions and unsupported user-fact critical failures were not observed in this run, but explicit-fact omissions and repeated ASK persist in model-facing traces.
- **Step 7.2:** the trace cannot count rejected ASK candidates; selected ASK actions passed the gate, while 43/112 were classified irrelevant and 39/112 redundant.
- **Step 7.3:** DA-04/DA-08 historical diary contradictions were not observed in this run. This is a run-specific observation, not proof of general resolution. No new critical grounding failure was observed.

## Largest Deltas

### Five largest improvements
- `V2-CA-05`: delta +70; path ['ASK', 'ASK', 'ASK', 'ASK', 'ASK', 'ASK'] → ['ASK', 'RETRIEVE', 'ANSWER']; attribution `combined_effect`.
- `V2-PD-09`: delta +42; path ['ASK', 'ASK', 'ASK', 'ASK', 'ASK', 'ASK'] → ['ASK', 'ASK', 'ASK', 'READ_DIARY', 'ANSWER']; attribution `combined_effect`.
- `V2-DA-04`: delta +30; path ['READ_DIARY', 'ANSWER'] → ['READ_DIARY', 'ANSWER']; attribution `combined_effect`.
- `V2-DA-08`: delta +30; path ['READ_DIARY', 'ANSWER'] → ['READ_DIARY', 'ANSWER']; attribution `combined_effect`.
- `V2-PD-07`: delta +28; path ['ASK', 'ASK', 'ASK', 'ASK', 'ASK', 'ASK'] → ['ASK', 'ASK', 'ASK', 'ASK', 'ANSWER']; attribution `combined_effect`.

### Five largest regressions
- `V2-KQ-06`: delta -52; path ['RETRIEVE', 'ANSWER'] → ['ASK', 'RETRIEVE', 'ANSWER']; attribution `combined_effect`.
- `V2-PD-10`: delta -45; path ['ASK', 'ASK', 'RETRIEVE', 'ANSWER'] → ['ASK', 'ASK', 'ASK', 'ASK', 'ASK', 'ASK']; attribution `combined_effect`.
- `V2-KQ-05`: delta -32; path ['ASK', 'ASK', 'ASK', 'RETRIEVE', 'ANSWER'] → ['ASK', 'ASK', 'ASK', 'RETRIEVE', 'ANSWER']; attribution `combined_effect`.
- `V2-CA-09`: delta -28; path ['RETRIEVE', 'ANSWER'] → ['ASK', 'RETRIEVE', 'ANSWER']; attribution `combined_effect`.
- `V2-CA-07`: delta -15; path ['ASK', 'RETRIEVE', 'ANSWER'] → ['ASK', 'ASK', 'ASK', 'ASK', 'ANSWER']; attribution `combined_effect`.

## Critical Failure Interpretation

V1 records 2 critical failures from the frozen historical reviewer file. V1.1
records 0 from the Step 7.4 offline first-pass review. Measurement is not fully
identical, so this must not be stated as a strict 2→0 causal reduction.

## V1.2 Candidate Research Directions (not implemented)

1. Persist rejected ASK-candidate reasons and a normalized question ledger so gate effectiveness is measurable.
2. Separate requirement schema completeness from goal-specific decision fields, especially for PD.
3. Add a model-independent extraction confidence/coverage audit before broad ASK generation.
4. Add paired diary summary fixtures with formal expected date windows and automated claim checks.

No V1.2 work was performed.
