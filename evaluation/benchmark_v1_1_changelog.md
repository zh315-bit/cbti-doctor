# Benchmark Changelog：V1 → V1.1

V1.1 不改变十个原始 user query、目标、Agent、RAG 或 Step 5.1 的结果；它只修订 benchmark/evaluation contract。

| 变更 | V1 问题 | V1.1 修订原因 |
| --- | --- | --- |
| 版本与继承 | `benchmark_v1_cases.yaml` 是唯一设计来源。 | 新增冻结 overlay `benchmark_v1_1.yaml`，明确引用 V1 baseline，保留历史结果。 |
| 信息通道 | `hidden_profile.session_facts` 可能被误解为运行时 State。 | 定义 user query、initial session、follow-up、diary、evidence 五个通道；legacy `session_facts` 仅为 evaluator oracle。 |
| 日记 fixture | entries 与 SessionDiaryTool 的 canonical facts 映射未说明。 | 定义 available/unread/loaded/unavailable、DA-01 unchanged entry projection、DA-02 empty unavailable result 与必经状态转换。 |
| PD-04 ASK | 首个 ASK 被写得过于固定。 | 按 Information Value 接受总睡眠、夜醒、近期模式或日记可用性的合理路径；禁止无价值追问或无依据处方。 |
| Failure Attribution | 同一漏抽取会同时拉低 facts、action、efficiency，易误读为多个根因。 | 增加 primary cause、downstream effects、independent failure 与 trace evidence。 |
| Critical Failure | 仅在报告叙述中出现。 | 固定布尔值、类型列表和 supporting trace；明确它独立于 100 分。 |
| 工具验证 | V1 只校验 YAML 基本字段。 | 新增 V1.1 resolver/validator，验证 overlay、10 例、PD-04 override 和 diary contract，不运行 Agent。 |

## 保留的 V1 Pilot 基线

`Average Score = 83.8`，`Critical Failures = 1`，来源为 `evaluation/runs/step5_1-pilot-2026-09-19/pilot-review.jsonl`。这不是 V1.1 rerun，也不因本次评分规范变更而重算。
