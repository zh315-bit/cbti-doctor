# Step 4 端到端验收报告

## 结论与验证边界

本阶段尚不能验收通过，不建议进入 Step 5。真实模型调用受网络权限阻止，且离线真实 Flask 路由复现了日记 available 分支的过早 ANSWER。Policy、Candidate 生成器、Sufficiency Estimator 本阶段未重设计。

真实调用已尝试：通过 Flask `create_app()` 的真实 `/api/chat` 路由请求 Case 1，在 Input Understanding 调用外部服务时出现 `openai.APIConnectionError`（沙箱 DNS 失败），HTTP 500。进一步本机 HTTP listener 在沙箱内报 `Operation not permitted`。向配置目的地 `api.deepseek.com` 申请网络执行权限两次均被自动审批拒绝；第二次已说明病例/追问/日记全部为人工测试数据，审批仍要求用户明确授权发送这些健康相关测试输入。没有绕过限制，未将 mock 输出当作真实模型结果。

随后完成的离线验收使用真实 Flask `test_client().post('/api/chat')`、真实 route/service/loop/session/requirements/sufficiency/candidates/policy/diary/recorder；只有输入理解、检索结果和最终回答是显式 fixture。它可以验证 HTTP 路由内的状态控制流程，不能验证实际网络传输、LLM 提取质量、真实 RAG 相关性或生成回答质量。

## 测试结果

| 阶段/环境 | 执行总数 | passed | unexpected failed | skipped | expected failure |
| --- | ---: | ---: | ---: | ---: | ---: |
| 初始系统 Python 3.9 | 25 | 21 | 0 | 4 | 0 |
| 初始项目 `.venv` Python 3.12.14 | 25 | 25 | 0 | 0 | 0 |
| 新增缺陷回归，修复前 | 5 | 0 | 5 | 0 | 0 |
| 修复后项目 `.venv` | 31 | 30 | 0 | 0 | 1 |

此前 4 个 LangChain skipped 是选择了错误解释器所致。项目 `.venv` 已有 `langchain_openai`、Flask、FAISS、sentence-transformers；无需安装或升级依赖。之前把 `Ran 25 ... skipped=4` 报成 25 passed 不准确；应为 21 passed。已知 expected failure 是真实未解决的验收失败，不能计为 passed。

命令：`.venv/bin/python -m unittest discover -s tests -v`。

离线路由复现：`.venv/bin/python scripts/validate_step4.py --offline --tag offline-fixed`。

真实外部服务复现（需网络授权）：`.venv/bin/python scripts/validate_step4.py --tag live-authorized`。该命令可能首次构建现有 RAG 本地索引并产生模型 API 费用。

## 轨迹文件

- 修复前：`evaluation/runs/step4-offline-baseline/http-traces.jsonl`。
- 修复后：`evaluation/runs/step4-offline-fixed/http-traces.jsonl`。
- 对应目录内 `YYYY-MM-DD.jsonl` 为真正由 `EvaluationRecorder` 产生的逐回合日志。
- 每个 HTTP trace 包含 request/response、prior/updated session、requirements，以及各次 understanding、decision、tool result、loop result；`mode=offline` 明确标记证据性质。
- 日志日期使用 UTC，可能比本地日期早进入下一天。

以下轨迹均指离线实测，不代表真实模型成功。

## Case 1：PERSONALIZED_DECISION

输入：`我每天11点上床，一个小时才能睡着，我应该早点上床吗？`

goal=`判断是否应该早点上床`；task_type=`PERSONALIZED_DECISION`。fixture 明确提供 bedtime=`23:00`、sleep_onset_latency=`60`（分钟）。这两个值来自人工预期输出，并非已经验证了真实提取。

Requirements：critical 为 bedtime、sleep_onset_latency、wake_time、total_sleep_time、nighttime_awakenings、recent_sleep_pattern；secondary 为 perceived_stress、nap、caffeine；evidence_required=true。

| HTTP 回合 | facts 更新（旧值全部保留） | critical_missing | 用户/证据充分性 | candidates → chosen_action → 下一步 |
| --- | --- | --- | --- | --- |
| 1 | bedtime=23:00，latency=60 | wake_time、total_sleep_time、nighttime_awakenings、recent_sleep_pattern | LOW/LOW | 对四个缺失字段各生成 ASK → ASK(wake_time) → 返回问题、保存 session |
| 2 | 加 wake_time=07:00 | total_sleep_time、nighttime_awakenings、recent_sleep_pattern | MEDIUM/LOW | 三个 ASK → ASK(total_sleep_time) → 保存 session |
| 3 | 加 total_sleep_time=360 | nighttime_awakenings、recent_sleep_pattern | MEDIUM/LOW | 两个 ASK → ASK(nighttime_awakenings) → 保存 session |
| 4 | 加 nighttime_awakenings=1 | recent_sleep_pattern | MEDIUM/LOW | ASK(recent_sleep_pattern) → 保存 session |
| 5a | 加最近两周作息的明确文本 | 无 | HIGH/LOW | RETRIEVE(query=当前 goal) → mock 工具返回一条明确标记的 fixture evidence |
| 5b | evidence 从空变为 fixture evidence；facts 不变 | 无 | HIGH/HIGH | 重算 candidates=[ANSWER] → ANSWER → 结束 |

