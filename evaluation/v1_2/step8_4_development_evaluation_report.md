# Step 8.4 — V1.2 Development Evaluation on Benchmark V2

## Protocol

V2 is now a **development/regression set**, not held-out evidence. One frozen
V1.2 run used the saved source/rubric/Benchmark manifest in
`step8_4_freeze_manifest.json`; no Agent, Benchmark or rubric change occurred
afterward. V1 and V1.1 are historical artifacts and were not rerun.

## Observed results

| Metric | V1.1 historical | V1.2 development run |
| --- | ---: | ---: |
| Overall | 65.03 | 67.50 |
| ASK/case | 2.800 | 1.775 |
| redundant ASK | 34.8% | 35.2% |
| irrelevant ASK | 38.4% | 32.4% |
| PD ASK/case | 5.333 | 3.000 |
| six-ASK limit | 11 | 0 |
| Critical failures | 0 observed | 4 |

V1.2 task scores: KQ 83.50, CA 72.50, PD 52.08, DA 64.38. It used
RETRIEVE 0.350/case, READ_DIARY 0.200/case, 2.775 turns/case and 3.325
steps/case. Premature-answer review rate was 7.5%; unsupported personalization
was 0 observed; resource-skipping failure: DA-07. Tokens, LLM calls and latency
are `not_available`.

## Information-value observability

There were 465 considered ASK-information candidates: HIGH 158, MEDIUM 187,
NONE 120 (LOW 0). 214 were rejected (46.02%): 120
unknown/redundant/not-decision-relevant and 94 below the raised HIGH threshold.
There were 18 bounded-answer stops. Resource alternatives selected is 0 under
the strict observable definition; `low_value_acquisition_avoidance_rate` is
not_measurable because traces do not retain a unique denominator for that rate.

## Guardrail

Of 18 bounded stops, 15 were reviewed correct, KQ-02/KQ-05 harmful, and DA-07
harmful because it skipped an authorized required diary. Thus the mechanism
does prevent acquisition, but the guardrail demonstrates that stopping can be
wrong when evidence/resource requirements have not been satisfied.

## Interpretation

**Observed:** this one V2 development run has fewer ASK and no six-ASK paths,
but four critical diary-projection failures and three harmful stops.

**Supported:** V1.2's observable rejection and stop mechanisms materially alter
the action path; their behavior cannot be assessed solely by ASK count.

**Not yet supported:** held-out generalization, real-user performance, clinical
effectiveness, calibrated information value, or superiority over CTA. V2 is no
longer held out and this is a single stochastic development run.
