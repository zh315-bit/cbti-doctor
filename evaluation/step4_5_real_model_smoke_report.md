# Step 4.5 Real-Model Smoke Test Report

日期：2026-09-19（America/New_York）  
数据声明：五个请求和全部七天日记均为人工构造的虚构测试数据；没有发送任何真实健康信息。  
路径：真实 `create_app()` → `/api/chat` → 真实 `LLMInputUnderstander`、`RagRetrievalTool`、`LLMAnswerGenerator`。Decision Policy 未改动。

## 总结

最终真实模型冒烟结果为 **2 PASS / 3 FAIL**。PASS 为知识问答和日记分析；三个失败均是模型结构化事实提取遗漏，导致后续 Policy 基于错误 State 发起不必要的 ASK。没有证据表明现有 Decision Policy 存在新的系统性问题。

第一次运行在任何业务决策前全部 HTTP 500：当前 `langchain-openai` 默认 `json_schema` structured-output mode 发出了该 DeepSeek endpoint 不支持的 `response_format`。这是 Input Understanding adapter 兼容性问题。最小修复是 `LLMInputUnderstander` 显式使用 `method="function_calling"`，并新增回归测试；修复后真实模型调用、RAG 和真实回答均已实际执行。

原始完整轨迹：`evaluation/runs/step4_5-real-model-smoke-rerun/http-traces.jsonl`；每行包含 raw input、understanding 输出、DECISION、工具调用、updated state、final answer 和 HTTP response。第一次失败轨迹单独保留在 `evaluation/runs/step4_5-real-model-smoke/`。

## Smoke Cases

| Case | 原始虚构输入 | 预期 | 实际路径 | 结果 / Failure Source |
| --- | --- | --- | --- | --- |
| 1 KNOWLEDGE_QA | `什么是刺激控制？为什么 CBT-I 建议只在困倦时上床？` | 检索相关 CBT-I 证据后回答 | `RETRIEVE(goal query) → ANSWER`，2 steps | **PASS** |
| 2 PERSONALIZED_DECISION，信息不足 | `每晚23:00上床，通常60分钟才能睡着；应该提前上床吗？` | 识别已知 latency，ASK 有价值的 `wake_time` | 错提取为只有 `bedtime=23:00`，`ASK(sleep_time_or_sleep_onset_latency)`，1 step | **FAIL — Input Understanding / extraction** |
| 3 PERSONALIZED_DECISION，较充分 | `23:00上床，60分钟入睡，07:00起床；应该提前上床吗？` | facts 足够后 `RETRIEVE → ANSWER` | 漏掉 latency，`ASK(sleep_time_or_sleep_onset_latency)`，1 step | **FAIL — Input Understanding / extraction** |
| 4 CAUSE_ASSESSMENT | `最近两周23:30上床、90分钟入睡、07:00起床，下午两杯咖啡；哪些可改变因素影响入睡困难？` | 保留明示 facts；按 State 决定检索或真正缺失项的 ASK | 漏掉 latency、recent pattern、caffeine，`ASK(sleep_time_or_sleep_onset_latency)`，1 step | **FAIL — Input Understanding / extraction** |
| 5 DATA_ANALYSIS | `分析这名虚构用户最近7天的睡眠日记` | `unread → READ_DIARY → facts → loaded → re-evaluate → ANSWER` | `READ_DIARY → ANSWER`，2 steps | **PASS** |

## 逐项检查

### Case 1 — PASS

- goal：`了解刺激控制是什么，以及为什么 CBT-I 建议只在困倦时上床`；task type：`KNOWLEDGE_QA`，均准确。
- extracted facts：全部 `null`，符合纯知识问题；未发现 fabricated facts。
- requirements：无需用户信息、需要 evidence；`decision_missing=[]`，user sufficiency `HIGH`、evidence `LOW`。
- candidate / chosen actions：一条目标相关 `RETRIEVE(query=goal)`，写入项目 RAG evidence 后重新评估为 `ANSWER`；无重复 RETRIEVE。
- evidence：内容直接说明刺激控制、床与睡眠的条件联系、困倦时上床的理由和注意事项；支持最终回答。
- answer scope：以 evidence 为界。回答没有把用户个人情况当成事实；虽包含资料中的注意事项和原则，但均有检索上下文支持。无 Goal Drift 或 premature ANSWER。

### Case 2 — FAIL（Input Understanding）

