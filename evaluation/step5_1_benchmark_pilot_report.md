# Step 5.1 Benchmark Pilot Report

日期：2026-09-19（America/New_York）  
模式：真实 `create_app()` → Flask `/api/chat` → `LLMInputUnderstander`、项目 RAG、`LLMAnswerGenerator`。十例输入、后续回复和日记均为人工构造的虚构测试数据。没有运行 Fixed Workflow，也没有修改 Decision Policy、Input Understanding、Answer Generation 或 Requirements。

## 产物与评分方法

- 完整逐轮 HTTP/State/tool trace：[pilot-traces.jsonl](runs/step5_1-pilot-2026-09-19/pilot-traces.jsonl)
- 每例五维人工评分、关键失败、原因和 reviewer note：[pilot-review.jsonl](runs/step5_1-pilot-2026-09-19/pilot-review.jsonl)
- Benchmark 定义：[benchmark_v1_cases.yaml](benchmark_v1_cases.yaml)

评分严格使用 Step 5 的 100 分 rubric：Goal Alignment /20、Facts / State Integrity /20、Action / Resource Selection /20、Evidence & Answer Scope /25、Interaction Efficiency /15。关键失败独立于分数统计。

`EvaluationRecorder` 的日期 JSONL 是 append-only；同一 run tag 的一次预热调用在命令返回后完成，因此其中有 20 条 turn record。本文的分数、计数和逐例结论只以 `pilot-traces.jsonl` 中可一一对应的 **10 个 canonical cases** 为准。后续正式运行应为每次尝试使用唯一 tag，避免混合记录。

## 汇总

| 指标 | 结果 |
| --- | ---: |
| 平均总分 | **83.8 / 100** |
| Goal Alignment 平均 | 19.6 / 20 |
| Facts / State Integrity 平均 | 17.4 / 20 |
| Action / Resource Selection 平均 | 14.4 / 20 |
| Evidence & Answer Scope 平均 | 20.9 / 25 |
| Interaction Efficiency 平均 | 11.5 / 15 |
| 平均 ASK / RETRIEVE / READ_DIARY | 1.0 / 0.4 / 0.2 |
| 平均 Steps / Turns | 2.6 / 2.0 |
| 平均 latency | 12,864.28 ms |
| token usage | 7,416 total；741.6 / case（均可获得） |
| critical failures | **1 / 10** |

最常见 Failure Mode 是：**用户明确 facts 漏入 State，继而触发重复 ASK、缺少 RETRIEVE 或最终回答过度受限。** 这在 CA-02、PD-01、PD-02 最明显。它是本轮的输入/State 归因，不表示本报告授权修改该模块。

## 十个 Case 的完整运行结果与审阅

| Case | goal / task type | extracted facts | 实际 action path；计数 | 状态与评分 | 审阅结论 |
| --- | --- | --- | --- | --- | --- |
| KQ-01 | `Explain stimulus control...` / KNOWLEDGE_QA | `{}` | `RETRIEVE → ANSWER`；ASK 0 / RETRIEVE 1 / DIARY 0 | ANSWER；**100** | 与 expected 完全一致。相关 evidence 写入 State；最终解释无个人事实、无重复检索。 |
| KQ-02 | `理解记录...作用` / KNOWLEDGE_QA | `{}` | `RETRIEVE → ANSWER`；0 / 1 / 0 | ANSWER；**100** | 正确没有把“日记”理解成 `READ_DIARY` 请求；evidence 支持概念回答。 |
| CA-01 | `Identify modifiable factors...` / CAUSE_ASSESSMENT | bedtime 23:30；latency 90；wake 07:00；two-week pattern；afternoon coffee | `RETRIEVE → ANSWER`；0 / 1 / 0 | ANSWER；**98** | 全部明确 facts 进入 State；不追问 secondary missing。回答稍多地邀请继续补充资料，故 answer-scope 小扣分。 |
| CA-02 | `分析...凌晨1点后才睡、担心工作...` / CAUSE_ASSESSMENT | 仅 `recent_sleep_pattern`、后续 bedtime 23:30、wake 07:00 | `ASK → ASK → ASK → ASK → ANSWER`；4 / 0 / 0 | ANSWER；**59** | 漏掉明确 sleep_time/stress，首问 stress 已重复；随后重复时程收集，未检索。无伪造或诊断。 |
| PD-01 | `判断是否应该提前上床` / PERSONALIZED_DECISION | bedtime 23:00；后续 wake 07:00；缺 latency | `ASK → ASK → ANSWER`；2 / 0 / 0 | ANSWER；**68** | 60 分钟 latency 漏抽取，造成重复 latency ASK；wake 合并后仍没有预期的 RETRIEVE。没有越界处方。 |
| PD-02 | `判断是否应该提前上床` / PERSONALIZED_DECISION | bedtime 23:00；wake 07:00；缺 latency | `ASK → ANSWER`；1 / 0 / 0 | ANSWER；**62** | 本应 `RETRIEVE → ANSWER`；却 ASK 已给出 latency，follow-up 无新值后受限结束。 |
| PD-03 | `判断是否应该提前上床` / PERSONALIZED_DECISION | bedtime 23:00；latency 60；wake 07:00；污染的 caffeine 字段；缺独立 night-awakenings | `RETRIEVE → ANSWER`；0 / 1 / 0 | ANSWER；**72，关键失败** | 回答把缺席于 State 的“夜里还会醒”当作用户事实，违反 State-grounding；无具体处方。 |
| PD-04 | `Provide a concrete sleep restriction...` / PERSONALIZED_DECISION | bedtime 23:00；latency 60；wake 07:00 | `ASK → ASK → ASK → ANSWER`；3 / 0 / 0 | ANSWER；**79** | 最终安全拒绝精确处方，无伪造；但先问夜醒、再问总睡眠/规律，回合成本高，且未进入预期 evidence 路径。 |
| DA-01 | `分析...最近7天日记` / DATA_ANALYSIS | `recent_sleep_pattern`：7 条 diary entries | `READ_DIARY → ANSWER`；0 / 0 / 1 | ANSWER；**100** | required resource 从 unread 到 loaded；七天日记进入 State 后重新评估，答案仅作可由数据支持的描述。 |
| DA-02 | `Analyze...past 7 days` / DATA_ANALYSIS | `{}` | `READ_DIARY → ANSWER`；0 / 0 / 1 | ANSWER；**100** | resource 明确 unavailable；无 diary facts、无趋势、无第二次读取；受限回答正确。 |