secondary_missing 始终为三项；没有追问这些字段。共 5 个 HTTP 回合、6 个 action，ASK=4、RETRIEVE=1、ANSWER=1。最终 status=ANSWER。

结论：离线状态恢复/merge/重算/停止 ASK/单次 RETRIEVE **PASS**；真实提取和个性化回答质量 **BLOCKED**。不能认定四个 critical 问题都具有最高 goal 价值：当前算法以字段数量计算 MEDIUM，并要求所有 critical 填满才 HIGH；该 goal 的多个 ASK 同分时按配置顺序胜出。因此“只获取真正值得的信息”的完整验收仍未通过。

## Case 2：KNOWLEDGE_QA

输入：`什么是刺激控制？为什么 CBT-I 要减少不必要的卧床时间？`

```text
goal=解释刺激控制及减少不必要卧床的原因
→ task_type=KNOWLEDGE_QA
→ facts={}
→ requirements: critical=[], secondary=[], evidence_required=true
→ missing: critical=[], secondary=[]
→ sufficiency: user=HIGH, evidence=LOW
→ candidates=[RETRIEVE(query=goal, benefit=HIGH, cost=MEDIUM)]
→ chosen=RETRIEVE
→ tool_result: available=true, evidence=[显式 MOCK fixture]
→ state_update: evidence 入 State，facts 保持 {}
→ re-evaluate: user=HIGH, evidence=HIGH
→ candidates=[ANSWER] → chosen=ANSWER
→ final_status=ANSWER
```

一回合两步，未 ASK、未重复 RETRIEVE，query 保持 goal。离线控制流程 **PASS**；真实 evidence 相关性及最终回答是否只使用 evidence **BLOCKED**。Mock 回答不构成医学答案质量的证据。

## Case 3：DATA_ANALYSIS

输入：`帮我分析最近7天的睡眠日记。`

共同 goal=`分析最近7天的睡眠日记`，task_type=`DATA_ANALYSIS`。Requirements：critical=[]、secondary=[]、diary_preferred=true、evidence_required=false。日记 fixture 为 2026-09-11 至 2026-09-17 的七条人工记录，每条 bedtime=23:00、wake_time=07:00、latency=60、total_sleep_time=360、nighttime_awakenings=1。不是患者数据。

### A. 已知 available=true：FAIL

```text
goal → DATA_ANALYSIS → facts={}
→ requirements 如上 → critical_missing=[], secondary_missing=[]
→ user=HIGH（仅因 available_diary=true）, evidence=HIGH（配置不要求 evidence）
→ candidates=[READ_DIARY(target=recent_sleep_pattern), ANSWER]
→ chosen=ANSWER
→ tool_result=无（未执行 READ_DIARY）
→ state_update: facts 仍为空
→ next_decision=无 → final_status=ANSWER
```

这是 Premature ANSWER，由错误的用户充分性 HIGH 和优先 ANSWER 的组合造成。已有日记却完全没有读到 State；没有执行分析。对应 `test_known_policy_failure_available_diary_must_be_read_before_answer` 保留为 expectedFailure，明确追踪而非跳过。

### B. unavailable：离线控制流程 PASS

```text
goal → DATA_ANALYSIS → facts={}, available_diary=false
→ requirements 如上 → missing=[]/[] → user=LOW, evidence=HIGH
→ candidates=[READ_DIARY] → chosen=READ_DIARY
→ tool_result={facts:{}, available:false, detail: sleep diary unavailable}
→ state_update: facts={}, available_diary=false
→ re-evaluate: user=LOW, evidence=HIGH
→ candidates=[ANSWER(收益 MEDIUM，信息不足说明)] → chosen=ANSWER
→ final_status=ANSWER（有限度的说明，并非分析成功）
```

只读一次，无 fabricated facts、无无限循环、无 RETRIEVE。真实模型能否按限制回复仍 BLOCKED。

### C. 工具实际有数据，但开始时可用性尚未知：修复后离线 PASS

