# Step 9.6 Regression Report

## Results

| Suite | Passed | Failed | Skipped | Not verified |
| --- | ---: | ---: | ---: | ---: |
| Step 9.6 S1–S12 synthetic suite | 12 | 0 | 0 | 0 |
| Non-external-model regression suite | 133 | 0 | 0 | 0 |
| `tests.test_model_configuration` | 0 | 0 | 0 | 1 |

The non-model suite includes Information Value, diminishing return, bounded
answer, ASK de-duplication, validity-critical state, DependencyResolver, hard
preconditions, Diary Contract V2, Tool→State projection, unavailable diary,
new-goal reset, follow-up merge, Step 9.4 audit, and Step 9.6 synthetic tests.

`tests.test_model_configuration` did not return output within the current
environment's 30-second execution window. It is therefore **NOT_VERIFIED**,
not passed and not failed. It remains a separate environment/integration issue.

## Required scope declarations

* Decision Policy modified: **NO**
* Information Value / Cost modified: **NO**
* Answer Generation modified: **NO**
* Diary Contract V2 semantics modified: **NO**
* Benchmark V2 run: **NO**
* Benchmark V3 accessed: **NO**
