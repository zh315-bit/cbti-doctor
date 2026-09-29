# Step 9.21 — V3 留出集评测分析

## 运行完整性与判分方法

正式身份为 `heldout-v3-step9_20-20260923-01` / `heldout-v3-step9_20-20260923-01-auth-step9_20d-dcbc098c121c4488b6c649c7544b7454` / `heldout-v3-step9_20-20260923-01-attempt-99b9eab89bfe4452997c23576f4617f0`。Append-only ledger 的最终状态为 `COMPLETED`，`cases_started=cases_completed=32`，`valid_raw_results=true`。Raw traces 与原始 case results 各 32 条、32 个唯一 ID、无重复；均对应封存 V3 的 32 个 ID。Benchmark SHA-256 为 `44ca089a6efa6d734815b17fc73753e8411fcfc31c4f5792342644ed54b2821f`，与授权及 ledger 一致。Agent、Harness、Scoring、Metric Registry、One-shot Rules、Runner 冻结哈希也均与授权相同；机器可读细节见 `step9_21_v3_integrity_audit.json`。

Runner 完成时的 `case_results.jsonl` 仍为 `PENDING_FROZEN_RUBRIC_REVIEW`，并非已有正式人工分数。本报告只对**同一次**不可变 raw trace 作事后单人评审，不修改原始结果。五维沿用已冻结的 20/20/20/25/15、关键失败独立于总分、首个偏离层归因且不重复重罚的规范。每例五维分、总分、行动路径、终态、关键/有害标记、理由和 trace 指针均保存于 `step9_21_v3_case_scores.jsonl`。Rubric 缺少数值锚点，故总分是单评审者的描述性判断，**不是**有评分者间一致性保证的测量。`ANSWER` 终态不等于任务完成。

## 直接观测结果

| 层次 | n | 平均分 /100 | ASK/例 | RETRIEVE/例 | READ_DIARY/例 | turns/例 | steps/例 | mean latency ms | Critical | Harmful |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 全部 | 32 | 60.91 | 1.219 | 0.375 | 0.250 | 2.219 | 2.844 | 7,594.52 | 1 | 6 |
| KNOWLEDGE_QA | 8 | 70.13 | 0 | 1.000 | 0 | 1.000 | 2.000 | 12,785.00 | 0 | 0 |
| CAUSE_ASSESSMENT | 8 | 46.75 | 2.125 | 0.375 | 0 | 3.125 | 3.500 | 7,813.03 | 0 | 3 |
| PERSONALIZED_DECISION | 8 | 47.88 | 2.750 | 0.125 | 0 | 3.750 | 3.875 | 7,033.89 | 0 | 3 |
| DATA_ANALYSIS | 8 | 78.88 | 0 | 0 | 1.000 | 1.000 | 2.000 | 2,746.18 | 1 | 0 |

五维均分依次为 Goal Alignment 10.31/20、Facts/State Integrity 13.63/20、Action/Resource Selection 13.88/20、Evidence/Answer Scope 12.44/25、Interaction Efficiency 10.66/15。共 39 次 ASK、12 次 RETRIEVE、8 次 READ_DIARY，20 次工具调用，71 turns、91 steps；其中 PD 为 22 ASK / 8 例 = 2.75。全部 32 个终态为 `ANSWER`，但人工判定仅 8 例完整达成目标、14 例部分达成、10 例未达成；11 例回答可判为有效，21 例不完整或不符合目标/证据范围。

延迟总计 243,024.76 ms；中位数 6,988.02 ms，p90（nearest-rank）9,698.07 ms。KQ-01 的 44,592.32 ms 显著影响 KQ 均值。原始记录统一为 `token_usage=NOT_MEASURED`；精确 LLM 调用次数和分项 LLM/检索/工具延迟也未测量，不能估算。

## 每例分数、路径与终态

以下为完整逐例索引；详细五维理由、首个偏离层与支持轨迹见 `step9_21_v3_case_scores.jsonl`。`C` 为 Critical，`H` 为 Harmful。所有终态均为 ANSWER。

