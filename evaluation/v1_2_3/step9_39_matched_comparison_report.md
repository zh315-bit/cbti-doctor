# Step 9.39 — Baseline vs Treatment Matched Comparison

Comparison integrity: **PASS**. This is a post-hoc, case-matched comparison against a frozen baseline, not a randomized trial or causal estimate.

- Overall: 70.5 → 79.625 (delta +9.1250).
- Task means: KNOWLEDGE_QA: 82.2 → 82.2 (+0.0); CAUSE_ASSESSMENT: 59.1 → 79.1 (+19.999999999999993); PERSONALIZED_DECISION: 62.6 → 74.4 (+11.800000000000004); DATA_ANALYSIS: 78.1 → 82.8 (+4.700000000000003).
- Dimension means: action_resource_selection: 13.9 → 18.475 (+4.575); evidence_answer_scope: 15.5 → 16.575 (+1.075); facts_state_integrity: 16.1 → 17.325 (+1.225); goal_alignment: 13.675 → 15.875 (+2.2); interaction_efficiency: 11.325 → 11.375 (+0.05).
- Completion: 16/40 (40.00%) → 20/40 (50.00%); delta +10.00% (+4 cases).
- Validity: 37/40 (92.50%) → 38/40 (95.00%); delta +2.50%.
- Count distinction: all 40 treatment adjudication records are structurally valid (`valid_case_count=40`); the separate reviewer answer-validity judgment is 38/40 (95%), not 40/40. The frozen treatment aggregate is authoritative for this comparison.
- Low-value ASK rate: 1.0000 → 0.6154; delta -0.3846 (-38.46 percentage points).
- Necessary-target preservation (M4): 1/4 → 1/4; unchanged. Event-level necessary ASK labels are a separate count.
- Harmful failures: 16/40 → 1/40; delta -15 cases; relative change -93.75%.
- Critical failures: 0/40 → 2/40; delta +2 cases (+5.00 pp). This is a frozen-policy safety regression.
- Completion transitions: fail→pass 5; pass→fail 1; pass→pass 15; fail→fail 19.
- Harmful transitions: yes→no 15; no→yes 0. Critical: yes→no 0; no→yes 2.

## Observed improvements

Overall score, completion, validity, low-value ASK rate, harmful-failure count, and CA/PD/DA task means moved in the favorable direction; KQ was unchanged. These are descriptive matched observations only.

## Observed regressions and tradeoffs

Critical failures increased from 0 to 2 (cases: V4-PD-06, V4-PD-08). This fails the frozen M5 non-increase condition and blocks comparative resume claims. Completion regressions: V4-DA-08. Validity regressions: V4-PD-06, V4-PD-08. Harmful-failure regressions: none. New/increased low-value ASK cases: V4-PD-05.
Necessary ASK target discordance: lost `V4-PD-03`; gained `V4-PD-01`. Aggregate M4 stayed at 1/4, but the target-level loss/gain is disclosed. Tool calls/case changed 0.575 → 1.025; turns/case 1.225 → 1.325; latency 6453.3615 → 9658.0275 ms. These are operational tradeoffs, not independently scored quality claims.

## Claim policy

RESUME_DESCRIPTIVE_MATCHED_COMPARATIVE_CLAIM_ELIGIBLE = **NO**. Exact blocker: M5 critical failures increased, which the frozen policy says cannot be offset by gains in other metrics. M1/M2/M3 are directionally improved; M4 is unchanged; M5 regressed.

## Limits and next path

No causal effect, randomized treatment effect, statistical significance, clinical effectiveness/safety improvement, or unseen-benchmark generalization is supported. V4 is development/postmortem matched-regression evidence; new generalization claims require sealed V5.
Recommended next path: **B. Repair the critical-failure regression before V5.** No next step was executed.

The 40 case transition rows contain IDs and frozen labels/telemetry only; no prompts, answers, evidence, or rationales.
