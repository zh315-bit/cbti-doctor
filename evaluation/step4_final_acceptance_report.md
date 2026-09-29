# Step 4 最终端到端验收报告（Step 4.1 后）

验收日期：2026-09-19（America/New_York）  
验收模式：受控离线 fixture；请求经真实 Flask `/api/chat`、session service 和 Adaptive Agent Loop。未调用外部 LLM API，也没有发送健康数据。

## 结论

**PASS（受控离线 Step 4 验收）**。三个核心案例均按目标驱动的状态循环完成，没有发现新的系统性 Policy 问题，完整测试套件无 unexpected failure。

本结论验证路由、状态、资源依赖、工具更新与决策边界；不把 fixture 的 `MOCK answer` 视为真实 LLM 的医学回答质量验证。`answer_scope` 已随状态传入回答生成器，且由单元测试覆盖。

## 测试结果

命令：

```text
.venv/bin/python -m unittest discover -s tests -v
```

结果：**41 passed，0 failed，0 skipped，0 expected failure**，50.691 秒。

此前由错误 Python 环境中 LangChain 依赖造成的 4 个 skipped tests 在项目 `.venv` 中不再存在；本轮也仅有一条 LangChain deprecation warning，不影响结果。

离线路由验收命令：

```text
.venv/bin/python scripts/validate_step4.py --offline --tag step4-final
```

输出目录：`evaluation/runs/step4-step4-final/`。`http-traces.jsonl` 按请求保存 input understanding、每一次 DECISION、tool result、更新后 State 和 HTTP 响应；同目录日期 JSONL 保存 evaluation run。

## Case 1 — PERSONALIZED_DECISION

输入：`我每天11点上床，一个小时才能睡着，我应该早点上床吗？`

```text
goal
  判断是否应该早点上床
task_type
  PERSONALIZED_DECISION
facts（首轮）
  bedtime=23:00, sleep_onset_latency=60
requirements
  critical=[bedtime, sleep_onset_latency, wake_time, total_sleep_time,
            nighttime_awakenings, recent_sleep_pattern]
  evidence_required=true
required_resources
  []
decision_missing / critical_missing
  [wake_time] / [wake_time, total_sleep_time, nighttime_awakenings,
                 recent_sleep_pattern]
sufficiency
  user=MEDIUM, evidence=LOW
candidate_actions → chosen_action
  ASK(wake_time, "你通常几点起床？") → ASK
tool_result / state_update
  无工具；保存 state，结束 HTTP 回合

第二轮 facts merge
  + wake_time=07:00；首轮 bedtime、sleep_onset_latency 保留
decision_missing / critical_missing
  [] / [total_sleep_time, nighttime_awakenings, recent_sleep_pattern]
sufficiency
  user=HIGH（方向性 answer_scope 已满足）, evidence=LOW
candidate_actions → chosen_action
  RETRIEVE(query="判断是否应该早点上床") → RETRIEVE
tool_result / state_update
  available mock evidence 写入 evidence；evidence=HIGH
next_decision → final_status
  ANSWER → ANSWER
answer_scope
  只讨论是否提前上床的方向与现有作息约束；不指定具体新上床时间、
  睡眠窗口或睡眠限制处方；不将未收集的总睡眠、夜醒、近期规律当作已知。
```

ASK 数为 **1**，target 为 `wake_time`。这不是次数上限：起床时间会改变“提前上床”这一方向判断的作息约束，故有直接决策价值；补完后其余三项虽仍是 critical missing，却不在这个狭窄 answer_scope 的 `decision_missing` 中，继续问预期收益不足。RETRIEVE 数为 1，READ_DIARY 数为 0。

检查结论：无 unnecessary ASK、unnecessary RETRIEVE、unnecessary READ_DIARY、Goal Drift、fabricated facts、premature ANSWER 或 repeated tool call。回答生成器接收上述 scope；fixture 仅验证 scope 的传递与流程终止，未宣称验证真实自然语言医学质量。

## Case 2 — KNOWLEDGE_QA

输入：`什么是刺激控制？为什么 CBT-I 要减少不必要的卧床时间？`

