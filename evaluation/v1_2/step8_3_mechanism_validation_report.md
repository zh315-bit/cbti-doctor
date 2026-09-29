# Step 8.3 — V1.2 Information Value Mechanism Validation

## Scope and result

This is a controlled mechanism validation, not a Benchmark run. It did not run
V2, create/view V3, call an LLM, or change Agent behavior. **Mechanism
validation passed: 18 / 18 scenarios.** The 12 requested A–L scenarios are
included, plus four diminishing-return checkpoints and a counterfactual pair.

| Scenario | Expected / observed behavior | Value | Cost | Selected | Stop reason | Result |
| --- | --- | --- | --- | --- | --- | --- |
| A | irrelevant missing field → no ASK | NONE | MEDIUM | ANSWER | — | PASS |
| B | detail-only gap → bounded answer | LOW | MEDIUM | ANSWER | — | PASS |
| C | scope-changing gap → early ASK | MEDIUM | LOW | ASK | — | PASS |
| D | decision-changing timing gap → ASK | HIGH | LOW | ASK | — | PASS |
| E–F | approximate/range timing is sufficient | NONE | LOW | ANSWER | — | PASS |
| G | semantic-repeat gap → no repeat | NONE | LOW | ANSWER | no remaining information value justified acquisition cost | PASS |
| H | authorized unread diary dominates ASK | HIGH | LOW | READ_DIARY | — | PASS |
| I | unavailable diary is not retried | NONE | MEDIUM | ANSWER | — | PASS |
| J | HIGH value survives five prior ASK | HIGH | LOW | ASK | — | PASS |
| K | MEDIUM after three ASK is rejected | MEDIUM | LOW | ANSWER | no remaining information value justified acquisition cost | PASS |
| L | missing but no worthwhile acquisition → bounded answer | NONE | LOW | ANSWER | no remaining information value justified acquisition cost | PASS |

The separate diminishing-return series confirms the same MEDIUM candidate is
accepted at 0 and 1 prior ASK, then rejected at 3 and 5; the HIGH case in J
continues to pass at 5. The counterfactual pair holds the missing field
`caffeine` constant: it is LOW/ANSWER for general education and HIGH/ASK when
the goal explicitly concerns caffeine's effect on tonight's sleep. Thus value is
observably goal/state/context dependent, not a fixed field label.

## Observability

Every trace records the direct `information_value` estimate (target, level,
decision impact, acquisition cost, resource alternative and rationale), complete
candidate actions, selected action, stop reason, and rejected information where
candidate generation considered and rejected an acquisition. `considered_information`
is intentionally empty in irrelevant/secondary-only states because those fields
are outside `decision_relevant_missing`; this is not an always-empty field and
the direct estimate makes the reason inspectable. Rejections in G/K/L include a
stable reason; H records both the diary alternative and rejected ASK.

## Historical failure-pattern check

| Pattern | Finding | Boundary |
| --- | --- | --- |
| repeated explicit-fact ASK | handles correctly **if** fact/provenance reaches State (G) | cannot determine extraction reliability from this state-only suite |
| irrelevant requirement-driven ASK | handles correctly (A/B) | no real user-language extraction tested |
| excessive personalized-decision gathering | MEDIUM is stopped after accumulated ASK; HIGH remains eligible (J/K/M) | cannot determine behavior when multiple candidate fields are all classified HIGH |
| unavailable-resource retry | handles correctly (I) | validates resource state, not external tool transport |
| unnecessary precision refinement | handles correctly for approximate/range facts (E/F) | depends on those uncertainty annotations reaching State |

## Test result and limitations

`tests/test_v1_2_mechanism_validation.py` passed under the repository's
`unittest` runner. `pytest` is not installed in this environment. This stage
makes no claim about ASK reduction, benchmark score, V1.1 comparison, clinical
quality, or generalization. It validates only the stated V1.2 mechanism under
controlled State/Requirements inputs.
