# Step 9.22 — V3 Failure Validation & Repair Boundary

本阶段仅复核已经完成且不可重跑的 V3 正式轨迹、case results，以及 Step 9.19 前冻结的 rubric/metric definitions。Step 9.21 的分数和失败标记保持原样：Overall 60.91/100，Critical 1，按冻结窄定义 Harmful 6。本报告细化首个偏离层，**不是**新评测或修改旧评分。原始模型请求体和完整未投影工具 payload 未记录；以下凡涉及这两项均区分“轨迹直接可见”和“由冻结代码重建”。

## 1. 19 次低价值 ASK 的逐次审计

完整逐条机器可读表见 `step9_22_ask_failure_audit.json`：每条保存 case/turn、原始问题、选中动作前的 goal/facts/missing/sufficiency、用户已提供信息、effective requirements、active dependencies、全部候选、选中候选的 information value/cost/gate 和 trace pointer。下表保留判读索引；`IU`=INPUT_UNDERSTANDING_MISS，`IV`=INFORMATION_VALUE_OVERESTIMATED，`WD`=WRONG_DEPENDENCY。

| Case / turn | ASK question | 冻结标签 | 首要根因 |
|---|---|---|---|
| CA-01 / 1 | 你通常几点上床？ | irrelevant | IV |
| CA-01 / 3 | 你通常几点起床？ | irrelevant | IV |
| CA-03 / 1 | 你通常几点上床？ | irrelevant | IV |
| CA-03 / 3 | 你通常几点起床？ | irrelevant | IV |
| CA-05 / 3 | 你通常几点入睡，或大约需要多久才能睡着？ | redundant | IU |
| CA-07 / 2 | 你通常几点入睡，或大约需要多久才能睡着？ | redundant | IU |
| CA-07 / 3 | 你通常几点上床？ | irrelevant | IV |
| CA-07 / 4 | 你通常几点起床？ | irrelevant | IV |
| PD-01 / 1 | 你通常几点上床？ | irrelevant | IV |
| PD-01 / 2 | 你上床后通常需要多久才能睡着？ | irrelevant | IV |
| PD-03 / 3 | 你通常几点起床？ | redundant | IU |
| PD-04 / 1 | 你上床后通常需要多久才能睡着？ | irrelevant | WD |
| PD-05 / 1 | 你上床后通常需要多久才能睡着？ | redundant | IU |
| PD-05 / 2 | 你通常几点上床？ | redundant | IU |
| PD-05 / 3 | 你通常几点起床？ | redundant | IU |
| PD-07 / 1 | 你通常几点上床？ | irrelevant | IV |
| PD-07 / 2 | 你上床后通常需要多久才能睡着？ | irrelevant | IV |
| PD-08 / 1 | 你通常几点上床？ | irrelevant | IV |
| PD-08 / 2 | 你上床后通常需要多久才能睡着？ | irrelevant | IV |

按**逐次 ASK 的近端首要根因**：IV 12、IU 6、WD 1，总计 19；不把同一次 ASK 同时计成 State、Candidate、Policy 三次失败。6 次是用户已说过相关事实、但目标字段或其等价语义未在 State（CA-05、CA-07、PD-03、PD-05×3）。19 次的 effective requirement 仍为 `useful_optional` 17 次、`mandatory` 2 次；这说明低价值追问并非从空白需求产生，但“不该获取”不能只由 requirement membership 判定。已满足 dependency 后仍 ASK：0；IV gate 本身作为首要根因：12；Decision Policy 选中一个已通过 gate 的候选作为独立错误：0。PD-04 首轮 latency 被错误升为 `VALIDITY_STATE` hard precondition，不应再将其归为普通 IV 判断。

## 2. 六个 Harmful Failure 的完整链

逐案的 User Input → Input Understanding → Facts/State → Requirements → Dependency → Candidates/Policy → Tool → State Update → Answer Context → Final Answer 见 `step9_22_harmful_failure_chains.json`。其每一层均保留轨迹或明确标为无法直接观测。

| Case | First divergence | 下游链，不重复算根因 |
|---|---|---|
| CA-01 | Input Understanding：工作赶项目/浅睡背景未结构化 | State 为空；USER_FACTS deferred；bedtime/wake 等可选项被 HIGH 接纳；三次 ASK 后回答不完整 |
| CA-03 | Information Value Gate：Goal 已保留“光照变化 vs 过度关注睡眠”的比较 | 可选 bedtime/wake 被标作 decision-changing，连续无关追问；情境 facts 缺失是并存问题，不是这两问必然前提 |
| CA-07 | Information Value Gate：Goal 已保留“单次争吵能否证明长期原因” | 仍给 bedtime/wake HIGH；一次入睡困难事实遗漏另造成冗余追问 |
| PD-01 | Information Value Gate：Goal 已保留“偶发一晚是否立即整体调整” | 两次无关时间追问；之后虽检索到可用证据，回答上下文又过滤掉，属于独立后续失败 |
| PD-07 | Information Value Gate：Goal 和已有 session wake time 足以讨论单次漏闹钟 | bedtime/latency 被 HIGH 接纳；无工具；最终答案可以更早受限给出 |
| PD-08 | Input Understanding：两晚短睡及白天困意未结构化 | State 看似空；bedtime/latency 高值追问；最终受限但未有效回答闹钟问题 |