```text
goal → DATA_ANALYSIS → facts={}, available_diary=false
→ requirements 如上 → missing=[]/[] → user=LOW, evidence=HIGH
→ candidates=[READ_DIARY] → chosen=READ_DIARY
→ tool_result: available=true，返回全部六类事实（含七条原始日记）
→ state_update: facts 合并全部明确数据，available_diary=true
→ re-evaluate: user=HIGH, evidence=HIGH
→ candidates=[ANSWER] → chosen=ANSWER → final_status=ANSWER
```

修复前日记工具仅保留 sleep_onset_latency，丢掉 bedtime、wake_time、睡眠总量、夜醒及七日日记；仍因 available=true 提升为 HIGH。此次修复数据过滤后，上述全部数据均进入 State。此路径的成功不抵消 A 分支失败。是否至少七天/日期适配目标仍无独立校验。

## 七类问题检查

| 项目 | 本次发现 |
| --- | --- |
| Redundant Action | 离线各案例未出现重复工具执行；Case 1 全部 critical 必须补齐的必要性未被验证 |
| Goal Drift | fixture 路径未见 goal 变化；真实 LLM 目标漂移尚无法验证 |
| Unnecessary ASK | 未追问 secondary；Case 1 同分时仍按列表顺序提问，不能证明最有价值 |
| Unnecessary RETRIEVE | Case 1/2 各一次；日记各分支零次。DATA_ANALYSIS 的 evidence_required 是固定 false，不能依据具体 goal 灵活判断 |
| Fabricated Facts | fixture 流程未见；unavailable 携带异常 payload 的防御测试修复前能污染状态，修复后不能 |
| Premature ANSWER | Case 3A 明确失败；Case 3C 修复前只有 latency 即 HIGH，也暴露同一充分性问题 |
| Repeated Tool Call | 未见；max_steps 回归仍有效 |

## 日志检查和最小修复

原 JSONL 不能完整还原要求的决策轨迹：工具后的快照带有新 facts/evidence 却保留旧 sufficiency，缺少 requirements、明确 chosen candidate 和完整 tool result。现在每次选择前保存 DECISION 快照（含 requirements、所有候选和选中的完整 action）；工具后先重算并保存 tool_result 与更新状态；MAX_STEPS 也有最终快照。这样 evaluation 日志本身即可还原成功回合的控制决策，不必依赖终态猜测。

本阶段局部修复：

1. `adaptive_agent/tools.py`：日记分析保留规范事实与原有七日记录，空结果返回 unavailable；不生成日记。
2. `adaptive_agent/state_update.py`：unavailable 结果不合并 facts/evidence。
3. `adaptive_agent/service.py`：用深拷贝执行一回合，失败不污染原 session。
4. `adaptive_agent/runner.py`：即使工具是 max_steps 最后一步也刷新派生状态；补足上述 trace 内容。
5. `tests/test_step4_regressions.py`：五个由 FAIL 变 PASS 的回归测试，另一个明确标记的策略验收 expectedFailure。
6. `scripts/validate_step4.py`：可重复执行的真实/离线路由观察器，不更改选择策略。

不完整之处仍需明确：模型抛异常的失败 HTTP 回合目前不会产生 evaluation 记录；RAG 文献 source/page/chunk metadata 尚未提供；token_usage 仅取最后回答器，ASK 可能带旧用量，输入理解和 RAG 成本不完整。日志里的 evidence 文本不等同于文档级溯源。

## Technical Debt、AGENT.md 与下一步

- 当前充分性不是严格 goal-aware：个人任务靠 critical 数量，数据任务靠 available 标志，证据靠列表非空。这些是系统性问题，本阶段仅复现记录。
- 同分 ASK 退化为需求顺序；DATA_ANALYSIS 永远不要求 evidence；已执行工具在整个 action_history 中被屏蔽，无法表达新日记/新证据需要重新读取的场景。
- Session 仍是内存，缺乏并发隔离和持久存储；本次仅修复异常回滚。
- Recorder I/O 错误仍可使 HTTP 请求失败；缺少 source metadata、完整用量与失败日志。
- 输入理解 prompt 未提供上一轮问题全文和明确字段 schema；真实多轮短回答与未知值保持 null 仍需验证。
- 实际导入 `main_flask` 仍初始化旧 fixed graph；真实 RAG 本地索引尚未构建。未据此开展架构重构。
- 独立医疗安全路由尚未实现，不能宣称满足 AGENT.md 的全部安全条款。

本阶段遵守了范围限制、最小修复和记录要求，但系统整体尚未满足 AGENT.md 的 goal-alignment、充分性判断及安全路由要求，不能沿用此前“无违反项”的结论。

不建议进入 Step 5。先取得对配置模型目的地发送指定合成验收数据的明确授权、完成真实提取/RAG/回答验证，并确认 Case 3A 的充分性修正范围；再验收已有三个案例。未进入 Benchmark、Calibration 或 RL，也未修改前端。
