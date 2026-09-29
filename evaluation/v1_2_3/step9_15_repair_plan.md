# Step 9.15 Repair Plan

## Priority order

### P1: Repair dependency formation

Implement a typed contract from goal semantics to dependencies. Education goals must create an evidence dependency; diary comparisons must create a diary resource dependency; personalized decisions must declare only the minimum decision dependencies. Add mixed-goal and negative tests, then inspect dependency completeness before candidate generation. Do not change Decision Policy in this step.

### P1: Repair diary projection contract

Define the canonical Tool Result -> State payload with raw entries, source/projected counts, dates, missing-day coverage, field provenance, and aggregation inputs. Keep the validator fail-closed. Add contract tests for complete, partial, unavailable, and malformed diary payloads. This is a separate P1 because it restores task completion without permitting fabricated values.

### P2: Revisit low-value information acquisition

After P1 repairs, re-audit the 55-ASK trace shape. Then narrow effective requirements, make provenance-backed facts available to missing detection, and require a counterfactual material-impact explanation before optional ASK. Only after those checks should ranking/value thresholds be adjusted. Negative tests must cover genuinely insufficient personalized decisions and hard validity preconditions.

### P3: Defer retrieval-support mismatch

Use a later trace study to distinguish retrieval coverage from answer claim binding. No implementation change is authorized in Step 9.15.

## Step 9.16 recommendation

Repair **Dependency Formation Failure (A)** only. It has the strongest combined safety, completion, interaction-cost, and generality case with a bounded repair surface. It also removes an upstream source of low-value ASK, making later ASK-quality measurement more interpretable. Do not implement B or C in Step 9.16 unless the user explicitly authorizes a broader scope.