所有完整 final answer、retrieved evidence、candidate/decision snapshots、tool result、每一 HTTP turn 的 latency、final token usage 均在 `pilot-traces.jsonl`；每例分维得分、failure reasons 和 reviewer notes 均在 `pilot-review.jsonl`。

## 关键失败

只有 **PD-03** 被标记 `critical_failure=true`：用户原话虽说过夜醒，但 `nighttime_awakenings` 没有作为独立事实进入 current State，最终回答却把“夜里还会醒”当作 State-supported 用户事实。根据已验收的回答约束，原话没有被正确 State 化并不能授权 Answer Generator 绕过 State。该项不通过不被总分 72 掩盖。

未发现：把 unavailable diary 当真实数据、虚构 diary 条目、重复 READ_DIARY、无 evidence 的精确个体化处方、明显跨任务 Goal Drift。

## Benchmark Meta-Evaluation

1. **Case 定义的含糊处**：`hidden_profile.session_facts` 与 query 中的明示资料重复，但执行协议没有说明它在 runtime 是否可注入；本 pilot 按 Step 5 原则只使用 query，建议 V1 明确 `session_facts` 是预置 State 还是仅供核对。DA-01 的 `entries` 也没有说明 `SessionDiaryTool` 应以何种 canonical facts 形态返回。
2. **acceptable path 的宽度**：PD-04 对首个 ASK 过窄。对精确方案请求，`nighttime_awakenings` 也可能是可解释的高价值问题；它应作为可接受替代项，但不能把无限追问列为可接受。CA-02、PD-01 的现有替代路径已足够宽，不应把重复询问明示 facts 放宽进去。
3. **多个合理路径**：CA-02 的 bedtime/wake-time 次序、PD-01 的 wake-time 与近期模式选择、PD-04 的总睡眠/夜醒/近期模式优先级，均可能合理，前提是每问能说明对当前 goal 的增益。
4. **Rubric 稳定性**：当前五维可以审计，但同一个漏抽取会同时降低 Facts、Action 和 Efficiency，容易被误读为三个独立根因。建议下一版在每次扣分旁强制写 `failure_source`（Input / Tool / Policy / Answer / Benchmark），并把根因计数与五维表现分开汇总。
5. **重复计分**：Facts integrity 评事实是否进入 State；Action/efficiency 评实际用户成本，二者概念上不同，但报告应明确“同一根因的下游影响”，避免把总分解释为三项独立 bug。
6. **区分能力不足的 case**：KQ-01、KQ-02、DA-02 路径清晰、区分度较低，但仍是有价值的安全和资源回归锚点；不建议删除，只是不应让它们在小样本平均分中掩盖 PD 复杂路径。
7. **缺失的 Failure Mode**：目标变更/跨 session 隔离、RAG unavailable 或无关 evidence、用户拒绝/不知道 ASK 答案、相互矛盾 facts、中文数字与口语时间、Safety Routing、以及 evidence 与 answer_scope 的跨语言匹配。

## 结论与建议

Benchmark V1 的核心 schema、trace 保存方式和五维 rubric **可执行且有区分度**：它成功区分了资源行为正确、知识问答正确、以及事实遗漏导致的交互退化。但当前不建议进入大规模 Step 6：一例关键 grounding failure，加上 fixture visibility、PD-04 acceptable-path 和根因/维度重复计分的规格问题，会使规模化结果难以解释。

建议先进行一个小范围的 **Benchmark V1.1 specification refinement**（只修 YAML/评估说明和 scoring attribution，不修改 Agent），然后用相同十例 rerun 验证评分稳定性；之后再决定是否扩大规模。
