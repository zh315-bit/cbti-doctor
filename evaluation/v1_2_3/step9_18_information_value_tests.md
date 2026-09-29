# Step 9.18 — Information Value Mechanism Tests

`tests/test_step9_18_information_value_gate.py` contains 17 offline synthetic tests. The matrix covers:

| Mechanism | Validation |
|---|---|
| Under-acquisition guard | Decision-critical ASK survives; validity-critical personalized fact survives; unresolved evidence still RETRIEVEs; required diary still READ_DIARYs; answer-scope-changing fact remains acquirable. |
| Over-acquisition guard | Sufficient answer with only secondary missing data does not ASK; unrelated/known/equivalent facts do not prompt duplicate ASK; no evidence/diary dependency means no corresponding tool acquisition; loaded/unavailable diary is not retried. |
| Cost and value | Low-value optional ASK with high interaction cost is rejected to bounded ANSWER. |
| Counterfactual | The same missing caffeine field has different value when requirements/goal context changes. |
| Trace | All required components/reasons are present; trace states heuristic is not calibrated and contains no fabricated numeric probability. |

Run: `.venv/bin/python -m unittest tests.test_step9_18_information_value_gate`

Result: **17 passed / 0 failed**. The combined relevant focused suite, including prior Information Value, sufficiency, policy, dependency, projection, answer-grounding, lineage and authorization coverage, passed **115 tests**.

No Benchmark cases, external model, external RAG, or V3 artifacts were used.