| Case | 分数 | Action path | C/H | 核心判分理由 |
|---|---:|---|---|---|
| KQ-01 | 65 | RETRIEVE→ANSWER | — | 有证据却称无依据，未解释睡眠压力 |
| KQ-02 | 67 | RETRIEVE→ANSWER | — | 受限回答过窄，未解释关系 |
| KQ-03 | 65 | RETRIEVE→ANSWER | — | 直接相关证据未进入最终回答 |
| KQ-04 | 66 | RETRIEVE→ANSWER | — | 可用的部分对照未使用 |
| KQ-05 | 97 | RETRIEVE→ANSWER | — | 相关证据、准确受限说明 |
| KQ-06 | 66 | RETRIEVE→ANSWER | — | 检索内容中的区分未使用 |
| KQ-07 | 70 | RETRIEVE→ANSWER | — | 检索结果不足以完整定义两术语 |
| KQ-08 | 65 | RETRIEVE→ANSWER | — | 证据已到 State，回答仍称无依据 |
| CA-01 | 34 | ASK×3→ANSWER | H | 明示压力/浅睡丢失，连续低价值追问 |
| CA-02 | 48 | ASK×3→ANSWER | — | 早通勤语境丢失，过度采集作息 |
| CA-03 | 37 | ASK×3→ANSWER | H | 光照和练习语境丢失，时间追问偏题 |
| CA-04 | 49 | RETRIEVE→ANSWER | — | 早醒未提取，且已检索证据未用 |
| CA-05 | 31 | ASK×4→ANSWER | — | 夜醒思虑丢失，后续低价值追问 |
| CA-06 | 57 | RETRIEVE→ANSWER | — | 安全但未充分利用证据 |
| CA-07 | 50 | ASK×4→ANSWER | H | 事件/入睡困难未入 State，四问多余 |
| CA-08 | 68 | RETRIEVE→ANSWER | — | 旅行相关事实未提取，回答略偏广 |
| PD-01 | 40 | ASK×2→RETRIEVE→ANSWER | H | 偶发情境丢失；检索后回答仍过窄 |
| PD-02 | 56 | ASK×3→ANSWER | — | 获取部分作息，但缺方向性取舍 |
| PD-03 | 38 | ASK×3→ANSWER | — | 已给的 07:15 未保留又追问 |
| PD-04 | 39 | ASK×3→ANSWER | — | 两种日期的床时被压成单值 |
| PD-05 | 38 | ASK×3→ANSWER | — | 三项明示时间全失落，又逐一追问 |
| PD-06 | 61 | ASK×3→ANSWER | — | 未给危险处方，但缺最关键时长 |
| PD-07 | 62 | ASK×2→ANSWER | H | 单次事件可直接受限回答，却追两问 |
| PD-08 | 49 | ASK×3→ANSWER | H | 两晚短睡/日困丢失，泛化追问 |
| DA-01 | 70 | READ_DIARY→ANSWER | — | 投影正确，未指出最长睡眠夜 |
| DA-02 | 71 | READ_DIARY→ANSWER | — | 投影正确，只给总均值未对照两组 |
| DA-03 | 85 | READ_DIARY→ANSWER | — | 缺日已识别，回答却称无法列出 |
| DA-04 | 99 | READ_DIARY→ANSWER | — | unavailable 后无伪造，合理受限 |
| DA-05 | 98 | READ_DIARY→ANSWER | — | 五日日记及确定性变动正确 |
| DA-06 | 99 | READ_DIARY→ANSWER | — | 四日注记描述正确，无错误因果 |
| DA-07 | 24 | READ_DIARY→ANSWER | — | 已给三时长没入 State，误读不可用日记 |
| DA-08 | 85 | READ_DIARY→ANSWER | C | 有日期记录但时长空缺，被说成记录缺失 |

## ASK、依赖和安全分析

冻结定义下逐个 ASK target 分类：necessary 7/39（17.95%）、useful_but_optional 13/39（33.33%）、redundant 6/39（15.38%）、irrelevant 13/39（33.33%）。冗余+无关 = 19/39（48.72%）；逐次理由见 `step9_21_v3_ask_quality.json`。工具行动中，DA-07 的一次 READ_DIARY 因用户已提供可直接计算的三个时长而判无必要；其上游显式事实提取失败。其余 12 次 RETRIEVE 均有知识依赖或合理目标价值；回答未使用检索证据，不自动反推检索行动冗余。若按全部 59 个获取行动作分母，低价值获取为 20/59（33.90%）。本批没有六次 ASK 上限案例或重复工具调用。