上述“首个偏离”是**每个 Harmful case 的整体传播链**；与逐次 ASK 的近端主因不同。例如 CA-01、PD-08 先发生 State 语境遗漏，但具体 bedtime/latency 问题在已有 Goal 下仍表现为 IV 高估。不能仅凭最终回答薄弱就统一归因为 Answer Generation，也不能因几例 IV 问题就声称整个 Decision Policy 错误。

## 3. 唯一 Critical 的取证结论：DA-08

`READ_DIARY` 的 `tool_result_id=tool_goal_t1_r1_1`；正式 trace 未保留完整未投影的原始 tool payload，但收到的 metadata 表明 5 条、五个日期。投影 `state_update_id=upd_goal_t1_r2_1`，`ENTRY_SHAPED`、`projection_status=valid`、source/projected=5/5、日期完全一致、provenance=`session_diary`、warning 为空。State 的 `recent_sleep_pattern` 明确有 `2026-09-04` 条目，只是它没有 `total_sleep_time`；其余四条为 384、360、408、372 分钟，确定性平均 381 分钟，分母 4。

语义边界：`valid` 指条目/来源投影通过契约；`invalid` 指契约无法验证（本例不是）；`missing` 在本例仅指**现有条目的时长字段缺失**，并非日期或整条记录缺失。冻结 `answer_generation.py` 的构造路径会在投影 valid 时把 diary facts、derived claims、provenance 传入回答上下文；State 的 claim provenance 亦列有“5 天记录、5 日期、381 分钟”。精确发给模型的 human message 没有存入 trace，因此这一步是由代码与 State 重建，不冒充直接观测。最终答案的确定性前缀仍正确，随后写出“其中 2026-09-04 的记录缺失”，首次把字段缺失错误映射为记录缺失。因此在给定五选项中，最有证据支持的主因是 **Answer Generation**，而不是 Tool Contract、Tool→State Projection 或 State Semantics；对 Answer Context Construction 的排除受“prompt body 未日志化”这一可观测性限制约束。Critical type 仍为冻结的 `ANSWER_CONTRADICTS_KNOWN_STATE`，不因高五维分而消除。

## 4. RETRIEVE 后证据未使用

12 例执行 RETRIEVE 且 State 有 evidence；无 evidence 投影丢失。KQ-05、CA-08 的最终回答实质使用证据。KQ-07 的材料缺两术语直接定义，有限回答可合理不采纳不足以支持概念区分的内容，归为 legitimate nonuse。其余 **9 例**（KQ-01/02/03/04/06/08、CA-04/06、PD-01）虽有 State evidence，却因冻结 `relevant_evidence(goal, evidence)` 仅按少数词面 goal terms 筛选、且这些 goal 没有匹配词，得到空回答证据列表；`claim_provenance` 中亦没有 evidence-grounded 条目。最终回答多称“无证据”。这是 **C：evidence stored but not included in answer context**，不是 B 投影失败，也没有 trace 支持 D“模型看到了相关证据却忽略”。A 无完全不相关项；KQ-07 为直接支持不足而合法受限，不算 grounding failure。统计：`retrieved_evidence_cases=12`，`evidence_projection_failures=0`，`answer_context_failures=9`，`answer_generation_grounding_failures=0`，`legitimate_nonuse=1`，`material_use=2`。这里 `TRUE_GROUNDING_FAILURES=9` 指真实的上下文/证据衔接失败，**不**指九次模型无视证据。逐例分类与 excerpt 在 `step9_22_evidence_usage_analysis.json`。

## 5. V2→V3 失败家族，而非配对评分

`step9_22_failure_family_comparison.json` 对八类给出 V2/V3 证据和判定：Dependency Formation **REDUCED**（V3 KQ 8/8 形成 evidence、DA 8/8 读 diary，但 DA-07 假 diary dependency、PD-04 可疑 validity dependency）；Tool→State Projection **NOT_EVALUABLE**（V2 的 summary-shaped mismatch 在 V3 的 entry-shaped 样本上未被重测）；Explicit Fact Missing from State、Low-Value ASK、Evidence Retrieved but Unused、Bounded Answer Failure 均 **PERSISTENT**；Answer-layer Semantic Distortion（DA-08）为 **NEW**；Resource Unavailable Handling 作为失败家族 **NOT_EVALUABLE**，但两套数据都观察到 fail-closed，无伪造或重复不可用调用。V2 的 47.27% 和 V3 的 48.72% 低价值 ASK 比例来自不同 case set，不支持因果升降结论。

## 6. 修复边界，只设计不实施

候选修复详见 `step9_22_repair_boundary.json`：P1 为显式事实/语义的有来源结构化、回答上下文的跨语言证据相关性、最终 claim→State 一致性、以及真正 validity-critical 的 dependency 边界；P2 为可选信息的目标特定反事实价值及有效需求优先级；P3 为有效日记上的确定性极值/分组比较/缺日描述。每项均列目标模块、V3 证据、预期效果、过度修复风险、是否改 Policy 及后续评估要求。不得对 V3 case ID 或句式写分支。

**V3 从正式评估结果被查看和用于失败分析起，未来只能作为 development/regression evidence，不再是后续修复版的 final held-out。** 若以后需要新的泛化结论，必须在通用修复完成、重新冻结 Agent 与评估协议之后再构建新的 V4 留出集；本阶段不构建、不查看 V4，也不修改任何系统。

本阶段仅新增七个分析文件并追加 `record.md`。没有运行 Agent、Benchmark 或模型；原始 ledger、V3、Agent、评分、Harness、Metrics 与 One-shot Rules 均未改动。
