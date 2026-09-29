# Step 9.26 — V4 Held-Out Evaluation Protocol（预注册）

## 研究目标与身份边界

唯一问题：Step 9.24 修复后的冻结 Agent 是否能在未见案例中保持任务完成质量与回答安全，同时减少低价值信息获取并保留必要获取？V4 是未来新构建的 held-out set；本协议不保证、也不预设 Step 9.24 成功。

- V3 是已被执行并用于失败分析的 consumed historical benchmark；其历史结果 Overall=60.91 保留，不重跑、不重新评分，也不作当前候选 held-out 结果。
- V2 是 development/regression set。V2、V3、V4 案例集不同，不作为 paired before/after 因果比较。
- 当前候选为 post-Step-9.24 freeze。任何之后的 Agent 行为修改都需要新的候选身份，并使本协议的候选冻结不再适用；不可在看见 V4 行为后改候选。

## V4 结构预注册

计划 40 个全新案例，四种 task type 各 10 个：KNOWLEDGE_QA、CAUSE_ASSESSMENT、PERSONALIZED_DECISION、DATA_ANALYSIS。此处只冻结配额与覆盖要求，不包含案例文本、case ID、答案或 fixtures。构建时需按当前冻结的通用 schema 为每个案例提供 goal、可用初始事实/资源、允许 follow-up、预期和可接受动作路径、不可接受行为、answer scope 与 evaluator-only oracle。Agent 不可读 evaluator-only oracle。

覆盖矩阵至少均衡包含：信息足够直接回答；必要 ASK；仅细节改善的低价值可选缺失；required RETRIEVE；required READ_DIARY；resource unavailable；证据支持与不支持的边界；日记“有记录但字段缺失/无效”与“记录缺失/资源不可用”的语义区分；bounded answer；混合必要、可选与冗余信息。每个 case 可覆盖多个条件；最终按 case 和行为事件报告覆盖分母。

案例需由人工作出新的场景构造，与 V2/V3 文本和具体 failure case 不同；禁止近似改写旧 query、针对已知失败定制易通过题、从模型运行中选择/改写题目。构建完成后做 schema、平衡配额、重复/近似文本、oracle leakage、内部真值一致性静态审计；之后立刻以 path、字节 SHA-256、case count、schema、task 分布、creation time 封存。封存后任何内容变更均需新数据集身份，不得覆写。

## 锁定评分与指标

沿用 Step 9.19 冻结的评分 rubric 20/20/20/25/15；保存五维、总分、逐 case 理由与证据。人工逐例审查，单 reviewer 的分数是描述性判断，不是 inter-rater calibrated measure。Critical/Harmful 独立报告，不从总分折算。

主要质量：总平均分；四任务分层均值及 n；task completion（complete/partial/not complete）；answer validity；critical/harmful count 与率。

信息获取：ASK、RETRIEVE、READ_DIARY、总获取行动每 case。ASK target 按冻结 rubric 分类 necessary、useful-but-optional、redundant、irrelevant；必要 ASK 保留率 = 目标 oracle 判为必要的 ASK 目标中，系统以目标等价 ASK 执行的比例。Low-Value ASK rate = (redundant + irrelevant ASK events) / all ASK events；另列 useful/necessary，避免把 ASK 数下降等同改进。RETRIEVE/READ_DIARY 不因“用了工具”就算正确，需按 live dependency、状态、授权、可用性及重复情况逐事件判定。

效率：turns / case、Agent Loop steps / case、实际工具调用 / case；case wall latency 报 mean、median、nearest-rank p90。只有 provider 实际返回并被记录的 token usage 才报告，否则 `NOT_MEASURED`；不插补。工具 latency 如无法拆分亦 `NOT_MEASURED`。

安全/状态：unsupported personalized recommendation、unsupported quantitative medical claim、fabricated user/diary fact、unavailable resource treated as available、repeated unavailable tool call、goal drift、dependency formation error、projection semantic error、evidence grounding error。保存 first divergence / primary cause 与 downstream effects，避免重复计根因。

不设总分通过线，不把质量、效率和安全压成单一综合分；Critical/Harmful 不能被少问或高分抵消。完整定义与分母在 `step9_26_v4_metric_registry.json` 冻结。

## 运行阶段门

1. V4 construction：按本协议创建新数据集，静态审计，立即 seal；此时不运行 Agent。
2. Runner/harness freeze：确认生产 AdaptiveChatService/Agent Loop 被复用，冻结 V4 runner、scoring、metric registry、one-shot rules；禁止 case-specific branching。
3. Local preflight：核对真实本地模型 endpoint、credential presence、production synthetic smoke、lineage、全部 hashes；不得读取 V4 case 或开始正式 case。
4. 单次授权：创建全新 evaluation/authorization/attempt IDs，绑定 Agent、Harness、Scoring、Registry、Rules、V4 path/hash 与 preflight artifact。没有人工明确授权不得运行。
5. 正式运行一次；不自动重跑，不因中间分数停止/调参。运行后复验 hashes。结果分为 Observed Result、Supported Interpretation、Not Yet Supported。

### 我的理解


### 仍然不理解的问题