- goal / task type：`PERSONALIZED_DECISION` 与“是否提前上床”目标正确。
- extracted facts：只得到 `bedtime=23:00`；用户明确给出的“60分钟才能睡着”被错误保留为 `sleep_onset_latency=null`。
- requirements：方向性 goal 的 `decision_missing` 应为仅 `wake_time`；实际成为 `[sleep_time_or_sleep_onset_latency, wake_time]`，user sufficiency `MEDIUM`。
- chosen action：ASK 是大方向合理的，但 target 重复询问用户已给出的信息，属 unnecessary ASK。
- fabricated facts：无；错误是遗漏而非捏造。没有 RAG、重复工具调用、Goal Drift 或 premature ANSWER。
- Failure Source：真实模型的 function-calling structured output 对中文时长信息漏抽取；Policy 对传入 State 的处理符合既有规则。

### Case 3 — FAIL（Input Understanding）

- goal / task type：`PERSONALIZED_DECISION` 和方向性范围正确。
- extracted facts：`bedtime=23:00`、`wake_time=07:00` 正确；明确的 `sleep_onset_latency=60` 漏掉。
- 因错误 State，`decision_missing=[sleep_time_or_sleep_onset_latency]`，sufficiency 为 `MEDIUM`，因此无法进入预期的 `RETRIEVE → ANSWER`。
- chosen action：ASK 重复询问已知 latency，是异常 Action Path；没有 fabricated facts、RAG 重试或 Goal Drift。
- Failure Source：Input Understanding，而非 Sufficiency、Candidate 或 Policy。

### Case 4 — FAIL（Input Understanding）

- task type：`CAUSE_ASSESSMENT` 正确；goal 虽被生成成英文，但语义仍聚焦“可改变的入睡困难影响因素”，不构成 Goal Drift。
- extracted facts：只保留 `bedtime=23:30`、`wake_time=07:00`；遗漏明确给出的 90 分钟 latency、最近两周规律和下午两杯咖啡。
- resulting State：`decision_missing=[sleep_time_or_sleep_onset_latency, recent_sleep_pattern]`，因此选取重复 latency ASK；这不是有效的缺失信息追问。
- 未进入 RAG 或最终回答；未产生 fabricated facts、重复工具调用或 premature ANSWER。
- Failure Source：Input Understanding extraction。此例尤其表明 prompt / structured-output 约束不足以稳定抽取中文时长、频率与咖啡因事实。

### Case 5 — PASS

- goal：`分析该（虚构）用户最近7天的睡眠日记`；task type：`DATA_ANALYSIS`，均准确。
- required resource：`sleep_diary` 从 `unread` 经 `READ_DIARY` 变为 `loaded`；全部虚构 diary facts 被写入 State 后重新评估。
- requirement / sufficiency：resource 未读取前 user sufficiency 不是 ready；读取后 user/evidence sufficiency 为 `HIGH`，`decision_missing=[]`。
- chosen actions：`READ_DIARY → ANSWER`，无 ASK、RAG 或重复工具调用。
- final answer：仅整理日记中的 23:00/07:00、60 分钟、360 分钟、1 次夜醒，并从已知数值算出 75% 睡眠效率；明确说这是描述性、非诊断和非处方结论。该算术推导有给定 facts 支持，未出现虚构 diary facts，且符合 answer_scope。

## 与 Step 4 Mock 的差异

- Mock 环境能确定性地把 `60分钟` 映射到 `sleep_onset_latency`，故 Case 2 只问 `wake_time`、Case 3 会检索后回答。真实模型漏抽取该信息，导致路径退化为重复 ASK。
- Mock 验证了 Policy / State 边界；真实运行验证了 RAG 与 Answer Generation 可以工作，也暴露了 Input Understanding 的非确定性这一独立风险。
- Step 4.1 的 diary resource behavior 在真实模型下仍成立，没有异常变化。

## Regression

```text
.venv/bin/python -m unittest discover -s tests -v
Ran 42 tests in 41.304s
OK
```

原 Step 4 的 41 个测试仍全部通过；第 42 个为本阶段新增的 structured-output adapter 兼容性回归测试。

## 当前结论与后续建议

- 没有新的 **Policy Failure**；不建议为了本次失败修改 Candidate、Sufficiency 或 Policy。
- 应将此三例作为 Step 4.5 的 Input Understanding failure cases，下一阶段单独评估结构化抽取 prompt、schema/工具调用描述和必要的 deterministic validation，而不是让 Policy 猜测遗漏事实。
- 本阶段停止；不进入 Step 5。
