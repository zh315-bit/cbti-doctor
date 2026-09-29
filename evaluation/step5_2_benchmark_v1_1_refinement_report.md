# Step 5.2 Benchmark V1.1 Refinement Report

## 结论

Benchmark V1.1 已冻结为 **1.1**。本阶段只变更 benchmark definition、schema、scoring documentation 与 schema validation tooling；未运行 Agent，也未修改 Decision Policy、Input Understanding、Requirements、Sufficiency、Candidates、Answer Generation 或 RAG。

V1 原始 case 文件仍保留不动。Step 5.1 的历史基线同样保留：**Average Score = 83.8；Critical Failures = 1**。这些不是 V1.1 的新实验结果，也没有被重新解释或重算。

## 新增与修改的评估产物

| 文件 | 作用 |
| --- | --- |
| `evaluation/benchmark_v1_1.yaml` | V1.1 冻结 overlay：引用不变的 V1 十例，定义通道、日记合同、PD-04 替代路径、归因、critical failure 和评分字段。 |
| `evaluation/benchmark_v1_1_scoring.md` | 人工 reviewer 的维度评分、primary/downstream attribution 与关键失败记录规范。 |
| `evaluation/benchmark_v1_1_changelog.md` | V1 → V1.1 的变更及理由，并固定 V1 Pilot 历史基线。 |
| `scripts/validate_benchmark_v1_1.py` | 只加载和验证 YAML 叠加规格；不会导入或调用 Adaptive Agent。 |

## 1. 信息通道与 `hidden_profile.session_facts`

V1.1 明确分离五类信息：

| 通道 | Agent 在 case 开始时是否可见 | 进入 State 的唯一方式 |
| --- | --- | --- |
| `user_query_facts` | 是 | Input Understanding 从本轮字面 user query 提取。 |
| `initial_session_facts` | 仅 case 显式声明时 | 初始化 `AdaptiveAgentState.facts`。V1.1 十例均为 `{}`。 |
| `follow_up_facts` | 否 | 仅在实际 ASK 后，作为下一轮 user message 再经 Input Understanding。 |
| `diary_facts` | 否 | 成功 `READ_DIARY` 的 tool result。 |
| `evidence` | 否 | `RETRIEVE` 的 tool result；V1.1 初始为空。 |

旧 V1 `hidden_profile.session_facts` 的新语义为 `expected_user_query_facts`：它是 evaluator 的提取核对 oracle，而不是预置 session State，严禁因评估器知道它而注入 Agent。

## 2. DA-01 / DA-02 diary fixture contract

V1.1 固定资源状态机：

```text
available fixture + Agent resource=unread
→ READ_DIARY
→ available=true + canonical tool_return_facts
→ State merge + resource=loaded
→ re-evaluate
→ ANSWER / goal-relevant RETRIEVE → ANSWER

unavailable fixture + Agent resource=unread
→ READ_DIARY
→ available=false + facts={}
→ no merge + resource=unavailable
→ re-evaluate
→ limited ANSWER (or one explicit request for diary data)
```

DA-01 的 canonical return 严格是完整七条 `entries` 投影为 `recent_sleep_pattern`，不为了测试便利伪造汇总 bedtime、wake time、总睡眠或临床数值。DA-02 永远返回 `available=false, facts={}`。这保证 fixture 不改变正常的 Resource Dependency 行为。

## 3. PD-04 的 Information-Value ASK

V1.1 不再将唯一首问写死为 `total_sleep_time`。以下均可接受：总睡眠、夜醒、近期模式、可靠日记是否可用；前提是每次 ASK 对精确方案的安全性或 readiness 有当前的、可说明的决策价值。

仍不可接受：只因 YAML 排序指定而打分、继续询问已无新增信息价值的字段、把不存在的 diary 当可用、或在资料不足时给出具体上床时间/睡眠窗口/睡眠限制处方。

## 4. Failure Attribution 与评分

V1.1 增加十类 primary cause：`INPUT_UNDERSTANDING`、`STATE_INTEGRITY`、`SUFFICIENCY`、`ACTION_SELECTION`、`RESOURCE_SELECTION`、`RETRIEVAL`、`ANSWER_GROUNDING`、`GOAL_DRIFT`、`EFFICIENCY`、`BENCHMARK_AMBIGUITY`。

每条 failure record 必须有一个 `primary_cause`、可选 `downstream_effects`、`independent_failure` 和指向 trace 的 supporting evidence。五维分数仍反映可观察影响，但上游 explicit-fact 漏失不应让下游 ASK/turns 被重新算作完整独立 Policy failure；只有后续组件在当前实际 State 下自行违反契约，才是独立 failure。

## 5. Critical Failure

V1.1 强制保存：

```yaml
critical_failure: true_or_false
critical_failure_type: [] # false 时为空；true 时为一个或多个枚举值
supporting_trace: []      # true 时必须非空
```

类型包括：伪造用户事实、伪造日记、将 unavailable resource 当作真实数据、无证据的量化医学主张、回答与已知 State 矛盾、无支持的个体化治疗指令。Critical Failure 独立于 100 分，保留所有 dimension scores 供根因分析；绝不自动改成 0 分。

## 冻结验证

执行命令：

```text
.venv/bin/python scripts/validate_benchmark_v1_1.py
```

结果：V1.1 version 正确；解析到 10 个 base cases；任务配额为 2/2/4/2；PD-04 override 存在；DA-01/DA-02 的 required state transitions 齐全；failure attribution 与 critical type 枚举完整。该验证只读取 YAML，**没有运行 Agent**。

## 建议

V1.1 的设计现在足以支持一次可解释的同十例 rerun；但按照本阶段范围没有执行它，也不建议直接进入 Step 6。下一步应先验收 V1.1 规格，再决定是否进行一个仅用于验证评分稳定性的 10-case rerun。