```text
goal → task_type
  解释刺激控制及减少不必要卧床的原因 → KNOWLEDGE_QA
facts
  {}
requirements / required_resources
  critical=[]；evidence_required=true / []
decision_missing / critical_missing
  [] / []
sufficiency
  user=HIGH, evidence=LOW
candidate_actions → chosen_action
  RETRIEVE(query="解释刺激控制及减少不必要卧床的原因") → RETRIEVE
tool_result → state_update
  available mock evidence → evidence=HIGH
next_decision → final_status
  ANSWER → ANSWER
answer_scope
  仅依据当前 goal 与检索 evidence 解释概念；不收集无关个人睡眠信息。
```

仅检索 1 次；未 ASK bedtime、stress、caffeine 等无关字段，且没有日记读取。无冗余行动、目标漂移、虚构事实、过早回答或重复工具调用。最终 ANSWER 的输入只含 goal、相关 evidence 和该范围。

## Case 3 — DATA_ANALYSIS

输入：`帮我分析最近7天的睡眠日记。`

### 日记可用

```text
goal → task_type
  分析最近7天的睡眠日记 → DATA_ANALYSIS
facts
  {}
requirements / required_resources
  resource=sleep_diary / [sleep_diary]
resource_status
  sleep_diary=unread
decision_missing / critical_missing
  [] / []（资源未读不是被伪装为 facts 的字段缺失）
sufficiency
  user=LOW（required resource 未加载）
candidate_actions → chosen_action
  READ_DIARY → READ_DIARY
tool_result → state_update
  available 日记 facts 合并到 State；sleep_diary=loaded
re-evaluate
  user=HIGH；无额外 evidence 需求
next_decision → final_status
  ANSWER → ANSWER
answer_scope
  只基于已加载的日记 facts 分析，未将缺失条目补全。
```

这证明资源依赖链为：`required_resource=sleep_diary → available + unread → READ_DIARY → facts enter State → loaded → re-evaluate → ANSWER`，而不是 `task_type` 到行动的硬编码。

### 日记不可用

```text
required_resources / resource_status
  [sleep_diary] / unread
chosen_action
  READ_DIARY
tool_result → state_update
  unavailable；不写入 diary facts；sleep_diary=unavailable
next_decision → final_status
  受限 ANSWER → ANSWER
answer_scope
  明确无法完成基于日记的分析，且不得生成分析结论。
```

不可用分支没有 fabricated diary facts，也没有第二次 READ_DIARY；这是合理的受限 ANSWER，不是把无数据误判为充分。

另行执行的 `case3-discovered` 也验证“初始标志未声明可用、但工具实际发现数据”时仍为一次 READ_DIARY 后 `loaded → ANSWER`。

## 跨案例检查

| 检查项 | Case 1 | Case 2 | Case 3（可用 / 不可用） |
| --- | --- | --- | --- |
| unnecessary ASK | 无 | 无 | 无 |
| unnecessary RETRIEVE | 无 | 无 | 无 / 无 |
| unnecessary READ_DIARY | 无 | 无 | 无 / 无 |
| Goal Drift | 无 | 无 | 无 / 无 |
| Fabricated Facts | 无 | 无 | 无 / 无 |
| Premature ANSWER | 无 | 无 | 无 / 无 |
| Repeated Tool Call | 无 | 无 | 无 / 无 |
| ANSWER 符合 answer_scope | 通过 scope 传递测试 | 通过 | 通过（不可用时为限制说明） |

## 技术债与边界

- 外部真实 LLM/RAG 的行为没有测试，原因是本阶段明确禁止向外部 API 发送健康测试数据；离线 fixture 不能证明模型的事实提取、证据相关性或语言层 scope 遵从。
- `sleep_diary=loaded` 表示读取成功，不代表已经验证恰好七天覆盖、日记质量或临床有效性。
- Policy 是 V1 的人工可解释规则；新目标类别需要继续以失败案例扩展，而不是以字段完整度代替目标判断。

## Step 5 建议

满足进入**离线、可控的 Step 5 Benchmark**的前提：核心三案例通过、完整套件无意外失败、轨迹已可复核。不要在本阶段自动进入 Step 5。

若未来 Benchmark 要评估真实 LLM/RAG，仍需单独取得允许使用何种合成/脱敏数据及外部服务的授权。
