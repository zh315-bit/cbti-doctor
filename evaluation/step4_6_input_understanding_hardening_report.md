# Step 4.6 Input Understanding Hardening Report

日期：2026-09-19（America/New_York）  
数据：全部为人工构造的虚构用户文本与七天日记；不含真实健康信息。  
范围：只强化 Input Understanding；**没有修改 Decision Policy**。

## 结论

Step 4.5 中三个由事实遗漏导致的失败已修复：显式的入睡时长、两周模式、咖啡因以及方向性 goal 均能进入已验证 State。最终真实模型 Smoke 为 **4 PASS / 1 FAIL**；唯一失败来自 DATA_ANALYSIS 的 Answer Generation 擅自加入未提供 evidence 的“85% 一般参考”阈值，不属于 Input Understanding 或 Policy。

建议重新验收 Step 4.5 的 **Input Understanding / Action Path** 部分；不建议把 Step 4.5 整体标为通过，直到 Answer Generation 的 evidence-boundary failure 被单独处理。

## 实现：五个明确阶段

```text
LLM Extraction
  → Raw Structured Facts（完整保留，仅用于审计）
  → Deterministic Normalization（仅匹配原文明确表述）
  → Derived Facts（仅由已验证 source facts 确定性计算）
  → Validated Facts + fact_sources
  → AgentState merge（null 不覆盖既有 facts）
```

修改位置：

- `adaptive_agent/input_understanding.py`
  - `RawFactsOutput` 为 12 个 canonical facts 提供具体 structured schema 描述。
  - Prompt 明确列出时长、时钟时间、咖啡因、午睡、运动、屏幕和压力的提取要求，仍禁止猜测。
  - `extract_explicit_facts()` 只对原文明确表达做窄范围解析；支持时间、分钟/小时、夜醒次数、近期模式与行为表达。
  - 由 `bedtime` + `sleep_time` 计算 `sleep_onset_latency` 时写入 `kind=derived` 和 `source_fields=[bedtime, sleep_time]`。
  - `normalize_goal()` 保留用户原文中明确的“提前上床”等方向性中文 goal，避免 LLM 翻译成英文后丢失既有 Requirements 的语义匹配。
  - 未被文本规则支撑的 LLM raw fact 不能进入 validated facts 或 AgentState。
- `adaptive_agent/state.py`、`adaptive_agent/runner.py`、`evaluation/recorder.py`
  - 增加 `fact_sources`，使 State snapshot 和 JSONL 可追溯 explicit / derived 来源。
- `tests/test_input_understanding_hardening.py`
  - 新增 17 个专用测试方法（含内部语言变体，共覆盖 20 余个正反例）。

## Extraction Test Matrix

| 覆盖项 | 示例 / 断言 |
| --- | --- |
| 上床时间变体 | `晚上11点上床` → `23:00`；`23:30躺下` → `23:30` |
| 跨午夜派生 | `23点上床，凌晨12点睡着` → `sleep_time=00:00`、derived latency `60`，记录两项来源 |
| 时长变体 | `60分钟才能睡着` → `60`；`1.5小时才入睡` → `90` |
| 起床与总时长 | `早上7点起床，每晚睡6小时` → `07:00`、`360` 分钟 |
| 夜醒 | `每晚醒1次` → `1` |
| 最近模式变体 | `已经这样两个星期`、`最近两周都是这样`、`持续大概14天` |
| caffeine 变体 | 下午咖啡、每天两杯、午饭后一杯、下午经常拿铁 |
| nap | 明示午睡与“从不午睡” (`False`) |
| exercise / screen / stress | 明示跑步、睡前刷手机、工作压力很大 |
| 多事实句 | 同一句抽取 bedtime、latency、wake、nighttime awakenings |
| Negative extraction | `咖啡会影响睡眠吗？` 不生成 caffeine use；LLM raw 说有 latency、原文未说时不得进入 State |
| 状态 merge | 第二轮只提供 wake time 时保留已有 bedtime；null 不会覆盖已知 facts |
| Goal normalization | 英文 LLM goal 不覆盖原文明确的“提前上床”方向性语义 |

