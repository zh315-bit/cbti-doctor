# Step 4.1 策略修正报告

## 范围与结论

本阶段仅修正资源依赖、goal 级充分性和候选同分排序，未调用外部 LLM API，未修改前端、未开展 Benchmark，也未进入 Step 5。三个验收案例通过真实 Flask 路由离线复跑；输入理解、RAG evidence、回答模型均为显式 fixture，日记为人工数据。这里的 PASS 只证明该控制流程，不证明真实模型提取或医疗回答质量。

报告对应最终轨迹：`evaluation/runs/step4-policy-refined-final/http-traces.jsonl`，以及同目录由 EvaluationRecorder 写入的日期 JSONL。

## 三个根因与修正

1. **资源存在与已读取混淆。** 以前 DATA_ANALYSIS 直接以 available_diary 决定 HIGH；Policy 又优先 ANSWER。现在 Requirements 显式声明 `resources=(sleep_diary,)`，State 分别保存 `available_diary` 和 `resource_status`。资源状态为 unread / loaded / unavailable：只知道可用仍是 unread；只有 DiaryResult 返回可用的非空事实并完成合并，才成为 loaded。Sufficiency 对未 loaded 的依赖保持 LOW，因而不生成 ready ANSWER。资源不可用则允许“无法完成分析”的有限度 ANSWER，不会假装分析成功。

2. **critical 完整度被当作任务完成条件。** 以前仅看 critical 缺失数量。现在保留原 critical_missing/secondary_missing 作为诊断信息，另以 `resolve_requirements(goal)` 生成 `decision_fields`、`decision_missing` 和 `answer_scope`。对“是否早点上床”的方向问题，需 bedtime、sleep_time 或 latency、wake_time；这只允许讨论方向与作息约束，不指定具体新时间、睡眠窗口或限制处方。睡眠总量、夜醒、近期规律不因此伪装成已知。如果 goal 明确提到咖啡、夜醒、近期趋势等，它们会重新成为决策依赖。具体处方和未识别目标保留保守需求，不套用方向规则。

3. **排序退化为 YAML 顺序。** 原策略同分时用 `max` 的首项。现在候选携带 goal_relevance、decision_impact、redundancy 和 cost。Policy 按定性等级逐项比较：收益 → 目标相关性 → 决策影响 → 更低冗余 → 更低交互成本；语义因素全部相同，再优先免用户回合的工具，最后按稳定字段名排序。该最后规则只保证可重复，不冒称字段名具有临床价值。没有等级相减的虚假 utility 数值或概率。

## 修改文件与职责

- `configs/requirements.yaml`、`adaptive_agent/requirements.py`：资源声明；Python 配置中的方向目标词、处方排除词、显式相关字段规则；goal 级需求解析。
- `adaptive_agent/state.py`：资源生命周期、decision_missing、answer_scope 和候选解释维度。
- `adaptive_agent/sufficiency.py`：依据当前 decision_missing 和资源状态判断 readiness，移除 task_type 特判与字段占比。
- `adaptive_agent/candidates.py`：从未满足的目标需求生成问题；已有事实、等价事实或已问过的同一字段不重复询问；资源未读时形成 READ_DIARY 候选。
- `adaptive_agent/policy.py`：定性、可解释且不依赖输入顺序的排序。
- `adaptive_agent/tools.py`、`state_update.py`：按资源 requirements 保留日记事实；执行后标记 loaded/unavailable。
- `adaptive_agent/runner.py`、`evaluation/recorder.py`：把当前 goal requirements 和资源状态写入决策轨迹。
- `adaptive_agent/answer_generation.py`：将受限 answer_scope 传给回答模型，防止缩减信息后扩大回答范围。
- 测试：新增 `tests/test_policy_refinement.py`；原 Step 4 expectedFailure 改为普通通过测试；多轮 ASK 持久化测试改用仍有两个有效缺口的输入，保留多轮覆盖。

## 修改前后状态转换

### Case 1：是否早点上床

| 指标 | Step 4 | Step 4.1 |
| --- | --- | --- |
| total ASK count | 4 | 1 |
| ASK targets | wake_time → total_sleep_time → nighttime_awakenings → recent_sleep_pattern | wake_time |
| RETRIEVE count | 1 | 1 |
| READ_DIARY count | 0 | 0 |
| final status | ANSWER | ANSWER（方向讨论范围） |

修改前：两项 facts → 四轮补齐所有 critical → RETRIEVE → ANSWER。

修改后：

```text
goal=判断是否应该早点上床 → PERSONALIZED_DECISION
facts={bedtime:23:00, sleep_onset_latency:60}
critical_missing=[wake_time,total_sleep_time,nighttime_awakenings,recent_sleep_pattern]
decision_missing=[wake_time] → 用户充分性 MEDIUM、证据 LOW
ASK(wake_time)：起床约束仍直接影响当前方向判断
→ 用户回复 07:00 → 保留原 facts 并 merge wake_time
→ decision_missing=[]，critical_missing 仍有总睡眠、夜醒、近期规律三项
→ 用户充分性 HIGH（仅限 answer_scope）、证据 LOW
→ RETRIEVE(query=当前 goal) → fixture evidence 入 State
→ 用户/证据 HIGH/HIGH → ANSWER
```

