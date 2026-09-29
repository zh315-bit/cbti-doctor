# Step 6.1 — Frozen Adaptive V1 on Benchmark V2

V2 was frozen before execution: 40 cases, SHA-256
`dfa9b9e5a12b0017fa68d344d01b313ebc29e583b933fbe1e93c125f55ecafd2`.
Adaptive V1 completed all 40 unchanged. This is independent V2 evidence and is
not combined with V1.1 historical/development results.

| Result | Value |
| --- | ---: |
| Overall score | 63.85 / 100 |
| Critical failures | 2 / 40 |
| ASK / RETRIEVE / READ_DIARY per case | 2.775 / 0.325 / 0.175 |
| Tool calls / turns / steps | 0.50 / 3.45 / 3.95 |
| observed total latency | 8,551.2 ms/case |

Dimension means: Goal 18.02/20; Facts/State 13.10/20; Action/Resource
10.90/20; Evidence/Scope 13.10/25; Efficiency 8.72/15. Tokens, exact LLM
calls, and component latency are `not_available`.

KQ averaged 91.5; CA 65.4; PD 31.67; DA 75.62. The V1 repeated-ASK/state
integrity failure naturally recurred: 13 cases exhausted six ASK turns and PD
averaged 5.42 asks/case. Seven DA cases read the diary, but DA-04/08 expose a
novel fixture-projection/answer contradiction.

The traces support strong knowledge-QA behavior and poor personalized-decision
interaction efficiency. The 40 synthetic cases justify an explicitly authorized
V1.1 development and paired plan, but do not establish real-world quality.