输入理解矩阵：**17 tests passed**；加上其内部语言变体，覆盖 20 余条专门案例。未提供的字段在 validated facts 中保持 `null`，进入 AgentState 时不 materialize；没有发现测试矩阵中的 hallucinated facts。

## Step 4.5 三个原始失败的归因与修复

| Case | 原始虚构输入 | 原实际提取 / 漏失 | 根因 | 修复 | 修复后结果 |
| --- | --- | --- | --- | --- | --- |
| 信息不足个性化决策 | `23:00上床，60分钟才能睡着；应该提前上床吗？` | 仅 bedtime；漏 latency | LLM function-call output 漏字段 | 明确 schema/prompt + 原文时长 normalization + 方向 goal normalization | facts 为 bedtime+latency；ASK 正确 target=`wake_time` |
| 较充分个性化决策 | `23:00上床，60分钟入睡，07:00起床；应该提前上床吗？` | 漏 latency；后续重复 ASK | LLM 漏字段；英文 goal 使方向性 requirements 未命中 | 同上，保留中文规范 goal | facts 三项齐全；`RETRIEVE → ANSWER`，2 steps |
| 原因评估 | `最近两周23:30上床、90分钟入睡、07:00起床，下午两杯咖啡…` | 仅 bedtime/wake；漏 latency、recent pattern、caffeine | LLM 漏抽取时间、持续期和摄入行为 | 原文显式解析与来源记录 | 四项均进入 State；`RETRIEVE → ANSWER`，2 steps |

三个失败中，修复前都没有 fabricated facts；问题是 missing explicit facts。修复后上述字段均有 `fact_sources.kind=explicit` 和匹配原文片段，派生 latency 则有两个 source fields。

## 最终真实模型 Smoke（相同五个 Case）

轨迹：`evaluation/runs/step4_5-input-hardening-final/http-traces.jsonl`。

| Case | 最终路径 | PASS / FAIL | 说明 |
| --- | --- | --- | --- |
| KNOWLEDGE_QA | `RETRIEVE → ANSWER` | PASS | goal/task 正确；RAG query 与 goal 相关；一轮检索，无个人 facts。 |
| PERSONALIZED_DECISION（信息不足） | `ASK(wake_time)` | PASS | latency 已验证；仅询问当前方向性 decision_missing。 |
| PERSONALIZED_DECISION（较充分） | `RETRIEVE → ANSWER` | PASS | 三个方向性 facts 完整；无多余 ASK、无重复检索；未给精确上床处方。 |
| CAUSE_ASSESSMENT | `RETRIEVE → ANSWER` | PASS | 90 分钟、两周、咖啡均被验证；回答将咖啡因表述为可能关联并说明限制。 |
| DATA_ANALYSIS | `READ_DIARY → loaded → ANSWER` | **FAIL — Answer Generation** | 输入、资源、facts、State、行动路径正确；回答却在无 evidence 时加入“低于一般参考的85%水平”。这是未由 state facts/evidence 支撑的外部阈值。 |

未发现 Input Understanding 的 hallucinated facts；在这五例中不再有 missing explicit facts。DATA_ANALYSIS 的最终回答仍有 1 个 Answer Generation hallucinated / scope violation，已保留为 failure case，未在本阶段修改。

## Regression

```text
.venv/bin/python -m unittest discover -s tests -v
Ran 59 tests in 47.215s
OK
```

原有 42 tests 全部保持通过；新增 Input Understanding matrix 后总计 59 tests。

## 推荐下一步

不要进入 Step 5。先进行单独、受限的 Answer Generation evidence-boundary hardening：针对无 evidence 的 DATA_ANALYSIS answers 加入回归失败案例，验证模型不能输出未提供阈值、指南或医学事实。该工作不应以修改 Policy 作为替代。