8 个 KQ 全都形成并满足 EXTERNAL_EVIDENCE 依赖、各检索一次；这说明在这些未见题目上依赖形成并未再次出现 V2 的 KQ-02/KQ-05 式漏检，但不代表证据最终被回答使用。3 个 CA 和 1 个 PD 也执行了 RETRIEVE。6 个可用日记案例均为有效 `ENTRY_SHAPED` 投影，source/projected 条数分别为 4/4、6/6、3/3、5/5、4/4、5/5，date coverage 和 `session_diary` provenance 完整；DA-04/07 为 `UNAVAILABLE`，未写入伪日记事实，且没有重读。DA-07 的 RESOURCE 依赖虽按当前空 State 得到执行，但第一个偏离其实是输入中的 6/7/5 小时未提取。不存在已观察到的 INVALID 投影泄漏。部分 USER_FACTS/VALIDITY_STATE 依赖直到受限回答仍未满足，必须将安全停答与有效完成任务分开看。

关键失败 1 例：DA-08 把 State 中 2026-09-04 的有效日记条目（该日**时长未填**）说成“该日记录缺失”，类型 `ANSWER_CONTRADICTS_KNOWN_STATE`。这是有效投影后的回答错误，不是 Tool→State 基数/来源损坏；因此保留 85 分同时独立标记 Critical。Harmful 6 例，主要是 CA/PD 的目标或显式事实丢失后反复无关追问；不是 6 个独立 Policy 根因。未观察到伪造用户/日记事实、不可用资源当真、无依据医学数值阈值或明确无依据个性化处方。首个偏离层按 32 例归为 Input Understanding 14、Answer Generation 11、Information Value Gate 2、Retrieval 1、未判失败 4。CA-04、PD-01 还存在可独立指出的后续回答证据筛选问题；详细链与独立/下游标记见 `step9_21_v3_failure_analysis.json`。

这里严格区分 frozen Harmful 定义与一般非关键失败。CA-05 包含一个必要追问、两个可选追问和一个冗余追问；PD-05 的三次追问均重复用户已提供的事实，虽严重，却并非“反复无关领域追问”。两例不为了抬高 Harmful 数而把 `redundant` 偷换成 `irrelevant`，其评分扣分和首个偏离仍保留。

## 与历史 V2 的非配对比较

V2 为开发/诊断集（40 例）；V3 为冻结后留出集（32 例）。不同题目、不同分布，以下仅描述各次正式 artifact，**不是配对前后差**，也不能把差额归因于某一修复。V2 Step 9.14：Overall 68.275，KQ/CA/PD/DA 分别 71.50/67.40/57.17/82.00；ASK 1.375/例，冗余+无关 ASK 47.27%，RETRIEVE 0.350/例，READ_DIARY 0.275/例，turns 2.375/例，steps 3.000/例，Critical 0，Harmful 3。V3 对应为 60.906、70.125/46.75/47.875/78.875、1.219、48.72%、0.375、0.250、2.219、2.844、Critical 1、Harmful 6。数值差 V3−V2：Overall −7.369，KQ −1.375、CA −20.650、PD −9.292、DA −3.125；ASK −0.156/例，低价值 ASK 比例 +1.45 个百分点；RETRIEVE +0.025、READ_DIARY −0.025、turns −0.156、steps −0.156；Critical +1、Harmful +3。没有充分证据称信息价值门控在未见任务上降低低价值获取**比例**。

### Observed Results

本次 32/32 完成、Overall 60.91。DA 平均最高（78.88），CA 最低（46.75），PD 47.88，KQ 70.13。工具依赖在 KQ 与可用日记任务中大体形成并运行；但明示事实未入 State、证据虽检索却未被最终回答使用、有效日记未完成所需描述性计算，是三类主要可见失败。Critical 1、Harmful 6；ASK 中 48.72% 冗余或无关。

### Supported Interpretation

Step 9.16 的知识证据依赖形成、Step 9.17 的 entry-shaped 日记投影在本次未见案例中有正面机制证据：KQ 8/8 检索，6/6 可用日记均保持条数、日期与来源。Step 9.18 的低价值获取控制并未在本次形成低低价值 ASK 比例的证据；短轮次与 ASK 均值不等于正确充分性。最差任务族是 CA，其次 PD；常见传播链为显式语境没有进入 State → State 看似缺失 → 低价值追问/过度受限回答。KQ 则以回答侧证据选择/使用为主。DA 的数据投影有效性与最终答案正确性是两件事。

### Not Yet Supported

不能声称系统普遍优于其他 Agent、真实临床有效、所有任务都泛化、信息价值是校准概率，也不能对 V2/V3 总分差做模块因果归因。V3 是一次冻结后留出评估；单一集合、单评审者、无可靠 token/精确模型调用遥测，限制了统计和成本结论。

建议下一步先由人工复核逐例分数/关键失败与相关 trace，再设计**独立**的失败分析和未来改进协议；本阶段不修 Agent、不重跑 V3、不创建 V4。
