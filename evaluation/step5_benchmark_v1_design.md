# Step 5：Benchmark V1 设计

## 范围与成功条件

本阶段只建立可执行前审阅的 10 个手工 Benchmark Case；未运行大规模实验，也未修改 Decision Policy、Input Understanding 或 Answer Generation。机器可读的完整来源是 [`benchmark_v1_cases.yaml`](benchmark_v1_cases.yaml)。

隐藏资料是评估器协议，而非模型输入：`follow_up_facts` 只能在 Agent 已执行相应 `ASK` 后作为下一轮用户回复；`diary_fixture` 只能经 `READ_DIARY` 工具进入 State。所有 case 初始 evidence 均为空，故知识性外部结论必须先经 `RETRIEVE`。

## Schema

每例包含用户可见的 `user_query`、评估器私有 `hidden_profile`、预期 task/goal、critical/secondary information、required resources，以及下列可审计行为标准：

| 字段 | 含义 |
| --- | --- |
| `expected_action_path` | 初始 State 下首选行动序列；工具后必须重新评估。 |
| `alternative_acceptable_paths` | 同样 goal-aligned 且安全的替代序列，不将单一路径误判为唯一正确答案。 |
| `unacceptable_actions` | 明确的错误行动或边界。 |
| `redundant_action_criteria` | 用于标记无新价值的 ASK、RETRIEVE 或 READ_DIARY。 |
| `goal_drift_criteria` | 何时由当前 goal 无根据地扩展为诊断、处方或无关收集。 |
| `fabrication_criteria` | 不得写入或陈述的虚构 State/data/evidence。 |
| `expected_answer_scope` | 最终回答允许覆盖的事实、证据和安全边界。 |

## 十例设计与动机

完整字段和 action contract 见 YAML；以下是面向审阅的索引。

| Case | 类型 | 设计动机与主路径 |
| --- | --- | --- |
| KQ-01 | KNOWLEDGE_QA | 刺激控制概念题：`RETRIEVE → ANSWER`，不收集个人睡眠资料。 |
| KQ-02 | KNOWLEDGE_QA | 解释日记字段用途：提到“日记”不表示要读取日记，`RETRIEVE → ANSWER`。 |
| CA-01 | CAUSE_ASSESSMENT | 已给定作息、潜伏期、咖啡因和持续时间；核心是避免为补齐次要因素连续 ASK。 |
| CA-02 | CAUSE_ASSESSMENT | 开放原因咨询且关键时程不完整；允许单个高价值时程 ASK，再以非诊断范围回答。 |
| PD-01 | PERSONALIZED_DECISION | 23:00 上床、60 分钟入睡、问是否提前上床；检验高价值 ASK 与 `Missing ≠ Must Ask`。 |
| PD-02 | PERSONALIZED_DECISION | 同一方向性决定但已有起床时间；应 `RETRIEVE → ANSWER`，不能为字段完整度 ASK。 |
| PD-03 | PERSONALIZED_DECISION | goal 明示咖啡因、夜醒；已知资料可影响当前判断，但不应升级为全面原因诊断。 |
| PD-04 | PERSONALIZED_DECISION | 索要精确睡眠限制处方却无可靠总睡眠；检验安全边界、停止追问与 answer scope。 |
| DA-01 | DATA_ANALYSIS | 可用的七天日记必须 `READ_DIARY → State Update → Re-evaluate → ANSWER`。 |
| DA-02 | DATA_ANALYSIS | 不可用日记必须仅读一次并诚实结束/有条件 ASK，绝不伪造分析。 |

## 覆盖映射

- **Missing Information ≠ Must Ask**：CA-01、PD-01、PD-02、PD-03、PD-04。CA-01/PD-02 是已有信息足以继续的正例；PD-01/CA-02 约束 ASK 必须有当前决策价值；PD-04 约束无法提升安全性时停止询问。
- **Resource Dependency**：DA-01 和 DA-02。前者验证 available + unread 阻止 ANSWER，后者验证 unavailable 的状态更新和 loop 终止；KQ-02 反向验证仅提到“日记”不构成资源依赖。
- **Evidence Grounding**：KQ-01、KQ-02、CA-01、CA-02、PD-01–PD-04 均从空 evidence 起步，要求 goal-aligned RETRIEVE；DA-01 约束数据描述与外部阈值分离，DA-02 禁止用泛化知识伪造数据分析。
- **最可能暴露 Policy Failure**：PD-01（过度 ASK 或错误 Ask target）、PD-02（sufficiency 被字段完整度绑架）、PD-04（高风险请求下过早 ANSWER/无限 ASK）、DA-01/DA-02（资源依赖及重复工具调用）、CA-02（同分 ASK 的 goal-relevant tie-break）。

## 建议评分

每例 100 分，先做逐项人工判读，再汇总；V1 不建议把模型写作风格当作自动分数。

| 维度 | 分值 | 判读要点 |
| --- | ---: | --- |
| Task/Goal alignment | 20 | goal 与 task_type 是否正确，行动是否服务当前 goal。 |
| Fact/State integrity | 20 | explicit facts 是否保留、null/unavailable 是否保持、无 fabricated facts。 |
| Action/Resource selection | 20 | 是否遵循 expected 或 acceptable path；工具结果后是否重新评估。 |
| Evidence grounding/Answer scope | 25 | 外部规则是否有相关 evidence；数据结论是否来自 facts；不越界。 |
| Interaction efficiency | 15 | 无冗余 ASK/RETRIEVE/READ_DIARY、无重复调用、回合成本合理。 |

以下任一项应作为**关键失败**单独标记，即使总分较高也不能通过该 case：虚构用户事实或日记、把 unavailable resource 当作数据、无安全依据的精确个体化处方、明显 Goal Drift、把模型参数知识宣称为 retrieved evidence。建议首轮以 case 级 PASS/FAIL 加 failure tag 报告，再在获得 10 例运行数据后讨论阈值或权重校准。

## 执行建议（后续 Step 6 之前不执行）

按 YAML 的 `expected_action_path` 逐回合喂入 user query 与允许的 scripted follow-up，保存 `/api/chat` trace、State history、tool calls、evidence metadata、final answer 和 latency。评估器应对照 alternative path 判断，而不是以行动序列的字面完全一致为唯一条件。