这不是“问一次就停”的次数限制。额外回归把 goal 改成“最近夜醒和咖啡影响下是否应该早点上床”：会询问 wake_time、nighttime_awakenings、caffeine、recent_sleep_pattern 四项，每个目标依赖消失后重新生成候选；total_sleep_time 仍缺失也能 RETRIEVE。另有具体处方请求不会提前变 HIGH 的测试。

Case 1 **离线 PASS**，没有为了总量/夜醒/近期规律的一般重要性继续询问；scope 明确限制结论。尚无临床验证证明该启发式足以支持真实个性化治疗处方，也没有声称如此。

### Case 2：知识问答

修改前后均为：goal=解释刺激控制及减少不必要卧床原因 → KNOWLEDGE_QA → facts={} → 个人需求为空、evidence_required=true → 用户 HIGH、证据 LOW → RETRIEVE(goal) → evidence 合并 → HIGH/HIGH → ANSWER。

ASK=0，RETRIEVE=1，READ_DIARY=0，final_status=ANSWER。**离线 PASS**；没有无关个人信息收集，也没有重复检索。

### Case 3：七天日记分析

修改前，available=true → facts={} 仍 HIGH → ANSWER，无工具调用。

修改后，Requirements 明确依赖 sleep_diary（与当前 task_type 到 action 的硬编码无关）：

```text
available=true + resource_status.sleep_diary=unread + facts={}
→ required_resources=[sleep_diary] → 用户 LOW
→ candidates=[READ_DIARY(target=sleep_diary)]，无 ready ANSWER
→ READ_DIARY 返回七日 fixture → facts 完整写入 State
→ resource_status.sleep_diary=loaded
→ 重算用户 HIGH、证据 HIGH（本描述性分析配置不要求外部 evidence）
→ ANSWER
```

ASK=0，RETRIEVE=0，READ_DIARY=1，final_status=ANSWER。**离线 PASS**。资源规则跨四种 TaskType 的测试也得到相同 READ_DIARY → loaded → ANSWER，证明依赖由 Requirements 驱动。

unavailable 路径：unread → READ_DIARY 一次 → facts={}、resource_status=unavailable → 用户仍 LOW → ANSWER（说明缺少资源，无法分析）。无假日记，无重试循环，**离线 PASS**。

开始时未宣告 available、工具实际有数据的补充分支，同样 READ_DIARY → loaded → ANSWER，**离线 PASS**。

## Regression Tests 与完整测试结果

新增十项：方向目标保留 critical 缺失仍可结束询问、具体处方不套用简化、显式 goal 因素恢复价值、资源规则与任务类型无关、unavailable 安全停止、requirements 任意排列结果不变、四项排序因素和稳定兜底、等价已知事实/已问字段不重复、扩展 goal 可合理询问四次、回答器收到 scope 限制。

原 Step 4 日记 expectedFailure 已移除标记，并作为普通测试通过。原两轮 ASK 测试仍保留，但首次输入只给 bedtime；随后补 latency，仍需 wake_time，因此测试的多轮行为有真实缺口支撑。

最终执行：`.venv/bin/python -m unittest discover -s tests -v`：**41 passed / 0 failed / 0 skipped / 0 expected failure**。之前四项 LangChain 测试在项目环境正常运行，无需安装依赖。

离线验收命令：`.venv/bin/python scripts/validate_step4.py --offline --tag policy-refined-final`。所有六次 HTTP 请求（Case 1 两轮，其余各一轮）返回 200，记录完整决策轨迹。

## Missing Information ≠ Must Ask 与剩余边界

在本次支持的方向目标和案例范围内，该原则有直接可执行证据：critical_missing 非空仍能进入 RETRIEVE/ANSWER；只有 decision_missing 才生成高影响 ASK。已知/等价信息被排除；同一未获回答字段不会无限重复，仍缺依赖时返回限制说明。

V1 的价值判断依然是人工可解释规则，不是测量所得的概率。未识别目标仍保守使用任务默认需求；不应将本次三个案例通过推广为所有个人决策都已最优。loaded 表示读取成功，不是七天完整度、日期范围、临床可用性或来源质量的充分验证。证据相关性判断、全量 token 成本和真实模型遵循 scope 的能力仍需后续验收。

建议重新进行 Step 4 的离线行为验收；本阶段已满足这三个明确修正目标。完整真实 LLM/RAG 验收继续遵守“不向外部 API 发送健康测试数据”的限制，不应标记为完成。停在 Step 4.1，不进入 Step 5。
