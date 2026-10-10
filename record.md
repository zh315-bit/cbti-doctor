# 开发学习记录

## 第 1 步：状态、需求、充分性与决策策略

### 已实现内容

实现了 V1 自适应智能体的基础能力：类型化的 `AdaptiveAgentState`、可配置的需求库、定性的用户信息/证据充分性判断、具体候选行动，以及可解释的启发式决策策略。

### 重点阅读代码

1. [adaptive_agent/state.py](adaptive_agent/state.py)
   - 定义唯一、可追踪的状态对象，包含 facts、缺失信息、evidence、充分性、候选行动与行动历史。
2. [configs/requirements.yaml](configs/requirements.yaml)
   - 为各任务类型声明 critical、secondary 和 evidence requirements，从而将任务分类与行动选择分离。
3. [adaptive_agent/sufficiency.py](adaptive_agent/sufficiency.py)
   - 展示为何 secondary 缺失字段不会阻止已有充分依据的回答，以及用户信息和证据为何要独立判断。
4. [adaptive_agent/candidates.py](adaptive_agent/candidates.py)
   - 将当前 goal 和 state 转换为具体的 ASK / RETRIEVE / READ_DIARY / ANSWER 候选行动，而不是选择固定工作流步骤。
5. [adaptive_agent/policy.py](adaptive_agent/policy.py)
   - 以定性的收益和成本选择一个行动；当已满足回答条件时，ANSWER 优先于可选的次要信息收集。

### 重要执行流程

```text
goal + task_type + facts
→ requirements lookup
→ critical_missing / secondary_missing
→ user_info_sufficiency + evidence_sufficiency
→ concrete candidate actions
→ one policy-selected action
```

### 关键设计决策

- `task_type` 只提供 requirements，绝不直接决定行动。
- 缺失信息不会自动变成向用户提问的问题。
- 除非当前 goal 明确使其有价值，否则 secondary 信息是可选的。
- 候选问题的优先级取决于与 goal 的相关性，而非 YAML 中字段的排列顺序。

### 阅读后应能回答的问题

- 当 secondary 字段仍未知时，为什么个性化回答仍可能满足回答条件？
- 用户信息充分性与证据充分性有何区别？
- 哪一处代码决定某个 ASK 候选问题比另一个 ASK 更有价值？
- 为什么任务分类不会直接选择 RETRIEVE 或 READ_DIARY？

### 已知限制或技术债务

- V1 的 goal 相关性使用透明的关键词规则；后续 benchmark 数据可能支持更好的校准判断器。
- Requirements 目前是任务级默认值，尚未通过 LLM 做更细粒度的 goal-specific 需求细化。

### 我的理解


### 我仍有的问题


## 第 2 步：工具执行、状态更新与同步智能体循环

### 已实现内容

实现了结构化输入理解接口、稳定的检索和日记工具接口、显式状态更新，以及同步智能体循环。RETRIEVE 和 READ_DIARY 会在同一循环内更新状态并重新评估；ASK 会保存返回的状态并结束当前交互回合；ANSWER 或 `max_steps` 会结束循环。

### 重点阅读代码

1. [adaptive_agent/input_understanding.py](adaptive_agent/input_understanding.py)
   - 定义 goal、task type 和规范 facts 的结构化提取；未知字段会被设为 `None`，模型输出的 null 不会覆盖会话中已有 facts。
2. [adaptive_agent/tools.py](adaptive_agent/tools.py)
   - 定义 `RetrievalTool` 和 `DiaryTool` 契约，通过懒加载适配器复用现有 RAG，并在无日记时明确返回 unavailable 而不虚构数据。
3. [adaptive_agent/state_update.py](adaptive_agent/state_update.py)
   - 包含将 retrieval evidence 或 diary facts 合并到 `AdaptiveAgentState` 的唯一入口。
4. [adaptive_agent/runner.py](adaptive_agent/runner.py)
   - 实现一次只执行一个行动的循环、工具后的重新评估、ASK/ANSWER 的终止行为以及 `max_steps` 保护。
5. [tests/test_adaptive_loop.py](tests/test_adaptive_loop.py)
   - 提供检索、日记、ASK、ANSWER、工具不可用和循环安全行为的可执行示例。

### 重要执行流程

```text
user input + prior state
→ structured understanding and non-destructive fact merge
→ requirements / missing / sufficiency / candidates / policy
→ selected action
  → RETRIEVE or READ_DIARY: update state, then repeat evaluation
  → ASK: return question and persisted state to caller
  → ANSWER: return final loop result
→ max_steps: return a bounded limitation response
```

### 关键设计决策

- 工具依赖通过注入提供，因此循环可使用 mock 测试，之后接入 Flask 时无需重写决策逻辑。
- 仅在实际执行检索时导入现有 RAG；单元测试不需要模型凭据或向量索引。
- 日记数据只可来自 session/mock。不可用的日记不返回 facts，也不可能变成虚构的用户数据。
- 默认策略不会无限重试失败工具；循环可安全地返回有限度的说明。

### 阅读后应能回答的问题

- 哪些行动会在同一循环中继续执行，哪个行动会结束当前用户交互回合？
- `DiaryResult` 如何改变 facts、missing fields 和用户信息充分性？
- 为什么不可用的日记不会产生看似成功但内容为空的分析？
- 即使注入的策略重复选择 RETRIEVE，`max_steps` 如何保护循环？

### 已知限制或技术债务

- `BoundedAnswerGenerator` 是安全占位实现；尚未接入真正以 evidence 为依据的自然语言回答生成器。
- 真实 LLM 和 RAG 集成测试需要项目的可选运行时依赖与凭据。
- Flask session 持久化和 evaluation JSONL 日志被有意推迟到后续步骤。

### 我的理解


### 我仍有的问题


## 第 3 步：Flask 集成、会话持久化、真实回答与评估记录

### 已实现内容

将现有 Adaptive Agent Loop 接入唯一的 `/api/chat` 路径，并通过 `AdaptiveChatService` 保存每个 session 的 `AdaptiveAgentState`。接入结构化 LLM 输入理解、现有 RAG 的适配器和受 State/Evidence 约束的 LLM 回答生成器。每次 API 回合会追加 JSONL 评估记录；不会影响 Agent 的决策。

### 重点阅读代码

1. [main_flask.py](main_flask.py)
   - `/api/chat` 现在仅创建或读取 session id，并把请求委托给 `AdaptiveChatService`；没有新增并行聊天流程。
2. [adaptive_agent/service.py](adaptive_agent/service.py)
   - 定义会话状态生命周期：保存 state、累计 turns、调用循环、写评估记录，以及 reset 时清除指定 session。
3. [adaptive_agent/runner.py](adaptive_agent/runner.py)
   - 处理新 goal 时的状态重置，并在输入理解、工具执行和结束行动后保存可审计的 state history。
4. [adaptive_agent/answer_generation.py](adaptive_agent/answer_generation.py)
   - 将 goal、明确 facts、evidence 和限制条件作为唯一上下文传给回答模型，禁止用模型自身知识绕过证据约束。
5. [evaluation/recorder.py](evaluation/recorder.py)
   - 将每回合的初始 facts、状态历史、行动、证据、时延和 token usage 以追加式 JSONL 写入 `evaluation/runs/`。

### 重要执行流程

```text
/api/chat
→ AdaptiveChatService 读取 session state
→ AdaptiveAgentLoop 合并当前输入
→ ASK：保存 state，返回一个问题
→ 下一轮：恢复同一 state，合并新 facts，继续循环
→ RETRIEVE / READ_DIARY：同一循环内更新 state 并重新判断
→ ANSWER / MAX_STEPS：保存最终 state，返回响应
→ EvaluationRecorder 追加一条 JSONL 记录
```

### 关键设计决策

- Flask 只负责 HTTP contract；会话与决策逻辑集中于可测试的 service 和 loop 模块。
- 输入理解模型显式输出 `is_new_goal`；若用户明确切换任务，会创建新 state，避免继承旧 facts、evidence 或 action history。
- 回答模型接收的是 State 中的受限上下文，不能把模型内部知识当作已检索证据。
- RAG 保持在 `RagRetrievalTool` 适配器边界；旧 Fixed Workflow 没有成为 Adaptive Loop 的依赖。

### 阅读后应能回答的问题

- ASK 后哪些对象被保存在 session 中，下一轮如何恢复？
- 用户明确切换 goal 时，哪些旧状态会被重置，为什么？
- API 为什么不会直接调用旧 `CognitiveTherapyAgent.main_graph`？
- Evaluation JSONL 记录了哪些信息，又为什么不会参与决策？

### 已知限制或技术债务

- 当前 session 存储在 Flask 进程内存中；服务重启或多进程部署会丢失会话，尚未接数据库或共享存储。
- 真实模型/RAG 集成依赖项目运行环境中的 LangChain、模型凭据与 FAISS 索引；当前系统 Python 缺少 `langchain_openai`，相关既有 4 项配置测试保持 skipped。
- 当前 RAG 接口返回既有 RAG 的生成结果，尚未暴露文档块级来源 metadata。

### 我的理解


### 我仍有的问题


## 第 4 步：端到端验收与失败案例定位

### 已实现内容

运行完整测试；发现项目已有 Python 3.12 `.venv`，此前四个 LangChain 跳过项在该环境全部运行通过。新增三类案例的路由验收脚本，记录修复前后真实 Flask 路由的状态轨迹。真实外部模型调用因沙箱网络和自动审批拒绝未完成；离线模式明确使用输入理解、检索与回答 fixture，不能代替真实服务验收。

修复日记数据过滤、空日记可用性、unavailable 数据合并、失败回合状态污染和最后工具步骤未刷新状态等局部缺陷；补齐决策日志。available 日记未经读取就 ANSWER 的策略问题保留为已知失败，不据此重写 Policy。

### 重点阅读代码

1. `scripts/validate_step4.py`：看同一真实 Flask 路由如何分别接入真实依赖与显式 mock，以及如何观察实际 decision/tool/session 边界。mock 通过不能证明模型提取正确。
2. `adaptive_agent/runner.py` 的 `run_turn`：看 DECISION 快照如何保存 requirements、候选及所选行动；工具后为什么必须先刷新状态再记录，尤其在达到 max_steps 时。
3. `adaptive_agent/tools.py` 的 `SessionDiaryTool.read`：看 DATA_ANALYSIS 的空 requirements 曾如何导致已有七日数据被过滤，以及空日记为什么必须 unavailable。
4. `tests/test_step4_regressions.py`：五个局部回归与一个 expectedFailure。后者要求先 READ_DIARY，但现有策略返回 ANSWER，说明“测试套件无意外失败”不代表验收通过。
5. `adaptive_agent/sufficiency.py` 的 `user_information`：重点理解 available 标志与已有足够信息的区别，以及当前 critical 数量法还没有真正证明每个问题对 goal 的必要性。

### 重要执行流程

```text
完整测试 → 真实 /api/chat 尝试（网络阻塞）
→ 显式 fixture + 真实 Flask 路由离线复现
→ 保存 requirements / candidates / choice / tool result / updated state
→ 局部缺陷写回归并修复 → 重跑
→ 保留系统性策略失败 → 不进入 Step 5
```

### 关键设计决策

- 分开报告外部模型验收与离线路由验证；不以预设提取结果证明提取质量。
- 保留原 Policy 与 Sufficiency 的算法，将日记可用但过早回答记录为可执行的 expectedFailure。
- 工具更新、派生状态刷新与日志快照按相同执行顺序保存，避免日志里混合新数据和旧判断。
- 失败回合使用状态副本，成功才替换原 session。

### 阅读后应能回答的问题

- 为什么 available_diary=true 不能说明模型已经读过七天日记？
- 为什么所有单元测试都成功仍可能存在真实验收失败？
- 如何从一条 DECISION 和下一条工具快照还原行动原因及状态变化？
- 为什么 mock 可以证明状态 merge，但不能证明 LLM 没有虚构用户信息？
- 当前信息充分性中哪些判断仍依赖字段数量，而不是 goal？

### 已知限制或技术债务

真实 LLM/RAG 验收等待向 api.deepseek.com 发送指定合成数据的明确授权；available 日记仍可能过早 ANSWER；七天覆盖和证据相关性尚无可靠检查。记录器的失败回合、完整 token usage 和文献级 metadata 仍不完整。详见 `evaluation/step4_acceptance_report.md`。

### 我的理解


### 仍然不理解的问题

## 第 9.23a 步：P1 后候选冻结与回归身份审计

审计确认此前 3 个失败都来自“当前 Agent 仍须等于 Step 9.18/V3 旧身份”的断言。Step 9.23 后仅 4 个已授权 State→Answer 文件与 Step 9.18 清单不同：回答上下文与一致性守卫、State 审计字段、检索证据来源血缘、runner trace snapshot。没有发现超出 Step 9.23 范围的 Agent 改动。旧 Step 9.11、9.18、9.19/V3 身份保持不变；原 V3 runner 继续拒绝当前 Agent，保持 fail closed。

创建了 `evaluation/v1_2_3/step9_23a_candidate_freeze.json`，作为独立开发候选身份，不授权任何 Benchmark。测试现区分历史冻结完整性、当前候选哈希匹配与行为回归。完整非 Benchmark 回归 232/232 PASS、0 FAIL、0 SKIP；真实外部模型配置测试未运行。没有运行 V2/V3、没有模型调用、没有修改 V3 结果。

重点阅读：

1. `evaluation/v1_2_3/step9_23a_identity_failure_audit.md`：逐个失败记录旧断言、期望与当前哈希、首次合法分叉及归类依据。
2. `evaluation/v1_2_3/step9_23a_authorized_change_lineage.json`：机器可读的历史身份、Step 9.23 四个 Agent 文件哈希与父候选关系。
3. `evaluation/v1_2_3/step9_23a_candidate_freeze.json`：当前开发候选的聚合哈希和未变化模块；该文件不等同于 V3 运行授权。
4. `tests/test_step9_13a_authorization_infrastructure.py`：验证历史 freeze 原样保留，同时当前代码匹配最新候选。
5. `tests/test_step9_20a_v3_runner.py`：验证旧 V3 runner 仍拒绝新 Agent，并分别测试未签发授权的拒绝路径。

读完应能回答：历史 freeze 为什么必须继续失败关闭？当前候选哈希由哪些授权文件变化构成？为什么 V3 结果不能算作当前候选的评测？

### 我的理解


### 仍然不理解的问题

## 第 9.19 步：Final Candidate Freeze & Held-Out Evaluation Protocol（最终候选冻结与留出评估协议）

当前唯一候选身份锁定为 `post-step9_18-candidate-20260923-01`。最终清单逐类记录 requirements/dependency、Input Understanding、State/Loop、Sufficiency、Candidate/Information Value/Policy、Tools/RAG、Tool→State Projection、Answer Grounding、model/runtime configuration、evaluation harness 与 scoring specification 的组件 hash。Agent aggregate 为 `0dfdbac361d68dfeb577433107395b50f4c2fa8ca59f3e1d226fbd9271a839a7`，Harness aggregate 为 `8bc271bebc1c5da5351d517e2bb4a0d1a99fda3de1b713a6197b12f81fad70c7`，Scoring aggregate 为 `f742a8f8af7c8747818dadad81621c15d12d74f50538019913dfe18ab53bf59b`。全部当前文件均通过既有 freeze verifier。Step 9.11 historical manifest、Step 9.17a 与 Step 9.18 candidate freeze 均保留；没有覆盖历史身份。

在 V3 仍封存时，预注册质量、信息获取、效率、安全指标及其分母/判定口径；冻结 20/20/20/25/15 的原有评分权重，并明确单 reviewer、无数值锚点这一限制。解释原则不设单一总分过线值：质量、获取效率和安全分开报告；少问不能抵消无效回答或关键/有害失败。V2 被明确标为 development/regression context，不与不同 case set 的 V3 组成配对前后因果比较。V3 不读取、不哈希、不运行。

one-shot 规则规定正式访问 V3 时先追加记录 UTC 时间与 evaluation identity；正式运行前后核对 Agent/Harness/Scoring/configuration hash；执行采用新的 evaluation、authorization、attempt ID 和 append-only ledger。若运行进入 Agent Loop 或已开始 provider request 后失败，不重启同一正式运行；只对可证实发生于首个 case 执行前、无 provider request、无 case trace 的外部基础设施失败，才可在保留原 attempt、修复纯基础设施、通过等价性回归并获新人工授权后考虑新 attempt。V3 的第一次完整正式运行将作为不可覆盖的 Primary Held-Out Result。

重点阅读：

1. `evaluation/v1_2_3/step9_19_final_candidate_manifest.json`：当前候选、授权变更链、各组件 hash、V2/V3 身份边界与 case-specific logic 静态审计范围。
2. `evaluation/v1_2_3/step9_19_metric_registry.json`：各类指标定义、分母、评分权重、Critical/Harmful Failure 与未测遥测处理。
3. `evaluation/v1_2_3/step9_19_heldout_evaluation_protocol.md`：研究问题、V2/V3 解释边界、评分方式及预注册运行/失败处置。
4. `evaluation/v1_2_3/step9_19_one_shot_rules.md`：可操作的一次性执行约束和重跑边界。
5. `evaluation/v1_2_3/step9_19_freeze_audit.md`：文件 hash 核验、protocol artifact hashes 与封存状态审计。

### 我的理解


### 仍然不理解的问题

## 第 9.20 步：Benchmark V3 最终授权与运行器准备

本阶段仅做冻结身份与现有运行器审计，没有打开、列出、哈希、计数或读取 Benchmark V3，也没有调用模型或执行任何 Benchmark case。

Step 9.19 Final Candidate Manifest、Agent aggregate、Harness aggregate、Scoring aggregate、Metric Registry、One-Shot Rules 与 Held-out Protocol 在当前工作区均与冻结哈希一致；production source 的案例特定逻辑检查仍为 NO。旧 Step 9.12 本地预检 artifact 虽记录过 credential、endpoint 与 smoke PASS，但它绑定的是旧 Evaluation ID 和 Step 9.11 Agent hash，不能证明当前 V3 evaluation 的本地生产链路可用。当前执行环境的 `DEEPSEEK_API_KEY` 为 ABSENT，因此本轮没有发起模型探测或 production smoke。

现有 `scripts/run_step9_12_frozen_evaluation.py` 明确绑定旧 V2 case 文件、旧 evaluation identity 与 V2 ledger，不能复用或改指向 V3。没有新增 Step 9.20 runner：新增 runner 会成为实际 execution harness 的一部分，但它不在 Step 9.19 锁定 harness inventory 内；在没有独立 runner 审查/冻结身份时，不应悄悄扩展原 Harness freeze。故未签发 authorization/attempt，执行命令文件明确为 NOT ISSUED。

结果：静态 Final Freeze 匹配；当前环境的模型可用性未验证；V3 Runner 未准备/冻结；Authorization NOT ISSUED；不能手动执行。Benchmark V2 未重跑，V3 未访问，Agent/Benchmark/Scoring/Metric/Protocol 未修改。

重点阅读：`evaluation/v1_2_3/step9_20_v3_runner_audit.md`（运行器为何不可复用及阻塞项）、`evaluation/v1_2_3/step9_20_v3_authorization_manifest.json`（冻结核验和授权状态）、`evaluation/v1_2_3/step9_20_v3_execution_protocol.md`（后续必须补齐的门槛）。

### 我的理解


### 仍然不理解的问题

主要执行链：Step 9.18 candidate manifest → 最终候选清单 hash → 组件 hash 清单 → 指标注册表与解释协议 → one-shot 运行规则 → 将来独立人工授权。当前只建立冻结与协议，不产生新的 Benchmark 结果。当前候选与 Harness/Scoring hash 全部匹配；Step 9.11 manifest hash 保持不变。静态搜索范围仅覆盖 Agent 生产目录与 requirements config，未发现已知 Benchmark case ID、expected-path 查表或 V2 fixture lookup。V3 保持 `SEALED_NOT_ACCESSED`。

关键设计决定：V2 旧分数仅作历史开发集背景；V2 与 V3 case set 不同，不计算 paired before/after effect。评分沿用冻结 rubric，但 rubric 没有数值锚点，因此分数仅是 trace-based reviewer judgment，不宣称校准或 inter-rater reliability。Critical/Harmful Failure 单独报告，绝不由总体均分抵消。缺失 token / 分项 latency / 精确调用数保持 `NOT_MEASURED` 或 `NOT_AVAILABLE`。允许基础设施重试的门槛非常窄，并要求保留失败 attempt 和新的显式授权。

读完后应能解释：最终 Agent/Harness/Scoring 身份如何从旧 freeze 链继承；各个 metrics 的分母如何确定；为何 V2 与 V3 不能解释为 paired causal comparison；何种运行中断有资格进入人工恢复审查；为什么质量、效率、安全必须分开报告。

已知限制：V3 尚未访问，协议未产生 held-out 实证结果；V3 来源 hash/正式 evaluation ID 必须在下一次明确授权时创建，不能在本阶段预设；单一 reviewer 与评分锚点不足限制分数稳定性；当前 hash 锁定的是仓库记录的非 secret runtime fingerprint，不会记录 API key 内容。最终清单 hash 为 `21e325516f955986497b69e18eebca1d0a0658a24c4293fe75853dd464c901f5`。

### 我的理解


### 仍然不理解的问题

## 第 9.18 步：Low-Value Information Acquisition Repair（低价值信息获取修复）

在 Candidate Generation 与 Heuristic Decision Policy 之间加入统一 Information Value / Acquisition Gate。每个获取候选会按目标相关性、预期信息增益、决策/回答范围影响、当前缺失的关键性、冗余、真实依赖状态及交互/工具成本进行可解释的序数判断。`HIGH / MEDIUM / LOW / NONE` 是启发式等级，不是经校准概率或统计期望收益。Trace 记录 `expected_information_gain`、`goal_relevance`、`decision_impact`、`missing_criticality`、`redundancy`、`resource_dependency`、`estimated_cost`、`acquisition_value`、门控结论和理由。

强制 Hard Precondition 路径保持优先，门控不会因成本、ASK 次数增加或 bounded-answer stop 否决它。可选 ASK 只从当前 goal 的 decision-relevant missing 生成，并拒绝已知、语义等价或已问过的信息；没有活动的证据/日记依赖时不保留相应可选工具动作，已经满足或 unavailable 的资源不重试。若所有可选获取都被拒绝，则转入有明确 `no_worthwhile_information_after_acquisition_gate` 原因的受限回答。没有调低 Sufficiency 阈值。

重点阅读：

1. `adaptive_agent/acquisition_gate.py`：组件如何合成可解释的 ordinal acquisition value，并区分 mandatory dependency 与 optional acquisition。
2. `adaptive_agent/candidates.py`：raw generation 与 policy-ready gating 的边界；候选仍来自 State/Requirements/Dependencies，不由 Benchmark case 驱动。
3. `adaptive_agent/runner.py`：生产 Agent Loop 中门控相对 Candidate Generation 和 Policy 的位置，以及如何把 acquisition decisions 放进每次 state-history snapshot。
4. `tests/test_step9_18_information_value_gate.py`：17 个过度获取/获取不足/反事实和 trace 场景。
5. `evaluation/v1_2_3/step9_18_candidate_freeze.json`：不覆盖 Step 9.11 或 Step 9.17a 的新开发候选身份与完整授权变更链。

验证：新机制测试 **17 passed**；相关聚焦回归 **115 passed**；完整非 Benchmark unittest suite **217 passed / 0 failed / 0 skipped**。其中包含 mocked/offline 的 `test_model_configuration`，未调用真实模型或外部 RAG。无 Benchmark V2 运行、无 V3 访问。Step 9.11 historical freeze 与 Step 9.17a candidate freeze 均保留；新增 post-Step-9.18 candidate freeze，Agent aggregate 为 `0dfdbac361d68dfeb577433107395b50f4c2fa8ca59f3e1d226fbd9271a839a7`。

限制：价值等级尚未统计校准；没有宣称 ASK 数量或 Benchmark 表现改善。当前仅验证候选门控机制与回归兼容性，不替代未来的受控评估。Step 9.18 完成后停止，没有开始下一阶段。

### 我的理解


### 仍然不理解的问题

## 第 9.16 步：Dependency Formation Repair（依赖形成修复）

本阶段完成架构级 Dependency Formation 修复。未读取 Benchmark case 作为开发输入，未修改 Benchmark V2、评分规范或 Decision Policy，未运行 Benchmark V2，未访问 Benchmark V3。

主要修改：

1. `adaptive_agent/dependency_resolver.py` 新增规范化来源类别 `USER_FACTS`、`EXTERNAL_EVIDENCE`、`DIARY_DATA`，并保留旧 `EVIDENCE/RESOURCE` trace 值兼容性。
2. Goal Semantics 现在先形成单一或组合依赖，再同步 Effective Requirements；Task Type 只作为 prior，不直接选择 action。
3. `adaptive_agent/candidates.py` 传递 `source_dependency_id`，形成 `Goal → Dependency → Candidate → Selected Action` 可观测血缘。
4. 未知依赖安全降级为 bounded ANSWER；可选用户事实不会阻塞 evidence retrieval；可用 diary 不会被转换成重复 ASK。

新增 `tests/test_step9_16_dependency_formation.py`，覆盖 8 类 synthetic dependency 场景。聚焦 dependency、effective-requirements 和 integration 回归共 **34 passed / 0 failed**；另有 curated existing Agent regression **64 passed / 0 failed**。完整 unittest discovery 受环境缺少 `flask`/`yaml` 阻塞了 4 个模块导入，未出现本次行为断言失败。

最终状态：

`DEPENDENCY_FORMATION_REPAIRED = YES`

`CASE_SPECIFIC_LOGIC_ADDED = NO`

`AGENT_BEHAVIOR_CHANGED = YES`

`BENCHMARK_V2_RERUN = NO`

`BENCHMARK_V3_ACCESSED = NO`

`REGRESSION_STATUS = PASS`

Step 9.17（Tool → State Projection Repair）可以进入，但本阶段未执行。

## 第 9.15 步：Failure Taxonomy & Repair Prioritization（失败分类与修复优先级）

本阶段只分析 Step 9.14 正式 frozen traces；未修改 Agent、Benchmark V2、评分规范，未重新运行 Benchmark V2，也未访问 Benchmark V3。基于 40/40 完成、Overall 68.275、55 次 ASK、26 次 redundant/irrelevant ASK、3 个 harmful failures 的正式产物，建立了四类架构级失败图谱。

主要结论：

1. **Dependency Formation Failure（P1）**：KQ-02、KQ-05、DA-07 在 `Goal → Goal Semantics / Task Classification → Dependency Formation` 共享首次偏离。前两者缺少 EVIDENCE dependency，后者缺少 RESOURCE(sleep_diary) dependency；后续 ASK 是上游错误的结果。KQ-04/KQ-10 还显示教育目标误触发 diary resource 的反向过度依赖。
2. **Tool → State Projection Failure（P1）**：DA-01/02/03/04/05/08 在 `READ_DIARY → Tool Result / Fixture Adapter → State Projection` 共享 Diary Contract V2 缺陷。系统安全地 fail closed，没有伪造 diary 数据，但 source/projected count、date coverage、provenance 和 aggregation inputs 均未进入 State，导致任务不完整。
3. **Low-Value Information Acquisition（P2）**：26/55 ASK 被复核为 redundant 或 irrelevant。10 次直接来自上述 A 类依赖错误；其余主要涉及过宽 effective requirements、State 缺失导致的 missing detection，以及把低价值候选仍估为 HIGH。不能简单归因于 Decision Policy。
4. KQ-03/08/09 的 retrieval-support mismatch 暂列 P3，当前 trace 不足以隔离 retrieval coverage 与 claim binding。

输出文件：

- `evaluation/v1_2_3/step9_15_failure_taxonomy.json`
- `evaluation/v1_2_3/step9_15_repair_priority.json`
- `evaluation/v1_2_3/step9_15_failure_map.md`
- `evaluation/v1_2_3/step9_15_repair_plan.md`

Step 9.16 只推荐修复 **Dependency Formation Failure**：它有三个共享上游偏离且涉及 harmful failures，修复边界清晰，能同时改善安全、任务完成和一部分 ASK 负担；先修它也能让后续 ASK 质量测量更可解释。当前不应把 ASK/case 优化到零、不应放宽 diary validator、不应孤立调整 ranking/policy，也不应从本轮数据声称泛化或临床有效性。

### 我的理解

### 仍然不理解的问题

## 第 9.13b 步：Final Authorization Audit（最终授权审计）

读取并核验了用户提供的最新 `LOCAL_REAL_PREFLIGHT` artifact（SHA-256：`cd65b8b955c48a3366343cb494646cfeca1bff450b3ca0ef816c0554bd1efeb5`），其 Evaluation ID 与 `clean-evaluation-v1_2_3-20260922-01` 一致，所有本地联网、模型端点、生产 smoke、lineage 和 readiness 门槛均为 PASS。随后执行了 runner 的只读 preflight：Agent、Benchmark V2（40 cases）、Scoring、当前 Harness 四类冻结均匹配，combined identity 匹配，`prior_attempt_count=0`，可执行性为 true。没有运行模型或 Benchmark。

审计确认生产 Agent/configuration 中没有 case-specific 分支或 Benchmark V2 泄漏；冻结的评分代码中存在 reviewer adjudication 映射，属于评分域而非生产 Agent 行为。当前 clean evaluation 尚未运行 Benchmark V2，本阶段未访问 V3。Step 9.8 的失败历史保持不变。

依据用户本轮明确授权签发一次性 Authorization：`clean-evaluation-v1_2_3-20260922-01-auth-step9_13b-22c60aff04df448ea142b2a788d53fbf`，状态为 `ISSUED_NOT_EXECUTED`。它仅允许从 case 1 开始执行一次完整 40-case Benchmark V2 run；runner 会再次核验 frozen hashes，任何正式 attempt（包括失败/部分执行）后都不得自动重试。本阶段没有执行授权命令。

重点阅读：

1. `evaluation/v1_2_3/step9_13a_local_real_preflight_20260922T185940Z_c7153f2c4b6f47b5a7943132a24f9e12.json`：本地真实预检原始机器记录及其冻结 hash。
2. `scripts/run_step9_12_frozen_evaluation.py`：只读 `preflight()` 的四域冻结核验、尝试账本检查，以及正式运行前的 fail-closed guard。
3. `evaluation/v1_2_3/step9_13b_authorization_manifest.json`：本次独立授权身份、范围、输入 hash 和禁止重跑约束。
4. `evaluation/v1_2_3/step9_13b_authorized_command.txt`：唯一允许的本地正式运行命令；本阶段未执行。
5. `evaluation/v1_2_3/step9_13b_final_authorization_audit.md`：本阶段所有 gate 的证据和授权边界。

### 我的理解


### 仍然不理解的问题


## 第 8.8 步：Critical State Semantics & Hard Precondition Boundary

### 已实现内容

本阶段完成了最小的状态语义边界修正：新增
`validity_critical_missing`，并把真正使当前目标无法形成有效有限回答的
state dependency 表达为 `VALIDITY_CRITICAL_STATE`。它不是把
`requirements.yaml` 的所有 critical 字段变成必问项；只有个性化、方向性的
作息时间判断在缺少睡眠时段/起床边界时才进入该硬前置条件。

对于这个窄类型的硬前置条件，系统先看已授权、可用、未读取的睡眠日记；若日记
可提供同一信息，优先 `READ_DIARY`，否则才 `ASK`。如果等价问题已经在上一轮问过
但尚未得到回答，trace 标为 `deferred`，不重复 ASK，而是保留限制并允许受约束回答。

### 重点阅读代码

1. `adaptive_agent/preconditions.py`：阅读 `classify_validity_critical` 和
   `evaluate_preconditions`。前者回答“为什么不是所有 critical field 都是硬条件”，
   后者展示 Resource alternative 如何优先于 ASK，以及为什么已问未答会 deferred。
2. `adaptive_agent/sufficiency.py`：看 `secondary_missing`、
   `decision_relevant_missing`、`validity_critical_missing` 如何并存，而不是被压成一个
   “missing” 列表。
3. `tests/test_v1_2_1_preconditions.py`：看同一个 `wake_time` 在方向性决策与知识解释
   中得到不同分类；同时看 caffeine、夜醒、recent pattern 不会仅因 requirement rank
   升级为 hard precondition。
4. `evaluation/v1_2_1/step8_7_mechanism_traces.jsonl`：阅读 `H_critical_state`；它是
   trace contract 的具体例子，包含 type、target、goal、validity reason、resource
   alternative、selected action 与 status。
5. `docs/v1_2_1_critical_state_semantics.md`：作为本阶段的概念约定，先读三层 missing
   语义表，再读“Repeated Questions and Bounded Answers”。

### 验证结果

Step 8.7 从 **18 / 19** 变为 **19 / 19**。回归测试按全部测试模块分别汇总为
**111 passed，0 failed，0 skipped**。未运行 Benchmark V2，未创建或查看 Benchmark V3。

### 我的理解


### 仍然不理解的问题


## 第 8.9 步：V1.2.1 Development/Regression Evaluation

冻结 manifest 后完成一次 40-case Benchmark V2 development/regression run。结果为
67.50/100、ASK/case 1.650、PD ASK/case 2.917、six-ASK-limit 0、Critical Failures 4、
Harmful Failures 7。它不是 held-out 或泛化结果。Hard Preconditions 一旦在 State 中形成
就没有被 bounded stop 覆盖；但 KQ-02/KQ-05 的上游 task/state 错误仍阻止 EVIDENCE
precondition 形成，DA-07 仍阻止 RESOURCE precondition 形成；DA-03/04/05/08 仍是 diary
summary fixture 无 source cardinality/date metadata 导致的 Tool→State projection failures。

重点阅读 `evaluation/v1_2_1/step8_9_metrics.json`、`step8_9_precondition_analysis.json`、
`step8_9_failure_analysis.md` 和 `step8_9_version_comparison.md`。它们分别展示原始指标、
前置条件可观测性、已知失败链与 V1→V1.2.1 的 development-only 对照。

### 我的理解


### 仍然不理解的问题


## 第 9.1 步：Dependency Formation & Projection Failure Localization

只读 Step 8.9 的 7 个 harmful cases 后定位：KQ-02/KQ-05 的首次偏离在
Input Understanding → Task Representation，知识问答被表示成 PERSONALIZED_DECISION，
所以 Evidence dependency 从未形成；DA-07 同样被表示为个性化决策，Diary resource
dependency 从未形成。DA-03/04/05/08 则正确 READ_DIARY，但 raw tool output 是摘要型
字符串，缺少 source count/date/provenance；投影层错误地在没有可验证 source truth 时
标为 valid，最终把摘要项说成一两天日记。

重点阅读 `evaluation/v1_2_1/step9_1_architecture_diagnosis.md`，再看
`step9_1_failure_chains.json` 和 `step9_1_diary_contract_analysis.json`。前者说明为什么
3/7 是 Dependency Formation、4/7 是 Tool→State Projection，而不是把缺少 RETRIEVE /
READ_DIARY 误归因为 Policy；后者展示 future repair boundary 应在 Tool Contract，而非
靠 Policy 覆盖。

### 我的理解


### 仍然不理解的问题


## 第 9.2 步：Dependency Resolver Architecture Design（设计阶段）

本阶段没有实现或运行任何 Agent。设计正式区分 Requirement（可能改善回答的信息）和
Dependency（当前 goal 有效回答前必须满足的条件），提出 `DependencyResolver`：以 goal
semantics 为主、task type 仅为 signal，输出结构化 EVIDENCE / RESOURCE /
VALIDITY_STATE dependency 及 REQUIRED、AVAILABLE、SATISFIED、UNAVAILABLE、INVALID、
DEFERRED 生命周期。Mandatory dependency 在 Information Value/Cost/Diminishing/
Bounded Answer 之前处理；dependency 本身不是 action，Hard Preconditions 再从多个
satisfiers 中选择 RETRIEVE、READ_DIARY 或 ASK。

重点阅读 `docs/v1_2_2_dependency_resolver_design.md`：看“Goal semantics must dominate
task_type”如何解决 KQ/DA 的 dependency formation failure，以及 ASK pipeline 为什么不应再
从 requirements missing 直接跳到 ASK。再阅读 `docs/v1_2_2_diary_tool_contract_design.md`：
它区分 ENTRY_SHAPED、SUMMARY_SHAPED、UNAVAILABLE、INVALID，要求摘要型日记有 count/
coverage/provenance，否则 fail closed。`evaluation/v1_2_1/step9_2_mechanism_test_plan.md`
包含未执行的 M1–M12 与 diary contract 场景。

### 我的理解


### 仍然不理解的问题


## 第 9.3 步：DependencyResolver & Diary Tool Contract V2 Implementation

实现 `adaptive_agent/dependency_resolver.py`，以 goal semantics 优先、task type 为辅助
signal 形成 EVIDENCE、RESOURCE、VALIDITY_STATE dependencies，并通过 lifecycle 驱动
Hard Preconditions。`preconditions.py` 只消费 dependency objects：EVIDENCE→RETRIEVE，
可用 diary RESOURCE→READ_DIARY，VALIDITY_STATE 先看 resource alternative 再 ASK；这些
mandatory path 不进入 Information Value/Cost/Diminishing/ordinary bounded stop。

DiaryResult V2 增加 `kind`、source count、date coverage、provenance、summary semantics。
投影层区分 ENTRY_SHAPED、SUMMARY_SHAPED、UNAVAILABLE、INVALID；没有 count/date/
provenance/semantics 的 summary 必须 invalid 且不写入 State，防止摘要字符串被解释为一两天。

重点阅读 `adaptive_agent/dependency_resolver.py`、`adaptive_agent/preconditions.py`、
`adaptive_agent/tools.py` 与 `adaptive_agent/state_update.py`。新机制测试在
`tests/test_v1_2_2_dependency_contract.py`，覆盖错误 task signal 下的 goal dependency、
mandatory action precedence 与 diary contract fail-closed。27 项机制相关测试、115 项既有
非模型回归均通过；聚合 model configuration suite 受本环境 30 秒窗口限制未返回，未计为通过。

### 我的理解


### 仍然不理解的问题


## 第 9.4 步：Dependency Integration & Trace Audit

通过真实 `AdaptiveAgentLoop` 的 synthetic runtime audit 确认调用链为 Flask/service →
runner → candidates → preconditions → DependencyResolver → policy → tool → State Update →
refresh。EVIDENCE 与 RESOURCE dependencies 在错误 task signal 下仍能由 goal semantics
形成，工具执行后在 post-tool refresh 中变为 SATISFIED；unavailable/invalid diary 走
fail-closed，不写 diary facts。

重点阅读 `evaluation/v1_2_1/step9_4_integration_trace_audit_report.md` 的 Runtime Call
Chain、Trace Completeness Matrix 与 Integration Defects。审计还发现：goal-semantic
dependency 修复后，错误 task type 的旧 Requirements 仍可能在 RETRIEVE 后产生 ASK；
此外 trace 只有 `goal_semantics` source label，缺少匹配规则/span，也没有稳定 dependency
id 连接 dependency/precondition/candidate。此阶段按要求只记录，不修复。

回归：121 个非模型测试通过；`tests.test_model_configuration` 在环境 30 秒窗口内未完成，
严格标记 NOT_VERIFIED，不计为 passed。

### 我的理解


### 仍然不理解的问题


## 第 9.5 步：Goal / Requirement Synchronization & Trace Lineage Design（设计阶段）

本阶段只分析 Step 9.4 的冻结轨迹和现有代码，没有修改 Agent、Policy、Benchmark 或评分，
也没有运行 V2 或访问 V3。根因是 `runner.py` 在 Input Understanding 后按 `task_type` 解析
一次 Requirements，并在 RETRIEVE / READ_DIARY 后继续复用；因此 Goal Semantics 已正确形成
并满足 EVIDENCE dependency 后，不兼容的旧个性化 Requirements 仍可能计算
`decision_relevant_missing` 并生成额外 ASK。

推荐未来引入 `effective_requirements`：保留 task type 的 `base_requirements` 作为保守先验，
由 goal semantics、resolved dependencies 和已验证 State 同步出当前有效的 optional fields、
scope 与 suppressed fields。Dependency 继续只代表有效回答的硬条件，Requirements 继续代表
可提高回答质量的信息；`required_missing` 绝不直接等价于 ASK。这样不会删除用户已经提供的
optional facts，也不会把所有 field 收集重新引入系统。

重点阅读 `evaluation/v1_2_1/step9_5_goal_requirement_sync_design.md`：先看 Authority
Hierarchy 与 Options，再看 Recommended Lifecycle；它解释为何不应简单让 Goal 永远覆盖
task type，而要让 State truth → goal semantic applicability → task-type baseline → effective
requirements 分层。再读 `step9_5_trace_lineage_design.md`，看 `goal_id → semantic_id →
dependency_id → precondition_id → candidate_id → action/tool/state update` 如何替代依赖 type/
target 的手工推断。

Step 9.6 的最小候选改动边界是 requirements/runner refresh/sufficiency/candidates 及
dependency/precondition trace serialization；不得修改 Input Understanding、Policy、Information
Value、Answer Generation、Diary Contract V2 或任何 Benchmark/评分。模型配置测试保持
NOT_VERIFIED，是独立环境问题。

### 我的理解


### 仍然不理解的问题


## 第 9.6 步：Effective Requirements & Trace Lineage Minimal Implementation

实现了 Step 9.5 的最小同步边界。`RequirementSet` 现在可表达 requirement id、
`mandatory/useful_optional/irrelevant` 分类、semantic adjustments 与 effective marker；
`synchronize_requirements()` 用 base requirements、goal semantics、dependency 与 State 生成
当前 `effective_requirements`。关键点是 Dependency 仍然只通过 Hard Preconditions 强制行动；
Requirements 缺失不会直接变成 ASK。普通 knowledge goal 会抑制不兼容的旧个性化采集字段，
但用户已提供的 facts 仍保留在 State 供受限回答使用。

runner 现在在每次 refresh 从当前 goal/task type 重建 base requirements，执行 preliminary
missing → dependency resolution → synchronization → final sufficiency/candidates；RETRIEVE 与
READ_DIARY 后会产生新 state revision 并重新同步。这样 EVIDENCE 已 SATISFIED 后，旧
PERSONALIZED_DECISION requirements 不再制造 stale ASK；真正 directional 的 `wake_time`
缺失仍保留 VALIDITY_CRITICAL_STATE → ASK。

重点阅读 `adaptive_agent/requirements.py` 的 `synchronize_requirements()`，再看
`adaptive_agent/runner.py` 的 `_refresh()` 两阶段流程。血缘实现见
`adaptive_agent/dependency_resolver.py`、`preconditions.py`、`state.py` 与
`state_update.py`：trace 现能连接 `goal_id → semantic_id → dependency_id → precondition_id
→ candidate_id → action_id → tool_result_id → state_update_id`，而不是按 type/target 手工猜测。

`tests/test_step9_6_effective_requirements_lineage.py` 覆盖 S1–S12，结果 **12/12 PASS**；
非外部模型回归 **133 passed / 0 failed / 0 skipped**。`tests.test_model_configuration` 在本环境
30 秒窗口无输出，严格为 **NOT_VERIFIED**。本阶段未修改 Decision Policy、Information
Value/Cost、Answer Generation 或 Diary Contract V2；未运行 V2，未访问 V3。

### 我的理解


### 仍然不理解的问题


## 第 9.7 步：End-to-End Integration & Lineage Verification

本阶段没有修改 Agent。以受控 fixture 经生产 `create_app()` 的 `/api/chat` route 定义接入
真实 `AdaptiveChatService`、session persistence、Adaptive Loop、Requirements、DependencyResolver、
preconditions、candidates、Policy 与 State Update，执行 I1–I8。结果 **8/8 PASS**：错误
task signal 下的知识 goal 仍是 EVIDENCE→RETRIEVE→SATISFIED→ANSWER 且无 stale ASK；真实
directional 缺失仍 ASK；follow-up 不重复 ASK；diary valid/unavailable lifecycle、goal change
和 useful optional facts 均符合设计。

重点阅读 `scripts/run_step9_7_integration.py`，它演示如何不调用外部模型却验证 API route、
service、session 和 loop 链路。完整结果在
`evaluation/v1_2_1/step9_7_integration_scenarios.json`、
`step9_7_integration_traces.jsonl`、`step9_7_lineage_audit.json` 和
`step9_7_effective_requirements_lifecycle_audit.json`。Lineage audit 为 **PASS**，Agent trace
observability gaps 为 **0**；focused 40 项通过，完整非模型回归 **133 passed / 0 failed / 0 skipped**。

`tests.test_model_configuration` 及完整 `main_flask` module import 都在本环境 30 秒窗口内
未返回，因此严格为 **NOT_VERIFIED**，不能称为实时 WSGI/外部模型验证。该限制不属于 I1–I8
中的 Agent integration bug。本阶段未运行 V2、未访问 V3、未改 Policy、Information Value/Cost
或 Answer Generation。

### 我的理解


### 仍然不理解的问题


## 第 9.8 步：Frozen Benchmark V2 Development Evaluation（启动阻断）

本阶段先核对冻结输入：Benchmark V2 case count 为 40，Benchmark SHA-256 与 Step 8.9
完全一致，scoring rubric SHA-256 也完全一致；已写入 Step 9.8 freeze manifest。随后按授权
只启动一次正式 runner，但它在本环境 30 秒窗口内没有返回任何 case 输出。检查确认没有 raw
trace，意味着 40 个 case 中 **0 个开始执行**。

这与 Step 9.7 的完整 `main_flask` import NOT_VERIFIED 限制处于相同启动边界，不能被解释成
Agent 的 PASS/FAIL、空跑、零分或 benchmark 结果。为遵守“一次 frozen run、不得挑选重跑”的
约束，没有重试、没有生成假 trace、没有产生评分/ASK quality/failure/lineage/version delta。

阅读 `evaluation/v1_2_2/step9_8_freeze_manifest.json` 可确认冻结输入；
`step9_8_evaluation_report.md` 记录阻断层和不重跑理由。后续若要继续，必须由人工明确决定
如何处理这次未进入 case 的启动尝试，并单独授权 startup/infrastructure 调查。此阶段未修改
Agent、Benchmark、scoring、Policy、Information Value/Cost 或 Answer Generation，未访问 V3。

### 我的理解


### 仍然不理解的问题


## 第 9.8a 步：Run Infrastructure Preflight

保留 Step 9.8 的 `RUN_INITIALIZATION_FAILURE` 原始记录：0/40 case、无 trace、无分数，不能用于
结果选择。最小诊断用 faulthandler 确认首次阻塞发生在 **import-time**：`main_flask → rag_client
→ langchain_core.tools → callbacks/runnables` 的 legacy RAG/LangChain 加载链；此时 Flask factory、
Adaptive service、模型调用、RAG query 和任何 benchmark case 都尚未开始。

基础设施修复是抽取 `adaptive_agent/flask_app.py` 作为 import-light 的生产 `/api/chat` factory；
`main_flask` 继续导出同一 factory，而 Benchmark harness 直接导入该模块，避开无关 legacy workflow
初始化。它仍使用原有 AdaptiveChatService、Session、Loop、DependencyResolver、tools、State Update、
LLM understander/answer generator；没有第二套 Agent，也没有 case-specific branch。

重点阅读 `adaptive_agent/flask_app.py` 和 `scripts/run_step9_8_frozen_evaluation.py`，再读
`evaluation/v1_2_2/step9_8a_infrastructure_diagnosis.md`。非 Benchmark preflight 经真实 Flask
test client `/api/chat` 完成 `EVIDENCE → RETRIEVE → SATISFIED → ANSWER` 并产出 lineage。focused
44 项、I1–I8（8/8）和非模型回归（133）均为 0 failed。model configuration 仍 NOT_VERIFIED。

等价性审计结论：Agent behavior/Benchmark/Scoring 均未改变，production components reused=YES，
harness changes behavior=NO，case-specific logic=NO；因此 **ready for one authorized frozen Step 9.8 rerun=YES**。
本阶段没有运行 V2、没有访问 V3。

### 我的理解


### 仍然不理解的问题


## 第 9.8b 步：One Authorized Frozen Benchmark V2 Rerun（环境失败）

本次唯一授权重跑成功越过 Step 9.8 原有的 legacy `main_flask` import 阻断，并进入第一个
Benchmark 请求的真实 `LLMInputUnderstander`。随后在外部模型调用的 DNS 连接阶段发生
`httpx.ConnectError: nodename nor servname provided`，向上成为 `openai.APIConnectionError`。
此时第一个 HTTP response 尚未返回，因此 **0/40 case result**、无 case trace、无评分/ASK
quality/failure/lineage 结果。runner 创建的零字节 raw 文件被保留，不能解释为成功空跑。

严格遵守一次性协议：没有重试、没有请求网络权限、没有改用 mock/fallback 模型、没有修改
Agent/Benchmark/Scoring，也没有访问 V3。阅读
`evaluation/v1_2_2/step9_8b_execution_report.md` 和 `step9_8b_freeze_manifest.json` 可复查
此次授权调用的边界。后续若要运行必须再次由人工明确授权外部网络/模型环境和新的实验尝试。

### 我的理解


### 仍然不理解的问题


## 第 9.8c 步：External Model Connectivity Preflight

只读检查确认生产模型配置为 DeepSeek-compatible endpoint：model=`deepseek-flash`、
endpoint=`https://api.deepseek.com`、`DEEPSEEK_API_KEY=PRESENT`；没有读取或记录 key 内容，也
没有修改任何配置。对实际 endpoint hostname 的最小 DNS 解析直接失败：
`gaierror [Errno 8] nodename nor servname provided`。因此首个阻塞点是 DNS，HTTPS、endpoint、
真实模型 probe 和 `LLMInputUnderstander` smoke 全部按协议 **NOT_RUN**。

重点阅读 `evaluation/v1_2_2/step9_8c_external_model_connectivity_preflight.md`；它包含完整矩阵、
sanitized error 和历史运行状态。Step 9.8 的 RUN_INITIALIZATION_FAILURE 与 Step 9.8b 的
RUN_ENVIRONMENT_FAILURE 都已保留，本阶段不产生 Benchmark 分数、未运行 V2、未访问 V3，未修改
Agent/Policy/Input Understanding/模型配置。

### 我的理解


### 仍然不理解的问题


## 第 9.8d 步：Execution Environment Resolution

环境诊断同时解析公共控制域名 `example.com` 与 `api.deepseek.com`；两者都返回相同
`gaierror [Errno 8]`。因此证据支持 `ENVIRONMENT_NETWORK_RESTRICTED`：GENERAL_DNS=FAIL、
DEEPSEEK_DNS=FAIL、OUTBOUND_HTTPS=NOT_AVAILABLE、Work 中真实模型执行=UNSUPPORTED，推荐位置
为 LOCAL。没有发送 HTTPS/模型请求，因为 DNS 已是首个阻塞点；没有修改 provider、model、base URL、
credential 或 DNS，也没有运行 V2/访问 V3。

重点阅读 `evaluation/v1_2_2/step9_8d_execution_environment_resolution.md`，它说明为何这不是
endpoint-specific 或临时网络结论。若本地执行，遵循
`step9_8_local_execution_instructions.md`：在独立复制目录归档当前 output 后，使用现有 runner
和冻结 Benchmark/rubric 运行一次；original Work 的 Step 9.8/9.8b 失败记录必须保留。

### 我的理解


### 仍然不理解的问题


## 第 9.8e 步：Frozen Run State Reconciliation（冻结运行状态对账）

本阶段只审计 Step 9.8 系列工件与 runner guard；没有运行 Benchmark V2、没有修改 Agent、Benchmark、
scoring 或历史工件，也没有访问 V3。结论为 **`FROZEN_RUN_NOT_CONSUMED`**：Step 9.8 是
`RUN_INITIALIZATION_FAILURE`（0/40），Step 9.8b 虽进入第一个真实模型请求却在返回 response 前 DNS/API
连接失败（0 个完成的 case result），现存原始 trace 容器为 **0 bytes / 0 records**，没有有效 score 或结果。
`evaluation/v1_2_1/step8_9_raw_traces.jsonl` 的 40 行只属于历史 Step 8.9，绝不能误计为 Step 9.8 结果。

冻结输入仍可复查且完全一致：Benchmark V2 SHA-256 为
`dfa9b9e5a12b0017fa68d344d01b313ebc29e583b933fbe1e93c125f55ecafd2`，scoring rubric SHA-256 为
`a7f5681f4fc7421d3617a7cc69ec4c08dc84d1871b290f08f86df68bde808899`；均匹配 Step 8.9、Step 9.8、
Step 9.8b 与当前冻结文件。

当前 `scripts/run_step9_8_frozen_evaluation.py` 的 guard 是
`manifest exists → refuse run`，即 **MANIFEST_EXISTENCE_BASED**。它可以保护文件不被覆盖，却不能区分
“仅创建 manifest”“第一个 case request 已发出但无 result”“partial/completed run”。用户报告的本地尝试已
作为审计事实记录：`LOCAL_FROZEN_ATTEMPT=BLOCKED_BY_MANIFEST_GUARD`、`CASES_EXECUTED=0`、
`MODEL_CALLS=0`、`BENCHMARK_RESULTS=NONE`；该事实不是 Agent failure。

重点阅读 `evaluation/v1_2_2/step9_8e_frozen_run_state_audit.md`，它给出每个历史 attempt、证据边界和
对账结论；再读 `step9_8e_guard_fix_design.md`。后者只是最小设计：保留 immutable manifest，另建 append-only
attempt ledger，明确 `PREPARED / STARTED / COMPLETED / FAILED_BEFORE_FIRST_CASE /
FAILED_DURING_FIRST_CASE_BEFORE_RESULT / FAILED_AFTER_PARTIAL_EXECUTION`，并要求每次新尝试有独立人工授权。
本阶段**没有实施**该设计，不能据此自动重跑。

### 我的理解


### 仍然不理解的问题


## 第 8.7 步：V1.2.1 Preconditions & State Integrity Mechanism Validation

新增 19 个 synthetic mechanism scenarios：18 PASS、1 FAIL。Evidence/Resource
hard preconditions、cost/diminishing/stop precedence、diary projection truth 与
fail-closed 都通过；现有 V1.2 Information Value 回归也通过。

唯一 FAIL 是 `CRITICAL_STATE` 的 trace 语义：真正 decision-changing 的
`wake_time` 会 ASK，但没有写入 `preconditions_considered`，仍走 Information
Value candidate path。它不是行为失败，却说明当前 “CRITICAL_STATE 是 hard
precondition” 的架构声明与实现不一致；本阶段按要求不修复。

重点阅读 `evaluation/v1_2_1/step8_7_mechanism_validation_report.md` 和
`step8_7_mechanism_traces.jsonl` 的 H scenario；下一步必须先决定
CRITICAL_STATE 的正式语义，再修改实现。

### 我的理解


### 仍然不理解的问题


## 第 8.6 步：V1.2.1 Hard Preconditions & State Integrity

实现 `adaptive_agent/preconditions.py`：Evidence/Resource 的硬前置条件在
Information Value 之前运行；满足条件时生成唯一的 RETRIEVE/READ_DIARY action，
bounded stop 不能覆盖它。Critical state 仍只使用 decision-relevant missing，避免
把所有旧 critical requirements 重新变成强制 ASK。

Diary Tool→State 现在保存 source/projected entry count、dates、projection status
和 warning；显式 entry 投影不一致时进入 invalid 状态且不写入 diary facts。
目标回归 23 passed/0 failed；未运行完整 Benchmark V2。

重点阅读 `docs/v1_2_1_preconditions_state_integrity.md`、
`adaptive_agent/preconditions.py`、`adaptive_agent/state_update.py` 和
`tests/test_v1_2_1_preconditions.py`。

### 我的理解


### 仍然不理解的问题


## 第 8.5 步：V1.2 Failure Decomposition & Safety Boundary Analysis

只读 Step 8.4 frozen traces 后确认 4 个 Critical Failure 仅为 DA-03/04/05/08
的 diary fixture contradiction；KQ-02、KQ-05、DA-07 是 harmful stops，不能自动升级为 critical。它们的第一个错误是 Input Understanding/State 未建立 evidence 或 diary resource dependency，导致 RETRIEVE/READ_DIARY 从未进入 candidate set；因此不是已观测的 Information Value false negative。

重点阅读 `evaluation/v1_2/step8_5_failure_decomposition.json` 的 primary/downstream 区分，以及 `step8_5_safety_boundary_analysis.md` 的五层建议。核心结论是 hard precondition 必须在 Information Value/Cost 前验证；diary projection 要单独修 Tool→State integrity，不能用 Policy 掩盖。

### 我的理解


### 仍然不理解的问题


## 第 8.4 步：V1.2 Development Evaluation on Benchmark V2

V2 已明确转为 development/regression set。冻结 source/rubric/V2 hash 后只运行
一次 V1.2：Overall 67.50、ASK/case 1.775、PD ASK/case 3.000、six-ASK 0。
但不能把 ASK 降低视为成功：DA-03/04/05/08 有 4 个 diary-projection critical
failures；KQ-02、KQ-05 与 DA-07 是 harmful bounded stops，其中 DA-07 跳过了
已授权的 required diary。

重点阅读 `evaluation/v1_2/v1_2_information_value_metrics.json` 的 465 个
considered candidates、214 个 rejection 和 18 个 stop；再读
`step8_4_failure_analysis.md`，理解为什么 V1.2 的 Information Value 机制确实
改变路径，但还不能声称泛化或性能优越。

### 我的理解


### 仍然不理解的问题


## 第 8.3 步：V1.2 Information Value Mechanism Validation

新增 `tests/test_v1_2_mechanism_validation.py` 与
`evaluation/v1_2/step8_3_mechanism_traces.jsonl`，用 18 个不属于 Benchmark
的纯 State/Requirements 场景验证 V1.2：题设 A–L、MEDIUM 在 ASK 0/1/3/5 的
diminishing return，以及同一 caffeine 缺口在不同 goal 下 LOW→HIGH 的
counterfactual pair。结果为 **18/18 PASS**；未运行 V2、未创建/查看 V3、未改
Agent。

重点阅读 `tests/test_v1_2_mechanism_validation.py` 的 `evaluate()`：它直接
保存 estimate、候选、rejection、selected action、stop reason，而不伪装成模型
输出；再对照 `evaluation/v1_2/step8_3_mechanism_validation_report.md` 的
historical-pattern boundary，理解“已验证 state-level mechanism”与“尚未证明
真实 extraction / Benchmark 改善”的差别。

### 我的理解


### 仍然不理解的问题

## 第 7.5 步：V1.1 Post-Evaluation Diagnosis

## 第 8.1 步：Information Value Design for Adaptive Agent V1.2

## 第 8.2 步：Adaptive Agent V1.2 Information Value Implementation

### 已实现内容

新增 `adaptive_agent/information_value.py`，实现 HIGH/MEDIUM/LOW/NONE 信息价值、
counterfactual decision test、ASK/RETRIEVE/READ_DIARY 成本、资源替代、边际收益递减
和 bounded-answer stop rule。候选生成现在记录 considered/rejected information、
rejection reason、value/cost、resource alternative 与 stop reason；高价值决策问题仍
可在多轮后保留 ASK。新增 7 个通用测试，完整测试结果：98 passed，4 skipped，0 failed。

未运行 Benchmark V2，未创建或查看 Benchmark V3，未进入 Step 8.3。

### 已实现内容

仅基于冻结 Step 7.4/7.5 artifacts 完成离线 Information Value 设计，未修改 Agent、
Benchmark V2、评分规范或历史实验结果。提出 HIGH/MEDIUM/LOW/NONE 序数模型、
counterfactual decision test、ASK/RETRIEVE/READ_DIARY/ANSWER 成本模型、边际收益
递减和 bounded-answer stop rule。

对 V1.1 的 112 ASK 完成回顾映射：21 HIGH、9 MEDIUM、0 LOW、82 NONE（其中
redundant 39、irrelevant 43）。PD 的通用失败模式包括 requirements completeness
冒充决策价值、抽取失败扩大缺失集合、缺少边际收益递减、未比较资源替代、以及把
detail-improving 当作个性化必要信息。

已生成 `evaluation/v1_2/` 下三个 Step 8.1 输出文件。仅提出 V1.2 候选架构与未来
held-out Benchmark V3 协议；没有实现 V1.2、创建 V3 或运行 Benchmark V2。

### 诊断结果

只读取 Step 7.4 冻结 artifacts，未修改 Agent、Benchmark、rubric 或重新运行。
V1.1 共 112 ASK（2.800/case），其中 necessary 21、useful-but-optional 9、
redundant 39（34.8%）、irrelevant 43（38.4%）。V1 为 111 ASK、2.775/case、
72.1% redundant。说明 ASK 数量没有下降；redundant rate 按同一 trace-only 分类下降，
但 irrelevant ASK 上升，质量改善不完整。

PD 仍是主要瓶颈：V1.1 为 5.333 ASK/case、9 个 six-ASK-limit cases。Step 7.1 的
显式事实遗漏和重复追问在模型运行轨迹中仍存在；Step 7.3 的 DA-04/DA-08 日记投影
矛盾本次未观察到，但这是本次离线 review 的 run-specific 结果。ASK gate 被拒绝的
候选数量无法从冻结 trace schema 精确观测。

已生成 `step7_5_ask_quality_analysis.json`、`step7_5_failure_clusters.json` 和
`step7_5_post_evaluation_diagnosis.md`。仅提出未实施的 V1.2 研究方向；未进入 V1.2。

## 第 7.4 步：Frozen V1 vs V1.1 Paired Evaluation

### 实验结果

使用未修改的冻结 Benchmark V2（40 cases、manifest SHA-256 保持不变）完成一次
V1.1 正式运行。V1 历史结果复用，不重跑；V1.1 原始轨迹永久保存在
`evaluation/v1_1/v1_1_v2_raw_traces.jsonl`。V1.1 观察到 Overall 65.03，ASK/case
2.800，11 个 six-ASK-limit cases，离线 rubric review 未发现 critical failure。
V1 对应为 63.85、2.775、13、2 个 critical failures。配对逐 Case 结果、metrics、
failure analysis 和报告均已生成。

这次运行仍有较高 ASK 负担，不能仅凭 ASK 减少或总分变化宣称泛化优势；token/LLM
调用 telemetry 继续标记 `not_available`。没有运行后修复、覆盖或第二次重跑。

### 实验状态

Step 7.4 已完成；未修改 Agent、Benchmark V2 或评分规范；未进入 V1.2。

## 第 7.3 步：Answer & Tool Data Grounding

### 已实现内容

新增 claim taxonomy 与 `claim_provenance` 追踪，区分用户事实、日记事实、确定性
派生、证据支撑和 unsupported claim。回答上下文现在包含结构化 provenance；确定性
投影统一计算跨午夜卧床时长、睡眠效率、日记条目数、平均总睡眠和日期覆盖，范围/近似
时间不会被压成唯一 duration，不可用或缺失日记数据不会伪造进入回答。

最终回答增加确定性 validation：移除无证据的医学量化规则、拒绝不一致数字，并在
State 为 range/approximate 时弱化精确时间表达。新增工具→State→Answer 一致性回归测试。
完整单元测试结果：91 passed，4 skipped，0 failed。Benchmark V2 未运行；未进入 Step 7.4。

### 已知限制或技术债务

非量化 unsupported prose 的自动识别仍较保守；证据 provenance 当前按本轮 evidence
列表位置编号，而不是稳定文档 ID；没有正式期望日期窗口时不会推断日记缺失天数。

## 第 7.2 步：Sufficiency & Redundant ASK Control

### 已实现内容

在 Step 7.1 State 基础上新增 `required_missing`、`decision_relevant_missing` 与
`secondary_missing` 三类区分。ASK 现在必须通过未知、当前目标相关、可能改变下一步
决策/回答范围、且未被等价问题询问过的资格门槛。range / approximate 已有事实默认
可用于有界判断；secondary 缺失不再阻塞 ANSWER。ASK history 按规范化 requirement
target 去重，资源可提供信息时优先保留 READ_DIARY，不可用资源不会无限重试。

新增通用 Step 7.2 回归测试。完整单元测试结果：84 passed，4 skipped，0 failed。
冻结 Failure Set 未修改；Benchmark V2 未运行；未进入 Step 7.3。

### 已知限制或技术债务

信息价值仍是可解释的 ordinal heuristic，不是校准概率；ASK 等价性当前基于规范化
requirement target，不使用 embedding；只有目标明确要求更高精度时才应进一步扩展 refinement。

## 第 7.1 步：Adaptive Agent V1.1 Input Understanding & State Integrity

### 已实现内容

完成输入理解与 State 完整性加固：显式事实按 Raw → Normalized → Validated →
State 进入；支持中英文时间/时长、复合句多字段拆分、跨午夜计算，以及 range /
approximate 不确定性保留。新增字段级 provenance（source type、turn、原文、
raw/normalized value、certainty、derived source fields），多轮更新遵循新显式
事实修正同字段、无关事实保留、派生/日记事实不覆盖显式事实。

新增 `adaptive_agent/facts.py` 确定性计算模块和通用回归测试。完整单元测试结果：
75 passed，4 skipped，0 failed。冻结的 `adaptive_v1_failure_set.yaml` 未修改；
Benchmark V2 未运行；未进入 Step 7.2。

### 已知限制或技术债务

规范化器只覆盖现有 Requirements Schema 相关睡眠事实，不扩展为通用临床语义解析。
直接调用理解器而非通过 loop 时没有可用的真实 turn index；未明确的矛盾表达保持保守，
需要后续澄清。

## 第 6.1 步补充：V2 冻结基线运行结果

运行器的 stdout 未回传曾造成短暂误判，但 trace 文件确认同一轮冻结运行
实际完成 40/40；没有重跑。V2 独立基线为 **63.85/100**，Critical Failure
为 **2**。KQ 91.5、CA 65.4、PD 31.67、DA 75.62；V1 的 repeated-ASK
问题自然复现（111 asks 中 80 redundant，13 case 到达六轮 ASK 上限）。

DA-04/DA-08 还发现新模式：`READ_DIARY` 后，压缩 diary fixture 被回答层
错误描述为一/两天，形成与日记数据矛盾的 critical failure。没有改 Agent、
Benchmark 或 scoring；这是后续获授权后要通过通用 diary projection/provenance
机制处理的问题，而不是针对 case 的特判。

重点阅读 `evaluation/v2/adaptive_v1_v2_traces.jsonl`（原始状态与行动）、
`evaluation/v2/adaptive_v1_v2_scores.jsonl`（五维分数与 critical 标记）、
`evaluation/v2/adaptive_v1_v2_metrics.json`（聚合且不估算缺失 telemetry）和
`evaluation/v2/adaptive_v1_v2_failure_analysis.md`（根因/下游影响边界）。

### 我的理解


### 仍然不理解的问题


## 第 6.1 步：Frozen Adaptive V1 on Benchmark V2（阻断记录）

### 已实现内容

V2 已在第一次运行前正式冻结：`benchmark_v2_cases.yaml` 标记为
`benchmark_v2_frozen`，并在
`evaluation/v2/benchmark_v2_freeze_manifest.json` 保存 40 例与 SHA-256。

本次基线运行在第一个 Case 之前被基础设施阻断。运行器必须从
`main_flask` 获得真实 `/api/chat` factory；但该模块导入期间无法返回，且
没有 Python traceback。没有发送任何 V2 user turn、没有运行 Agent、没有
评分。按第 6.1 步规则，保留零字节 trace 和阻断报告，不绕过、修复或
重跑。它不能被解释为任何 Adaptive V1 泛化结果。

### 重点阅读代码

1. `evaluation/v2/benchmark_v2_freeze_manifest.json`：确认冻结状态、40-case
   count 与 dataset hash；它是后续重新授权运行时的可审计输入，而不是结果。
2. `scripts/run_step6_1_v2_baseline.py`：看它为何坚持经现有 `/api/chat`
   factory、如何隔离 session/diary fixture，以及为何零字节 trace 不可覆盖。
3. `main_flask.py` 的 `_create_adaptive_chat_service`、`create_app` 与模块级
   `cognitive_therapy_agent = CognitiveTherapyAgent().main_graph`：理解生产
   factory 和 legacy global initialization 的耦合为何会阻断实验启动。
4. `evaluation/v2/adaptive_v1_v2_failure_analysis.md`：阅读诊断证据与保守的
   `other` attribution；它不是 Policy、Input Understanding 或 Answer
   Grounding failure。
5. `evaluation/v2/adaptive_v1_v2_report.md`：核对哪些指标应为
   `not_available`，而不是误写为零或失败分数。

### 我的理解


### 仍然不理解的问题


## 第 4.1 步：资源依赖、目标级充分性和候选排序修正

### 已实现内容

将日记可用性与资源读取状态分离，以 Requirements 的 sleep_diary 依赖驱动读取。将 critical_missing 与真正影响当前回答范围的 decision_missing 分开：方向问题可以在部分 critical 仍缺失时停止 ASK。候选携带定性的相关性、影响、冗余和成本，排序不依赖 YAML 顺序。仅离线测试，没有调用外部模型。

### 重点阅读代码

1. `adaptive_agent/requirements.py` 的 `resolve_requirements`：看“是否早点上床”的方向范围如何与具体处方区分，以及 goal 明确涉及咖啡、夜醒时为什么会增加必要信息。
2. `adaptive_agent/sufficiency.py` 的 `update`、`user_information`：看为什么 available 不能替代 loaded，为什么 critical_missing 非空而 decision_missing 为空时仍可在限制范围内 HIGH。
3. `adaptive_agent/candidates.py` 的 `build_candidates`：看剩余缺口如何重新估计价值，已知/等价/已经问过的信息如何排除，unavailable 如何转成限制说明。
4. `adaptive_agent/policy.py` 的 `preference`：看收益、相关性、影响、冗余与成本的定性比较；字段名只用于完全等价时保证确定性，不代表医疗价值。
5. `tests/test_policy_refinement.py`：重点读 Case 1 留三项 critical 缺失仍可停止询问的测试，以及 goal 明确涉及更多因素时会合理问四次的对照；不是人为设置 ASK 次数上限。

### 重要执行流程

```text
goal → 任务默认 requirements → 当前 goal 的 decision_fields / answer_scope / resources
→ facts 与资源状态 → decision_missing + sufficiency
→ 具体候选与定性价值 → 稳定排序 → 一个行动
→ ASK 的下一轮/工具结果 → 合并并重新评估
```

Case 1 从四次 ASK 变成一次 wake_time，再 RETRIEVE → ANSWER；总睡眠、夜醒和近期规律继续保持未知。Case 3 从 available 后直接 ANSWER，变为 unread → READ_DIARY → facts 合并 → loaded → ANSWER。未宣告可用但工具有数据时也遵循此流程。

### 关键设计决策

- 资源依赖来自 requirements；没有 `DATA_ANALYSIS → READ_DIARY` 的直接映射。
- readiness 必须对应 answer_scope。减少询问只支持更窄的方向讨论，不自动支持具体限制处方；scope 已传给回答生成器。
- critical_missing 用于追踪已知/未知；decision_missing 表达当前范围真正需要的信息，不再以缺失数量决定是否继续问。
- 完全同分时使用稳定字段名，不让 YAML 顺序隐式充当价值判断。

### 阅读后应能回答的问题

- 为什么日记 available 但 unread 时不能 ready ANSWER？
- Case 1 为什么补完 wake_time 后可以停问，却不能给出精确新上床时间？
- goal 加上“咖啡影响”后，为什么原本 secondary 的 caffeine 会变为高价值问题？
- 如何证明 ASK 减少不是来自硬编码“一次或两次”的上限？
- 排序中哪些因素反映语义，哪一步仅保证可重复？

### 已知限制或技术债务

目标规则是人工维护的有限 V1 规则；未知目标仍采用保守默认需求。资源 loaded 不表示七天覆盖或临床信息质量已验证。真实模型提取、证据相关性和 scope 遵循尚未外部验证。完整报告见 `evaluation/step4_1_report.md`。

### 我的理解


### 仍然不理解的问题



## 第 4 步最终验收：Step 4.1 后的受控离线复验

### 已实现内容

未修改 Policy，也未调用外部 LLM API。通过真实 Flask `/api/chat` 加显式离线 fixture 重新执行三个验收案例，并把 HTTP 级输入理解、决策、工具结果、更新后 State 与响应写入 `evaluation/runs/step4-step4-final/`。完整测试在项目 `.venv` 中为 41 passed、0 failed、0 skipped、0 expected failure；原先错误环境导致的 LangChain skipped 本轮不存在。

Step 4（受控离线验收）通过：Case 1 只问一次 `wake_time`，随后 RETRIEVE → ANSWER；Case 2 不问无关个人信息，RETRIEVE → ANSWER；Case 3 在 `sleep_diary=unread` 时必定 READ_DIARY，日记可用则 facts 合并并标记 loaded 后再 ANSWER，不可用则不合并 facts、标记 unavailable 并受限 ANSWER。真实模型的语言质量不在本轮结论内。

### 重点阅读代码

1. `scripts/validate_step4.py`：本轮验收的入口。看它如何不经过平行聊天流程，而是调用真实 `create_app()` 和 `/api/chat`，并将每个 HTTP 回合的 observation 写入 JSONL。
2. `adaptive_agent/runner.py` 的 `run_turn`：看一个工具完成后为何一定重算 State 并再次决策；Case 1 的 RETRIEVE、Case 3 的 READ_DIARY 都在同一 loop 中走到 ANSWER。
3. `adaptive_agent/sufficiency.py` 的资源和 `decision_missing` 判断：这是“Case 1 不补齐全部 critical”和“Case 3 未读日记不能 ANSWER”同时成立的关键边界。
4. `adaptive_agent/candidates.py` 的 `build_candidates`：看 READ_DIARY 是由 resources 状态而不是 `DATA_ANALYSIS` 任务类型直接触发，unavailable 后又为何不会重复读取。
5. `evaluation/runs/step4-step4-final/http-traces.jsonl`：重点顺序阅读 Case 1 的两行与 Case 3 可用/不可用两行；每行的 `observations` 和嵌套 `state_history` 可还原完整决策轨迹。

### 重要执行流程

```text
真实 /api/chat（offline fixture）
→ load / merge session state
→ requirements + required_resources + decision_missing
→ sufficiency + candidate → one action
→ ASK 保存回合，或 tool result 更新 State
→ re-evaluate → ANSWER
→ HTTP / evaluation JSONL 记录
```

Case 1 的继续 ASK 不由 critical 字段数决定：`wake_time` 影响方向判断，故值得问；余下缺失字段不影响限定范围内的下一步。Case 3 的资源必须从 unread 变为 loaded 或 unavailable，不能仅凭 available 标志生成数据分析。

### 关键设计决策

- 本轮只验证 Step 4.1 后行为；没有为了验收结果继续增加规则。
- 把“受控离线路由与状态验收通过”与“真实外部模型医学回答质量”明确分开报告，避免 fixture 被误解为真实 LLM 证据。
- 把不可用日记的最终 ANSWER 视为限制说明：它符合 scope，但不是分析结论。
- 允许进入离线可控的 Step 5 Benchmark；真实模型/RAG benchmark 仍须单独授权合成或脱敏数据的外部调用。

### 阅读后应能回答的问题

- 为什么 Case 1 的三项 remaining critical_missing 不会自动产生三次 ASK？
- 在 Case 3 中，`unread`、`loaded`、`unavailable` 三种资源状态分别如何影响候选和最终回答范围？
- `http-traces.jsonl` 的一条 observation 如何证明工具结果进入 State 后确实重新决策？
- 为什么本轮的 PASS 不等于真实 LLM 的回答质量已经通过验收？
- 什么条件下可以把此结果作为进入离线 Benchmark 的门槛？

### 已知限制或技术债务

外部真实 LLM/RAG 的事实提取、证据相关性、回答质量与语言层 scope 遵从尚未测试，原因是当前禁止发送健康测试数据。日记 loaded 仅表示读取成功，并未验证七天完整覆盖或临床信息质量。人工 V1 goal 规则的覆盖范围有限；新增目标应以明确失败案例扩展。完整结果见 `evaluation/step4_final_acceptance_report.md`。

### 我的理解


### 仍然不理解的问题


## 第 4.5 步：真实模型冒烟测试

### 已实现内容

使用五条人工构造的虚构睡眠数据和一份人工构造的七天日记，通过真实 `/api/chat` 验证真实 Input Understanding、项目 RAG 和真实 Answer Generation；未改动 Decision Policy。首先发现 SDK 默认的 `json_schema` structured output 被当前 DeepSeek endpoint 以 HTTP 400 拒绝。将 Input Understanding adapter 最小改为显式 `function_calling` 并增加一条兼容性回归测试；这不是 Policy 修改。

修复后五例结果为 2 PASS / 3 FAIL。知识问答走真实 `RETRIEVE → ANSWER` 并使用相关 RAG evidence；日记分析走 `READ_DIARY → loaded → re-evaluate → ANSWER`，回答只基于虚构日记。三个失败都来自真实 Input Understanding 漏掉用户明确给出的入睡时长；原因评估还漏掉“两周”和咖啡。错误 State 随后导致重复询问 latency，不是 Policy 的系统性问题。完整回归为 42 passed；其中原有 41 项保持通过。

### 重点阅读代码

1. `adaptive_agent/input_understanding.py` 的 `LLMInputUnderstander.__init__` 与 prompt：看为什么此 endpoint 必须选 `function_calling`，以及“只提取明确事实”的指令为什么仍不足以稳定抽取中文时长、频率和咖啡因信息。
2. `scripts/smoke_step4_5.py`：本轮唯一新增的验收入口。它使用真实 app factory 和 `/api/chat`，只注入虚构日记，不替换模型、RAG、Answer Generator 或 Policy，并保存各边界 observation。
3. `evaluation/runs/step4_5-real-model-smoke-rerun/http-traces.jsonl`：先读 Case 2/3/4 的 `input_understanding` result，再读 `DECISION`，可以看到“遗漏事实 → decision_missing 虚增 → 重复 ASK”的完整因果链。
4. `adaptive_agent/requirements.py`、`adaptive_agent/sufficiency.py` 与 `adaptive_agent/candidates.py`：对照失败 State 可确认 Policy 是按已有 state 合理运作，而不是通过 task_type 强制 ASK 或检索。
5. `tests/test_adaptive_loop.py` 的 `test_llm_understander_uses_function_calling_for_configured_endpoint_compatibility`：防止 LangChain SDK 升级或默认值变化后重新触发所有真实模型请求的 HTTP 400。

### 重要执行流程

```text
虚构用户输入 → 真实 structured Input Understanding
→ goal / task type / extracted facts → Requirements / Sufficiency
→ Candidate / Policy → ASK 或真实 RAG / 虚构日记工具
→ State Update → 真实 Answer Generator → JSONL trace
```

本轮的真实差异发生在第一步：模型没有将“60分钟/90分钟才能入睡”放入 `sleep_onset_latency`。之后 `decision_missing` 合理地包含该字段，Policy 合理选择 ASK，但从用户视角看它是重复问题。因此修复目标应是提取可靠性，而不是调整“重复 ASK” Policy。

### 关键设计决策

- 不以失败为理由修改已验收的 Policy；失败被保留为可复现 Input Understanding failure cases。
- `function_calling` 是对已配置模型服务不支持 `json_schema` 的最小协议兼容修复；未改变 State、Requirements、Candidate 或回答边界。
- 报告区分“真实 RAG / Answer 已工作”和“真实抽取仍不可靠”，不将 2/5 的成功扩大成系统整体通过。
- 日记及全部用户文本均为虚构；不包含用户真实健康信息。

### 阅读后应能回答的问题

- 为什么 Case 3 在 Mock 中会 RETRIEVE → ANSWER，而真实模型中变成重复 ASK？
- HTTP 400 的 `response_format` 问题和随后三个 fact-extraction 失败分别属于系统的哪一层？
- 为什么“Policy 选择了 ASK”不等于“Policy 本身有错”？
- Case 5 如何证明真实模型接入后 Resource Dependency 仍然成立？
- 下一步若要提高提取可靠性，为什么应优先测试 Input Understanding 而不是修改 Policy？

### 已知限制或技术债务

真实模型对中文时长、频率、时间范围和咖啡因事实的 function-calling 抽取不稳定；没有 deterministic validation 来识别“文本有数值但 schema 为空”的遗漏。真实 RAG 虽能返回相关内容，但尚未做系统性相关性/忠实性评估。当前真实 Smoke 为 2/5 通过，因此不应据此宣告真实模型路径已完成验收，也不进入 Step 5。完整报告见 `evaluation/step4_5_real_model_smoke_report.md`。

### 我的理解


### 仍然不理解的问题


## 第 4.6 步：输入理解强化

### 已实现内容

未修改 Decision Policy。输入理解现在将 LLM 的 goal/task/raw structured facts 与程序的确定性事实标准化分开：只有用户原文明确支持的事实才进入 validated facts 和 AgentState；LLM raw facts 被保留用于轨迹审计，但不再能凭自身填充 State。新增 `fact_sources`，显式事实保留原文片段；由 bedtime 与 sleep_time 得出的 latency 标记为 `derived` 并记录两个 source fields。

修复了 Step 4.5 的三个明确遗漏：60/90 分钟入睡、最近两周、下午两杯咖啡，以及 LLM 将“提前上床”翻为英文导致方向性 requirements 失效的问题。最终真实冒烟为 4/5：前三类与原因评估的事实和行动路径均通过；日记分析的输入理解和资源读取也通过，但回答生成器在没有 evidence 时引入 85% 阈值，因此保留为 Answer Generation failure，未越界修改。

### 重点阅读代码

1. `adaptive_agent/input_understanding.py` 的 `RawFactsOutput`、`normalize_facts`、`extract_explicit_facts`：看 LLM raw、确定性 explicit、derived、validated 四层如何分离，为什么 raw 输出不会直接污染 State。
2. `adaptive_agent/input_understanding.py` 的跨午夜时间计算与 `fact_sources`：看 23:00 上床、00:00 入睡如何得到 60 分钟，及其来源为什么可追溯而不是模型推测。
3. `adaptive_agent/input_understanding.py` 的 `normalize_goal`：看为何这是输入层兼容处理——保存用户已明确表达的方向性中文 goal——而不是更改 Policy。
4. `tests/test_input_understanding_hardening.py`：17 个测试方法、20 余正反变体；尤其读“问题不能变成摄入事实”和“LLM raw 无文本依据不能进 State”两类负例。
5. `evaluation/runs/step4_5-input-hardening-final/http-traces.jsonl`：对比原 Step 4.5 三个失败案例，确认 validated facts、source、decision_missing 与 action path 如何恢复；也可看到日记回答仍输出无 evidence 的 85% 阈值。

### 重要执行流程

```text
LLM extraction → raw structured facts（审计）
→ explicit text normalization → derived facts（带 source fields）
→ validated facts（unknown=null） → merge 到 AgentState
→ 既有 Requirements / Sufficiency / Policy
```

决定 ASK 的 Policy 没有变。此前多余 ASK 的真正因果链是“明确事实遗漏 → decision_missing 虚增 → ASK”；现在明确时长等 facts 进入 State 后，Case 2 改问 wake_time，Case 3 改为 RETRIEVE → ANSWER。

### 关键设计决策

- 采用保守规则：宁可保持 null，也不把 LLM 未被原文支持的 raw fact 当作用户事实。
- 派生只允许确定性的时钟差值，不将临床判断、阈值或业务规则塞进 normalization。
- 本阶段不修日记回答的 85% 阈值问题，因为它属于 Answer Generation evidence boundary，不是输入提取或 Policy。
- 完整回归 59/59 通过；真实 Smoke 4/5，故不进入 Step 5。

### 阅读后应能回答的问题

- raw LLM facts 与 validated facts 为什么需要同时存在？
- 为什么 `sleep_onset_latency=60` 有时是 explicit，有时是 derived？如何追溯？
- 为什么英文 goal 会让已有中文 requirements 规则失效，且这应由输入层而不是 Policy 修复？
- 为什么 Case 5 的 85% 阈值不是 Input Understanding failure？
- 负例怎样证明系统没有把“咖啡会影响睡眠吗”误作用户正在喝咖啡？

### 已知限制或技术债务

确定性规则覆盖当前 V1 中文表达，仍不能穷尽所有口语、模糊表达或中文数字写法；未匹配时会保守保持 null。真实模型的 goal/task 分类仍有可能波动，当前只对明确“提前上床”做了稳定化。Answer Generation 在无 evidence 的 DATA_ANALYSIS 回答中仍会添加未支持的参考阈值，这是下一步应单独处理的 failure case。完整报告见 `evaluation/step4_6_input_understanding_hardening_report.md`。

### 我的理解


### 仍然不理解的问题


## 第 4.7 步：回答生成证据约束强化

### 已实现内容

只修改 `adaptive_agent/answer_generation.py`，没有修改 Decision Policy、Sufficiency、Candidates 或 Input Understanding。回答输入现在明确只包含 goal、relevant facts、relevant evidence、answer_scope 和由 facts 确定性计算出的 descriptive claims。日记 facts 的卧床时间、总睡眠、睡眠效率和记录天数由代码计算；外部阈值、规则、建议时长和临床数字则必须存在于当前 goal 相关的 evidence。

加入通用 Quantitative Claim Audit：它不是禁止某一个“85%”，而是审计包含百分比、时长、天/周、次数的句子。模型若输出 State facts、派生计算和 evidence 都没有支持的数值规则，输出会删除该句并说明当前 State 不支持该量化规则。DATA_ANALYSIS 即使模型句子被删除，也会附加代码计算出的描述性统计，避免 evidence 为空时无话可说。

原日记 failure 已通过：最终真实回答包含 480 分钟卧床、360 分钟总睡眠、75% 计算睡眠效率、7 天记录；不再输出无 evidence 的 85% 阈值。专项测试 8/8、完整回归 67/67、五个真实 Smoke Cases 5/5 PASS。未进入 Step 5。

### 重点阅读代码

1. `adaptive_agent/answer_generation.py` 的 `data_derived_claims`：看哪些描述可完全由 diary facts 计算，尤其是 480 分钟和 75% 为什么属于数据结论而不是医学阈值。
2. `adaptive_agent/answer_generation.py` 的 `relevant_evidence`：看无关 evidence 如何在进入模型前被排除，避免模型拿咖啡因资料回答刺激控制问题。
3. `adaptive_agent/answer_generation.py` 的 `allowed_quantities` 与 `remove_unsupported_quantitative_claims`：这是泛化的数字/规则审计，不依赖特定阈值常量。
4. `tests/test_answer_generation_grounding.py`：八项回答层回归，重点比较“证据支持的 85% 可出现”与“空 evidence 的 85% 必须被删除”。
5. `evaluation/runs/step4_5-answer-grounding-final-rerun/http-traces.jsonl`：重点看 DATA_ANALYSIS 的最终 answer，确认 descriptive calculations 保留且无外部阈值；再与 Step 4.6 的 trace 对比。

### 重要执行流程

```text
facts → deterministic descriptive claims
evidence → goal relevance filter → evidence-grounded rules
模型受限回答 → quantitative audit
→ 保留数据计算 / 有证据规则，删除不受支持量化结论
```

这条流程不改变 Agent Loop 何时 ANSWER，只限制 ANSWER 的内容来源。Policy 仍只负责行动选择；Answer Generator 负责不把模型参数知识当作 State evidence。

### 关键设计决策

- “75%”只有作为已知 360/480 数据计算时允许，不自动携带“偏低/异常”的临床意义。
- “85%”或其他数字在 current relevant evidence 明确支持时允许出现；没有 evidence 则不允许。
- DATA_ANALYSIS 的计算结果优先由代码给出，避免不同模型算出不同数值。
- 输出审计只删除不受支持的量化规则句，保留不依赖数字阈值的共情、限制说明和事实描述。

### 阅读后应能回答的问题

- 为什么 75% 可以出现，而 85% 在无 evidence 时不能？
- 什么证据链使得一个数字从 Unsupported Claim 变为 Evidence-grounded Claim？
- 为什么要先由代码计算 diary statistics，再让模型组织语言？
- 无关 evidence 为什么不能仅仅依赖 prompt 让模型“不要用”？
- 这个审计为什么属于回答层，而不是 Policy 或 Sufficiency 层？

### 已知限制或技术债务

量化审计目前基于可解释的文本模式，尚不能完全理解所有中文数字、隐含单位或复杂数学等价表达；遇到未知表达会保守删除量化句。Evidence relevance 采用 V1 的目标词项过滤，复杂同义词或跨语言 evidence 仍可能需要更强的 metadata 支持。五例真实 Smoke 全部通过，但尚非更大规模 benchmark。完整报告见 `evaluation/step4_7_answer_generation_grounding_report.md`。

### 我的理解


### 仍然不理解的问题


### 第 4.7 步最终复验补充

最终全套回归为 69/69，回答生成专项为 10/10；最后一次真实虚构数据 Smoke 位于 `evaluation/runs/step4_5-answer-grounding-ultimate/http-traces.jsonl`，五例均通过。最后补充了两项回答层边界：方向性 `answer_scope` 即使 evidence 含具体规则也不允许输出具体上床/睡眠限制处方；英文 goal（如 `Explain stimulus control`）仍可匹配英文 evidence，避免安全过滤误丢真实相关 RAG 内容。

最终日记回答保留代码计算的 480 分钟、360 分钟、75%、7 天，未出现无 evidence 的医学阈值。该结果支持重新正式验收 Step 4.5；但五例仍是受控虚构冒烟，不等同于大规模 Benchmark。


## 第 5 步：Benchmark V1 设计

### 已实现内容

新增 `evaluation/benchmark_v1_cases.yaml`，只定义 10 个手工、可审计的 Benchmark Case，没有运行大规模实验，也没有改变 Decision Policy、Input Understanding 或 Answer Generation。数量严格为：KNOWLEDGE_QA 2 例、CAUSE_ASSESSMENT 2 例、PERSONALIZED_DECISION 4 例、DATA_ANALYSIS 2 例。

每个 Case 除用户 query、task type、goal、critical/secondary information、required resources 外，也明确首选 Action Path、可接受替代路径、不可接受行动、冗余行动、Goal Drift、Fabrication 和最终 answer scope。`hidden_profile` 是评估器私有资料：用户后续补充事实只能在 ASK 后进入下一轮；七天日记只能由 `READ_DIARY` 从工具返回，不能直接给模型。这使 Benchmark 真正能检查 State 和工具边界，而不是只检查最终文本。

### 重点阅读代码

1. `evaluation/benchmark_v1_cases.yaml` 的 `execution_contract`：先看 hidden_profile 的可见性约束；它规定事实和日记何时能合法进入 State。
2. `evaluation/benchmark_v1_cases.yaml` 的 `PD-01` 与 `PD-02`：同一“是否提前上床”目标分别测试一次高价值 ASK 和信息已足够时不 ASK，最直接解释 `Missing Information ≠ Must Ask`。
3. `evaluation/benchmark_v1_cases.yaml` 的 `DA-01` 与 `DA-02`：成对阅读 available/unavailable，理解 Resource 状态如何决定 `READ_DIARY → State Update → Re-evaluate` 或诚实结束。
4. `evaluation/benchmark_v1_cases.yaml` 的 `PD-04`：看高风险精确方案请求如何把“安全的 answer_scope”与“有限、有价值的 ASK”分开。
5. `evaluation/step5_benchmark_v1_design.md` 的评分和覆盖映射：看为何 V1 以人工审计与关键失败标签为主，而不把文字风格或单一路径当成自动分数。

### 重要执行流程

```text
case user_query → Input Understanding / 初始 AgentState
→ expected 或 acceptable action path
→ ASK 后才注入 scripted follow-up / READ_DIARY 后才暴露 diary fixture
→ 保存 State trace、tool calls、evidence、final answer
→ 以 scope、冗余、漂移、伪造和关键失败项人工评分
```

### 关键设计决策

- 每例起始 evidence 为空；知识性规则必须先通过 goal-aligned RETRIEVE，避免把模型参数知识当 evidence。
- 允许替代路径，防止 Benchmark 因 tie-break 的合理差异而把安全且 goal-aligned 的行为误判失败。
- DA-01/DA-02 是资源正反对照；KQ-02 则反向证明“提到日记”不自动构成日记资源依赖。
- 关键失败（虚构 facts/diary、unavailable 当可用、无依据精确处方、明显漂移、伪造 evidence）独立于总分：出现即不能通过 case。

### 阅读后应能回答的问题

- 为什么 `hidden_profile` 不能直接提供给模型，而必须按 ASK/工具协议释放？
- PD-01 和 PD-02 怎样共同检验“缺失字段”与“必须追问”的区别？
- 为什么 DA-02 不能用泛化 CBT-I 知识代替缺失的七天数据分析？
- 为什么 Benchmark 要有 alternative acceptable path，而不能只做严格的字符串式 action-path 比较？
- 哪些错误应判为关键失败而不是从总分里小幅扣分？

### 已知限制或技术债务

这是 V1 的设计规格，尚未执行、没有获得分数分布，也尚未校准不同 failure tag 的频率或评分者一致性。十例刻意优先覆盖已验收架构的高风险边界，不能代表真实人群分布或医学效果。后续执行时仍需使用虚构资料，并把每轮 State trace 与 evidence metadata 保存到 evaluation 日志；在有结果前不应据此修改 Policy。

### 我的理解


### 仍然不理解的问题


## 第 5.1 步：Benchmark Pilot Run（基准测试试运行）

### 已实现内容

通过真实 `create_app()` 的 `/api/chat` 路由运行了 Benchmark V1 的全部 10 个虚构 Case，实际使用 `LLMInputUnderstander`、项目 RAG、`LLMAnswerGenerator` 和现有 Adaptive Agent Loop；没有运行 Fixed Workflow，也没有修改 Policy、Requirements、Input Understanding 或 Answer Generation。新增的 `scripts/run_benchmark_pilot.py` 只负责按 Benchmark protocol 调用现有接口、观察过程并保存 trace，不替换任何 Agent 组件。

每个 Case 的 raw input、State、action path、ASK target/count、工具调用、steps/turns、retrieved evidence、answer scope、final answer、latency、token usage 和逐轮 observation 都保存于 `evaluation/runs/step5_1-pilot-2026-09-19/pilot-traces.jsonl`。人工五维分数、failure reasons、reviewer notes 与 critical failure 则逐行保存于同目录 `pilot-review.jsonl`。平均总分 83.8/100；有 1 个关键失败（PD-03），不是由总分掩盖。

### 重点阅读代码

1. `scripts/run_benchmark_pilot.py` 的 `follow_up_message`：看脚本如何只在 Agent 实际 ASK 后把对应的虚构 follow-up 转成下一轮 user message，而不是把 hidden facts 直接写入 State。
2. `scripts/run_benchmark_pilot.py` 的 `diary_facts` 与 case loop：看 DA-01 的七天 fixture 如何只经 `SessionDiaryTool` 的 `READ_DIARY` 暴露，DA-02 则返回 unavailable。
3. `evaluation/runs/step5_1-pilot-2026-09-19/pilot-traces.jsonl`：最重要的真实运行证据；优先比较 CA-02、PD-01、PD-02 的 explicit facts 漏失怎样导致冗余 ASK。
4. `evaluation/runs/step5_1-pilot-2026-09-19/pilot-review.jsonl`：看每例五个维度为什么分别扣分，以及 `critical_failure=true` 不依赖 total score。
5. `evaluation/step5_1_benchmark_pilot_report.md` 的 Meta-Evaluation：看 Benchmark 的 fixture visibility、alternative path 和“根因/维度重复计分”问题为何需要先修规格再扩展样本。

### 重要执行流程

```text
YAML case 的 user_query → 真实 /api/chat
→ Input Understanding / Agent Loop
→ 若实际 ASK，才发送该 target 的 scripted follow-up
→ 若 DATA_ANALYSIS，才通过 READ_DIARY 返回 diary fixture
→ EvaluationRecorder + pilot trace
→ 人工五维评分 + critical failure / failure source 记录
```

### 关键设计决策

- 隐藏资料仍是 evaluator-only；`session_facts` 没有被偷偷注入生产 State。
- 每例用独立 session id，避免前一 Case 的 facts/evidence/action history 泄漏到后一例。
- 评分同时保留总分、五维分数和 failure source；这避免“83.8 平均分”掩盖 PD-03 的 State-grounding 关键失败。
- PD-03 的原话出现过夜醒，但 State 没有独立的 `nighttime_awakenings`；回答仍把它当作已知用户事实，因此按回答只能依赖 current State 的约束判为关键失败。

### 阅读后应能回答的问题

- 为什么 scripted follow-up 必须在 ASK 之后才发送？
- CA-02、PD-01 和 PD-02 的错误怎样证明“事实遗漏”和“Policy 选错行动”是不同层次？
- 为什么 PD-03 即使原 query 提到夜醒，仍会在 State-grounding 规则下成为关键失败？
- DA-01 和 DA-02 如何共同证明 Resource Dependency 与 unavailable 停止条件？
- 为什么同一次 Input failure 会同时影响 Facts、Action 和 Efficiency，却不应该被解释为三个独立根因？

### 已知限制或技术债务

十例的 schema 可执行且能区分资源行为、证据行为和多余 ASK，但还不适合直接扩大到 Step 6。需要先在 Benchmark 规格层明确 `hidden_profile.session_facts` 的 runtime 含义、DA-01 entries 到 SessionDiaryTool facts 的适配合同、PD-04 的可接受 ASK 路径，并为评分增加独立的 failure-source attribution。建议进行只修改 benchmark YAML/评估说明的 V1.1 refinement 后，再以相同十例复跑；本阶段不应借此修改 Agent。

### 我的理解


### 仍然不理解的问题


## 第 5.2 步：Benchmark V1.1 Refinement（基准测试规格修订）

### 已实现内容

冻结了 `benchmark_version: 1.1` 的 evaluation-specification overlay：`evaluation/benchmark_v1_1.yaml` 引用保持不变的 V1 十例，而不覆盖 V1 文件或 Step 5.1 trace。V1 历史基线 **Average Score = 83.8、Critical Failures = 1** 明确保留为历史结果，未执行 V1.1 Agent rerun，未重新打分。

本次只增加 benchmark/schema/scoring/tooling：明确 user query、initial session、follow-up、diary、evidence 五个信息通道；定义 DA-01/DA-02 的 available/unread/loaded/unavailable 资源状态与 canonical tool-return contract；将 PD-04 从唯一 ASK 顺序改为 Information Value 标准；增加 failure primary/downstream attribution 与可追溯的 critical failure record。没有改动任何 Adaptive Agent 模块。

### 重点阅读代码

1. `evaluation/benchmark_v1_1.yaml` 的 `information_channels`：重点看 V1 legacy `hidden_profile.session_facts` 为什么只是 query-fact oracle，绝不能因 evaluator 已知而直接注入 State。
2. `evaluation/benchmark_v1_1.yaml` 的 `diary_fixture_contract`：看 DA-01 的七条 entries 如何只经 READ_DIARY 变为 `recent_sleep_pattern`，DA-02 为什么必须返回空 facts 和 unavailable。
3. `evaluation/benchmark_v1_1.yaml` 的 `case_overrides.PD-04-specific-plan-boundary`：看总睡眠、夜醒、近期模式、日记可用性为何可有多个合理 ASK 次序；判断标准是信息价值而非 YAML 位置。
4. `evaluation/benchmark_v1_1_scoring.md`：看 primary cause、downstream effects 和 independent failure 怎样防止同一 fact-extraction 漏失被误读为多个独立 Policy failure。
5. `scripts/validate_benchmark_v1_1.py`：这是纯 schema 验证入口；读它确认 V1.1 冻结仍解析为十例、2/2/4/2 配额和完整 critical-type 枚举，且不会运行 Agent。

### 重要执行流程

```text
V1 base cases（保留） + V1.1 overlay
→ 明确每类事实的可见性/合法进入 State 的通道
→ 定义 case-specific acceptable actions 与 critical-failure schema
→ schema-only validator
→ 未来同十例 rerun 才能产生新的 V1.1 experiment result
```

### 关键设计决策

- V1.1 是 overlay，不改写 V1 历史定义和 Pilot 分数，避免 benchmark 规格变化伪装成模型进步。
- 每条 failure 只有一个 earliest primary cause；Action/Efficiency 可记录 downstream impact，但需要独立证据才算新的组件失败。
- Critical Failure 永远独立于 100 分；记录 `critical_failure_type` 和 `supporting_trace`，但不强行把 case 归零。
- DA fixture 的 canonical projection 不制造摘要/临床数值，因此测试框架不会绕过 Resource Dependency 或伪造 Agent facts。

### 阅读后应能回答的问题

- 为什么 `expected_user_query_facts` 和 `initial_session_facts` 必须是两个不同通道？
- DA-01 的 available 与 loaded 分别由谁知道、何时进入 Agent State？
- PD-04 怎样判定一个 alternative ASK 合理，而不是仅仅“字段不同”？
- 一个 Input Understanding failure 何时会导致 downstream action 扣分，何时又该视作独立 Action Selection failure？
- Critical Failure 为什么不能简单等同于 0 分？

### 已知限制或技术债务

V1.1 只验证 schema，尚未用新归因合同复跑十例；因此没有 V1.1 分数、均值或新 failure rate。V1.1 也尚未覆盖目标变更、RAG unavailable、矛盾事实、用户拒答或 Safety Routing 等 future failure modes。下一步应先验收规格后，决定是否做同十例的评分稳定性 rerun；不要直接进入大规模 Step 6。

### 我的理解


### 仍然不理解的问题


## 第 5.3 步：Fixed vs Adaptive Controlled Comparison（固定流程与自适应流程受控对照）

### 已实现内容

用冻结的 Benchmark V1.1 同一组十例完成 Existing Fixed Workflow 与 Adaptive Agent V1 的受控对照。两边使用相同模型工厂、RAG、原始输入、仅在实际 ASK 后释放的 follow-up facts 与同一 diary fixture；没有修改 benchmark、Fixed、Adaptive、RAG 或 Answer Generation。

最终有效目录为 `evaluation/runs/step5_3-controlled-final-2026-09-19/`。Fixed 的 V1.1 平均为 20.2，Adaptive 为 88.3；各有 1 个 Critical Failure，类型不同。Step 5.1 的 83.8/1 仅是 V1 历史结果，未被当成此次比较成绩。

### 重点阅读代码

1. `scripts/run_step5_3_comparison.py`：看 V1 base + V1.1 overlay 怎样生成孤立 case、只在真实 ASK 后释放 follow-up，以及为何要用两个已存在的系统入口适配。
2. `evaluation/runs/step5_3-controlled-final-2026-09-19/adaptive-traces.jsonl`：看 facts/state、行动、工具结果和最终回答；重点比较 DA-01 的 `READ_DIARY → ANSWER` 与 DA-02 unavailable 的有限回答。
3. `evaluation/runs/step5_3-controlled-final-2026-09-19/fixed-traces.jsonl`：看 Fixed 在知识、日记场景的重复 ASK；其 `task_type`/structured state 为 null 是 legacy 架构事实，不是测试遗漏。
4. `evaluation/runs/step5_3-controlled-final-2026-09-19/paired-results.jsonl`：看同一 V1.1 rubric 的五维分数、primary/downstream attribution，以及 PD-01/PD-03 两类 critical failure。
5. `evaluation/step5_3_fixed_vs_adaptive_controlled_comparison_report.md`：先读四个 Experimental Confounds 和效率原始数值，再读 trade-off 结论。

### 关键设计决策

- 不向 Fixed 注入 hidden facts 或 diary 内容；否则比较对象会变成被 benchmark 改造的第三个系统。
- raw trace 与人工评分分开保存，前者是可复查事实，后者是带归因的评价结论。
- 两边 token telemetry 的统计口径不同，只报告原始观测值，不作严格 token 成本结论。
- 不为分数修复失败：Fixed PD-01 的无依据个性化建议和 Adaptive PD-03 超出 current State 的夜醒陈述均原样保留。

### 已知限制或技术债务

endpoint、State 架构和 token telemetry 仍是混杂因素，因此本实验适合评价任务行为和安全失败，不是严格性能基准。Fixed 缺少 `/api/chat` 与 `READ_DIARY` 是真实架构差异，不能由 evaluator 临时填平。后续如需继续，应先单独决定 Failure Analysis 或 Step 6，而非直接改 Agent。

### 我的理解


### 仍然不理解的问题


## 第 5.4 步：Comparison Validity & Failure Analysis（对照有效性与失败分析）

### 已实现内容

只读取并重新聚合 Step 5.3 的最终十例 trace；没有运行 Agent、没有修改 Fixed、Adaptive、Benchmark V1.1 或评分规范。保存结果显示总分差的精确算术是 **88.3 - 20.2 = +68.1**。排除两个 Fixed 缺少 `READ_DIARY` 的数据分析例后，八个 capability-matched cases 仍是 Fixed 24.5、Adaptive 85.4、差距 +60.9。

此次分析将 DA-01/DA-02 明确标作 `capability_gap`，而不是把 +97 分差误说成 Policy 优越。它也将 ASK 从数量分成必要、可选但有价值、重复和无关：Fixed 54 次 ASK 中 30 次无关；Adaptive 10 次 ASK 中 4 次重复，但无无关 ASK。后者四次重复来自 explicit fact 没有进入 State，不能包装为 Policy 成功。

### 重点阅读代码

1. `evaluation/step5_4_comparison_validity_failure_analysis_report.md`：本阶段完整结论。先看“Validity boundary”，再看逐例 primary driver，避免把分数差直接归因给 Policy。
2. `evaluation/runs/step5_3-controlled-final-2026-09-19/paired-results.jsonl`：这是固定 rubric 下每个 case score、critical failure 与归因的事实基础。
3. `evaluation/runs/step5_3-controlled-final-2026-09-19/fixed-traces.jsonl` 的 PD-01：看一个狭窄“是否提前上床”问题怎样经过多轮通用 intake、RAG 和最终回答，产生无依据个性化指令。
4. `evaluation/runs/step5_3-controlled-final-2026-09-19/adaptive-traces.jsonl` 的 PD-03：沿 `raw_input → facts → action_history → final answer` 看 `nighttime_awakenings` 为什么没进 State，回答却仍使用该事实。
5. `evaluation/runs/step5_3-controlled-final-2026-09-19/experimental-confounds.json`：看 endpoint、State、日记工具与 token telemetry 的四个限制，理解为何 token/latency 只能如实报告、不能当严谨成本结论。

### 重要执行流程

```text
Step 5.3 raw traces + frozen paired scores
→ case-level driver / capability-gap review
→ exclude DA cases for capability-matched aggregation
→ ask quality review against visible facts and frozen goal
→ critical-failure propagation analysis
→ observed / supported / not-yet-supported conclusions
```

### 关键设计决策

- “both systems have required capabilities”的子集只排除 DA-01/DA-02；它仍保留 endpoint 和 State 架构混杂，因此不能当作纯因果实验。
- `useful_ask_rate` 定义为 `(necessary + useful_but_optional) / all asks`，因此既能看总量，也不会把每个 ASK 都默认判为无价值。
- PD-03 分成两个层级：Input Understanding/State 没解析夜醒是上游错误；Answer Generation 使用不在 State 的事实是独立 critical failure。
- 推荐下一步是 C：先设计预注册、能力和测量口径匹配的 comparison；不在本阶段私自修复系统或扩展 benchmark。

### 阅读后应能回答的问题

- 为什么去掉两个 Diary case 后，仍不能把 +60.9 分严格解释为“Decision Policy 的因果效果”？
- 为什么 Adaptive ASK 总数更低，却仍有 40% 的 redundant ASK rate？
- Fixed PD-01 的风险来自 retrieval 本身、workflow、还是最终 answer boundary？
- PD-03 的 source input 明明提到夜醒，为什么在 State-only answer contract 下仍是 critical failure？
- 哪些原始 cost 指标能报告，哪些因为 telemetry/endpoint 不同不能比较？

### 已知限制或技术债务

本次是十例、单次、人工分类的 trace analysis；ASK 分类没有双评分者一致性，也没有端到端统一 token/latency instrumentation。Fixed 的无结构 State 和无日记工具是现实能力差异，但也限制了架构中立的因果结论。当前最重要的未修复 failure fixtures 仍是 Fixed PD-01 与 Adaptive PD-03；是否修复 Adaptive 必须由后续单独授权。

### 我的理解


### 仍然不理解的问题


## 第 5.5 步：Capability-Matched Controlled Comparison（能力匹配受控对照）

### 已实现内容

新增 observation-only 的统一实验适配器与 runner，重新执行冻结 V1.1 十例。适配器统一输出 response、action path、ASK targets、tool calls、可观察 state、evidence、steps、turns、tokens 与 latency；它不改写任何 Fixed/Adaptive 决策。Fixed 没有的 structured State 字段明确写为 `not_available`，不伪造 AdaptiveState。

主比较只包含八个不依赖日记工具的 capability-matched cases：Fixed **20.9**，Adaptive **86.3**，差距 **+65.4**。两边的 observed RAG/tool call 都是 0.50/case；Adaptive 的 turns/steps 明显更少（2.25/2.75 对 5.75/6.25）。DA-01/DA-02 单独放在 Full-System resource-capability analysis：Fixed 缺少 `READ_DIARY`，所以它们是 `capability_gap`，不用于主机制分数。

本次保留了 Adaptive 的四个 redundant ASK：它们都来自 explicit fact 未进入 State。由于模型输出具有随机性，本轮 PD-03 没有再次把缺失夜醒写入回答，因此没有产生新的 Adaptive critical failure；这不是修复。反而 Fixed 在 PD-02、PD-04 出现了两条新的 answer-grounding critical failure，说明单次十例不足以证明稳定安全性。

### 重点阅读代码

1. `scripts/run_step5_5_capability_matched.py`：看 `FixedExperimentAdapter`、`AdaptiveExperimentAdapter` 如何只适配外部接口，且为什么 `cost_record` 将不完整指标写成 `not_available`，而不估算为“精确成本”。
2. `evaluation/runs/step5_5-controlled-valid-2026-09-19/adaptive_matched_traces.jsonl`：优先读 CA-02、PD-01、PD-02 的 action/state，确认四个重复 ASK 没有在实验前被修掉；再读 PD-03 的 compound caffeine fact 与本轮安全输出。
3. `evaluation/runs/step5_5-controlled-valid-2026-09-19/fixed_matched_traces.jsonl`：重点看 KQ 的 generic intake、PD-02 的无依据个性化建议以及 PD-04 的虚构实际睡眠/百分比规则。
4. `evaluation/runs/step5_5-controlled-valid-2026-09-19/cost_metrics.json`：看每个字段的 telemetry scope；total token/latency 虽被记录，但不能被误读为 end-to-end 可比较成本。
5. `evaluation/step5_5_capability_matched_report.md`：先读 Layer 1 与 Layer 2 的分离，再读“what can and cannot be attributed”，理解为什么主结论是机制关联而不是 Policy 的单独因果效应。

### 重要执行流程

```text
Frozen V1.1 + synthetic case
→ unified adapter input/output boundary
→ Fixed legacy observable state / Adaptive full State snapshot
→ matched subset (8) + resource capability subset (2)
→ identical frozen rubric + primary/downstream failure attribution
→ quality, interaction, cost-telemetry and validity report
```

### 关键设计决策

- `READ_DIARY` 不是可以临时注入 Fixed prompt 的“测试资料”；缺少该 capability 必须如实成为 Full-System 差异。
- 两边同样的 RAG/tool call rate 不代表所有条件完全一致，但削弱了“更多检索导致 Adaptive 更高分”的解释。
- `LLM_calls` 与 component latency 在现有接口没有可靠观测，明确标 `not_available`；不能用 turn 数或 token 反推后伪装为真实调用数。
- 固定评分结果记录本次 run 的输出，不回填 Step 5.3 的 PD-03 critical failure，也不把随机未复现当作系统修复。

### 阅读后应能回答的问题

- 为什么八例 matched subset 仍不能将 +65.4 全部因果归给 Decision Policy？
- 为什么 Adaptive 的 redundant ASK rate 高于 Fixed，却仍有更高 valuable ASK rate？
- 为什么 DA 结果要保留在 Full-System report，却不能进入主机制分数？
- token/latency 哪些是测量值、哪些因 scope 不同不能比较？
- PD-04 为什么同时构成 fabricated fact、unsupported quantitative claim 和 individualized instruction？

### 已知限制或技术债务

本轮仍有 endpoint、prompt 和 state-architecture 混杂；成本 telemetry 只覆盖部分模型调用。十例、单次、随机模型输出不足以证明可靠性或普遍优势。推荐先设计预注册的 repeated-run、统一 telemetry 的 capability-matched comparison，再决定是否扩大 Benchmark；不得基于本次结果直接修改任一系统。

### 我的理解


### 仍然不理解的问题


## 第 5.6 步：Adaptive V1 Baseline Freeze & Failure Set（V1 基线冻结与失败集）

### 已实现内容

正式将当前系统定义为 `adaptive-agent-v1-baseline`。基线不是新 Git tag 或 release：当前 Git 仓库没有 `HEAD` commit，无法记录 commit hash，也没有擅自创建 tag。取而代之的是核心 Agent、冻结 benchmark/scoring 和实验 runner 的 SHA-256 manifest；未来比较必须匹配该 manifest 或将差异列为 confound。

V1 的主指标来自 Step 5.5 的八例 capability-matched subset：**86.3/100、ASK 1.25、RAG 0.50、Tool calls 0.50、Turns 2.25、Steps 2.75、Critical Failures 0**。DA-01/DA-02 单独保存为 Full-System resource capability 结果，绝不混入主机制 baseline。

还建立了 append-only Failure Set：CA-02、PD-01、PD-02 的 explicit fact omission / repeated ASK 是 deterministic failure；PD-03 的 compound fact/provenance omission 也是 deterministic；它在 Step 5.1/5.3 触发的最终 Answer Grounding critical failure 被标为 stochastic，即使 Step 5.5 未复现也永久保留。Improvement Backlog 只描述通用机制方向，不授权实现。

### 重点阅读代码

1. `evaluation/baselines/adaptive_v1_baseline.md`：从 architecture snapshot、Baseline 指标、Full-System diary 分离到 SHA-256 manifest，理解“冻结”是可复查比较点，而非新行为版本。
2. `evaluation/failures/adaptive_v1_failure_set.yaml`：重点看 `expected_state`、`actual_state`、primary/downstream 和 reproducibility，理解 deterministic 与 stochastic failure 为什么都不能因后续运行变化而删除。
3. `evaluation/improvement_backlog.md`：看 P0 的 fact normalization、field provenance 和 claim provenance 为什么是可泛化机制，而不是 PD-03 特判；也看为什么 Sufficiency/Candidate/Policy 目前只允许观测、不应抢先改动。
4. `evaluation/version_comparison_contract.md`：这是以后 V1.x/V2 的强制协议；尤其注意两层（matched/full-system）报告、`not_available` 测量规则和 confound disclosure。
5. `evaluation/runs/step5_5-controlled-valid-2026-09-19/matched_paired_results.jsonl`：基线的可审计评分来源；它应始终被保留，不能被任何新实验覆盖。

### 重要执行流程

```text
Step 5.1–5.5 immutable traces
→ Baseline architecture + hash manifest
→ deterministic / stochastic failure classification
→ improvement backlog (planning only)
→ version comparison contract
→ future V1.x/V2 must use paired, two-layer comparison
```

### 关键设计决策

- 无 HEAD commit 时记录 `not_available`，而非编造 Git revision；SHA-256 仅补充本地复查，不等同于 Git release。
- Baseline 使用 Step 5.5 的八例 matched 指标；日记能力差异是 Full-System 事实，不是 Policy metric。
- 一次未复现 stochastic failure 是输出波动，不能反向改写历史 failure evidence。
- 缺失的 token、exact LLM calls 和 component latency 必须保持 `not_available`，后续只能通过 instrumentation 真实测量。

### 阅读后应能回答的问题

- 为什么 SHA-256 manifest 不能代替 Git commit，却仍能帮助本地 baseline 复查？
- 为什么 PD-03 在 Step 5.5 没出错仍必须留在 Failure Set？
- 为什么 current repeated ASK 不能直接被说成 Policy defect？
- 后续某版本增加 READ_DIARY 或改 RAG 时，为什么必须分 matched/full-system 并记录 confound？
- 什么情况下 token/latency 可以写为 measured，什么情况下必须写 `not_available`？

### 已知限制或技术债务

当前 baseline 仍没有 Git commit、完整 cost telemetry、重复运行的方差估计或双评分者 failure 分类。十例不能代表真实人群或临床性能。建议下一阶段优先处理 P0 的通用 fact normalization / provenance / answer-claim grounding 设计，但必须先获得明确的 Agent 修改授权，并按 Version Comparison Contract 与本基线对照。

### 我的理解


### 仍然不理解的问题


## 第 6 步：Benchmark V2 Expansion（V2 基准扩展）

### 已实现内容

建立独立、未运行的 `Benchmark V2 Evaluation Set`：40 个新案例，配额为 KQ 10、CA 10、PD 12、DA 8。它不覆盖或合并 V1.1；后续报告必须把 V1.1 historical/development performance 与 V2 evaluation performance 分开。

V2 使用与 V1.1 一致的信息可见性边界：query facts 只是 evaluator oracle，follow-up 只能在真实 ASK 后释放，diary facts 只能经 READ_DIARY 进入 State，evidence 初始为空。案例有 Easy 10 / Medium 20 / Hard 10，语言覆盖简短中文、口语中文、信息分散中文、中英混合和英文。没有运行 Adaptive、Fixed、RAG 或任何模型。

### 重点阅读代码

1. `evaluation/benchmarks/benchmark_v2_cases.yaml`：先读 `channel_rules`，再挑 KQ、CA、PD、DA 各一例；它展示 evaluation oracle 和 Agent 可见 State 的边界，以及每例的 expected/acceptable/unacceptable actions。
2. `evaluation/benchmarks/benchmark_v2_design.md`：看为什么 information sufficiency 是可重叠覆盖标签，而不是虚假的概率；也看七类 action path 如何避免只奖励 `ASK → RETRIEVE → ANSWER`。
3. `evaluation/benchmarks/benchmark_v2_quality_audit.md`：重点读 Leakage、Ground-truth/path、Duplicate/overfitting 三项审计，理解为什么 V2 不应按现有 Agent failure 反向造题。
4. `evaluation/benchmark_v1_1.yaml`：与 V2 的 channel rules 对照阅读，确认 V1.1 仍保持不动、V2 只是独立扩展集。

### 重要执行流程

```text
真实 CBT-I 任务家族
→ 新的语言 / 信息充分性 / 资源 / 路径组合
→ evaluator-only fixture 与 Agent-visible channel 分离
→ static schema + distribution + leakage audit
→ V2 design_only_unrun freeze recommendation
```

### 关键设计决策

- V2 不把 CA-02、PD-01、PD-02、PD-03 的失败字段名当作出题目标；自然语言多事实只是现实任务覆盖。
- `Missing Information ≠ Must Ask` 通过 answer-ready、secondary-only、用户提供过多信息和有限回答案例共同检验，而不是规定唯一问法。
- DA-01–08 均要求先读资源；PD-11 明确“有日记但用户不授权读”不是自动 resource dependency，DA-06/PD-12 则检验 unavailable 限制回答。
- Case 的 alternative path 以当前 goal 的信息价值判断，不按 YAML 字段顺序判错。

### 阅读后应能回答的问题

- 为什么 `user_query_facts` 存在却不能直接注入 Agent State？
- 哪些 V2 Case 是 diary required、diary optional 或 unavailable，为什么它们不能混为同一种任务？
- 为什么 hard case 的难度来自资源、冲突、范围和多轮状态，而不是故意难懂的句子？
- 为什么 V2 运行结果不能和 V1.1 合成一个总分？
- 何种 action path 可以是合理替代，而不是被唯一 expected path 限死？

### 已知限制或技术债务

V2 是人工设计、synthetic、design-only 数据集，尚未运行或评分，也未做独立双评分者校准。`analysis_focus` 是 DA-07 的普通用户澄清语义，未来 runner 必须通过 user text 处理而不能直接写 State。建议接受后冻结为 `design_only_unrun`；任何改动都应创建新数据集版本和 changelog，不覆盖当前 V2。

### 我的理解


### 仍然不理解的问题


## 第 6.2 步：Research Summary Snapshot

新增 `docs/research_summary_v1.md`，以教授两分钟阅读量总结研究问题、
动机、State→Sufficiency→Candidate→Action 的设计、V1.1 与 V2 的评估边界、
V2 的 63.85/100 结果及 failure chain。摘要明确把 CBT-I 作为应用领域，
不将 V1.1 development score 与 V2 independent score 混合，也不宣称统计显著、
临床有效性或普遍优势。

重点阅读 `docs/research_summary_v1.md` 的 “Evaluation design” 与
“Failure analysis”：前者解释为什么 V1.1 和 V2 不可合并，后者解释为什么
repeated ASK 的上游归因是 extraction/state integrity，而 diary projection
问题不能误归因于 Decision Policy。

### 我的理解


### 仍然不理解的问题


## 第 9.8f 步：Frozen Run Guard Implementation（冻结运行 guard 实现）

本阶段只修改评估基础设施，不改变 Agent。新增 append-only execution-attempt ledger：
`evaluation/v1_2_2/step9_8_execution_attempts.jsonl`，将 immutable manifest（冻结输入身份）与 actual
execution attempt（执行历史）分开。它追加了历史对账：Step 9.8、Step 9.8b 和本地 manifest-guard 阻断均为
`FAILED_BEFORE_FIRST_CASE`、0 started/0 completed、无有效结果；不可恢复字段保持 `unknown`，未伪造
timestamp、model call 或 trace。

新的 guard 区分 `PREPARED`、`STARTED`、`FAILED_BEFORE_FIRST_CASE`、
`FAILED_AFTER_PARTIAL_EXECUTION` 与 `COMPLETED`。manifest 本身不再消费运行机会；仅 STARTED、partial 或
COMPLETED 才阻止自动重跑，未知 ledger 状态 fail closed。真实 runner 在首个真实 case 前 durable append
`STARTED`，每个 completed case 追加进度；`PREPARED → STARTED` 再次校验 Benchmark/rubric hash。历史的
zero-byte trace 不会被覆盖：每个新 attempt 使用唯一 trace path。

重点阅读：

1. `scripts/frozen_run_guard.py`：`preflight()` 的只读/失败关闭判断与 `mark_started()` 的二次 hash 校验。
2. `scripts/run_step9_8_frozen_evaluation.py`：`--preflight` 不导入 Flask/model；真实 run 必须提供新的
   `--authorization-id`，并用 runner callbacks 记录状态，不接触 Agent。
3. `scripts/run_step8_9_v1_2_1.py`：新增 optional callbacks/trace path，默认行为不变。
4. `tests/test_step9_8f_frozen_run_guard.py`：13 项 guard 测试。
5. `evaluation/v1_2_2/step9_8f_guard_implementation_report.md`：完整状态机、历史对账与 readiness 边界。

执行流程：

```text
immutable manifest + current frozen inputs
→ read-only preflight
→ new explicit authorization
→ append PREPARED
→ revalidate hashes
→ append STARTED before first real case
→ append per-case progress / final status
```

验证：guard focused **13 passed**；S1–S12 **12/12**；I1–I8 **8/8**、lineage PASS；非外部模型回归
**146 passed / 0 failed / 0 skipped**。`tests.test_model_configuration` 保持 **NOT_VERIFIED**。未运行
Benchmark V2、未访问 V3、未调用真实外部模型。当前 preflight 返回
`FROZEN_INPUTS=MATCH`、`RUN_STATE=PREPARED`、`PREVIOUS_VALID_RESULTS=NONE`、
`EXECUTION_ELIGIBLE=YES`、`AUTHORIZATION_REQUIRED=YES`。

已知限制：ledger 只解决执行状态可审计性，不能证明模型连通性或 Agent 质量。真实 run 仍需可联网本地环境和
新的人工授权；任何 STARTED/partial/COMPLETED 结果都会阻止自动重跑。

### 我的理解


### 仍然不理解的问题


## 第 9.8g 步：Frozen Run Recursion Failure Audit（冻结运行递归失败审计）

本阶段只读审计本地授权 attempt `step9_8_local_frozen_20260921_auth01`，没有修改代码、ledger、manifest、
Agent、Benchmark 或 scoring，也没有重跑 V2、调用模型或访问 V3。ledger 显示 attempt id 为
`attempt_9915d68189f343f8996fc412d4efec53`：先有 `PREPARED`，再有 `STARTED`（`first_case_id=V2-KQ-01`、
`cases_started=1`），最后是 `FAILED_AFTER_PARTIAL_EXECUTION`（`cases_completed=0`、
`failure_type=RecursionError`）。因此这次 run 已进入 **consumed execution history**；即使无有效结果，也不能
按协议写成 `FAILED_BEFORE_FIRST_CASE` 或自动重跑。

本次 unique raw trace 文件存在但为 **0 bytes / 0 records**，没有保存 case trace、state transition、model
response、score 或 partial benchmark result。ledger 的 `model_calls_started=unknown`；终端的 “Loading weights”
不是可审计的外部模型调用记录。因此只能写 `MODEL_CALL_STARTED=UNKNOWN`、
`MODEL_CALL_COMPLETED=NOT_VERIFIABLE`、`VALID_CASE_RESULTS=NO`，不能据 traceback 或终端输出补造结果。

根因是 evaluation harness 的函数绑定错误，而非 Agent：
`run_step9_8_frozen_evaluation.state_view()` 调用 `base.state_view()`，但 runner 在随后把
`base.state_view = state_view`，使 wrapper 经 `base` 调回自己；base runner 在创建首轮 trace 时触发无限递归。
Step 9.8f guard tests 是独立状态机测试，Step 9.7 则不安装这一 monkey patch，所以未覆盖这个组合路径。

重点阅读 `evaluation/v1_2_2/step9_8g_recursion_failure_audit.md`：它分开 ledger evidence、artifact evidence、
consumption protocol 和 root cause。也可对照 `scripts/run_step9_8_frozen_evaluation.py` 的 wrapper/assignment 与
`scripts/run_step8_9_v1_2_1.py` 的 trace call，理解为何 Agent 的 source hash 仍与冻结 manifest 一致。

冻结完整性仍为 MATCH：Benchmark V2 hash 和 scoring hash 均匹配 manifest，Agent/Benchmark/scoring 在授权后均为
NO modification。本阶段不提出、更不实施修复或下一次 run。

### 我的理解


### 仍然不理解的问题


## 第 9.9 步：Post-Frozen-Run Recovery Protocol Design（恢复性评估协议设计）

本阶段只设计协议，未修改代码、修复 recursion、运行 Benchmark 或调用模型。Step 9.8 永久保留为
`FROZEN_RUN_CONSUMED / FAILED_AFTER_PARTIAL_EXECUTION / EVALUATION_HARNESS_FAILURE`；它有 1 个已启动 case、
0 个完成 case、0 个有效结果。未来结果不得称为 Step 9.8 rerun，也不得覆盖 ledger、manifest、zero-byte trace
或失败审计。

协议定义新的独立实验身份：**Step 9.10 — Benchmark V2 Recovery Evaluation**。它必须有新的 evaluation、
authorization、attempt id 和独立 append-only ledger，同时显式指向 Step 9.8 failure。其运行前 gate 要求：
Benchmark/rubric hash 不变、Agent 行为 hash 不变或公开为 confound、只修 evaluation harness、无 case-specific
workaround、harness 回归/等价性通过、未访问 V3，并在全部核验后获得新人工授权。

重点阅读：

1. `evaluation/v1_2_2/step9_9_recovery_protocol_design.md`：新实验身份、资格 gate、科学解释边界与四段式后续步骤。
2. `evaluation/v1_2_2/recovery_state_machine.json`：区分不可变的 Step 9.8 终态与新 recovery evaluation 的独立状态机。
3. `evaluation/v1_2_2/recovery_eligibility_checklist.json`：未来不能漏过的 R1–R10 核验项。
4. `evaluation/v1_2_2/harness_fix_boundary.md`：Step 9.10a 允许/禁止边界与 9.10b 必需的等价性证据。

核心流程：

```text
Step 9.8 immutable failure
→ Step 9.10a harness-only fix
→ Step 9.10b equivalence/regression
→ Step 9.10c local preflight
→ Step 9.10d new authorized recovery evaluation
```

V2 仍是 development/regression benchmark；即使未来 recovery 完整完成，也不支持 held-out generalization、临床
有效性或最终性能结论。任何 Step 8.9 对比只能使用同一 40 cases、同一 rubric 和同一评分定义，并披露 Agent/
harness version 差异。本阶段没有计算任何新指标。

### 我的理解


### 仍然不理解的问题


## 第 9.10a 步：Evaluation Harness Minimal Fix（评估框架最小修复）

本阶段只修复 Harness 的确定性 recursion：在 monkey-patch 之前保存
`original_state_view = base.state_view`，wrapper 只调用该 captured callable，不再在 wrapper 内解析已被替换的
`base.state_view`。这不会改变 state serializer 原有字段/值；只保留既有的 Step 9.8 lineage/trace augmentation。
没有修改 Agent、Benchmark、scoring、工具、Answer Generation 或任何 case fixture。

重点阅读：

1. `scripts/run_step9_8_frozen_evaluation.py`：`original_state_view` 必须在 `base.state_view = state_view` 前捕获；
   这是防止函数绑定回到 wrapper 自身的关键。
2. `tests/test_step9_10a_harness_fix.py`：F1–F6 直接验证一次调用、语义等价、重复调用、callback audit、历史只读和
   prospective recovery ID 独立性；全程不运行 case。
3. `evaluation/v1_2_2/step9_10a_harness_equivalence.json`：机器可读地声明 Agent/Benchmark/scoring 未变与
   serializer 等价证据。
4. `evaluation/v1_2_2/step9_10a_callback_audit.json`：逐项列出 state_view、before/after_case、ledger、recorder、
   trace、tool projection 的 recursion 风险或不适用边界。
5. `evaluation/v1_2_2/step9_10a_harness_minimal_fix_report.md`：完整 scope、tests、frozen hash 与下一阶段边界。

执行流程：

```text
capture original serializer
→ wrapper augments copied view only
→ monkey-patch base serializer for trace collection
→ base trace call reaches captured original exactly once
```

验证：F1–F6 **6/6 PASS**；Step 9.8f guard **13 PASS**；S1–S12 **12/12**；I1–I8 **8/8** 且 lineage PASS；
非外部模型回归 **152 passed / 0 failed / 0 skipped**。`tests.test_model_configuration` 保持 **NOT_VERIFIED**。
原 Step 9.8 ledger/history 未改；未创建 recovery authorization、未运行 Benchmark V2、未调用真实模型、未访问 V3。

### 我的理解


### 仍然不理解的问题


## 第 9.10b 步：Recovery Equivalence Validation（恢复实验等价性验证）

本阶段完成只读资格审计与 dry tests，没有运行 V2、调用模型或访问 V3。冻结 Benchmark 和 rubric hash 均为 MATCH；
Step 9.8 manifest 所列 13 个 Agent/model 文件也全部与当前 SHA-256 一致。Harness 语义等价、production path、
recovery identity isolation、Step 9.8 history preservation 与 active-runner leakage audit 均为 PASS/YES；没有新增
case-specific logic。

但最终 `AGENT_BEHAVIOR_EQUIVALENT=NO`，因此 `READY_FOR_STEP9_10C=NO`。原因不是发现 Agent 改动，而是原 Step 9.8
manifest 没有覆盖所有实际 production-path 文件（例如 `flask_app`、`service`、`dependency_resolver`、`facts`、
`evaluation/recorder`），而仓库没有可用 Git baseline 可用于对遗漏文件做历史 diff。按协议，无法证明的范围必须归为
`F_UNKNOWN`，不能把“部分 hash MATCH”宣传成全部 Agent 等价。

重点阅读：

1. `evaluation/v1_2_2/step9_10b_recovery_qualification.json`：机器可读的资格结论、文件分类与 F_UNKNOWN 原因。
2. `evaluation/v1_2_2/step9_10b_recovery_equivalence_report.md`：区分 observed hash evidence、harness equivalence、
   production path 与为什么最终保守阻断。
3. `evaluation/v1_2_2/step9_8b_freeze_manifest.json`：看 source hash 列表为什么不足以覆盖实际 import path。
4. `scripts/run_step9_8_frozen_evaluation.py` 与 `scripts/run_step8_9_v1_2_1.py`：确认 active path 仍使用生产 factory/
   loop/tools，且没有 mock、manual State 或 case-ID 分支。

验证：9.10a focused **6/6 PASS**、9.8f guard **13 PASS**、S1–S12 **12/12**、I1–I8 **8/8** 且 lineage PASS、
非外部模型回归 **152 passed / 0 failed / 0 skipped**；`tests.test_model_configuration` 仍是 **NOT_VERIFIED**。
当前需要人工决定如何建立遗漏 active Agent 文件的可审计 immutable source baseline；在此之前不进入 9.10c，也不创建
recovery authorization。

### 我的理解


### 仍然不理解的问题


## 第 9.10b.1 步：Frozen Agent Provenance Reconstruction（冻结 Agent 来源重建）

本阶段完成只读取证重建；没有运行 Benchmark V2、调用真实模型或访问 V3，也没有修改 Agent、Benchmark、scoring 或原 Step 9.8 manifest。核心结论是 **`AGENT_EQUIVALENCE_STATUS=INSUFFICIENT_PROVENANCE`**，而不是发现 Agent 已变化。原 manifest 对 13 个实际行为文件有强 SHA-256 证据，且当前均 MATCH；但真实生产链还有 10 个会影响行为的遗漏依赖无法在冻结时点建立不可变身份。

遗漏范围包括 `/api/chat` factory、session/service、DependencyResolver、确定性 facts、recorder、requirements 配置、RAG 实现、embedding 及 RAG index/corpus。较早的 baseline manifest 和 2026-09-16 Git object 对其中四项提供历史线索，但不构成 2026-09-21 冻结时点的连续证明；9.8a/9.3/9.6 的文字报告只作为弱证据。因此不能将任何 `UNKNOWN` 升格为 MATCH，也不能借当前 hash 回填历史 manifest。

重点阅读：

1. `evaluation/v1_2_2/step9_10b1_production_dependency_inventory.json`：完整 production dependency inventory；每项都有 role、importer、是否影响行为、manifest 覆盖、当前观察 hash、历史来源、证据强度和严格的 equivalence status。
2. `evaluation/v1_2_2/step9_10b1_provenance_reconstruction.json`：区分 Step 9.8 强证据、早期 hash、后事件快照和 prose 的证据等级，并保留 five explicitly investigated files 的未知边界。
3. `evaluation/v1_2_2/step9_10b1_provenance_report.md`：为什么结论是“证据不足”而非“发生变化”，以及为何 unresolved RAG/API/Dependency 文件使 recovery 不能被称为严格可恢复。
4. `evaluation/v1_2_2/step9_8_freeze_manifest.json`：原始、不可改写的 13-file 证据边界。

最终状态：`RECOVERY_EXPERIMENT_STATUS=NOT_STRICTLY_RECOVERABLE`、`READY_TO_REASSESS_STEP9_10B=NO`。若以后需要提升资格，必须建立新、独立、可审计的来源/身份协议；本阶段未提出或实施任何 recovery run。

### 我的理解


### 仍然不理解的问题


## 第 9.11 步：Clean Evaluation Re-Freeze（干净评估重新冻结）

Step 9.8 recovery 已永久关闭；本阶段没有重试或改写历史，而是从当前代码创建了独立的 `clean-evaluation-v1_2_3-20260922-01`。它的 `historical_parent` 是 `STEP9_8_FAILED_EVALUATION`，但 `recovery_of_step9_8=false`；当前只完成冻结，`execution_state=NOT_AUTHORIZED`。

新的冻结不再使用手工挑选的 13 个文件。它从真实 `/api/chat` 路径建立 25 项 Agent-behavior closure：Flask/service/loop、输入理解、facts、目标语义/requirements、DependencyResolver、充分性、preconditions、候选与 policy、State/State Update、tools、Answer Generation、recorder、model config、RAG code、index/corpus，以及不含 API key 的运行时配置指纹。Harness 有 3 项；Benchmark V2 和 scoring 分别独立冻结。

验证结果：Benchmark V2 **40 cases** 且 hash MATCH；scoring hash MATCH；四个 domain aggregate 均可重复计算。Production Agent/config 中未发现 V2 case-ID、expected-action lookup 或 benchmark-specific prompt/requirement/answer rule。V2 仍明确是 development/regression set，**不是 held-out**。Focused deterministic tests **59 passed**，non-external-model regression **152 passed**；`tests.test_model_configuration` 未运行且未被计为 PASS。

重点阅读：

1. `evaluation/v1_2_3/step9_11_clean_freeze_manifest.json`：新 evaluation/freeze/manifest identity、按 A/B/C 域分离的文件 hash 和 aggregate hash。
2. `evaluation/v1_2_3/step9_11_dependency_inventory.json`：从 `/api/chat` 向下的完整 closure；尤其看 RAG index/corpus 和 redacted runtime configuration 为什么必须纳入 Agent behavior domain。
3. `evaluation/v1_2_3/step9_11_freeze_audit.json`：复算、V2/rubric hash、leakage audit 和 test 状态的机器可读结论。
4. `evaluation/v1_2_3/step9_11_clean_refreeze_report.md`：为什么本次是新的 evaluation generation，而不是 Step 9.8 rerun。

最终状态：`READY_FOR_STEP9_12=YES`。本阶段没有运行 Benchmark V2、调用真实模型或访问 V3，也没有修改 Agent、Benchmark 或 scoring。

### 我的理解


### 仍然不理解的问题


## 第 9.12 步：Local Execution Preflight & Authorized Run Preparation（本地执行预检与正式运行准备）

本阶段没有执行 Benchmark V2。新 identity 的 Agent、Harness、Benchmark、Scoring 文件与 aggregate hash 均重新核验为 MATCH，V2 为 40 cases，且 production Agent/configuration 内没有 case-specific logic。为保持新 identity 的完整闭包，新增的 Step 9.12 preflight 与 one-shot runner 被纳入 Harness domain；这不改变 Agent、V2、评分或 Step 9.8 历史。

本机只读预检结果：Python/venv/required imports、`api.deepseek.com` DNS、HTTPS 均 PASS；但当前环境 `DEEPSEEK_API_KEY` 为 absent。协议因此没有发起真实 model probe，也没有运行 synthetic production smoke；trace lineage 只能标为 NOT_VERIFIED。该阻塞属于环境 credential readiness，不是 Agent failure。Measurement schema 已准备好，但 token usage 继续明确为 `NOT_MEASURED`。

重点阅读：

1. `scripts/preflight_step9_12_local.py`：只读检查 hash、环境、DNS/HTTPS；仅在 credential/DNS/HTTPS 都正常时才允许最小 model probe 与非 Benchmark production smoke。
2. `scripts/run_step9_12_frozen_evaluation.py`：新的 evaluation identity runner；需要 scoped、non-secret authorization ID，并在 case 1 前记录 STARTED 和二次复核 frozen closure。
3. `evaluation/v1_2_3/step9_12_local_preflight.json`：本机实测的 PASS/FAIL/NOT_RUN 状态及 first blocking point。
4. `evaluation/v1_2_3/step9_12_execution_protocol.md` 与 `step9_12_authorization_template.json`：一次性运行协议与新授权字段；没有正式授权时不得运行。

最终状态：`READY_FOR_AUTHORIZED_RUN=NO`。原因仅为 credential 缺失，故没有生成当前可执行的唯一正式命令，也没有创建 formal attempt/ledger entry。

### 我的理解


### 仍然不理解的问题


## 第 9.12a 步：Production Trace Lineage Gap Diagnosis（生产血缘缺口诊断）

本阶段只读诊断了用户本地真实 synthetic production smoke 的 lineage 缺口；没有重新运行 preflight、Benchmark V2 或模型，也没有访问 V3 或修改 Agent/Benchmark/scoring。真实请求本身已经正常完成（State、action 和 answer 均存在）。问题是预检脚本只查询**最终可变 State**，并错误要求每次最终 action 同时保留所有历史节点 ID。

证据表明这不是 Agent 行为或 production wiring 丢失 ID：知识问答先形成 EVIDENCE dependency，RETRIEVE 在第一轮 `DECISION` snapshot 中拥有 `precondition_id` 和 `candidate_id`；检索完成、证据 SATISFIED 后，最终 ANSWER 合法地不再有 active precondition。`candidate_id` 已保存在 action 的 `selected_candidate_id` 和 `state_history`，但最终 `considered_information` 是每轮刷新会重置的观测列表，不是持久 ID 载体。

诊断结论：`ROOT_CAUSE=LINEAGE_SCHEMA_TOO_STRICT`；`precondition_id` 属于 F（该最终 action 合法地无 active precondition），`candidate_id` 属于 G（预检观察者读取了错误的最终 State 表示）。完整 lineage 假设只能是 `PARTIAL`：强制工具行动需要 dependency → precondition → candidate → action → tool/state update；满足依赖后的 policy-selected ANSWER 则不要求 precondition。需要修复的是 Harness 的观测查询，不是 Agent。

重点阅读：

1. `evaluation/v1_2_3/step9_12a_lineage_gap_diagnosis.md`：完整调用链、静态代码证据、合法 lineage shapes 和最终根因。
2. `evaluation/v1_2_3/step9_12a_lineage_path.json`：机器可读的层级路径、ID 生命周期与 failure class。
3. `evaluation/v1_2_3/step9_12a_fix_boundary.md`：仅设计的最小 observability 修复边界；若未来授权，它只改变 Harness freeze，不改变 Agent、V2 或 scoring。
4. `scripts/preflight_step9_12_local.py`：当前仅查看 final State 的 smoke observer；这是后续应修改的唯一位置，而本阶段未动它。

最终状态：`AGENT_BEHAVIOR_BUG=NO`，`TRACE_OBSERVABILITY_BUG=YES（仅 preflight observer）`，`LINEAGE_SCHEMA_ISSUE=YES`，`READY_FOR_AUTHORIZED_RUN=NO`。必须先经人工审查并单独授权 observer-only Harness 修复与新的 Harness freeze。

### 我的理解


### 仍然不理解的问题


## 第 9.12b 步：Minimal Trace Observer Fix（最小追踪观察器修复）

本阶段只修改 `scripts/preflight_step9_12_local.py` 的 synthetic smoke **观察方式**：通过内存 recorder 读取生产 `/api/chat` 请求真实产生的 `LoopResult.state_history`，再按 action/revision 恢复 candidate、precondition 与 tool/state-update 血缘。没有修改 production Agent、Decision Policy、State、DependencyResolver、Candidate、Answer Generation、Benchmark V2 或评分。

修复不再要求最终 ANSWER 持有全部历史 ID。`HARD_PRECONDITION` action 必须有 `precondition_id`；所有 policy-selected action 必须从真实 Decision snapshot 与 action history 恢复 `candidate_id`；工具 action 必须有 `tool_result_id` 和 `state_update_id`；已满足依赖后的 ANSWER 合法地无需 active precondition 或 tool result。缺少真实关系时 observer fail closed，并保留 null；绝不生成 fake ID。

验证：focused tests **8 passed**；S1–S12 **12 passed**；I1–I8 integration scenarios **8/8 PASS** 且 lineage audit PASS（输出写到临时目录，未覆盖历史 Step 9.7 工件）；integration trace audit tests **6 passed**；合计 focused test modules **26 passed**。排除 `tests.test_model_configuration` 的完整非外部模型回归为 **160 passed / 0 failed / 0 skipped**。`tests.test_model_configuration=NOT_VERIFIED`，未计为 PASS。未调用 DeepSeek、未运行 V2、未访问 V3。

新增独立 Harness Freeze：Step 9.11 的 Agent freeze 完全保留；新 freeze 仅替换 preflight observer 的 hash，`CHANGE_CLASS=OBSERVABILITY_ONLY`。当前新 Harness、Agent、Benchmark、Scoring hash 均 MATCH；旧 Harness hash 预期不再匹配，因此不得将其重写为新值。

重点阅读：

1. `scripts/preflight_step9_12_local.py`：`_lineage_validation` 如何以 history 中真实 `candidate_id`、`source_precondition_id`、`source_action_id` 验证条件化 lineage。
2. `tests/test_step9_12b_trace_observer.py`：T1–T8，特别是 final State 已刷新但仍可恢复 candidate、SATISFIED ANSWER 无 precondition 合法、以及真正缺失时 fail closed。
3. `evaluation/v1_2_3/step9_12b_lineage_validation_spec.json`：四种 action lineage shape 的机器可读契约。
4. `evaluation/v1_2_3/step9_12b_harness_freeze.json`：旧/新 Harness aggregate hash 与仅观察器变更边界。
5. `evaluation/v1_2_3/step9_12b_observer_fix_report.md`：实现、验证、冻结和执行限制的完整报告。

最终状态：`OBSERVER_FIX_IMPLEMENTED=YES`，`AGENT_BEHAVIOR_CHANGED=NO`，`HARNESS_FREEZE_UPDATED=YES`，`READY_FOR_LOCAL_PREFLIGHT_RECHECK=YES`，但 `READY_FOR_AUTHORIZED_RUN=NO`。下一步只能在人工授权后执行真实本地 preflight recheck。

### 我的理解


### 仍然不理解的问题


## 第 9.13 步：Authorized Benchmark V2 Run Preparation（正式运行准备）

本阶段没有执行 runner、Benchmark V2 case、模型或 V3，只读审计了本地 preflight artifact、冻结身份与 one-shot runner。结果必须 fail closed：工作区中唯一持久化的 `step9_12_local_preflight.json` 仍是旧记录，显示 credential 缺失、smoke NOT_RUN、`ready_for_authorized_run=false`；它和用户报告的后续本地 PASS 不一致，且未找到可审计的更新 artifact。

另一个独立阻塞是：`scripts/run_step9_12_frozen_evaluation.py` 仍验证 Step 9.11 的 legacy Harness manifest。Step 9.12b 已有新的 observability-only Harness freeze，因此当前 runner 不会接受它；同时 runner 没有显式 `--evaluation-id` 参数。Step 9.13 不被授权修改 runner，因此没有伪造 Authorization ID 或给出会失败的 Benchmark 命令。

冻结审计中 Agent、Benchmark V2（40 cases）、Scoring 与 Step 9.12b Harness 的各自 hash 均 MATCH；ledger 尚不存在任何新的 formal attempt。失败分类规则已在执行前冻结：COMPLETED、PARTIAL_EXECUTION、ENVIRONMENT_FAILURE、MODEL_FAILURE、HARNESS_FAILURE、AGENT_FAILURE、SCORING_FAILURE。

重点阅读：

1. `evaluation/v1_2_3/step9_13_authorization_manifest.json`：未签发授权的机器可读理由、用户报告与 workspace artifact 的证据边界、全部 frozen hashes。
2. `evaluation/v1_2_3/step9_13_one_shot_runner_audit.md`：runner 已具备与缺失的 guard 语义，以及执行前固定的 failure classification。
3. `evaluation/v1_2_3/step9_13_final_frozen_identity_summary.md`：Step 9.11 Agent/Benchmark/Scoring freeze 与 Step 9.12b 独立 Harness freeze 的关系。
4. `evaluation/v1_2_3/step9_13_execution_command.txt`：为何本阶段没有下发可执行命令。
5. `evaluation/v1_2_3/step9_13_report.md`：正式 gate matrix 与下一次最小授权边界。

最终状态：`READY_FOR_FINAL_AUTHORIZATION=NO`，`AUTHORIZATION_ID=NOT_ISSUED`，`BENCHMARK_V2_EXECUTED=NO`，`BENCHMARK_V3_ACCESSED=NO`。需要人工授权一个 Harness-only reconciliation 后，才可重新进行 preflight/正式运行准备。

### 我的理解


### 仍然不理解的问题


## 第 9.13a 步：Final Authorization Blocker Resolution（最终授权阻塞修复）

本阶段只改评估基础设施。预检脚本新增 `--capture`：用户在本地执行真实网络、模型和 synthetic production smoke 后，原有判断结果会以 `LOCAL_REAL_PREFLIGHT` 写入独立、带 UTC 时间戳的 JSON；记录 Evaluation ID、四个冻结域的 hash 与必要 gate 字段，只记录 credential 是否存在，不保存 API key。旧 FAIL artifact 原样保留。Work 环境没有替用户执行真实 preflight。

One-shot runner 现在强制要求精确的 `--evaluation-id clean-evaluation-v1_2_3-20260922-01`，并验证 Step 9.13a 新 Harness freeze、Step 9.12b 父冻结、Step 9.11 Agent/Benchmark/Scoring 冻结及实际文件。`STARTED` 仍须在第一个 case 之前进入只追加 ledger；历史状态不明确或同一 authorization ID 已使用时拒绝运行。没有签发正式 Authorization ID。

值得重点阅读的代码位置：

1. `scripts/preflight_step9_12_local.py`：`_capture_local_result` 的机器可读字段白名单、唯一文件名与不覆盖旧 artifact；`main` 在原有 readiness 判断之后才选择保存。
2. `scripts/run_step9_12_frozen_evaluation.py`：`verify_frozen_identity` 如何把新 Harness freeze 接到四域校验；`main` 与 `run` 如何在创建 attempt 之前检查 evaluation ID 和授权 ID。
3. `evaluation/v1_2_3/step9_13a_harness_freeze.json`：Step 9.12b 父 hash、本阶段两个 Harness 脚本的新 hash、Agent/Benchmark/Scoring 不变的边界。
4. `tests/test_step9_13a_authorization_infrastructure.py`：真实结果保存结构、密钥不落盘、错误 identity/freeze 拒绝、重复授权拒绝与测试不触发 runner 的离线验证。
5. `evaluation/v1_2_3/step9_13a_report.md`：冻结结果、测试证据和本地下一步的完整说明。

关键执行流：用户在 Mac 运行 `--capture` → 预检沿用原有判断 → 独立保存 PASS/FAIL artifact → 人工审核后才可能签发授权 → runner 在创建 attempt 与首个 case 前分别核验冻结内容。本阶段没有运行真实 preflight、Benchmark V2 或 V3。

阅读后应能回答：为什么用户口头报告 PASS 仍需可审计的本地 artifact？为什么旧 Step 9.11/9.12b 冻结不能覆盖更新？为什么正式 runner 在首个 case 前还要二次校验 hash？

已知限制：新真实 artifact 尚未由用户生成，因此 `READY_FOR_AUTHORIZED_RUN=NO`。`tests.test_model_configuration` 本阶段继续 `NOT_VERIFIED`。初版离线测试曾因模拟授权值不一致误入 runner 初始化，停在依赖导入阶段；空 trace 和模拟 artifact 已清理，测试增加了 runner 不可调用断言。最终离线回归为 **168 passed / 0 failed / 0 skipped**，四域冻结核验均 MATCH。

### 我的理解


### 仍然不理解的问题

## 第 9.14 步：Final Clean Evaluation Analysis（正式评估结果分析）

正式 one-shot evaluation `clean-evaluation-v1_2_3-20260922-01` 已从 append-only ledger 与 attempt-scoped traces 核验为 `COMPLETED`，40/40 cases 完成，最终状态均为 ANSWER。授权、attempt 与 Agent / Harness / Benchmark / Scoring freeze hash 已记录于 `evaluation/v1_2_3/step9_14_official_metrics.json`。本阶段只分析该次正式产物，没有重跑 case、调用模型、修改 Agent、Benchmark、评分或 Harness，也没有访问 Benchmark V3。

从 40 条 raw traces 重算的总分为 68.275；KQ 71.500、CA 67.400、PD 57.167、DA 82.000。ASK 55 次（1.375/case；PD 2.500/case），其中 necessary 8、useful-but-optional 21、redundant 14、irrelevant 12；冗余与无关合计 47.27%。RETRIEVE 0.350/case，READ_DIARY 0.275/case，turns 2.375/case，steps 3.000/case。观察到 critical failure 0；但 KQ-02、KQ-05、DA-07 仍有目标/依赖表示导致的显著交互失败。DA-01/02/03/04/05/08 的可用 diary fixture 均因 summary payload 不满足 Diary Contract V2 元数据要求而 fail closed，未生成虚假数据但未完成分析。KQ-04/KQ-10 还出现知识教育目标误触发无关 diary resource 的新问题。

与 Step 8.9 的记录值相比，平均 ASK −0.275/case、PD ASK −0.417/case、turns −0.275/case、steps −0.150/case；critical failure 记录数从 4 到 0。该轮 fresh trace review 得分仅比历史值高 0.775，且打分是单人按五维权重做的轨迹审阅（冻结 rubric 没有数值锚点），故分数与历史分数比较需谨慎。Benchmark V2 仍是 development/regression set，不能据此宣称泛化或临床效果。Token usage 未测量；精确模型调用数及组件级延迟不可用。

重点阅读：

1. `evaluation/v1_2_3/step9_14_final_evaluation_report.md`：正式运行核验、总体结果、失败根因、历史差值及结论边界。
2. `evaluation/v1_2_3/step9_14_priority_case_audit.json`：KQ-02 / KQ-05 / DA-07 的首个偏离点与 DA 日记检查结果。
3. `evaluation/v1_2_3/step9_14_failure_analysis.json`：目标/依赖错误、错误资源选择、检索支持和日记 fixture 失败簇。
4. `evaluation/v1_2_3/step9_14_ask_quality.json`：55 个 ASK 的逐 case、逐目标分类。
5. `evaluation/v1_2_3/step9_14_lineage_audit.json`：tool candidate payload 未持久化的 25 条可观测性缺口。

### 我的理解


### 仍然不理解的问题

## 第 9.17 步：Tool → State Projection Repair（工具到状态投影修复）

建立了可复用的 Tool→State 投影信封，并强化当前 Diary 投影验证：明确区分 `ENTRY_SHAPED`、`SUMMARY_SHAPED`、`UNAVAILABLE`、`INVALID`；无来源数量、日期覆盖、来源信息或摘要语义的 summary 会 fail-closed，且摘要只存为 `diary_summary`，不伪装成逐日 entries。无效/不可用的新读取会清除旧的 diary-sourced facts，避免旧值被误认为本次读取结果。有效 entry 可确定性计算日记天数、平均睡眠时长、精确上床/起床时间变化、逐日卧床时长和有足够精确输入时的睡眠效率。派生 State facts 与 answer claim provenance 均保留 tool result、state update、日期、来源和投影状态。检索证据也使用通用 lineage envelope。

重点阅读：

1. `adaptive_agent/state_update.py`：投影校验、fail-closed、计数/日期核验、统计派生以及工具结果到 State 的 lineage 写入。
2. `adaptive_agent/answer_generation.py`：无效 diary 来源如何被排除；有效日记统计与 retrieved evidence 的 claim provenance 如何保留。
3. `adaptive_agent/tools.py`：`DiaryResult` 的显式数据形态和 `SessionDiaryTool` 如何提供来源元数据；不再自动补造 provenance。
4. `tests/test_step9_17_tool_projection.py`：20 个合成场景，涵盖多日/非连续/同日多条、缺值、不确定时间、summary 校验、空/不可用日记、派生数据及 claim lineage。
5. `evaluation/v1_2_3/step9_17_projection_contract.md` 与 `step9_17_projection_repair_report.md`：通用 envelope、日记形态契约、执行链、限制与回归结果。

重要执行流：Diary Tool → 形态与 metadata 校验 → 有效原始 entries 或分离保存的 summary → State facts 与确定性派生 → answer context 过滤 → 带 tool/state IDs 的 claim provenance。无效结果只保留诊断 metadata/warnings，不写 diary facts，也不能进入最终回答。

关键设计决定：`projected_entry_count` 表示真正进入 State 的逐日记录数；另记 `received_entry_count` 帮助审计失败载荷。无效结果 projected count 为 0；summary 的逐日 projected count 也为 0。summary 的 source count 仅表示其声称汇总的来源记录数，不把摘要值数量当成记录数。有效空日记是已知的 0 条数据，不会被扩写成虚构日期。

测试：Step 9.17 合成测试 **20 passed**；相关组合测试 **93 passed**；完整 unittest **200 项：198 passed / 2 failed / 0 skipped**。两项失败来自历史 Step 9.11 Agent freeze 检查仍要求当前 Agent 源码 hash 与旧冻结相同；本阶段修改了获准范围内的 Agent 投影代码，因此旧 hash 不再匹配。未改写历史 freeze。整体 regression 状态据此标记为 **FAIL（2 个历史冻结身份断言）**，不能报告为全通过。

已知限制：summary 的 provenance 目前是结构校验，不能独立证明上游数据真实性；条目要求 ISO 日期和规范化时间，其他格式需由明确 adapter 转换。全套回归中的两个旧 freeze 测试需要单独决定如何表达“历史基线不可变”和“当前开发源码变化”，本阶段不擅自刷新 baseline。没有运行 Benchmark V2，没有访问 V3，也没有调用真实模型。

### 我的理解


### 仍然不理解的问题

## 第 9.17a 步：Regression Identity Transition Audit（回归身份迁移审计）

确认 Step 9.17 报告中的两个全量测试失败均为 `STALE_FREEZE_ASSERTION`，不是行为回归。旧断言错误地要求当前 Agent 源码仍等于 Step 9.11 历史 Agent 身份；第一个合法分叉实际发生在已验收的 Step 9.16（`dependency_resolver.py`、`candidates.py`），Step 9.17 又在已授权投影范围内修改了四个 Agent 文件。另一个失败在进入其原本要测的 attempt-ledger 逻辑前，就先被 Step 9.11 identity gate 阻断。

Step 9.11 freeze 未改写；其 manifest SHA-256 为 `ab1720e0…c17c1aa5c`，历史 Agent aggregate `ee914db7…a6446927` 可从原历史清单重算。新增的 `step9_17a_post_step9_17_candidate_freeze.json` 以 Step 9.11 为父身份，记录新的 development candidate aggregate `5e0ef044…0f9db94c`，不替代历史基线，也不授权任何 Benchmark 执行。经逐文件比较，25 项历史 Agent inventory 中 6 个变化全部对应 Step 9.16/9.17 授权路径，另 19 项 hash 不变；未发现未授权 Agent 文件改动。历史 inventory 明确将仅导出符号的 `adaptive_agent/__init__.py` 排除为非行为文件，该文件本阶段未改动。

测试修复只区分两种身份：一项断言验证历史 Step 9.11 manifest/aggregate 仍完整、当前 Agent 不再匹配旧身份但匹配新 candidate；attempt guard 单测仅 mock 身份结果以隔离它真正测试的 ledger 逻辑，另有非 mock 断言确保旧正式 runner 对新 Agent 仍 fail-closed。没有删除测试、放松 hash 校验或改动生产 runner。

重点阅读：

1. `tests/test_step9_13a_authorization_infrastructure.py`：历史冻结完整性、当前候选身份匹配和 one-shot runner 旧身份 fail-closed 的分离断言；也展示 attempt-ledger 单测为何只 mock 外层 identity gate。
2. `evaluation/v1_2_3/step9_17a_post_step9_17_candidate_freeze.json`：新候选 freeze 如何引用旧 manifest、继承未变 hash 并只替换授权改动文件。
3. `evaluation/v1_2_3/step9_17a_regression_identity_audit.json`：两条失败的 first divergence、授权路径和每组测试结果。
4. `evaluation/v1_2_3/step9_17a_regression_identity_audit.md`：完整 freeze chain 与旧 runner 保持 fail-closed 的原因。
5. `evaluation/v1_2_3/step9_11_dependency_inventory.json`：为什么 `adaptive_agent/__init__.py` 不在历史行为冻结清单中。

结果：原两个失败测试 **2 passed**；freeze/authorization/lineage focused **53 passed**；Step 9.16 dependency **8 passed**；Step 9.17 projection **20 passed**；全量非 Benchmark unittest **200 passed / 0 failed / 0 skipped**。未运行 Benchmark V2、未访问 V3、未调用真实模型。满足用户定义的进入 Step 9.18 readiness 条件；本阶段没有执行 Step 9.18。

### 我的理解


### 仍然不理解的问题

## 第 9.20a 步：V3 One-Shot Runner Preparation（一次性运行器准备）

新增独立 `scripts/run_step9_20_v3_heldout.py`，只在正式授权路径中读取 V3；模块导入、冻结验证与本地 preflight 均不读取 V3。正式路径要求 evaluation / authorization / attempt 三个显式 ID、已签发 authorization artifact、与 Step 9.19 一致的 Agent/父 Harness/Scoring/Metric/Rules hash、以及绑定新身份的真实本地 preflight。第一次 V3 内容读取之前先持久写入 UTC 首次访问事件；每个 case 的 STARTED、raw trace、lineage、case result 和完成状态按顺序 fsync；已有账本阻止第二次运行。执行路径复用生产 `/api/chat`、AdaptiveChatService、Agent Loop 与 Tool adapters，不按 case ID 分支。

新 runner 的 SHA-256 存于独立 `step9_20a_v3_runner_freeze.json`，作为 Step 9.19 父 Harness 的子身份；旧冻结未重写。`step9_20a_v3_authorization_template.json` 仍为 `TEMPLATE_NOT_ISSUED`，authorization/attempt ID 均为空。`step9_20a_local_preflight_command.txt` 仅提供用户之后在本地执行的预检命令，本阶段没有执行该命令或调用真实模型。Token 总量仍无可靠完整遥测，记录为 `NOT_MEASURED`；case 评分留给冻结 rubric 的人工审阅，不伪造数值。

离线 synthetic + 既有 guard/lineage/authorization focused tests：**34 passed / 0 failed**。验证了模板拒绝、首次访问日志先于合成 fixture 读取、raw/case 持久化、合成故障保留和重复运行拒绝。Benchmark V2 未运行；V3 未访问。

重点阅读：`scripts/run_step9_20_v3_heldout.py`（冻结校验、授权门控、首次访问与执行账本）；`tests/test_step9_20a_v3_runner.py`（离线 one-shot 证明）；`evaluation/v1_2_3/step9_20a_v3_runner_audit.md`（边界和限制）；`evaluation/v1_2_3/step9_20a_v3_runner_freeze.json`（独立 runner 身份）。

### 我的理解


### 仍然不理解的问题

## 第 9.20b 步：V3 最终授权审计（暂未签发）

本地真实预检 artifact 与 `heldout-v3-step9_20-20260923-01` 一致。独立重算确认 Step 9.19 Agent、Harness、Scoring、Metric Registry、One-shot Rules 及 Step 9.20a runner 的冻结哈希均匹配；没有正式 attempt 账本。未读取 V3、调用模型或运行案例。

唯一未满足的授权输入是 sealed V3 数据集的确切仓库相对路径：现有未签发模板的 `benchmark_path` 为空，非 V3 文档也没有指定路径。猜测路径可能在 one-shot attempt 创建后导致错误来源或失败，因此本轮 fail closed：不签发 authorization/attempt ID，不生成可执行命令。详见 `evaluation/v1_2_3/step9_20b_final_authorization_audit.md`。

重点阅读：

1. `evaluation/v1_2_3/step9_20b_final_authorization_audit.md`：已通过的冻结/预检门槛及尚缺的唯一授权输入。
2. `scripts/run_step9_20_v3_heldout.py`：授权清单如何绑定 `benchmark_path`，以及 attempt ledger 和首次 V3 读取的顺序。
3. `evaluation/v1_2_3/step9_20a_v3_authorization_template.json`：未签发模板为何不能直接执行。

关键执行流：真实本地预检 → 当前冻结身份复核 → one-shot 历史检查 → 确定 sealed V3 路径 → 签发授权 → 人工执行。当前停在路径绑定之前。请思考：为什么只知道冻结哈希和预检通过，还不足以安全签发绑定具体数据源的一次性授权？

### 我的理解


### 仍然不理解的问题

## 第 9.20c 步：Benchmark V3 构建与封存

纠正来源状态：Step 9.19 的 `SEALED_NOT_ACCESSED` 当时只是计划状态，实际应解释为 `PLANNED_HELDOUT_NOT_YET_CONSTRUCTED`；历史清单没有改写。现在首次创建独立的 32 例 V3 数据集，四类任务各 8 例，并在静态 schema、日期/单位、V2 查询重复与近似情景审计后，以 SHA-256 `44ca089a6efa6d734815b17fc73753e8411fcfc31c4f5792342644ed54b2821f` 封存。此后的 `SEALED_NOT_ACCESSED` 意味着构建者已为审计读取内容，但 Agent 与正式 evaluation 尚未访问。未签发 authorization，也未运行模型或 Benchmark。

重点阅读：

1. `evaluation/benchmarks/benchmark_v3_cases.yaml`：新的任务、信息充分性、资源和 answer-scope 组合；日记时长数字以分钟为单位。
2. `evaluation/v1_2_3/step9_20c_v3_manifest.json`：真实数据集路径、hash、case count、分布及封存边界。
3. `evaluation/v1_2_3/step9_20c_v3_provenance_correction.md`：为何旧的“sealed”并不代表已存在数据集，以及构建访问和首次正式评估访问的区别。
4. `evaluation/v1_2_3/step9_20c_v3_leakage_audit.md`：V2/V3 静态重复检查、schema 校验与无法由静态审计证明的限制。

关键执行流：设计新的 evaluator-only oracle 与通用 fixture → 静态验证，不调用 Agent → 记录 dataset bytes/hash → 等待人工审查 → 未来单独签发绑定 path/hash 的一次性授权。设计决定是允许多个合理路径，按当前 goal 判断缺失信息是否值得获取，而不是奖励固定的 ASK→RETRIEVE 序列。

已知限制：单人静态审阅不能保证临床判分或 inter-rater 一致性；V3 尚无 Agent 输出，不能报告性能。请思考：为什么直接给出的三个时长不需要读取日记？为什么不可用日记不能用通用知识替代个人数据？

### 我的理解


### 仍然不理解的问题

## 第 9.20d 步：V3 最终授权（未执行）

只做封存数据集的结构/哈希审计和冻结身份核对：V3 路径与 Step 9.20c manifest 一致，SHA-256 仍为 `44ca089a6efa6d734815b17fc73753e8411fcfc31c4f5792342644ed54b2821f`；32/32 个 case 满足 frozen runner 必需字段，四类任务各 8 例。Agent、父 Harness、Scoring、Metric Registry、One-shot Rules、Final Candidate Manifest 和 V3 runner 均与既有 freeze 一致；没有正式 V3 attempt 目录/账本。未运行 Agent、模型或任何 V3 case，未改动冻结组件。

新签发 `ISSUED_NOT_EXECUTED` 授权，仅绑定 `heldout-v3-step9_20-20260923-01` 下的一组新 authorization/attempt ID、V3 路径与哈希、本地真实 preflight artifact 及全部冻结身份。命令文件仅供人工审查后手动执行；runner 会在首次 case 前再次校验冻结身份和 V3 字节哈希，并以独占 append-only ledger 阻止第二次正式 attempt。本阶段没有执行命令。

重点阅读：

1. `evaluation/v1_2_3/step9_20d_v3_final_authorization_audit.md`：每个 gate 的证据、首次正式访问与构建期静态访问的边界。
2. `evaluation/v1_2_3/step9_20d_v3_authorization_manifest.json`：单一 evaluation/authorization/attempt、V3 path/hash 与冻结身份绑定。
3. `evaluation/v1_2_3/step9_20d_v3_authorized_command.txt`：唯一允许人工执行的正式命令。
4. `scripts/run_step9_20_v3_heldout.py`：授权验证、首次 V3 正式访问日志、case 前哈希核验和 one-shot ledger。

关键执行流：静态封存核验 → 冻结身份核验 → 历史 attempt 核验 → 签发唯一授权 → 人工决定是否运行 → runner 再次 fail closed。已知限制：本地 preflight 是先前时点的网络/模型可用性证据，不能保证正式执行时外部服务仍可达；正式 runner 会复核配置但环境故障仍须按冻结协议记录。请思考：为何授权清单既绑定 V3 hash，又仍要在 runner 首次正式读取时核验实际字节？

### 我的理解


### 仍然不理解的问题

## 第 9.21 步：V3 留出集正式结果分析（不重跑）

只读取正式 one-shot ledger、32 条 raw traces、32 条 case results 与冻结的授权/评分/指标规范；完整性审计为 `COMPLETED`、32/32、ID 无重复、冻结身份匹配。原始 runner 的 `score_status=PENDING_FROZEN_RUBRIC_REVIEW` 保持不变；本步另存单人逐例五维评审，不覆写原始结果或冻结输入。V3 Overall 60.91；KQ 70.13、CA 46.75、PD 47.88、DA 78.88；ASK 1.219/例，其中冗余+无关 19/39=48.72%；Critical 1、严格定义下 Harmful 6。有效日记投影没有基数/日期/来源损坏，但 DA-08 回答把“有记录、时长未填”说成“无记录”。KQ 依赖通常形成并检索，却多次在回答时丢失可用证据；CA/PD 的显式事实遗漏与低价值追问仍明显。V2 是开发集、V3 是冻结后留出集，两者不是配对比较。

重点阅读：

1. `evaluation/v1_2_3/step9_21_v3_integrity_audit.json`：正式 ledger、授权及四类冻结哈希、32/32 行数与唯一 ID 的核对。
2. `evaluation/v1_2_3/step9_21_v3_case_scores.jsonl`：32 例五维分数、行动路径、完成度、关键/有害失败、首个偏离层及评分理由；请特别检查 DA-08 的独立关键失败与 CA/PD 的下游追问归因。
3. `evaluation/v1_2_3/step9_21_v3_ask_quality.json`：39 次追问的逐 target 分类；用于审查“ASK 变少”是否真的表示低价值获取减少。
4. `evaluation/v1_2_3/step9_21_v3_failure_analysis.json`：证据依赖、资源依赖、Tool→State 投影、回答证据过滤和数据派生声明的首个偏离分析。
5. `evaluation/v1_2_3/step9_21_v3_analysis_report.md`：总结果、非配对 V2 对照、三层研究解释及测量限制。

关键阅读问题：为什么 `RETRIEVE → EVIDENCE SATISFIED` 后仍可能出现“没有可用证据”的回答？为什么 6/6 日记投影正确仍不能保证 6/6 数据分析答案正确？为什么 1.219 ASK/例和 48.72% 低价值 ASK 可以同时成立？

### 我的理解


### 仍然不理解的问题

## 第 9.22 步：V3 失败复核与修复边界（只分析）

保持 Step 9.21 的正式结果及 1 Critical / 6 Harmful 不变。本轮按冻结标签逐条复核 19 次低价值 ASK：近端首要根因为 Information Value 高估 12、明示事实未进入 State 6、错误 hard dependency 1；其中 17 个目标仍被标为 `useful_optional`、2 个标为 `mandatory`，没有“依赖已满足却继续 ASK”或独立 Policy selection 错误。六个 Harmful case 的整体传播链中，首个偏离为 Information Value Gate 4、Input Understanding 2。两种统计口径不同，不要混为一谈。

DA-08 的 5/5 日记投影、日期与 provenance 正确；2026-09-04 有条目、没有时长，四个可用时长的平均数 381 分钟也正确。最终模型文本把“时长缺失”写成“记录缺失”，因此最有依据归于 Answer Generation；精确模型请求体没有日志化，不能把由冻结代码重建的上下文冒充直接观测。12 次 RETRIEVE 中 2 次实质使用、1 次因材料不够直接而合理受限、9 次证据在 State 但被回答上下文的词面过滤排除；没有证据证明是模型看到相关证据后无视。

重点阅读代码：

1. `adaptive_agent/input_understanding.py`：用户显式数值和定性情境如何提取、归一化；它是 PD-05、DA-07 上游遗漏的第一检查点。
2. `adaptive_agent/requirements.py` 与 `adaptive_agent/dependency_resolver.py`：有效需求和硬依赖如何分开形成；理解 PD-04 为什么会把 latency 升为必要条件。
3. `adaptive_agent/information_value.py` 与 `adaptive_agent/acquisition_gate.py`：可选信息的反事实影响与成本门控；对照 12 次被 HIGH 接纳的低价值追问。
4. `adaptive_agent/state_update.py`：日记工具元数据、日期/条数与派生事实如何进入 State；它证明 DA-08 不是基数投影错误。
5. `adaptive_agent/answer_generation.py`：`relevant_evidence` 的词面过滤、回答上下文与最终校验；对照 9 次证据被过滤及 DA-08 的字段/记录语义错误。

逐次证据与修复边界分别保存在 `evaluation/v1_2_3/step9_22_ask_failure_audit.json`、`step9_22_harmful_failure_chains.json`、`step9_22_critical_failure_forensics.json`、`step9_22_evidence_usage_analysis.json`、`step9_22_repair_boundary.json` 和总报告 `step9_22_failure_validation_report.md`。阅读执行链时依次追踪：原始输入 → Goal/State → 有效需求/依赖 → 候选价值/门控 → Action → Tool/State → 回答上下文 → 最终声明。设计决定是坚持首个偏离层和一个主因，而不是把后续 ASK 或回答薄弱重复统计为多个 Policy failure。已知限制是模型请求体与完整原始工具载荷未日志化。

从现在起 V3 已被用于具体失败分析，后续只可作 development/regression evidence，不得再充当修复版的新留出最终评估。若需要新的泛化证据，须在后续通用修复完成且重新冻结之后另建 V4；本轮没有构建或访问 V4，也未调用模型、重跑 V3 或改动 Agent/Benchmark/评分/评估框架。

## 第 9.23 步：State → Answer 完整性修复（P1）

这一步只修回答链：显式事实与来源从已验证 State 投影到统一 Answer Context；检索证据不再由少数固定目标关键词决定是否进入回答，而按检索血缘/通用词面回退筛选并记录排除原因；有效日记中的“有记录但字段缺失/无效”与“记录不存在”“资源不可用”分开表示。最终回答增加与 State 冲突的事实声明检查，保留原有量化医学声明证据约束和 answer_scope。没有修改 Policy、Information Value Gate 或 ASK 排序。

重点阅读代码：

1. `adaptive_agent/answer_generation.py` 的 `project_evidence`、`build_answer_context`：看同 goal 的 RAG 来源如何进入回答、排除证据如何留审计，以及为什么原始用户话语不能作为第二事实通道。
2. `adaptive_agent/answer_generation.py` 的 `diary_semantic_status`、`remove_state_conflicting_claims`：看“记录存在但字段缺失/无效”与“没有记录”的边界，以及最终文本如何保守地拦截矛盾事实。
3. `adaptive_agent/state_update.py` 的 `apply_retrieval_result`：看 evidence 的 tool/state ID、检索 query 与 goal ID 如何与当前 State 相连。
4. `adaptive_agent/runner.py` 的 `_snapshot`：看 `answer_context_audit` 如何进入 Agent Loop 轨迹，便于排查证据为什么被纳入或排除。
5. `tests/test_step9_23_state_answer_integrity.py`：14 个合成测试覆盖事实来源、证据、日记语义、无依据陈述和回答范围；可以从测试逆向理解契约。

读完应能回答：检索证据何时进入模型、未进入时在哪看排除理由？为何“某日有记录但时长未填”不能被说成“某日无记录”？为什么最终事实守卫不能代替人工语义审计？

专项 14/14 PASS。完整非外部模型回归为 229/232 PASS、3 FAIL；三个失败均为旧冻结身份断言在本次获授权回答层修改后失效，不能当作 PASS，也没有改写历史冻结以消除失败。详见 `evaluation/v1_2_3/step9_23_regression_report.md`。V2/V3 未重跑，未调用真实模型；V3 已用于诊断，不能继续充当修复版最终留出集。下一步应先处理新候选身份及历史冻结测试的区分，再考虑 P2，本步未实施。

### 我的理解


### 仍然不理解的问题

## 第 9.24 步：目标条件化信息价值修复（未运行 Benchmark）

本步仅修复低价值 ASK 过度放行。`information_value.py` 现在要求候选信息能够沿当前 Goal、USER_FACTS dependency 和缺失字段形成可审计链路，并以反事实判断未知/已知状态是否会改变下一步、建议方向或回答范围。只改善细节的候选不再仅因字段缺失被判为高价值。`acquisition_gate.py` 在候选动作生成后、Policy 前记录序数启发式组成并过滤不可行动的可选获取；Hard Precondition 仍可直接通过，不受可选信息门控拦截。所有等级都是可解释启发式，不是概率或校准收益。

重点阅读：

1. `adaptive_agent/information_value.py`：理解 goal-conditioned relevance、dependency lineage、反事实影响等级与 ASK 成本递增。
2. `adaptive_agent/acquisition_gate.py`：理解 ASK 接纳条件、NONE/LOW 拒绝理由、工具依赖去重以及 Hard Precondition 豁免。
3. `tests/test_step9_24_information_value.py`：A–J 合成反事实测试，尤其比较同字段在不同目标下的价值，以及硬前置条件在高交互成本/多次 ASK 后仍保留。
4. `evaluation/v1_2_3/step9_24_candidate_freeze.json`：当前候选身份如何从 9.18 + 9.23a 获准变化链构造，不覆盖历史 freeze。
5. `evaluation/v1_2_3/step9_24_regression_report.md`：完整非 Benchmark 回归与身份核验口径。

关键执行流：Goal/State 与已同步 dependency lineage → 信息价值估计 → Candidate acquisition gate → Decision Policy。估值若无完整依赖/目标联系，不会凭 requirement 字段本身升成 HIGH；范围变化型候选可为 MEDIUM；决策方向变化型候选可为 HIGH；既有 cost/diminishing-return 规则继续约束可选获取。新增场景测试 10/10 通过；合并后的机制组 67/67 通过；完整离线非 Benchmark 回归 244 passed / 0 failed / 0 skipped。`tests.test_model_configuration` 因导入 Transformers 时 metadata 扫描卡住而保持 NOT_VERIFIED，不计入上述套件。冻结清单记录 26 个 Agent 行为文件的聚合身份，Step 9.11、9.18、9.23a 历史 freeze 均保留。

本步只运行了单元/回归测试：未运行 Benchmark V2、未访问 Benchmark V3、未调用真实模型；因此没有性能或泛化结论。V3 已经被此前的失败分析使用，不能作为本修复的新留出集。当前信息价值仍是启发式，尚无校准数据；真实模型 smoke 与 Benchmark 表现也未在本步复测。

### 我的理解


### 仍然不理解的问题

## 第 9.25 步：Step 9.24 修复后机制验证（非 Benchmark）

先验证 Step 9.24 的 26 项 Agent inventory 与候选 freeze 完全匹配，再用 12 个纯合成场景检查信息价值门控。A 组中 3 个实际进入 gate 的低价值 optional ASK 均被抑制；另外，无关知识事实根本没有生成 ASK、State 已知的事实也没有重复 ASK，因此不计入 ASK gate 抑制率分母。B 组同一 caffeine 缺失在不同 goal 下表现为：仅概括睡眠时 LOW→拒绝→ANSWER；目标明确要求比较/改变安排时 MEDIUM/HIGH→ASK 保留。C/D 组的 validity-critical ASK、evidence RETRIEVE、授权且可用 diary READ_DIARY 均保留；不可用且已有读取历史的 diary 不重读，混合缺失时没有顺次追问次要字段。

观测：低价值 optional ASK 抑制 3/3；必要 Hard-Precondition ASK 保留 2/2；五个预期 ASK（包含 decision-relevant optional ASK）保留 5/5；Hard-Precondition acquisition 4/4；Required RETRIEVE 1/1；Required READ_DIARY 1/1；under-acquisition 与 hard-precondition violation 均为 0。12/12 场景符合预期。相关机制/依赖/充分性/身份 focused regression 76/76 PASS。

重点阅读：

1. `evaluation/v1_2_3/step9_25_mechanism_cases.yaml`：受控案例输入、成对对照和预期动作，不是 Benchmark。
2. `scripts/run_step9_25_mechanism_validation.py`：如何校验冻结身份，并以依赖解析→充分性→候选→gate→Policy 的离线生产机制路径执行场景、计算分母与保存 trace。
3. `evaluation/v1_2_3/step9_25_mechanism_results.json` 与 `step9_25_counterfactual_pairs.json`：逐例动作、依赖、门控理由与 CF-CAFFEINE 对照。
4. `evaluation/v1_2_3/step9_25_mechanism_validation_protocol.md`：事先判定口径及 Pre-P2 对照不可测的处理。

重要限制：可执行的 pre-Step-9.24 源码不在工作区，只有历史 hash，故不能安全运行机制消融；相对旧机制的改善为 NOT_MEASURED。当前 100% 抑制/保留只说明这些合成场景中的机制行为符合预期，不是性能、真实用户或临床有效性证据。单次离线决策不测量 turn/loop latency/tokens。未修改 Agent，未运行 V2/V3，未创建/运行 V4。V3 已用于失败分析，仅保留历史 Overall=60.91，不重新评分。下一步最多可进入 V4 protocol design，不构成创建或运行授权。

### 我的理解


### 仍然不理解的问题

## 第 9.26 步：V4 协议预注册与最终候选冻结准备

以 Step 9.24 候选为父身份创建新的 Step 9.26 final-candidate freeze。26/26 个 Agent 行为文件逐项 hash 和 aggregate 匹配；已核对父候选、Harness、Scoring、V4 metric registry 与 one-shot rules 哈希。Step 9.25 的 12 个机制场景结果及 76 项 focused regression 状态随候选记录。未覆盖任何历史 freeze；V3 保留为已消耗历史集（Overall 60.91），不再作为当前候选留出证据。

预注册未来 V4 为 40 例、KQ/CA/PD/DA 各 10 例，只冻结配额与场景覆盖要求，没有创建案例内容。指标固定评分维度、ASK 质量分母、必要 ASK 保留、资源获取、安全失败、时延分位数与 token 缺测规则；解释原则分为 Observed / Supported / Not Yet Supported，禁止把跨数据集差异作配对因果解释。one-shot 规则要求 seal/hash、正式首次读取事件、全哈希复验、append-only attempt 状态、唯一人工授权、禁止自动重跑。授权文件只是未签发模板。

重点阅读：

1. `evaluation/v1_2_3/step9_26_final_candidate_freeze.json`：26 个 Agent 文件哈希、当前 harness/scoring/metrics/rules 身份、父候选及历史 V3 边界。
2. `evaluation/v1_2_3/step9_26_v4_protocol.md`：V4 研究目标、40 例均衡配额、覆盖要求、指标使用与运行阶段门；此处没有 V4 case 文本。
3. `evaluation/v1_2_3/step9_26_v4_metric_registry.json`：每个指标的分子/分母、ASK 质量分母、安全指标和禁止结论。
4. `evaluation/v1_2_3/step9_26_v4_one_shot_rules.md`：数据集 seal、首次 evaluation access、授权绑定和失败后不得自动重跑的规则。
5. `evaluation/v1_2_3/step9_26_v4_authorization_template.json`：绑定候选、Harness、评分和协议哈希的未签发模板；V4 path/hash 与正式 IDs 仍为空。

执行边界：现在只完成 freeze 与 protocol/metric preregistration；V4 尚未构建、访问或运行，Agent/模型没有执行。未来还需先构建并 seal 新数据集，再冻结/审计 V4 runner、做本地 preflight、经人工授权后才能运行。V3 已被失败分析使用，历史数据不能复用作当前候选的最终 held-out 结果。

### 我的理解


### 仍然不理解的问题

## 第 9.27 步：Benchmark V4 构建与封存（未评测）

按 Step 9.26 冻结协议构建 40 个全新案例，KQ、CA、PD、DA 各 10 个；每例将 Agent 可见的 query/session/follow-up/diary fixture 与 evaluator-only 的目标、依赖、可接受路径、scope 和失败判据分开。静态检查确认 schema/fixture/覆盖矩阵完整；V2/V3 规范化精确 query 重复均为 0，ID 重用为 0，表面相似度筛查（SequenceMatcher ≥0.52）无命中。生产 Agent/config 未发现 V4 case ID、数据集 lookup 或 expected-action lookup。共享 CBT-I 主题不自动算泄漏；V3 只用于静态文本/ID 泄漏核查，没有用其回答、预期路径或评分作答案来源。

数据集已封存为 `evaluation/benchmarks/benchmark_v4_cases.yaml`，SHA-256 `8b8c72092fcd7544e69d5d2ecd13610c7bb4c14210fca330698b3e5ab3f01d7f`，状态 `SEALED_NOT_EVALUATED`。完整配额、schema、hash、UTC 时间及冻结身份见 `evaluation/benchmarks/benchmark_v4_manifest.json`。难度分布 easy 3 / medium 19 / hard 18；语言标签 English 14 / 口语中文 11 / 信息分散中文 7 / 简短中文 5 / 中英混合 3；可用日记 9、不可用 31。Step 9.26 未规定难度或语言的硬配额。

重点阅读：

1. `evaluation/benchmarks/benchmark_v4_cases.yaml`：看 runtime fixture 与 evaluator-only `evaluation` metadata 的边界、40 例均衡任务分布及覆盖矩阵；正式 runner 只能读取通用 fixture 字段。
2. `evaluation/benchmarks/benchmark_v4_manifest.json`：核对 V4 字节 hash、case count、分布、静态审计状态与 Step 9.26 candidate identity。
3. `evaluation/v1_2_3/step9_27_v4_construction_report.md`：查看 schema、fixtures、冻结身份与无 Agent/model 执行的简要证据。
4. `evaluation/v1_2_3/step9_27_v4_leakage_audit.md`：查看 V2/V3 精确重复、ID 重用、近似文本筛查方法及其局限。
5. `evaluation/v1_2_3/step9_27_v4_seal_report.md`：理解封存后不得原地编辑，任何数据缺陷都需要新的 benchmark identity。

本步只构建、静态审计并封存：Agent、Harness、Scoring、指标注册表、one-shot 规则均与 Step 9.26 冻结身份匹配且未修改；没有运行 Agent、调用模型、开始评测或签发授权。V4 runner preparation 是单独的下一阶段，本次不授权。

### 我的理解


### 仍然不理解的问题

## 第 9.28 步：V4 Runner Preparation & Local Preflight（未执行 V4）

已创建独立 V4 runner `scripts/run_step9_28_v4_heldout.py`，其正式路径复用 production `/api/chat`、`AdaptiveChatService`、当前 Agent Loop 和真实 diary/tool adapters；没有 case-ID 分支、expected-action lookup 或 benchmark 专用 policy。正式路径要求单独的人类签发 authorization，绑定 evaluation/authorization/attempt IDs、所有冻结 hash、sealed V4 dataset、通过的本地预检；首次读取前持久化 `FIRST_EVALUATION_ACCESS`，每例 `STARTED`、raw trace、unscored result 和 lifecycle ledger 都 fsync。已有 ledger 一律禁止自动重跑。

已冻结 runner 与未签发授权模板，并完成通用 schema 与所有身份校验：Final Agent、Harness、Scoring、Metric Registry、One-Shot Rules、V4 manifest 和 V4 SHA-256 都匹配；静态审计的 case-specific logic 为 NO。V4 dataset 仍为 `SEALED_NOT_EVALUATED`。

Local Real Preflight 只核对 sealed bytes/hash、schema、imports、credential、网络和 synthetic production path，没有把任何 V4 输入送入 Agent。credential/imports 存在，但 `api.deepseek.com` DNS 未就绪，故 HTTPS、model endpoint probe 和 synthetic production smoke 均 `NOT_RUN`；按 fail-closed，尚不能进行最终 authorization。未创建 formal attempt，V4 case executed=0，score generated=NO。

## 第 9.28a 步：V4 Local Real Preflight Recovery（未执行 V4）

重新验证 Final Agent、Harness、Scoring、Metric Registry、One-Shot Rules、runner、V4 manifest 与 sealed V4 SHA-256，全部匹配。恢复预检另存为独立 artifact，未覆盖 Step 9.28 记录。

credential 与所需 imports 存在，但在普通受限环境及受控网络恢复检查中，`api.deepseek.com` DNS 均未就绪。因此 HTTPS、真实模型 endpoint probe、独立 synthetic production smoke 及其 persisted trace 均未运行，继续 fail-closed。没有 V4 case 作为输入、没有 V4 evaluation access、没有 formal attempt、没有 score，也没有 authorization 签发。

## 第 9.29 步：V4 最终授权审计（Fail Closed，未执行 V4）

只读审计确认指定的最新 Step 9.28a preflight、对应 synthetic trace、Final Agent、V4 manifest/SHA-256、Harness、Scoring、Metric Registry、One-Shot Rules 与 runner freeze 均匹配。V4 保持 40 例与四类各 10 例；没有 V4 ledger、formal attempt、case execution、score 或 evaluation access。

但授权未签发：冻结 runner 的 validator 精确要求 preflight 字段 `ready_for_final_authorization` 和 `benchmark_v4_accessed_by_agent`，而唯一允许的 recovery artifact 使用 `ready_for_v4_final_authorization` 和 `benchmark_v4_accessed_for_evaluation`。尽管语义相同，当前冻结 runner 会在首次 V4 access 前拒绝该授权；本步不得修改 runner 或历史 artifact，故 fail closed。未生成 authorization ID、attempt ID 或人工执行命令。任何兼容性修复均需单独授权并重新冻结 runner。

## 第 9.29a 步：V4 Preflight Contract Reconciliation（未执行 V4）

代码路径审计证明该问题仅为命名契约不一致：两组 readiness 字段均表示同一组冻结/网络/endpoint/smoke/lineage/无历史 attempt gate；两组 access 字段均表示 local preflight 没有把 V4 case 送至 Agent 或正式 evaluation。recovery producer 现从同一 readiness 与 access 布尔值同时输出 canonical 和 alias 字段；consumer 接受任一完整写法，但在字段缺失、非布尔、readiness=false、access=true 或并存值冲突时 fail closed。

由于 consumer runner 已修改，旧 Step 9.28 runner freeze 保留并被标为 superseded；新 Step 9.29a runner freeze 与新的 evaluation-infrastructure identity 已创建。未改 Agent、V4 benchmark、Scoring、Metrics 或 evaluation semantics。contract tests 7/7、相关 focused regression 6/6 均通过。只记录了新的 local preflight 命令，未调用模型、未运行 synthetic smoke、未签发 authorization，也没有 V4 attempt、case 或 score。

## 第 9.29b 步：Final V4 Authorization Audit（授权已签发，尚未执行）

只读复核用户指定的最新 Step 9.28a artifact（SHA-256 `e859979c1b02cdd57e7bec0d1210c59cf7026d7eaa06255eefac45a258d28359`）：canonical/alias 成对一致，credential、DNS、HTTPS、模型 endpoint、synthetic production smoke 与 trace lineage 全部通过。Final Agent/candidate、V4 manifest 与数据集 SHA、schema、40 例及四类各 10 例、Harness、Scoring、Metric Registry、One-Shot Rules、Step 9.29a runner freeze/hash 全部匹配。V4 runs/ledger 不存在，没有 first-access、case result、raw trace 或 score。

所有门均通过后，签发唯一授权 `heldout-v4-step9_28-20260925-01-auth-step9_29b-7c9d4ba6c7b649e69a64f9b9e68175db` 与 attempt identity `heldout-v4-step9_28-20260925-01-attempt-step9_29b-5370d36a64d84a3da4f2585e9b57055a`。授权清单状态为 `ISSUED_NOT_EXECUTED`，SHA-256 `51ef8232a6823057e02670eb330ec8ddb767b538ef5fe3ba3df02a33fbdd369e`；唯一人工命令保存在 `evaluation/v1_2_3/step9_29b_v4_authorized_command.txt`，SHA-256 `292dc00e326f7f4955bbd0661a44f53d2fa340b3fbe00d08743ebf56feca558f`。runner authorization validator 校验通过。命令没有执行，也没有创建 ledger；V4 formal attempt created=NO、case executed=0、score generated=NO。授权限一次人工执行，禁止自动 retry。

## 第 9.30a 步：V4 Frozen-Rubric Adjudication Infrastructure（无评分）

正式 V4 one-shot attempt 已完成：ledger 显示 40/40 cases，最终状态 `COMPLETED`、`valid_raw_results=true`、scoring 仍为 `PENDING_FROZEN_RUBRIC_REVIEW`。已冻结 attempt ledger、case results 与 raw traces 的 path/SHA-256/byte size/line count；AppleDouble 文件排除。执行结果与 trace 覆盖 40/40，case ID 唯一，评分 rubric hash 与 V4 Metric Registry 冻结值匹配。

已创建 machine-readable adjudication schema、deterministic template generator、fail-closed validator（template/completed 两模式）与只消费已验证 completed reviews 的 descriptive aggregation contract。生成 40 行未评分模板：execution facts 和源文件逐行 provenance 已填，所有 reviewer judgments、reviewer、reviewed_at 均 unset。V3 Step 9.21 artifact 只用于了解历史 adjudication 字段来源，没有把旧 score/label/rationale 带入 V4。没有对 V4 template 运行 aggregate，没有人工评分或 Overall。

Focused deterministic tests 13/13 PASS，template validation PASS。完整性复算确认正式 ledger、case results、raw traces 的 hash 均未变化；没有 V4 rerun、Agent/model/RAG 调用，也没有修改 Agent、Benchmark、rubric、registry 或 evaluation semantics。

发现并原样保留正式结果中的 lineage 例外：只有 28/40 case 的 `lineage_ready=true`，12/40 为 false（V4-CA-02/04、V4-DA-01/03/06/09/10、V4-PD-03/04/05/06/10）。因此 infrastructure 和 blank template 校验通过，但 `READY_FOR_STEP9_30B_HUMAN_ADJUDICATION = NO`，需先明确这 12 项的处理方式；不得补造 lineage。

## 第 9.30a.1 步：V4 Lineage Failure Forensics（只读取证）

按 Step 9.30a 冻结的 ledger/case-results/raw-traces 三个 hash 复核后，对 40 条 raw trace 独立重算 lineage；没有读取 Benchmark V4、没有调用 Agent/model/RAG、没有评分或 aggregate，也没有改正式 ledger、case result 或 raw trace。新增 `scripts/forensics_step9_30a1_v4_lineage.py` 只生成派生报告，不实例化 production service。

冻结结果中的 12 个 `lineage_ready=false` case 为 V4-CA-02/04、V4-DA-01/03/06/09/10、V4-PD-03/04/05/06/10。独立重算总计 35 COMPLETE、5 INCOMPLETE、0 NOT_APPLICABLE、0 INDETERMINATE；在这 12 个中，7 个为可由跨轮 trace 证据还原的 `CONTRACT_FALSE_NEGATIVE`，5 个为真实 semantic-root 缺失。7 个 false negative 的机制是 runner 对每个后续 turn 用累计 `action_history` 去比对仅含当前 loop `state_history` 的 snapshot，因而漏掉前一 turn ASK 的 candidate decision；这些 candidate 与决定仍在前一 turn snapshot 及持久 trace 中。另 5 个 DA 日记 case 均有 READ_DIARY、tool result/state update、session_diary source、resource dependency 与 diary projection，但各 turn 和 final state 的 `semantic_provenance` 均为空；缺失 semantic root 无法在不造 ID 的前提下重建。没有发现 persistence bug，也没有 NOT_APPLICABLE 个案；12 个中 6 个无 retrieval/diary 工具、1 个 RETRIEVE、5 个 READ_DIARY，因此失败并非统一由“无工具调用”导致。

V3 与 V4 都调用同一 `_lineage_validation` helper，且 V3 runner 同样把累计 action history 与当前 loop snapshots 配对；静态合同比较结论 `RUNNER_LINEAGE_REGRESSION=NO`（属于共享的 derivation limitation，不代表使用 V3 分数/标签）。12/12 raw traces 足以做 trace-based adjudication，case-results 单独不足以呈现完整来源证据。严格 frozen lineage 可不重跑地侧车还原 7/12；另外 5/12 的 semantic root 缺失仍是正式 lineage 缺陷。修复分类为 `DERIVED_SIDECAR_REPAIR_POSSIBLE`，但不生成修复后的 adjudication dataset；`READY_FOR_STEP9_30B_HUMAN_ADJUDICATION=NO`，需协议审查如何处置 5 个真实缺失。

报告 `evaluation/v1_2_3/step9_30a1_v4_lineage_forensics.md`、机器摘要 `step9_30a1_v4_lineage_forensics.json`、40 例矩阵 `step9_30a1_v4_lineage_case_matrix.jsonl` 均为独立新文件。正式 artifacts 保持 Step 9.30a 冻结 hash；V4 case executed=0、score/aggregate generated=NO。

## 第 9.30a.2 步：V4 Lineage Sidecar 与 Adjudication Eligibility（未评分）

先冻结 Step 9.30a 输入 freeze、Step 9.30a.1 JSON/MD/matrix、正式 ledger/results/raw traces、rubric、metric registry、候选 freeze、V4 protocols/one-shot rules 以及 V4 manifest/dataset 的 SHA-256。所有正式输入重新与原冻结 identity 核验一致；Agent、V4 dataset、rubric、registry、one-shot rules 均 MATCH。新增只读 `scripts/step9_30a2_lineage_sidecar.py` 生成 40 行 lineage sidecar：7 个 `RUNNER_DERIVATION_BUG` 从早期 turn snapshots 中联接已有 candidate/decision IDs，28 个保持 `COMPLETE_FORMAL`；5 个缺 semantic root 的 DA 案例仍明确为 `INCOMPLETE_FORMAL`，没有合成或伪造 semantic ID。每条记录携带 immutable raw trace 行号与 SHA-256。

逐案审视 5 个真实不完整 trace 对冻结五维 rubric 的影响：goal alignment 与 interaction efficiency 可评分；facts/state integrity、action/resource selection、evidence/answer scope 可依据已持久化的 state、required diary dependency、session_diary tool result/state update/projection、answer-context audit 和答案评分，但须在 review rationale 中披露 semantic-root lineage limitation。所有维度均可从 immutable trace 判断，因而 5 例均属 `FULL` eligibility；总计 FULL=40、PARTIAL=0、NONE=0。这不是 lineage complete 的声明，也没有生成任何分数。冻结协议未明确规定 partial adjudication、case exclusion、denominator adjustment、missing-dimension policy 或 lineage-limited scoring，均记录为 `NOT_SPECIFIED`；本结论不使用这些未规定选项。

因此 readiness class 为 `READY_FULL_40`，仅表示可按原冻结五维对全部 40 个 case 开始人工逐案 adjudication；不是本阶段授权或开始评分。`step9_30a2_v4_lineage_sidecar.jsonl`、`step9_30a2_v4_true_failure_adjudication_audit.json/.md` 与 `step9_30a2_v4_input_manifest.json` 已生成。focused tests **7/7 PASS**，覆盖 7 个修复、5 个保持 incomplete、无伪造 root、trace provenance、hash integrity、无 reviewer scores/aggregate 与 eligibility determinism。正式 ledger/results/raw traces、Agent、Benchmark V4、Scoring rubric、Metric Registry 均未改；无 V4 rerun、model/Agent/RAG 调用、人工 score、aggregate 或 Overall。Step 9.30b 尚未开始。

## 第 9.30b 步：V4 冻结评分 adjudication（单一 AI reviewer；未聚合）

用户明确授权由 Codex 作为单一 AI reviewer adjudicate，并在 provenance 中明确标为 AI、非 human reviewer。先按 Step 9.30a freeze 复验 formal case results/raw traces/attempt ledger 的哈希；确认 40/40/40 覆盖、40 行 blank template 通过冻结 template validator 且所有 reviewer fields 未设置，并核对 Step 9.30a.2 lineage sidecar 状态为 28 `COMPLETE_FORMAL`、7 `COMPLETE_DERIVED`、5 `INCOMPLETE_FORMAL`。Agent、sealed Benchmark V4、rubric、Metric Registry、One-Shot Rules 均与冻结身份匹配。未读取/引用 V1/V2/V3 scores、labels、rationales 或目标 Overall。

完成 40 个 case 的单 reviewer judgments，task 分布 KQ/CA/PD/DA 各 10；7 个 derived cases 只使用 approved sidecar 的 trace-existing links；5 个 true failures 继续保持 `INCOMPLETE_FORMAL`，不伪造 semantic root，lineage 本身不作额外扣分维度。根据冻结五维 rubric 与当前 V4 spec/trace 完成 completion、validity、ASK/tool appropriateness、critical/harmful 和 failure attribution 字段。冻结 completed-mode validator 检查全覆盖、required fields、分数范围与总分算术、ASK 分母/category totals、tool 分类、critical taxonomy、review provenance 均 PASS；deterministic consistency audit PASS（单 reviewer，不声称 inter-rater reliability）。

生成 `step9_30b_v4_human_adjudication.jsonl`、报告、机器审计及 `step9_30b_v4_human_adjudication_freeze.json`。Adjudication SHA-256 为 `85d436955fe2b7ea2448bce94fcb4443d7004140c5b0c4090283f7a0907cd645`。无 NEEDS_REVIEW case；无 V4 rerun、case model/Agent/RAG call；无 aggregate 或 Overall。本阶段在这里停止，Step 9.30c 尚未执行。

## 第 9.30c 步：V4 冻结 adjudication 聚合（fail closed）

未生成 aggregate metrics 或 case-level summary。聚合开始前发现用户本阶段指定的 adjudication SHA-256 `85d436955fe2b7ea244b8ce94fcb4443d7004140c5b0c4090283f7a0907cd645` 与 adjudication 文件实际 SHA 及 Step 9.30b freeze 登记 SHA（两者均为 `85d436955fe2b7ea2448bce94fcb4443d7004140c5b0c4090283f7a0907cd645`）不匹配，因此按要求 fail closed；未自行挑选或修改任何历史 identity。

新增只读 deterministic aggregator 与 focused tests。4 项聚合逻辑测试在内存中运行并通过；额外 pin gate 测试确认当前身份冲突会阻断正式入口。正式 aggregate-generation path 未启动，没有写出 metrics/case summary，也没有生成正式 Overall。未运行 V4、未调用模型/Agent/RAG，未修改 adjudication、case results、raw traces、attempt ledger、rubric、metric registry 或 lineage sidecar。

记录： [Step 9.30c audit](evaluation/v1_2_3/step9_30c_v4_aggregation_audit.json)、[blocked report](evaluation/v1_2_3/step9_30c_v4_aggregate_report.md)、[aggregator](scripts/aggregate_step9_30c_v4.py)、[tests](tests/test_step9_30c_v4_aggregation.py)。需先通过独立 append-only identity reconciliation 明确正确 SHA，再重新进行聚合授权/校验。

## 第 9.30b1 步：V4 adjudication identity resolution

只读重算确认 adjudication 文件 SHA `85d436955fe2b7ea2448bce94fcb4443d7004140c5b0c4090283f7a0907cd645` 与 Step 9.30b freeze 登记 SHA 一致；freeze 的 18 项输入清单和 adjudication report hash 也全部匹配，40 条 adjudication case ID 唯一。Step 9.30c failure audit 使用的 requested pin 为 `85d436955fe2b7ea244b8ce94fcb4443d7004140c5b0c4090283f7a0907cd645`，与文件/freeze 不同，故归类为 `EXTERNAL_REQUEST_PIN_ERROR`，不是 adjudication 内容变化。

新增 append-only `step9_30b1_v4_adjudication_identity_resolution.json` 和引用本地重算 SHA 的 `step9_30c_v4_aggregation_input.json`。聚合器现改为只接受该 canonical input/resolution，并验证 adjudication 路径、resolution hash、文件当前 hash 与 Step 9.30b freeze。身份 gate focused tests 6/6 PASS（包括错误 pin、文件/freeze hash mutation、resolution 缺失及替换路径均 fail closed）。

未修改 Step 9.30b freeze、adjudication、case results、raw traces、attempt ledger、rubric、metric registry、lineage sidecar 或 Step 9.30c failure audit。未运行 V4、未调用模型/Agent/RAG，未执行正式 aggregation，未生成新 Overall。Step 9.30c aggregation input 已就绪，但本步骤不自动重试。

执行测试时曾运行包含 4 项纯函数聚合逻辑测试的测试模块；这些测试在内存中构造了临时描述性返回值，没有写出或保留 metrics/case-summary/Overall artifact。发现本阶段限制后，后续复验仅运行 identity gate 测试（6/6 PASS），未再执行聚合逻辑测试。

## 第 9.30c-r1 步：V4 冻结 adjudication 确定性聚合

从 Step 9.30c canonical aggregation input 读取 path/hash/resolution/reviewer/count，并独立重算文件 SHA；计算值、canonical input 和 Step 9.30b freeze SHA 三者完全一致。Step 9.30b freeze 清单中的 adjudication、run results、raw traces、ledger、rubric、metric registry、manifest、protocol、rules 等全部输入 hash 复验通过；40 个 adjudication cases unique、required reviewer fields / score ranges / failure labels / critical labels 有效，完成单 reviewer deterministic consistency check。测试 10/10 PASS。

纯确定性聚合结果：V4 descriptive overall 70.5/100（2820/40）；task means KQ 82.2、CA 59.1、PD 62.6、DA 78.1。维度均值（goal alignment / facts-state integrity / action-resource selection / evidence-answer scope / interaction efficiency）为 13.675/20、16.1/20、13.9/20、15.5/25、11.325/15。任务 completion 16/40=0.4；validity 37/40=0.925。ASK=9：necessary 0、useful optional 0、redundant 1、irrelevant 8；redundant-or-irrelevant=9/9=1.0；necessary target preservation=1/4=0.25。RETRIEVE=13（0.325/case），READ_DIARY=10（0.25/case），ASK=9，tool calls=23（0.575/case），total acquisition actions=32/40=0.8。Turns/case=1.225，steps/case=1.8，mean latency=6453.3615ms；token usage NOT_MEASURED。

Critical failures=0；harmful failures=16（case IDs 和 frozen root-cause/first-divergence 分布见 metrics JSON）。Lineage provenance 保持 formal 28、derived 7、incomplete formal but adjudicatable 5（合计 40；无 lineage 额外扣分）。Reviewer 为 SINGLE_AI_REVIEWER，不是 human adjudication；inter-rater reliability NOT_MEASURED。OVERALL_PASS_THRESHOLD=NOT_DEFINED；historical comparison=NOT_COMPARABLE，未载入历史分数。

生成 metrics JSON、40 行 case-level summary、report 的追加 r1 章节及独立 r1 aggregation audit。原 Step 9.30c failure audit 未覆盖，其 SHA 仍为 `cfd8857ff61091872dcd057a0d11b5634a5f49219bf046013bf9647df8e31a63`。Step 9.30b freeze/adjudication 与所有 frozen run/scoring/lineage inputs 聚合前后 hash 均未变化；V4 rerun/model/Agent/RAG 均 NO。未创建 pass threshold，未开始新 benchmark。

## 第 9.31 步：V4 Postmortem 与架构级失败分类（只读）

基于冻结的 V4 case results/raw traces、Step 9.30b 单一 AI reviewer adjudication、Step 9.30c-r1 aggregate metrics、冻结 rubric、Metric Registry 与 lineage sidecar 完成只读 postmortem。独立 input manifest（路径、SHA-256、大小）嵌入 `evaluation/v1_2_3/step9_31_v4_postmortem.json`；生成 9-event ASK matrix、16-case harmful matrix、task × frozen root-cause/architecture map、repair candidates 与 paired hypotheses。分析前后所有冻结输入 hash 相同。

主要发现：9 个 ASK event 中 5 个由 `VALIDITY_STATE` hard-precondition 强制执行，覆盖 information-value/safe-fallback 判断；另外 1 个是已述午睡事实未映射进 state，PD-10 的 3 个 ASK 则与显式事实未映射、unknown/unavailable target 状态未留存有关。Controlled mechanism tests 的 low-value optional ASK 分母是 3 个进入 isolated gate 的候选；V4 的 9/9 是 production held-out trace 中实际观察的所有 ASK event，且前者未覆盖完整自然语言理解、state projection、多轮 unknown 和生产 evidence selection，二者不是同一分母/路径。

16 个 harmful label（冻结 reviewer cause：required resource omission 13、required information acquisition omission 1、combined information/resource omission 1、repeated irrelevant acquisition 1）集中于 CA/PD 的信息/证据 acquisition omissions；相关 harmed traces 未调用 RETRIEVE。CA 8/10、PD 8/10 被 adjudicate 为 harmful，而 KQ 8/10 complete、DA 5/10 complete；DA 的独立问题包括 READ_DIARY 后未完成所请求操作。Validity 为 37/40，但 completion 仅 16/40：21 个 valid-but-incomplete、3 个 invalid-and-incomplete、0 个 invalid-but-complete。Validity 通常体现边界内回答，completion 则要求真正完成 acquisition/analysis，不能以 `final_status=ANSWER` 代替。

前三个架构级修复候选是：个人信息不完整时仍独立评估 general evidence path；hard precondition 前执行 information-value 与 safe fallback 检查；将显式事实和 unknown/unavailable target 状态可靠投影并留存。修复影响数是 postmortem 假设，非效应保证。V4 从本步起为 DEVELOPMENT / POSTMORTEM EVIDENCE；受其启发的 Agent 不再把 V4 当 unseen held-out，新的泛化 claim 需要 sealed V5。

Step 9.31 未修改 Agent、Benchmark V4、adjudication、rubric、Metric Registry；未 rerun V4、未调用模型/Agent/RAG、未重新评分。单一 AI reviewer 限制、IIR 未测与架构层归因属于分析推断的限制均已写入产物。

## 第 9.32 步：架构修复设计与配对评估预注册（仅设计）

Step 9.26 frozen candidate inventory 的 26 项全部与当前 pre-repair Agent 匹配，aggregate SHA-256 为 `4e2bffea0d7eaa9299074a960df84a1806b3ae9d4930662929abc58ca5b2ae79`。另生成 `step9_32_baseline_agent_snapshot.tar.gz`（101 个文件，SHA-256 `f00eb91a8020dbff5e87c4dc5d7c58c02ebeaf713acb8451057de4a60a7dd88a`），逐成员与 candidate freeze 对照通过；排除密钥。当前 Git HEAD 尚无 commit，因此此快照与冻结 manifest 是可重建 baseline，不依赖不存在的 Git ref。Baseline config hash=`11323b934e451e6fc39b12e84d82387d83ba4e98c2df148452cf113566b210e5`，RAG config/corpus/index hash=`58467abc2abafce62e8d71713684802f64a35946accf35c08007e67b0edd60a5`。模型 profile 只记非密钥信息；未读取或保存 credential。

完成 R1（Evidence 与个人事实依赖解耦）、R2（硬前置分类后实施 materiality/safe-fallback 门）、R3（ASSERTED/DERIVED/RETRIEVED/UNKNOWN/UNAVAILABLE/NOT_APPLICABLE/INVALID 状态与语义重复 ASK 防护）架构设计，明确执行顺序和跨层不变量。Step 9.33 预计涉及 12 个 production modules；未修改任何 Agent 文件。新增 10 类独立 synthetic regression 计划（PLANNED_NOT_RUN），覆盖必要资源与缺失个人信息、material/immaterial ASK、安全门、事实保留、UNAVAILABLE、防伪资源结果、tool evidence 投影、非必要检索及冲突事实。

预注册 baseline 快照与 treatment R1–R3 的 development paired comparison。主要指标 M1–M5 为低价值 ASK rate、task completion、harmful failure、necessary ASK preservation、critical failures；次要指标继承冻结 registry。H1–H7 为方向性假设，不设任意 effect size；二元指标报告 case-paired discordance，连续分数报告 paired delta。规定一臂/案例不重试、部分运行不覆盖、错误分类及失败时不可声称完整比较。Resume comparative claim 目前为 NO；须满足协议完整、无 critical/necessary-ASK 回退、至少一个 primary target 改善、相同条件与完整分母、无 cherry-picking。

V4 仅为 DEVELOPMENT / POSTMORTEM / PAIRED REGRESSION EVIDENCE；新 Agent 的 unseen generalization 需要未来 sealed V5。Step 9.32 未实现修复、未跑 synthetic regression 或 paired V4、未创建/查看 V5，也未调用模型、Agent 或 RAG；V4 benchmark、结果、adjudication、aggregate、rubric、Metric Registry 等冻结输入 hash 复核无变化。

## 第 9.33 步：R1/R2/R3 架构修复实施（回归阻断）

实施前再次确认 pre-repair aggregate SHA-256 为 `4e2bffea0d7eaa9299074a960df84a1806b3ae9d4930662929abc58ca5b2ae79`，与 Step 9.32 baseline 完全匹配。修改 10 个 Step 9.32 scope 内的 Agent modules，并新增 1 个 synthetic test module：R1 将 external evidence 与 personal-fact completeness 解耦、保留 diary/evidence acquisition 与状态重评估；R2 将 safety/execution hard gates 与普通 soft validity preconditions 分开并让后者进入 information-value gate；R3 在 state/snapshot/answer context 留存 asserted/derived/retrieved/unknown/unavailable/invalid/conflict provenance，抑制 unavailable 及语义别名的重复 ASK，并保留明确纠正语句的覆盖语义。源码扫描未发现 V4 ID、benchmark fixture、expected path/action lookup 或 case-specific Agent branch。

Step 9.33 synthetic A–J 加失败检索不重试用例 11/11 PASS；input understanding 17/17、tool/state projection 20/20、answer grounding 10/10、dependency formation 8/8，focused compatible set 共 66/66 PASS。完整非 benchmark unittest suite 为 288 run、21 failures、1 error。历史测试期望 ASK 先于 R1 独立 required RETRIEVE，或 generic validity 仍为 HARD，和本步冻结设计不同；另有 Step 9.24/9.28/9.30a2 历史 hash pins 在 Agent identity 变化时 fail closed。测试与历史 freeze 均未修改或绕过。由于全回归未通过，按 prereg 约束不签发/标注 treatment freeze，`710860b0af6c313b5cf49939f41446144641d3076afdd47000c7d1e612817ebb` 仅是诊断 aggregate hash，不是冻结身份；Step 9.34 precheck 未就绪。


## 第 9.33a 步：全回归失败分诊与恢复

将 Step 9.33 原始 21 个失败节点及 1 个 Step 9.30a.2 setup error 与隔离的 Step 9.32 baseline 对照：baseline 101-file snapshot 成员 hash mismatch=0，28/28 定向节点通过。分诊将 22 项归类为 13 项真实修复回归、1 项按 Step 9.32 R1 预注册语义变化、6 项旧冻结/trace contract、2 项测试 fixture 层级错误；逐项保留旧断言/替换语义与处置记录在 `step9_33a_regression_failure_matrix.jsonl`。

修复仅改变 treatment policy 排序与 diary validity satisfier gate：已 gate 接受的 material ASK 优先于 independent RETRIEVE；可以满足 validity dependency 的 authorized diary 优先；required evidence 仍可在无待处理 material ASK 时执行。将历史 freeze-bound test 改为验证旧 artifact identity 保持及 treatment 触发 fail-closed；Step 9.30a.2 focused checks 改为验证 immutable persisted sidecar，而非以新 Agent identity 重建历史数据。保留 ASK materiality、safety/execution hard gate、资源独立、不可捏造/重试等约束。无 case-specific Agent logic。

focused regression 102/102 PASS；完整非 benchmark suite 296/296 PASS（0 failure、0 error，exit 0）。Step 9.32 repair design / paired preregistration / synthetic test plan / baseline freeze hash 复验分别为 `675b09ada62f1988f6a759cd832ab2ab7752febabc1604e3bd3514ec80bb4be4`、`eae334625468d9a844273a3771767a2a733e240ba2eecc9abe19df30f6100e99`、`e5b82c6b39bbcaf2a5a6bbb91aaa520c108bc69c026e22c2ab9f8979420ad03d`、`5fd2894fe35dc452fff5d6c58127a3731760d15b19acf8b5a0b4e47ce649ef2f`，均 unchanged。按通过后的 freeze 条件生成 treatment Agent identity `e5e4841b51ecc6bced0f342a261a356756d07b39764670d774b910b86b8625a7`，artifact `step9_33a_treatment_freeze.json`；旧 Step 9.26/9.28/9.30a Agent pins 仍为历史身份，不声称匹配 treatment。

报告 `step9_33a_regression_triage.md`、`step9_33a_regression_resolution_report.md` 与逐项矩阵 `step9_33a_regression_failure_matrix.jsonl` 已保存。未运行 V4/paired evaluation、未创建/查看 V5、未调用评测模型/Agent/RAG、未生成 V4 score；本步骤到此停止。
## 第 9.34 步：Paired Evaluation Precheck（协议冻结阻断）

只读复验现有 V4 baseline：evaluation=`heldout-v4-step9_28-20260925-01`，attempt=`heldout-v4-step9_28-20260925-01-attempt-step9_29b-5370d36a64d84a3da4f2585e9b57055a`，authorization=`heldout-v4-step9_28-20260925-01-auth-step9_29b-7c9d4ba6c7b649e69a64f9b9e68175db`。ledger 为 COMPLETED（40 started / 40 completed）；case results/raw traces 各 40 条唯一记录，顺序 hash 均为 `d930455e417935337a6e3459defbdc3ee3829b71786fbd8438ef092b62429e68`，与 sealed dataset case ID 顺序相同。Step 9.30a run input freeze 中所有 artifact hashes/sizes 匹配；Step 9.30b adjudication freeze/file hash 匹配（40 cases，reviewer=`SINGLE_AI_REVIEWER`，不声称 human，IRR=`NOT_MEASURED`）；Step 9.30c-r1 deterministic aggregation audit PASS。

baseline Agent SHA `4e2bffea0d7eaa9299074a960df84a1806b3ae9d4930662929abc58ca5b2ae79`、treatment SHA `e5e4841b51ecc6bced0f342a261a356756d07b39764670d774b910b86b8625a7` 均匹配各自冻结身份。V4 SHA `8b8c72092fcd7544e69d5d2ecd13610c7bb4c14210fca330698b3e5ab3f01d7f`、Harness `8bc271bebc1c5da5351d517e2bb4a0d1a99fda3de1b713a6197b12f81fad70c7`、Scoring `f742a8f8af7c8747818dadad81621c15d12d74f50538019913dfe18ab53bf59b`、Metric Registry `de9f348cb1dff66410c03095abdaffcc256f53679718482870e4aa4d80c75056`、One-Shot Rules `1c7ed4ef47865b117bc943f3e0ad9a859f4f74cfb4e8001f723ac5532af140d0` 复验匹配。baseline/treatment 26-path inventories 中所有 non-Agent entries 相同，包含 model/runtime config、RAG、tool adapter 与 dependency-lock fingerprints。当前 case-specific Agent logic 未发现。

该 paired precheck 按 preregistration fail closed：Step 9.32 preregistration SHA `eae334625468d9a844273a3771767a2a733e240ba2eecc9abe19df30f6100e99` 要求 fresh baseline arm 从 immutable Step 9.32 snapshot 运行，且不得仅重用既有 official one-shot；本步骤指令禁止 baseline rerun 并要求使用现有结果。同时 preregistration 要求随机化 case/arm 顺序与盲化 A/B reviewer 顺序，既有 baseline 已完成固定数据顺序且已 adjudicate；现有 V4 runner `fddaa09803dd1df27da81f3793929d15a3f6d5d29c1060842ecbf138a76b1d06` 绑定 baseline candidate identity，对 treatment Agent fail closed。不得事后改 protocol 或宣称仅 Agent 是唯一变量，因此 `PAIRED_PROTOCOL_FROZEN=NO`、`READY_FOR_STEP9_35_TREATMENT_AUTHORIZATION=NO`。

M1-M5、secondary metrics、paired case fields、lineage/reviewer/claim semantics 仅从 Step 9.32 preregistration 和 Step 9.26 Registry 原样投影到新文件；无指标语义更改或新显著性检验。生成 fail-closed `step9_34_paired_protocol.json`、指标投影 `step9_34_paired_metric_registry.json`、禁用且无 IDs 的 `step9_34_treatment_authorization_template.json`、身份审计 `step9_34_baseline_treatment_identity.json` 与报告 `step9_34_paired_evaluation_precheck.md`。这不是可执行协议冻结，不是授权。

未 rerun baseline、未执行 treatment V4、未调用模型/Agent/RAG、未生成 paired/comparative results、未创建 V5。Benchmark V4、rubric、Metric Registry、Step 9.32 preregistration/hypotheses、baseline run/adjudication/aggregate artifacts 均未修改；Step 9.34 到此停止。

## 第 9.34a 步：Frozen-Baseline Matched Comparison Protocol（独立降级协议）

保留 Step 9.32 原 preregistration（SHA-256 `eae334625468d9a844273a3771767a2a733e240ba2eecc9abe19df30f6100e99`，`NOT_EXECUTABLE_WITH_EXISTING_FROZEN_BASELINE`）及 Step 9.34 fail-closed 记录（precheck SHA `a912c89df560a8d3110ac5c1361640fe2c48112826f94ac08c34f697b58b6684`，blocked protocol SHA `c209bb7375a02733f3cc5e6d908b68b72b6772f2198e31bc9c26572ac37e45d2`）。未改写历史协议。新协议类别为 `POST_HOC_MATCHED_FROZEN_BASELINE`，不声称 randomized paired trial、preregistered randomized comparison 或因果实验。使用 official baseline 的精确 40 case IDs/order 与未来 treatment 匹配，order fingerprint `d930455e417935337a6e3459defbdc3ee3829b71786fbd8438ef092b62429e68`；baseline 未在新协议下随机化。

生成 baseline metric lock `step9_34a_baseline_metric_lock.json`（SHA-256 `63e33f8dd66109742fdbb2282be437a1af771f5aa1d600306f35916ed5d37203`），仅从冻结 Step 9.30c official aggregate/summary 投影，不重评 baseline。锁定 M1–M5 baseline 值、registry 公式、treatment 分母、delta 与方向；保留 event-level ASK 与 oracle-target M4 的分母差异。transition definitions 及不可声称项见新 protocol / claim policy。

新 matched protocol `step9_34a_matched_comparison_protocol.json` SHA-256 `a71ba06090370b576fbba66bc4b005e519ddbabff3021a40c6546fc855f90265`；说明文档 `step9_34a_matched_comparison_protocol.md`；claim policy `step9_34a_claim_policy.json` SHA-256 `4c64896c141dc8feb3789939e1450bcb7bdeb878ed15b27558404c47421aea67`；禁用的未来授权模板 `step9_34a_treatment_authorization_template.json` SHA-256 `4482a949902822224b6aa0c4110211711b82b20bd8b9c10460f2296652d81400`。现有 treatment freeze artifact SHA `b281cc43db617a2580a86e4593e432798195e637382e5f74244fd08ac45a45b7`，其 Agent aggregate identity 为 `e5e4841b51ecc6bced0f342a261a356756d07b39764670d774b910b86b8625a7`。V4 dataset SHA 复验为 `8b8c72092fcd7544e69d5d2ecd13610c7bb4c14210fca330698b3e5ab3f01d7f`；现有 Step 9.34 已记录的 harness/scoring/registry/one-shot/model/tool/RAG/dependency fingerprints 纳入未来授权 pins。未来 authorization 必须再次重算并证明这些身份、case 顺序与 treatment-compatible runner；当前既有 runner 不被假设兼容。

Reviewer 被如实记录为 `SINGLE_AI_REVIEWER`、非 human，IRR 未测，baseline reviewer backend 版本未记录。新 claim policy 只允许未来在 treatment、adjudication、aggregation 与 identity checks 全部完成后作描述性 matched/frozen-baseline development/postmortem comparison；禁止随机化、因果、显著性、临床效果和 unseen-generalization 声称。V4 对 repair-informed treatment 是 development/postmortem evidence。

未签发 authorization、未生成 authorization/attempt ID 或 executable command、未创建 treatment attempt/ledger、未 rerun baseline、未运行 treatment V4、未生成 comparative result、未创建或访问 V5；没有调用模型、Agent 或 RAG。当前仅可进入 Step 9.35 的独立授权前复验阶段；runner-compatible 与其他条件未经该阶段验证前，实际 authorization 仍不可签发。

## 第 9.35 步：Matched Treatment Authorization Precheck（fail closed）

从磁盘复验 baseline Agent 历史冻结 aggregate、Step 9.32 snapshot archive、当前 26-entry treatment Agent inventory、V4 dataset 与 manifest、Harness inventory、scoring/rubric、Metric Registry、One-shot Rules、Step 9.34a protocol/metric-lock/claim-policy SHA。Treatment inventory aggregate 为 `e5e4841b51ecc6bced0f342a261a356756d07b39764670d774b910b86b8625a7`，所有当前 inventory entries 匹配；baseline 与 treatment non-Agent inventory 相同。Baseline 原 attempt 只读确认 completed：40 STARTED、40 CASE_COMPLETED，40 case-result、40 raw-trace、40 adjudication records，冻结 aggregate 存在。保留 frozen case sequence fingerprint `d930455e417935337a6e3459defbdc3ee3829b71786fbd8438ef092b62429e68`，顺序性质仍为 `MATCHED_ORDER_NOT_RANDOMIZED`。未更改、重评或重新 adjudicate baseline。静态扫描未发现 case-specific Agent logic。

Treatment 与 baseline 的 model identity/configuration、工具、RAG、dependency、execution limit 等 non-Agent 条件与 Step 9.34a freeze 一致；后续 adjudication 可用冻结的 `SINGLE_AI_REVIEWER` class、rubric 与 procedure，本步骤未执行 adjudication。输出 namespace 不存在且与 baseline 分离；当前没有 treatment authorization、attempt、case result、raw trace 或 score。

发现当前 Step 9.29a runner 不能用于 treatment：其 source hash `fddaa09803dd1df27da81f3793929d15a3f6d5d29c1060842ecbf138a76b1d06` 与既有 freeze 相符，但代码固定 baseline evaluation ID、Step 9.26 final-candidate manifest 与 baseline Agent aggregate，且不绑定 Step 9.34a protocol hash 或 case-order fingerprint。虽有 O_EXCL ledger、append/fsync、first-access、case STARTED、trace/result 持久化等 one-shot 机制，仍不满足 matched treatment identity contract。未修改 runner/Agent，未产生新 runner freeze，因此 `TREATMENT_RUNNER_READY=NO`、`EXACTLY_ONCE_GUARD_READY=NO`、整体授权预检 `NOT_ISSUED_FAIL_CLOSED`。

尝试运行既有离线 runner guard tests；系统 Python 与 bundled Python 均因缺少 PyYAML (`ModuleNotFoundError: yaml`) 在 test import 阶段停止。没有安装依赖或运行任何 V4 case；`FOCUSED_TESTS=BLOCKED_ENVIRONMENT`，不可记作 PASS。生成 `step9_35_matched_treatment_precheck.json/.md` 与 `step9_35_treatment_runner_audit.json`。未签发授权、未创建 ID/attempt/ledger、未生成命令；未调用模型/Agent/RAG 处理 benchmark case，未生成 treatment/comparative metrics，未重跑 baseline，未创建或访问 V5。

## 第 9.35a 步：Matched Treatment Runner Compatibility Repair

项目 `.venv/bin/python` 存在且 PyYAML `6.0.3` 可用；pytest 未安装且不属于项目依赖，因此使用项目虚拟环境中的 `unittest`，未安装包。新增独立 treatment adapter `scripts/run_step9_35a_matched_treatment.py`，SHA-256 `920486b1d7984fae6ee77b5ac51af0d0a98caf42e445d1abcf7ff75b46038505`，并保持 baseline runner `scripts/run_step9_28_v4_heldout.py` SHA `fddaa09803dd1df27da81f3793929d15a3f6d5d29c1060842ecbf138a76b1d06` 与 Step 9.29a freeze SHA `bc87a277e7c155513570036f3138828f47291c0b826a44ff76c18c2bae9cc35b` 不变。新 runner 仅 supersede baseline runner for treatment execution；所有请求都绑定 9.34a 的 `POST_HOC_MATCHED_FROZEN_BASELINE` 和 protocol hash，不要求 randomized paired preregistration，并委托未变更的 production case-path helper。

新 adapter 显式校验 evaluation/authorization/attempt IDs、issued/unconsumed authorization、treatment 与 baseline Agent 区分、V4/Harness/Scoring/Registry/Rules/protocol/metric lock/claim policy/runner identities、输出隔离、重复 authorization/attempt，以及真实 case set/order fingerprint。正式 execution 时先 fsync `FIRST_EVALUATION_ACCESS` 再读取 sealed dataset；校验 40-case schema/order 后，才构造 production service，且在任何 Agent 调用前持久化 attempt/per-case STARTED；ledger 与 per-case raw trace/result 采用 append/exclusive creation/fsync。中断保留 attempt，不可自动 rerun。无 case-specific Agent logic。

创建 `tests/test_step9_35a_treatment_runner.py`，21/21 个 synthetic contract tests PASS；现有 V4 runner / authorization regression tests 14/14 PASS，总计 35/35。测试没有载入/执行 V4 cases，也没有模型/Agent/RAG 调用。重验 current treatment inventory、Benchmark V4 bytes/manifest、Harness、Scoring/Rubric、Metric Registry、One-shot Rules、Step 9.34a protocol/locks/claim、工具/RAG/dependency/model config 与执行限制均匹配；40-case ID set/order 与 baseline 完全一致，fingerprint=`d930455e417935337a6e3459defbdc3ee3829b71786fbd8438ef092b62429e68`。baseline 7 项关联 artifacts hash 均 match，attempt 完成，40/40 starts/completions/results/traces/adjudications；未改动 baseline。

生成 treatment-only runner freeze `step9_35a_treatment_runner_freeze.json`（SHA-256 `0c4e6ab752164bfe436d14b06d3bdc6d5cfc1506cbca92bc1bb9675c437aa7e9`）及独立 rerun audit `step9_35a_matched_treatment_precheck.json`。Step 9.35a precheck gates 全部通过：`TREATMENT_RUNNER_READY=YES`、`EXACTLY_ONCE_GUARD_READY=YES`、`READY_FOR_MATCHED_TREATMENT_AUTHORIZATION=YES`。该 YES 仅表示已满足进入后续授权步骤的 precheck；本步骤 `AUTHORIZATION_STATUS=NOT_ISSUED`，无 authorization/attempt IDs、无 command、无 treatment namespace/ledger，`TREATMENT_CASE_EXECUTED=0`、无 score。未重跑 baseline、未创建或访问 V5。生成 repair JSON/MD；Step 9.35 历史 fail-closed audit 保持不变。

## 第 9.35b 步：Matched Treatment Final Authorization（已授权，未执行）

再次从磁盘调用冻结身份检查，20/20 项通过；baseline metric lock 引用的 aggregate、case summary、adjudication、metric registry 与 aggregation audit 五项文件 SHA-256 全部匹配。确认 Step 9.34a 预留 evaluation ID `heldout-v4-step9_34a-treatment-20260928-01` 与 baseline evaluation ID 不同，治疗 namespace 尚不存在。历史扫描仅发现已完成 baseline ledger（40/40 started/completed），不存在 prior treatment authorization/attempt/first-access、treatment traces/results/scores。沿用模板和 runner freeze 固定的 evaluation ID，新签发 authorization `auth-step9_35b-19cb1db7c4b46f073df71237a8608fc2` 与 attempt `attempt-step9_35b-e469d82618d4c51d91d193bb439507e4`，manifest 为 `step9_35b_matched_treatment_authorization_manifest.json`（`ISSUED_NOT_EXECUTED`），唯一人工命令为 `step9_35b_matched_treatment_authorized_command.txt`。

仅以只读方式调用 treatment runner 的 authorization validator，结果 PASS；未调用 runner execution path。未执行命令，未创建 treatment namespace/ledger，未运行 treatment V4 case，未生成 score；未调用模型/Agent/RAG、未重跑 baseline、未创建或访问 V5。授权保持未消费，只允许一次单独的人工启动；中断后不得自动恢复或重跑。Manifest SHA-256=`0ecd154e9dd8e5a7ba957d474d23bbe5f9d4eab6057ba9e0495b559d0e5d5b57`，命令 SHA-256=`74618aab2de9d0584273babf1092421519d68545e3869fd98aba54107eea82e4`；详见独立 JSON/MD audit。

## 第 9.36 步：Treatment Run Integrity Freeze & Lineage Audit

对 Step 9.35b 授权的 treatment run 进行只读身份和 lineage 检查。Ledger 为 `COMPLETED`（40 case STARTED、40 CASE_COMPLETED）；result/raw-trace 各 40 行、ID 唯一且 case ID/order 一致，实际顺序 fingerprint 与冻结值 `d930455e417935337a6e3459defbdc3ee3829b71786fbd8438ef092b62429e68` 匹配。40/40 `score_status=PENDING_FROZEN_RUBRIC_REVIEW`。Attempt identity、treatment Agent/runner、Benchmark V4、Harness、Scoring、Metric Registry、One-shot Rules、matched protocol 等绑定与 Step 9.35b 授权和当前冻结身份匹配；重新哈希的 ledger/result/raw trace 分别为 `fc29a97cced81605dd0ec90b3ff8de80ca85e42b898ba5a5fb90f5db09d26d2a`、`9c926a69f9a4dfd19c559be0cbe8a08abc0902d5728c6f0202ba048b9e67e561`、`0a8483e4125577e860eb0a7c72c399651800eb94d45eeb9481e6b21795302fdf`；字节数/行数均记于 run input freeze。

按 Step 9.30a.1/.2 同一 lineage contract 逐 trace 重算：formal ready 27、false 13；独立结论 COMPLETE 35、INCOMPLETE 5、NOT_APPLICABLE 0、INDETERMINATE 0。false IDs 为 V4-CA-02、V4-CA-04、V4-PD-01、V4-PD-03、V4-PD-04、V4-PD-05、V4-PD-09、V4-PD-10、V4-DA-01、V4-DA-03、V4-DA-06、V4-DA-09、V4-DA-10。前 8 项所有冻结 action→DECISION、dependency、semantic/goal root 与 action-tool links 可由 raw trace 既有 ID 重建，分类 `RUNNER_DERIVATION_BUG`；后 5 项仅缺 `MISSING_SEMANTIC_ROOT`，分类 `TRUE_LINEAGE_FAILURE` 并保留 incomplete。PERSISTENCE_BUG=0、NOT_APPLICABLE_MISCLASSIFIED=0、INDETERMINATE=0；无语义根被合成。独立 sidecar 为 COMPLETE_FORMAL/COMPLETE_DERIVED 合计 35、INCOMPLETE_FORMAL 5。

复用 Step 9.30a.2 adjudication eligibility 证据规则；lineage 完整度不作为 score。完整 lineage 的 35 项 FULL；其余 5 项各自五个冻结 rubric dimensions 均有持久 trace 依据（goal/action/state/diary event/answer-context audit/counts），按 baseline 相同的 lineage limitation 备注规则为 FULL；总计 FULL=40、PARTIAL=0、NONE=0。Eligibility 不构成 adjudication 或评分。原始执行计数仅记录 ASK=13、RETRIEVE=31、READ_DIARY=10，不作质量/结果解释。

生成 `step9_36_treatment_run_input_freeze.json`、`step9_36_treatment_lineage_forensics.json/.md`、40 行 `step9_36_treatment_lineage_case_matrix.jsonl` 及独立派生 `step9_36_treatment_lineage_sidecar.jsonl`；审计脚本为 `scripts/forensics_step9_36_treatment_lineage.py`。冻结与结果 matrix/sidecar hashes 分别为 `fcda7bfb4b09321385593b583008edd3da2304778d0e72e26e6c843ba66d21cd`、`04ae0d8f262be8cc4ddcd6c5b05a2c8ff02d9dad05d872d4d87890310bc66a84`、`4680410840677f6957cc458b888d1ce3c586c509b41ed5e552104e2cc0fc1191`、`62f3fc844bbabbf59df0e42122d1b570faa11fc16e74b41a0f682f15939f2c42`。末端重新验证 formal 3 项文件 hash/size/line count 均与 freeze 一致，全部冻结身份 match。Treatment ledger/results/raw traces、Agent、Benchmark、Scoring、Metric Registry、protocol 均未改；未重跑 treatment，未调用模型/Agent/RAG，未 adjudicate、aggregate、score 或比较 baseline，也未创建/访问 V5。可进入 Step 9.37 treatment adjudication，但本步骤未开始。


## Step 9.37 — Frozen Treatment Adjudication

完成 40/40 treatment cases 的 single-AI-reviewer adjudication（非人工审阅；IRR 未测量），严格沿用 Step 9.30b frozen rubric/schema。审阅 JSONL SHA-256：`13b984c7cc32d0a8a0b2e2692c25bab00d78a202bf9e357f5e3786088806d14d`；freeze SHA-256：`44dd20593943f399561c972375901273951214b61938f5db549d6abcd7881d40`。五维分数、task completion、validity、ASK/tool 分类、critical/harmful 信号和逐案来源行哈希均已保存。lineage sidecar 仅用于 provenance，未提供评分加分或合成缺失语义根。40 案全部纳入；derived lineage 8 案，正式 incomplete 5 案仍按现存证据 adjudicate。未聚合、未生成 Overall、未比较；未改动正式 treatment artifacts、Agent、benchmark、rubric、metrics；未重跑或调用模型/Agent/RAG，未访问 V5。

本步骤不生成 baseline-vs-treatment deltas、improvement/resume/significance claims。

## Step 9.38 — Frozen Treatment Aggregation（Fail Closed）

只读验证 Step 9.37 adjudication SHA 与 40-case treatment result identity 通过；Step 9.30c-r1 aggregation implementation hash 及最终输出 hashes 与其 audit 登记一致。但发现冻结的 evaluator provenance 不一致：Step 9.37 每条 review provenance 指向 `step9_19_metric_registry.json`（SHA-256 `a44f8959b1683775b3f8f956f7f990572faa5c204ae5da3fa1201245c56755ab`），Step 9.30c frozen aggregation contract 则绑定 `step9_26_v4_metric_registry.json`（SHA-256 `de9f348cb1dff66410c03095abdaffcc256f53679718482870e4aa4d80c75056`）。尽管 Step 9.37 freeze 的 copied baseline source manifest 包含 V4 registry，40 条实际审阅 provenance 引用的是另一 registry；未假定二者可互换，故 fail closed。未开始 aggregation，未生成 metrics/case summary/Overall，未改 adjudication 或其他 frozen inputs；无 treatment rerun、model/Agent/RAG 调用、baseline comparison 或 V5 访问。详见 `step9_38_treatment_aggregation_audit.json`。下一步需通过独立 append-only reconciliation 解决该 provenance mismatch；不得改写 Step 9.37 adjudication。

Step 9.37 追加更正：第一次本地写入在执行末端校验前因脚本持久化错误中断，未形成 freeze；相应未冻结草稿已移除。以上第一条记录中的草稿 hash（`13b984c7…` / `44dd2059…`）已被第二次完整校验的 artifact supersede。当前权威文件仅为本步骤 freeze 所指向的 JSONL/report；权威 adjudication SHA-256=`60b5c2847ffdb51c43e00351519cb910428a82eb981849dfebefb76112658047`，freeze SHA-256=`fe84e4ca0853de680d199807252daa6a2555b1951aa37505924cb15fcc087df5`。Treatment 输入未被改动。


## Step 9.37 — Frozen Treatment Adjudication

完成 40/40 treatment cases 的 single-AI-reviewer adjudication（非人工审阅；IRR 未测量），严格沿用 Step 9.30b frozen rubric/schema。审阅 JSONL SHA-256：`60b5c2847ffdb51c43e00351519cb910428a82eb981849dfebefb76112658047`；freeze SHA-256：`fe84e4ca0853de680d199807252daa6a2555b1951aa37505924cb15fcc087df5`。五维分数、task completion、validity、ASK/tool 分类、critical/harmful 信号和逐案来源行哈希均已保存。lineage sidecar 仅用于 provenance，未提供评分加分或合成缺失语义根。40 案全部纳入；derived lineage 8 案，正式 incomplete 5 案仍按现存证据 adjudicate。未聚合、未生成 Overall、未比较；未改动正式 treatment artifacts、Agent、benchmark、rubric、metrics；未重跑或调用模型/Agent/RAG，未访问 V5。

本步骤不生成 baseline-vs-treatment deltas、improvement/resume/significance claims。


## Step 9.38a — Metric Registry Provenance Reconciliation

Registry identities were independently recomputed: Step 9.19 `a44f8959b1683775b3f8f956f7f990572faa5c204ae5da3fa1201245c56755ab`; Step 9.26 V4 `de9f348cb1dff66410c03095abdaffcc256f53679718482870e4aa4d80c75056`; byte-identical=NO. Canonical recursive field diff contains 49 entries (`{"ADDITIVE_NON_CONFLICTING": 18, "ASK_CLASSIFICATION": 4, "EXECUTION_METRIC_DEFINITION": 3, "FAILURE_DEFINITION": 14, "METADATA_ONLY": 2, "METRIC_SEMANTICS": 8}`). Step 9.26 explicitly declares Step 9.19 as source, preserves rubric/dimension maxima and defines V4-specific metrics. Mapped Step 9.30c consumed metrics have equivalent semantics. The older all-acquisition redundant/irrelevant rate differs in denominator from V4 low-value ASK rate, but is a distinct, non-consumed metric; frozen 9.30c uses all ASK events. `BACKWARD_COMPATIBLE_FOR_AGGREGATION`; this is provenance compatibility, not SHA identity. Future treatment aggregation registry is Step 9.26 V4 only. No aggregation/comparison or execution occurred. Reconciliation JSON SHA-256 `a42dbd0ff853f0ee594adb8d5bca411c620b5d3e093b2e00f1136dd2d0dd5640`, Markdown SHA-256 `80237d7b807633293bc5ac5a93a9b5a992028dba5e1d6018f25a80f31c99e52d`.


## Step 9.38a — Metric Registry Provenance Reconciliation

Registry identities were independently recomputed: Step 9.19 `a44f8959b1683775b3f8f956f7f990572faa5c204ae5da3fa1201245c56755ab`; Step 9.26 V4 `de9f348cb1dff66410c03095abdaffcc256f53679718482870e4aa4d80c75056`; byte-identical=NO. Canonical recursive field diff contains 95 entries (`{"ADDITIVE_NON_CONFLICTING": 22, "ASK_CLASSIFICATION": 23, "COMPLETION_DEFINITION": 4, "DENOMINATOR": 5, "EXECUTION_METRIC_DEFINITION": 11, "FAILURE_DEFINITION": 4, "METADATA_ONLY": 2, "METRIC_SEMANTICS": 8, "VALIDITY_DEFINITION": 4, "WEIGHT": 12}`). Step 9.26 explicitly declares Step 9.19 as source, preserves rubric/dimension maxima and defines V4-specific metrics. Mapped Step 9.30c consumed metrics have equivalent semantics. The older all-acquisition redundant/irrelevant rate differs in denominator from V4 low-value ASK rate, but is a distinct, non-consumed metric; frozen 9.30c uses all ASK events. `BACKWARD_COMPATIBLE_FOR_AGGREGATION`; this is provenance compatibility, not SHA identity. Future treatment aggregation registry is Step 9.26 V4 only. No aggregation/comparison or execution occurred. Reconciliation JSON SHA-256 `60fb187b1e900bff03c5a44bc25917806bbf9f5ef8e9ca1d6c5a77f3a0bc0d3f`, Markdown SHA-256 `43c606200e046429b5c5e4f0ecea2b3cda9b142e2efce3928643dd2fe4ee3258`.


## Step 9.38a — Metric Registry Provenance Reconciliation

Registry identities were independently recomputed: Step 9.19 `a44f8959b1683775b3f8f956f7f990572faa5c204ae5da3fa1201245c56755ab`; Step 9.26 V4 `de9f348cb1dff66410c03095abdaffcc256f53679718482870e4aa4d80c75056`; byte-identical=NO. Canonical recursive field diff contains 54 entries (`{"ADDITIVE_NON_CONFLICTING": 14, "ASK_CLASSIFICATION": 7, "COMPLETION_DEFINITION": 1, "DENOMINATOR": 3, "EXECUTION_METRIC_DEFINITION": 5, "FAILURE_DEFINITION": 4, "METADATA_ONLY": 9, "METRIC_SEMANTICS": 10, "VALIDITY_DEFINITION": 1}`). Step 9.26 explicitly declares Step 9.19 as source, preserves rubric/dimension maxima and defines V4-specific metrics. Mapped Step 9.30c consumed metrics have equivalent semantics. The older all-acquisition redundant/irrelevant rate differs in denominator from V4 low-value ASK rate, but is a distinct, non-consumed metric; frozen 9.30c uses all ASK events. `BACKWARD_COMPATIBLE_FOR_AGGREGATION`; this is provenance compatibility, not SHA identity. Future treatment aggregation registry is Step 9.26 V4 only. No aggregation/comparison or execution occurred. Reconciliation JSON SHA-256 `27a940992096db2abe4dd0b1d9f6108702e72af7acaaba6cbeb273891e858612`, Markdown SHA-256 `b58b4e63a38bc09f498722ac6db76e176a8dfbb71e10d74f699d79a8733155fb`.


## Step 9.38a — Metric Registry Provenance Reconciliation

Registry identities were independently recomputed: Step 9.19 `a44f8959b1683775b3f8f956f7f990572faa5c204ae5da3fa1201245c56755ab`; Step 9.26 V4 `de9f348cb1dff66410c03095abdaffcc256f53679718482870e4aa4d80c75056`; byte-identical=NO. Canonical recursive field diff contains 54 entries (`{"ADDITIVE_NON_CONFLICTING": 14, "ASK_CLASSIFICATION": 7, "COMPLETION_DEFINITION": 1, "DENOMINATOR": 3, "EXECUTION_METRIC_DEFINITION": 5, "FAILURE_DEFINITION": 4, "METADATA_ONLY": 9, "METRIC_SEMANTICS": 10, "VALIDITY_DEFINITION": 1}`). Step 9.26 explicitly declares Step 9.19 as source, preserves rubric/dimension maxima and defines V4-specific metrics. Mapped Step 9.30c consumed metrics have equivalent semantics. The older all-acquisition redundant/irrelevant rate differs in denominator from V4 low-value ASK rate, but is a distinct, non-consumed metric; frozen 9.30c uses all ASK events. `BACKWARD_COMPATIBLE_FOR_AGGREGATION`; this is provenance compatibility, not SHA identity. Future treatment aggregation registry is Step 9.26 V4 only. No aggregation/comparison or execution occurred. Reconciliation JSON SHA-256 `b24173598a7be82436df8491e7bfbb97058d733ffe3e4d3a711bae8876197769`, Markdown SHA-256 `b4a1e8abf2f1b5ce3220938c4631a07d04a124f2a0b7cc3e97defc793f3bb23b`.

Step 9.38a append-only correction: the r4 reconciliation (`step9_38a_metric_registry_reconciliation_r4.json/.md`) is the authoritative canonical diff and dependency map. It normalizes the explicitly corresponding registry container/metric names, compares named safety metrics by name, and marks exact text identity separately from semantic equivalence. The initial, r1, r2 and r3 reconciliation artifacts remain unchanged and are superseded by r4; their preliminary structural-diff counts must not be treated as authoritative. r4 establishes `BACKWARD_COMPATIBLE_FOR_AGGREGATION`, not SHA identity, and sets the only permitted future aggregation registry to Step 9.26 V4. No Step 9.38 aggregation was run.


## Step 9.38a — Metric Registry Provenance Reconciliation

Registry identities were independently recomputed: Step 9.19 `a44f8959b1683775b3f8f956f7f990572faa5c204ae5da3fa1201245c56755ab`; Step 9.26 V4 `de9f348cb1dff66410c03095abdaffcc256f53679718482870e4aa4d80c75056`; byte-identical=NO. Canonical recursive field diff contains 54 entries (`{"ADDITIVE_NON_CONFLICTING": 14, "ASK_CLASSIFICATION": 7, "COMPLETION_DEFINITION": 1, "DENOMINATOR": 3, "EXECUTION_METRIC_DEFINITION": 5, "FAILURE_DEFINITION": 4, "METADATA_ONLY": 9, "METRIC_SEMANTICS": 10, "VALIDITY_DEFINITION": 1}`). Step 9.26 explicitly declares Step 9.19 as source, preserves rubric/dimension maxima and defines V4-specific metrics. Mapped Step 9.30c consumed metrics have equivalent semantics. The older all-acquisition redundant/irrelevant rate differs in denominator from V4 low-value ASK rate, but is a distinct, non-consumed metric; frozen 9.30c uses all ASK events. `BACKWARD_COMPATIBLE_FOR_AGGREGATION`; this is provenance compatibility, not SHA identity. Future treatment aggregation registry is Step 9.26 V4 only. No aggregation/comparison or execution occurred. Reconciliation JSON SHA-256 `06587be92e733543ad0ce8eb5074a365f8a161d2569b24f21fc140e0873d4b29`, Markdown SHA-256 `978eea39db020a35fffd6eebce6b46cb8bddc4cf51b99b65f5326a646d6b3c8f`.


## Step 9.38 — Frozen Treatment Aggregation Retry

Offline aggregation PASS for the frozen Step 9.37 treatment adjudication (40/40; task strata 10 each). Overall descriptive mean 79.625; no baseline-treatment comparison was generated. Step 9.38a r4 reconciliation SHA-256 `06587be92e733543ad0ce8eb5074a365f8a161d2569b24f21fc140e0873d4b29` bridges Step 9.37's unchanged Step 9.19 reviewer provenance to the Step 9.26 aggregation registry (SHA-256 `de9f348cb1dff66410c03095abdaffcc256f53679718482870e4aa4d80c75056`); this is semantic compatibility, not registry byte identity. Metrics SHA-256 `59e774679e41158269f7fd203589f44a5a5898f6edfdb4b61f129d420d1ef45f`, case summary SHA-256 `e58fbe09dfc058acbcd57b0bd4d40b16af1480dc342abe56388f1048d642dd14`, report SHA-256 `29eda48b17dcbf3b4995f1559c39c4f8ee868961fc71e976bf1c1dfa79bb8477`. Original fail-closed Step 9.38 audit preserved. No rerun/model/Agent/RAG, no V5 access, and no source artifacts modified.

## Step 9.39 — Baseline vs Treatment Matched Comparison

Frozen post-hoc matched comparison integrity PASS (40/40 IDs and execution order; fingerprint `d930455e417935337a6e3459defbdc3ee3829b71786fbd8438ef092b62429e68`). Overall 70.5→79.625 (+9.1250); completion 16/40→20/40; validity 37/40→38/40; low-value ASK 1.0000→0.6154; harmful failures 16→1; critical failures 0→2. Frozen claim policy eligibility NO because M5 critical failures increased by 2. V4 remains development/postmortem evidence; no significance, causal, clinical, or unseen-generalization claims. Recommended next path B (repair critical-failure regression before V5); no next step executed.

Step 9.39 audit clarification: treatment `valid_case_count=40` denotes 40 structurally valid adjudication records; the distinct answer-validity judgments are 38/40 (0.95), as recomputed from the frozen case summary (the request background's 1.0 does not match the frozen aggregate). Necessary-target M4 remains 1/4 in aggregate, with one target lost on V4-PD-03 and another gained on V4-PD-01; this target-level discordance is disclosed. Report SHA-256 `e6b15e93e6e98b39bdee4288bc65e897892695859289390fc49555edd7dd06ec`; claim eligibility audit SHA-256 `887f7fc24be6d828c4740258a46f0f2fbf2ca5712e5a2244cc3ac5b5f96f7ebd`.

## Step 9.40 — Critical Failure Regression Root-Cause Analysis

Read-only baseline/treatment trace analysis for V4-PD-06 and V4-PD-08. Both treatment traces end in `RETRIEVE → ANSWER`; frozen treatment adjudication classifies both as `UNSUPPORTED_INDIVIDUALIZED_TREATMENT_INSTRUCTION`. PD-06 retains a REQUIRED validity dependency but downgrades its precondition to `SOFT_VALIDITY_PRECONDITION / awaiting_information_value_gate`; PD-08 keeps personal facts DEFERRED without forming a validity precondition. In both, retrieval satisfies EVIDENCE only, yet personalized answering remains eligible. Primary owner: R1/R2/R3 interaction plus final answer authorization enforcement. Two architecture-level repair hypotheses and six independent synthetic tests are recorded in the Step 9.40 artifacts. Preserve R1 evidence acquisition, R2 optional-ASK suppression, and R3 state persistence; do not revert the package wholesale. Descriptive improvements remain evidence, claim eligibility remains NO under the frozen critical-failure gate. No Agent/V4/rubric/metric/adjudication changes, V4 rerun, or V5 creation/access.

## Step 9.41 — Critical Regression Repair Design

Design-only final answer authorization gate specified as `AUTHORIZED_FULL`, `AUTHORIZED_BOUNDED`, `BLOCKED_NEEDS_INFORMATION`, or `BLOCKED_UNSAFE_OR_INVALID`. Resource acquisition remains independent from answer authorization (R1); only materially decision-changing personal dependencies can block a proposed individualized action, leaving low-value ASK suppression intact (R2); all asserted/derived/retrieved/unknown/unavailable/not-applicable/invalid/deferred states remain distinct and provenance-bound (R3). Proposed implementation surface is four existing modules: dependency resolver, preconditions, runner, and answer generation. Six independent synthetic tests T1–T6 and preservation assertions are planned, not run. Future treatment-v2 must have a new identity and preserve baseline/treatment-v1/Step 9.39 artifacts. Any V4 regression confirmation requires separate protocol/authorization; V4 remains development evidence; V5 remains a separately authorized sealed unseen stage. Claim eligibility remains NO until critical failures do not exceed baseline and prior primary gains are not materially destroyed. No Agent code, V4, V5, benchmark/rubric/metrics/adjudication, or claim policy was modified; no evaluation/tests/model calls were run.

## Step 9.42 — Critical Regression Repair Implementation

Implemented the final-answer authorization gate in adaptive_agent/answer_generation.py and enforced it in adaptive_agent/runner.py immediately before generation and on the max-step terminal path. The gate distinguishes full, bounded, needs-information, and unsafe/invalid outcomes; only materially decision-changing/answer-scope-changing or explicitly safety/execution-critical state can block full individualized scope. Bounded/unsafe output is deterministic and non-personalized. Independent retrieval, optional ASK suppression, and provenance-bound state distinctions are preserved; modified Agent files contain no case-specific logic.

Pre-change Agent aggregate matched treatment-v1 e5e4841b51ecc6bced0f342a261a356756d07b39764670d774b910b86b8625a7. New Step 9.42 answer authorization tests T1–T6 plus interactions: 16/16 pass (six scenario classes, ten interaction/integrity tests). Focused regression: 147/147 pass. Full non-benchmark unittest regression: 333 run, 0 failures, 0 errors. Read-only architecture audit recomputed all 22 Step 9.39 source hashes, Harness members/aggregate, and Scoring members/aggregate with no mismatch. Created separate treatment-v2 development freeze step9_42_treatment_v2_freeze.json (Agent aggregate b9e891e7cd077dd5b3c6fa72b71faad978a24226c2b5e89e0b06aabde93b51d6, freeze artifact SHA-256 06d0835af73c01c89e4aa8d2a7f03d3da023c14a7195ab8a1213817f7b353bc0); treatment-v1 and historical baseline/Step 9.37/Step 9.39 artifacts remain unchanged. Claim eligibility remains NO. No V4 case execution/rerun, V5 creation/access, authorization, attempt, score, model call, Agent evaluation, or RAG evaluation occurred.

## Step 9.43 — Treatment-v2 Regression Preclearance

The Step 9.42 treatment-v2 freeze was independently verified: all 26 inventory entries match and the recomputed aggregate is b9e891e7cd077dd5b3c6fa72b71faad978a24226c2b5e89e0b06aabde93b51d6. Treatment-v1's recorded freeze/aggregate and historical run remain intact; its two Agent-file bytes were superseded by Step 9.42 as recorded. All 22 Step 9.39 source hashes and its report/metrics/transitions match their pinned identities. Frozen regression gates: critical failures <= baseline 0; harmful failures, task completion, and low-value ASK must not materially regress from v1's 1, 20/40, and 8/13 (61.54%); R1/R2/R3 mechanisms remain observable. Materiality remains under the unchanged Step 9.34a claim policy; no numeric margin was added.

Benchmark identity (40 cases, 10 per task, frozen order), harness, scoring/rubric, metric registry, one-shot rules, model/tool/RAG configuration, dependency lock, limits, protocol, and claim policy match. No v2 output namespace or prior v2 attempt exists. The Step 9.35a runner source still matches its v1 freeze and its one-shot mechanics pass synthetic tests, but its loader hardcodes the v1 freeze/template/evaluation ID; its live treatment-agent check fails against v2. Thus `TREATMENT_V2_RUNNER_READY=NO`, `EXACTLY_ONCE_GUARD_READY_FOR_V2=NO`, and `READY_FOR_STEP9_44_TREATMENT_V2_AUTHORIZATION=NO`. A new v2-specific runner compatibility freeze is required; no Agent/evaluation semantics need change.

Focused offline tests passed 37/37 (Step 9.35a runner authorization tests and Step 9.42 synthetic answer-authorization tests); three additional temporary synthetic authorization checks confirmed v2 hash accepted and v1/baseline hashes rejected under v2 pins. No V4 cases were loaded/run. Created `step9_43_treatment_v2_preclearance.json/.md`, `step9_43_treatment_v2_runner_audit.json`, and a disabled non-executable `step9_43_treatment_v2_authorization_template.json`. No authorization/attempt/command/score, V4 execution, model/Agent/RAG evaluation call, V5 creation/access, or modifications to Agent, benchmark, scoring, metrics, protocol, claims, Step 9.39, or historical artifacts occurred.

## Step 9.43a — Treatment-v2 Runner Identity Compatibility Repair

Added an explicit v1/v2 treatment identity-contract adapter at `scripts/run_step9_43a_treatment_v2.py`; the frozen Step 9.35a runner and its freeze remain byte-identical (parent runner SHA-256 `920486b1d7984fae6ee77b5ac51af0d0a98caf42e445d1abcf7ff75b46038505`). The adapter accepts only the two exact identity contract paths pinned by the new runner freeze, recomputes the selected Agent inventory and every live shared infrastructure pin, binds authorization/freeze/runner identities, rejects aliases/fallback/missing IDs, and revalidates all pins immediately before the parent's first-case path. Execution remains delegated to the unchanged 9.35a runner/9.28 production case helper; no evaluation semantics changed.

Treatment-v2 freeze and all 26 inventory entries match `b9e891e7cd077dd5b3c6fa72b71faad978a24226c2b5e89e0b06aabde93b51d6`. V2 contract SHA-256 is `490f6c2f17a929317ed776c52c59ebc608dbaa4590ecc736f40f5c7bf56a4182`; v2 runner SHA-256 is `9509194370d7530327741f9da69f98bc1b554576e62023d5ebce2e8316adf9e9`; new runner freeze SHA-256 is `db59e36c546293b55be9ed5505ef10fc223ddfda17f2f9eb88ffc36993a37110`. The v1 explicit contract remains a separately pinned identity; synthetic contract tests accept v1+v1 and reject v1+v2, while v2+v2 passes live freeze/inventory checks and v2+v1/baseline reject.

Step 9.43 gates rerun PASS, including shared benchmark/harness/scoring/registry/one-shot/model/tool/RAG/protocol identities, order, namespace isolation and no prior v2 attempt. All 22 Step 9.39 source hashes, all three baseline Step 9.30a run files, and all three treatment-v1 Step 9.36 run files match their historical pins. New identity tests 26/26 PASS; existing Step 9.35a runner tests 21/21 PASS; Step 9.42 synthetic tests 16/16 PASS; combined focused 63/63 PASS; full unittest suite 359 PASS / 0 FAIL / 0 ERROR. No V4 case was loaded or executed.

Created `step9_43a_treatment_v2_runner_repair.json/.md`, `step9_43a_treatment_v2_runner_freeze.json`, `step9_43a_treatment_v1_identity_contract.json`, `step9_43a_treatment_v2_identity_contract.json`, `step9_43a_treatment_v2_preclearance_rerun.json`, and a disabled v2 authorization template with no IDs or command. Step 9.43 fail-closed artifacts remain unchanged. Authorization status is `NOT_ISSUED`; no attempt, command, score, V4 rerun, V5 creation/access, or Agent/benchmark/scoring/metrics/protocol/claim/history changes occurred. Resume descriptive matched comparative claim eligibility remains NO. `READY_FOR_STEP9_44_TREATMENT_V2_AUTHORIZATION=YES` means preclearance eligibility only; Step 9.44 must separately audit and issue any authorization.
## Step 9.44 — Treatment-v2 Regression Authorization

The authorization audit failed closed. Live frozen identity verification passed, and the frozen preclearance reports no prior v2 authorization/attempt and an absent output namespace. However, the Step 9.43a frozen identity contract pre-binds `evaluation_id=heldout-v4-step9_43-treatment-v2-20260928-01`, while Step 9.44 requires a fresh evaluation ID. The frozen adapter and parent runner reject a different ID. No authorization ID or attempt ID was generated; no authorization manifest or command was created. Step 9.43a identities and historical artifacts were not modified. No V4 case/score, Agent/model/RAG call, adjudication, aggregation, comparison, or V5 activity occurred. Claim eligibility remains NO. See `evaluation/v1_2_3/step9_44_treatment_v2_authorization_audit.json` and `.md`. A separate compatibility repair/refreeze and renewed preclearance are required before retrying authorization.
## Step 9.44-r1 — Treatment-v2 Regression Authorization

Revalidated the frozen Step 9.43a treatment-v2 identity and infrastructure pins, historical Step 9.30a/9.36 run-file hashes, and all 22 Step 9.39 source hashes and its three output hashes. No prior v2 authorization, attempt, or output namespace existed. The Step 9.43a frozen contract pre-binds the unique, unused v2/V4 regression evaluation namespace `heldout-v4-step9_43-treatment-v2-20260928-01`; the exact-ID requirement was honored without modifying frozen runner/contract. Issued one authorization `auth-step9_44r1-ecce3f6d87e64ace822fc46c97c18f55` and attempt identity `attempt-step9_44r1-cb362342ae31449aaffba8092c346864`, with manifest and one manual command in the Step 9.44-r1 artifacts. Adapter and parent-runner read-only validators passed; focused regression tests passed 63/63. Authorization remains unconsumed. The command was not executed; no attempt, V4 case/score, adjudication, aggregation, comparison, or V5 activity occurred. Descriptive matched comparative claim eligibility remains NO. The earlier Step 9.44 fail-closed audit remains unchanged.

## Step 9.46 — Treatment-V2 Frozen Adjudication

完成 Treatment-V2 的逐案 single-AI-reviewer adjudication（40/40；KNOWLEDGE_QA、CAUSE_ASSESSMENT、PERSONALIZED_DECISION、DATA_ANALYSIS 各 10）。Reviewer 为 `SINGLE_AI_REVIEWER`，非人工审阅；`HUMAN_ADJUDICATION=NO`、`INTER_RATER_RELIABILITY=NOT_MEASURED`。沿用 Step 9.30b canonical reviewer 字段及 Step 9.37 treatment protocol，使用冻结的五维 rubric（20/20/20/25/15）、task completion、validity、ASK、tool、critical/harmful、failure attribution 字段。

正式输入和 9.45a lineage sidecar 在审阅前后均与 pin 一致：case results SHA-256 `4648b8e320f535001922f13a969d1482433bfa15f88233cf9a7e70b06cafed6c`；raw traces `d7ddf2a9a47ba62a85a7d1b85f069cc9593fd8f46cc4a01c1f3c8a055698cec2`；attempt ledger `723fe40cd727db9f553049daccfa7e3cf5489ce6eabee09a7dbea66fd447626b`；9.45a sidecar `92f42eb5288f2b35d00d49212d4f012c0591d7493ff2db3b88c1083f1e0e51de`。Rubric、schema、metric registry 分别匹配 frozen SHA `a7f5681f4fc7421d3617a7cc69ec4c08dc84d1871b290f08f86df68bde808899`、`21367c176f6b070d875a203ff779cfd44e2cb86a4e8956e1f93870fd054834c8`、`de9f348cb1dff66410c03095abdaffcc256f53679718482870e4aa4d80c75056`。

Lineage 仅作为来源信息：27 `COMPLETE_FORMAL`、8 `COMPLETE_DERIVED`、5 `INCOMPLETE_FORMAL`。5 个不完整案（DA-01/03/06/09/10）保留原状态；未合成语义根，也未因 lineage 不完整本身扣分。逐案来源行 SHA、判断、理由和 ASK 分类保存在 JSONL。审计通过：字段完整、分值范围合法、ASK 分类与观察到的 ASK 一一匹配、任务分布匹配。Critical failure IDs 与 harmful failure IDs 均为空。

Artifacts：`step9_46_v2_adjudication.jsonl` SHA-256 `38e178b68d498ca8280901e071e84787342ba460b47ec3c7e9f55f76086eb0f0`；freeze `74c50c34bd869109d52862202245b7d7e9463928dea24e897b74e3ed85587cee`；audit `5cffe15dd810d2303c1ae91b3f13281382575ee45701fd11a7c7210c45ad5018`；report `8baf84391c75612ad4c7f4a4475877dbfb6cd2112b8e8f68c7bcee9f5ad2151d`。本步骤没有 rerun、model/Agent/RAG 调用、聚合、baseline/V1/V2 比较或 V5 访问；未修改任何 formal run 输入、rubric、schema、metric registry 或历史 adjudication。逐案 adjudication 已可作为 Step 9.47 输入；该步骤仍须独立执行其冻结的输入完整性和聚合资格门禁。本步骤未计算 Overall、task means、rates 或 critical/harmful totals。


## Step 9.47 — Treatment-V2 Frozen Aggregation

PASS: offline aggregation of the frozen 40-case V2 adjudication; overall descriptive mean 68.875. V2-only; no Baseline/V1/V2 comparison, rerun, model/Agent/RAG execution, or V5 access. Aggregate SHA-256 `98df31b2082ce808acec2d6d409c9febc01b79278201a94b0fd1a3c2d30fc936`; case summary `42d8d08d135a5cf97a8fc01748be93d97dcb7493e7ecdb8fd1e01e3ea6669133`; report `85e767bca2ca8672f37213c10d901976c13391db7e586c22ea7629d1197a25eb`; freeze `8bbee93a63d2cb15abb87176a5a27d8e18a2cc24053e9ce53f25968138041995`; audit `918c436ec841a40ca742db2757e7bb7f224a37b0377c36717682e82e263238ec`. All frozen input hashes remained unchanged; aggregate consistency audit PASS.


## Step 9.48 — Frozen Three-Way Matched Comparison

PASS: post-hoc descriptive Baseline/V1/V2 comparison on the identical frozen 40-case set/order `d930455e417935337a6e3459defbdc3ee3829b71786fbd8438ef092b62429e68`. Overall means: 70.5 / 79.625 / 68.875; completion 16/40 / 20/40 / 7/40; validity 37/40 / 38/40 / 40/40. V1→V2 completion pass→fail IDs: V4-KQ-01, V4-KQ-06, V4-KQ-10, V4-CA-03, V4-CA-05, V4-CA-08, V4-CA-10, V4-PD-02, V4-PD-04, V4-PD-05, V4-PD-10, V4-DA-04, V4-DA-07. No causal/significance/generalization claim, V4 rerun, V2 repair, V3 creation, or V5 access. Comparison SHA-256 `0eb3768049d35ec52c23ea9b143c66ed5dd68718deb10139d35bcf241e5ff548`; case matrix `1edfbbf5d154f4946577abcde3c0d9c9acd197369c7550a78907531b61f74c38`; report `351d58275403e8d9dcfc6ba6d746fef5404853eab9d4bb10da759c54737460dd`; claim audit `11bb09788ed3d91bc53cfee969b2e479a6dfa1814185be36363303cf24b35dce`; freeze `3d0040dd21a3129aab5c07630b59399b5e4b0c1725d300c10628b172d0eaabd8`; audit `a4ccb957315e5ef50b5c523987e1c172f32e3edab5aed0beba413022e9f36c83`.


## Step 9.49 — V2 Completion-Regression Forensic Postmortem

PASS_READ_ONLY_DIAGNOSTIC: dynamically derived 13 V1-complete/V2-incomplete cases from Step 9.48; primary counts `{"ANSWER_GENERATION_REGRESSION": 11, "CORRECT_SAFETY_BLOCK": 0, "CORRECT_UNRESOLVED_DEPENDENCY_BLOCK": 0, "CORRECT_VALIDITY_BLOCK": 0, "INDETERMINATE": 0, "OTHER_EVIDENCED_CAUSE": 2, "OVER_CONSERVATIVE_AUTHORIZATION_BLOCK": 0, "UPSTREAM_STATE_OR_DEPENDENCY_REGRESSION": 0}`. Over-conservative authorization blocks positively established: 0. Six bounded-stop traces show a generic bounded-response collapse, but do not persist authorization enum/reason; no authorization denial is inferred. Primary repair-surface hypothesis: `BOUNDED_ANSWER_GENERATION` (HIGH); 20 tests designed, none run. No Agent/V2 change, V3, V4 rerun, V5 access, or model/Agent/RAG execution. Freeze SHA-256 `308184e99061554d9111f6c8d3b35d2e4ac15055ee9a913d35454857c6e4fee4`; audit SHA-256 `4b5f45cff6908bf94a19da6cbba371388612f63f0c43f605b223fa7dd37647d4`.


## Step 9.50 — V3 Completion Repair Design

PASS_DESIGN_ONLY: primary surface BOUNDED_ANSWER_GENERATION (HIGH); 11 dynamically loaded answer-generation cases and 2 adjudication-boundary cases analyzed. Raw V2 formal `state_history` contains {'AUTHORIZED_FULL': 5, 'AUTHORIZED_BOUNDED': 6} authorization modes; Step 9.49 extractor omission is reconciled without modifying its historical artifact. PD-06/PD-08/common safety invariants preserved; no dependency/precondition/gate relaxation; 40 synthetic tests designed, none run. No implementation or V4/V5/model/Agent/RAG activity. Design freeze SHA-256 `31ffec0addcf5da72ec098aa90e53dbc3d0d899c8ee5e0e67e8649f0214f88d8`; audit SHA-256 `f845df36c9157d7d1f36d8e3e4e87964c45f6675a4311fb939a2cf031ee76bd4`.

## Step 9.51 / 9.51a — V3 Implementation Validation and Boundary Remediation

Step 9.51 initially failed closed because the broad `unittest discover('tests')` selector filtered for module names prefixed `tests.`, while discovery returns `test_...`; Step 9.30a and Step 9.30c therefore ran. Step 9.30c recomputed the frozen historical V4 aggregate in memory, but wrote no output. The Step 9.43a current-tree-equals-V2 identity test also errored as expected after entering V3 development; frozen V2 expected hashes were not changed. Step 9.51a replaced discovery exclusions with an explicit 31-module allowlist and fail-closed selector; 10 modules are excluded, including both V4 aggregation/adjudication modules, V4 execution modules, the V2 live-identity module, and tests that write historical traces. The independent V2 freeze self-consistency test validates the frozen artifact/inventory without comparing current V3 source bytes to V2.

The safe manifest dry-run passed (31 modules / 323 cases). Final `.venv` safe rerun passed 323/323, 0 failures, 0 errors, 0 skips; Step 9.50 synthetic tests 40/40 and Step 9.41/9.42 safety tests 16/16. Frozen historical result/trace/adjudication/aggregate/comparison pins: 183 checked before tests and 40 direct outputs rechecked afterward, 0 mismatches. No historical write/overwrite, formal result/trace change, or historical aggregate modification was found. Current V3 development Agent inventory SHA-256: `085d338ed95bbef7370c41cf97ca0d6653ffdfd2f1c924eef4b7123dfdea4607`; it intentionally differs from frozen V2. Agent/production code was not changed during this remediation. PD-06, PD-08, common safety, epistemic status, answer/final-state authorization mirroring, traceability, and anti-overfit audits PASS. Case-specific Agent logic not found.

Artifacts: `step9_51a_safe_test_manifest.json`, `step9_51a_validation_boundary_audit.json`, `step9_51_v3_test_report.json`, `step9_51_v3_architecture_audit.json`, `step9_51_v3_anti_overfit_audit.json`, `step9_51_v3_implementation_report.json/.md`, and `step9_51_v3_development_freeze.json`. The prior failed Step 9.51 in-memory V4 aggregation is disclosed; Step 9.51a ran no V4 case or formal aggregate, no formal adjudication, no model/Agent/RAG formal evaluation, no V5 access, no authorization, and no formal attempt. Step 9.52 was not run; authorization remains `NOT_ISSUED`.

### Step 9.51 append-only identity validation revision

Added an explicit V3 development identity assertion to the boundary test suite while retaining the independent frozen-V2 artifact/inventory self-consistency assertion. Re-ran the complete pinned safe manifest: 324/324 PASS, 0 failures/errors/skips. The initial 323-case report and freeze remain unchanged as historical artifacts; revision `step9_51-r1` is authoritative and supersedes them. See `step9_51a_validation_boundary_audit_r1.json`, `step9_51_v3_test_report_r1.json`, `step9_51_v3_implementation_report_r1.json/.md`, and `step9_51_v3_development_freeze_r1.json`. No production code or historical evaluation artifact changed; Step 9.52 remains unexecuted.

## Step 9.52 — V3 Pre-Evaluation Validation

PASS_PRE_EVALUATION_ONLY. Current V3 development Agent inventory SHA-256 `085d338ed95bbef7370c41cf97ca0d6653ffdfd2f1c924eef4b7123dfdea4607` and its pinned implementation files match the Step 9.51-r1 freeze; Step 9.50 bounded-answer and traceability design requirements are met by the frozen implementation and prior 40/40 synthetic contract tests. PD06, PD08, common safety, epistemic status, required-dependency and hard-precondition invariants PASS; case-specific Agent logic was not found. The Step 9.51a safe boundary passed dry-run only (31 allowlisted modules / 324 discoverable cases; 10 excluded); no tests ran in Step 9.52. Step 9.51a historical hash audit had zero mismatches across 183 pre-test and 40 post-test pins; independently, 43 frozen evaluation-artifact pins rechecked against Step 9.50 still match (the recorder source pin is an expected pre-implementation source revision and matches the V3 freeze). V4 dataset remains pinned at SHA-256 `8b8c72092fcd7544e69d5d2ecd13610c7bb4c14210fca330698b3e5ab3f01d7f`, 40 cases, balanced four-task distribution and case-order fingerprint `d930455e417935337a6e3459defbdc3ee3829b71786fbd8438ef092b62429e68`; evaluation infrastructure pins match. Trace schema change is ADDITIVE_COMPATIBLE and observational. Runner classification is IDENTITY_ADAPTER_UPDATE_REQUIRED (infrastructure-only; no evaluation-semantic change); no runner was modified. No aggregate/adjudication code, Agent, RAG, model, V4 case or V5 content was accessed/executed; no authorization, formal attempt, V4 result/score, or V5 artifact was created. Step 9.53 V3 runner preclearance is ready. Detailed append-only audits: `step9_52_v3_pre_evaluation_validation.json/.md`, `step9_52_v3_identity_audit.json`, `step9_52_v3_runner_compatibility_audit.json`, `step9_52_v3_trace_schema_audit.json`, and `step9_52_v3_historical_integrity_audit.json`.

## Step 9.53 — Treatment-V3 Runner / Identity Preclearance

PASS_RUNNER_IDENTITY_PRECLEARANCE, identity-binding-only. Added an independent Step 9.53 V3 identity adapter that binds the frozen V3 identity contract and delegates production execution to the unchanged Step 9.35a runner; the V2 adapter remains unchanged. Current V3 Agent aggregate matches the Step 9.51-r1 freeze (`085d338ed95bbef7370c41cf97ca0d6653ffdfd2f1c924eef4b7123dfdea4607`). Frozen V4 dataset/manifest, Harness, Scoring/rubric, Metric Registry, One-shot Rules, model/tool/RAG/dependency, matched protocol, case count/order/task distribution, parent runner/freezes, and V2 adapter/freeze all match. Exact-once guard is ready and the V3 output namespace is isolated with no prior attempt.

The initial runner freeze was superseded by r1 after a direct CLI import-path failure; no case access occurred. r1 was then superseded by r2 after preflight correctly failed closed because the freeze pinned `task_distribution` but the runner projection omitted it. r2 binds and compares task distribution explicitly. Authoritative Step 9.53 runner SHA-256 `02e37b60469f0fb36979b883be45cf3231d3088fc4c48ce21dacdf6e3d0d9b6e`; r2 freeze SHA-256 `4c4749cde621ed989ec9c0dc77a194931079cdaee7f20dc6ba5668afee46eb43`; contract SHA-256 `fc73e402e5bb59866f5f83b61b8ac642e0aec601612a2d81423971072dbdadfa`.

Focused tests PASS 39/39 (Step 9.53 adapter 8, Step 9.35a runner 21, Step 9.50 traceability 10). Anti-overfit audit found no case-specific Agent logic. Rechecked historical integrity pins: Step 9.51a pre/post sets 183/40; Step 9.50 frozen evaluation pins 43; Step 9.37–9.39 outputs 10; mismatches 0. Evaluation semantics unchanged; no Agent, benchmark, harness/scoring/metrics/one-shot rules, or historical artifacts modified. No authorization/attempt ID/ledger created; no V4 case, answer, score, adjudication, aggregation, or comparison; no model/Agent/RAG evaluation call; no V5 access. `READY_FOR_STEP9_54_V3_AUTHORIZATION=YES` is preclearance only and does not authorize execution.

Artifacts: `step9_53_v3_runner_freeze_r2.json`, `step9_53_v3_runner_preclearance.json/.md`, and `step9_53_v3_runner_audit.json`. The initial and r1 freezes and both fail-closed preflight outcomes remain preserved; no V4 case execution occurred.

## Step 9.54-r1 — Treatment-V3 Formal V4 One-Shot Authorization

Authorization-only audit PASS. Issued `auth-step9_54r1-b43c3282fd9344f6a7c3548e376ec6d1` for evaluation `heldout-v4-step9_53-treatment-v3-20260930-01`, purpose `REGRESSION_ONLY_CONFIRMATION`, claim scope `FROZEN_MATCHED_DEVELOPMENT_REGRESSION_ONLY`; status `ISSUED_NOT_CONSUMED`. Current V3 Agent SHA-256 `085d338ed95bbef7370c41cf97ca0d6653ffdfd2f1c924eef4b7123dfdea4607`; authoritative Step 9.53 runner freeze r2 SHA-256 `4c4749cde621ed989ec9c0dc77a194931079cdaee7f20dc6ba5668afee46eb43`; runner SHA-256 `02e37b60469f0fb36979b883be45cf3231d3088fc4c48ce21dacdf6e3d0d9b6e`. All frozen V4 identity and infrastructure pins matched.

Historical integrity PASS: Step 9.50 evaluation artifact pins 43/43; Step 9.51a recorded 183 pre-test and 40 post-test checks with zero mismatches; Step 9.48 frozen inputs/outputs 61/61; Baseline/V1/V2 formal run files 9/9; Step 9.37–9.39 and 9.45a–9.47 frozen artifacts/lineage rechecks 75/75; Step 9.51-r1/9.52/9.53 identity chains match. The frozen parent runner requires `attempt_id` in the authorization manifest and requires the same value when consumed, so attempt identity `attempt-step9_54r1-d2e272e499e24f5f82096a01b2bf9fe9` is preallocated as required by that protocol. This is not a formal attempt: no run namespace, ledger, case result, or trace exists.

Authorization artifacts were re-read and cross-checked; `AUTHORIZATION_ARTIFACT_AUDIT=PASS`. Manifest SHA-256 `0b416035d9cf2b0ef5b71a306b1edd9fda42ffaa1e17f2605dd217db9c8f4b4d`; audit SHA-256 `3a88081ce66f4c8fb4d790cbcd0dcce4dd32798a5d27a81004dd7443b816bc06`; report SHA-256 `751d7bdca668279ddb54ae880ba45a3220344e1b7a320bf8aa3f9f793641b13b`; authorization freeze SHA-256 `59bdcdbffe06be1b017d8d62c673fc3c35d0810e972ec30f25c873c98ccf05cc`. Authorization remains unconsumed. No formal attempt/ledger, V4 execution/score, model/Agent/RAG case call, aggregation, adjudication, comparison, or V5 activity occurred. No Step 9.55 execution was started.

Artifacts: `step9_54_r1_v3_authorization_manifest.json`, `step9_54_r1_v3_authorization_audit.json`, `step9_54_r1_v3_authorization.md`, `step9_54_r1_v3_authorization_freeze.json`.

## Step 9.55 — Treatment-V3 Formal V4 One-Shot Execution

The one-shot attempt was created with authorization `auth-step9_54r1-b43c3282fd9344f6a7c3548e376ec6d1` and its pre-bound attempt ID `attempt-step9_54r1-d2e272e499e24f5f82096a01b2bf9fe9`. Authorization was consumed exactly once. Ledger lifecycle: `PREPARED` → `AUTHORIZATION_CONSUMED` → `FIRST_EVALUATION_ACCESS` → `CASE_SET_AND_ORDER_VERIFIED` → `FAILED_BEFORE_FIRST_CASE`. The frozen 40-case set/order and 10/10/10/10 task distribution were verified. No case `STARTED` event occurred; cases started/completed = 0/0. No `COMPLETED` event was fabricated.

Failure: after the frozen parent runner created the one-shot namespace and verified case set/order, its fresh V3 identity callback reran the pre-attempt namespace-isolation guard. That guard correctly expects the namespace to be absent before an attempt, so it failed closed once the attempt had created it. This occurred before service construction and before the first case. The authorization is consumed and the attempt is not restartable; no retry or runner modification was made.

Formal ledger: `evaluation/v4_runs/heldout-v4-step9_53-treatment-v3-20260930-01/attempts.jsonl`, SHA-256 `57967d950a3a4c700f3187e3d495ca39b4e01d5700ef31a9ebe36c3380450de6`. Expected case-results and raw-traces files were not created (count 0 each; no SHA). Agent SHA remains `085d338ed95bbef7370c41cf97ca0d6653ffdfd2f1c924eef4b7123dfdea4607`; authoritative runner freeze remains Step 9.53 r2. Historical artifact integrity recheck PASS (123 pinned items rehashed, zero mismatches).

No model, Agent, or RAG case call occurred. No adjudication, aggregation, comparison, reviewer score, or V5 activity occurred. Step 9.55 stops in `FAILED_BEFORE_FIRST_CASE`; the consumed one-shot authorization/attempt must not be retried. A separate forensic follow-up is required to diagnose the runner guard lifecycle mismatch; it must not retroactively mark this attempt complete.

## Step 9.55a — V3 Runner Namespace Lifecycle Infrastructure Repair

PASS_INFRASTRUCTURE_REPAIR_ONLY. Confirmed the lifecycle mismatch from the unchanged Step 9.35a parent: it calls the frozen-binding callback before namespace creation, then creates the namespace and durable ledger, verifies case set/order, and calls the callback again before case 1. The adapter previously reapplied the pre-attempt namespace-absence check at that second callback. Repaired this as a phase-aware invariant: `PRE_ATTEMPT` still requires an absent namespace and rejects collisions/reuse; `POST_ATTEMPT_CREATION_PRE_FIRST_CASE` now requires the exact current authorized identity and parent ledger prefix, no result/raw-trace/other outputs, zero case counters, no completion, and no duplicate IDs in other ledgers. Exactly-once and collision checks remain enabled.

Created a new future-identity overlay and Step 9.55a runner freeze; these supersede Step 9.53 r2 only for a future identity. Step 9.53 r2 and its identity contract remain unchanged. New runner SHA-256 `ace3d58005a5c4ce01aeeb17ac54a437c64e4023f7c870e12964a1a5d72b0b7e`; new contract SHA-256 `a8f6e54f78d0f7d3f2722390da4779d87f68838c76fe17ccc2f5930adb1d68c0`; new runner freeze SHA-256 `745ea26d044909e398eccdfd41da2f9f58b138612d28af57ed7a507fca2acc14`. Synthetic namespace lifecycle conditions 12/12 PASS, including callback phase order; focused standard-library regression 51/51 PASS (Step 9.55a, 9.53 adapter, 9.35a parent runner tests, 9.50 traceability tests). Identity-only preflight passes all frozen pins and reports `NOT_ISSUED`.

V3 Agent was not modified; inventory SHA-256 before/after remains `085d338ed95bbef7370c41cf97ca0d6653ffdfd2f1c924eef4b7123dfdea4607`. Evaluation semantics, V4 benchmark, parent runner, harness, scoring/rubric, metrics, and one-shot rules were not modified. Step 9.55 failed ledger remains unchanged at SHA-256 `57967d950a3a4c700f3187e3d495ca39b4e01d5700ef31a9ebe36c3380450de6`; Step 9.54 authorization manifest/audit/report/freeze hashes remain unchanged. Old authorization and attempt are permanently non-reusable. No new authorization/attempt, V4 case/result/trace/score, model/Agent/RAG case call, adjudication, aggregation, comparison, or V5 access occurred. `READY_FOR_NEW_V3_AUTHORIZATION=YES` means the repaired runner identity/lifecycle preflight is eligible for a separate authorization audit only; it is not authorization to execute. See `step9_55a_v3_namespace_lifecycle_audit.json/.md` and `step9_55a_v3_namespace_lifecycle_test_report.json`.

## Step 9.55b — V3 Repaired Runner Freeze r3 + Formal Execution Preclearance

PASS_NON_CONSUMING_PRECLEARANCE. Created new authoritative runner freeze revision r3 for the exact Step 9.55a repaired adapter SHA-256 `ace3d58005a5c4ce01aeeb17ac54a437c64e4023f7c870e12964a1a5d72b0b7e`; the Step 9.53 r2 freeze remains unchanged. Parent Step 9.35a runner and freeze identities match. Current V3 Agent SHA-256 `085d338ed95bbef7370c41cf97ca0d6653ffdfd2f1c924eef4b7123dfdea4607` matches the V3 development freeze.

Read-only identity preflight passes for V4 benchmark/manifest, Harness, Scoring implementation and rubric, Metric Registry, One-shot Rules, matched protocol, model/tool/RAG/dependency identities, 40-case set/order fingerprint, balanced task distribution, and namespace isolation. The phase-aware `PRE_ATTEMPT` / `POST_ATTEMPT_CREATION_PRE_FIRST_CASE` lifecycle, callback order, exactly-once semantics, and collision protection pass; the old Step 9.54 authorization and Step 9.55 attempt remain unusable. Hypothetical fresh identities were validated synthetically only.

Historical integrity: the Step 9.55 failed ledger remains SHA-256 `57967d950a3a4c700f3187e3d495ca39b4e01d5700ef31a9ebe36c3380450de6`; Step 9.53 r2, all Step 9.54 authorization files, and Step 9.55a artifacts remain unchanged. Rechecked 43/43 historical V1/V2/V3 evaluation artifact pins with zero mismatches. `evaluation/recorder.py` is the documented expected V3 implementation source revision in the Step 9.52 audit, not a historical result artifact. Static checks and synthetic regressions found no case-specific Agent or runner logic; evaluation semantics did not change.

The exact safe test manifest selects six explicit offline unittest modules (namespace lifecycle; V3 adapter; Step 9.35a authorization/one-shot; Step 9.42 safety; Step 9.50 bounded-answer and traceability). Result: 97/97 passed, 0 failures, 0 errors. Formal V4 execution, historical aggregation, adjudication, comparison, V5, and formal attempt creation were excluded. No authorization was issued, no attempt created, no authorization consumed, and no V4 case executed; no model/Agent/RAG evaluation call occurred. `READY_FOR_FRESH_V3_AUTHORIZATION=YES` indicates eligibility for a separate authorization audit only, not permission to execute. Stop at preclearance.

Artifacts: `step9_55b_v3_runner_freeze_r3.json`, `step9_55b_v3_runner_preclearance.json/.md`, `step9_55b_v3_runner_audit.json`, and `step9_55b_safe_test_manifest.json`.

## Step 9.56 — Fresh V3 Formal Execution Authorization

PASS_AUTHORIZATION_ISSUED_NOT_CONSUMED. Verified Step 9.55b r3 freeze/preclearance artifacts and their recorded hashes, re-ran read-only V3 identity preflight (34/34 checks PASS), and revalidated Agent SHA-256 `085d338ed95bbef7370c41cf97ca0d6653ffdfd2f1c924eef4b7123dfdea4607`, runner SHA-256 `ace3d58005a5c4ce01aeeb17ac54a437c64e4023f7c870e12964a1a5d72b0b7e`, and frozen evaluation identity. The 40-case identity, order fingerprint `d930455e417935337a6e3459defbdc3ee3829b71786fbd8438ef092b62429e68`, and balanced 10/10/10/10 task distribution match. Parent runner's read-only authorization validator PASS; pre-attempt namespace was absent.

Issued exactly one fresh authorization `auth-step9_56-a754eddd5c8a4ffc9243a7f1644aa611`, bound to one-shot limit 1, V3, r3, all frozen evaluation identities, and claim scope `FROZEN_MATCHED_DEVELOPMENT_REGRESSION_ONLY`. Its required pre-bound attempt identity is `attempt-step9_56-93842f48f1554239ad14d2c11689635e`; this is an identity field only, not a created formal attempt. Authorization status is `ISSUED_NOT_CONSUMED`, `consumed=false`, consumption count 0. The Step 9.55 old authorization and attempt were not reused.


The failed Step 9.55 ledger remains unchanged at SHA-256 `57967d950a3a4c700f3187e3d495ca39b4e01d5700ef31a9ebe36c3380450de6`; Step 9.53 r2 and Step 9.55b artifacts remain unchanged. No attempt namespace/ledger was created and no authorization was consumed. No formal V4 case, model/Agent/RAG evaluation call, adjudication, aggregation, comparison, or V5 access occurred. No execution command was generated. `READY_FOR_STEP9_57_V3_FORMAL_EXECUTION=YES` reflects the issued one-shot authorization only; Step 9.57 is not executed by this record. Artifacts: `step9_56_v3_authorization_manifest.json`, `step9_56_v3_authorization_audit.json`, `step9_56_v3_authorization_report.md`, and `step9_56_v3_authorization_freeze.json`.
## Step 9.57 — Treatment-V3 Formal V4 One-Shot Execution

The single authorized attempt `attempt-step9_56-93842f48f1554239ad14d2c11689635e` began under authorization `auth-step9_56-a754eddd5c8a4ffc9243a7f1644aa611`. Pre-consumption checks passed, including 34/34 frozen identity checks, r3 runner/Agent hashes, parent authorization validator, fresh namespace, and the r3 post-create/pre-first-case guard. The parent ledger durably recorded `PREPARED` → `AUTHORIZATION_CONSUMED` → `FIRST_EVALUATION_ACCESS` → `CASE_SET_AND_ORDER_VERIFIED` → `STARTED` (attempt) → `STARTED` (case 1, V4-KQ-01).

Execution failed during the first production Agent/model request with `APIConnectionError` caused by DNS resolution failure (`httpx.ConnectError`, `[Errno 8] nodename nor servname provided, or not known`). No case completed. Final ledger event: `FAILED_AFTER_PARTIAL_EXECUTION`, failure stage `FIRST_EVALUATION_ACCESS`, counters started/completed `1/0`. The one-shot authorization is consumed exactly once. Formal ledger: `evaluation/v4_runs/heldout-v4-step9_55a-treatment-v3-20260930-01/attempts.jsonl`, SHA-256 `10d3577bd59f886e5b5b79f23c8e911e117bfc52004eb234034f9314c2c5728e`. The runner-created case-results and raw-traces files are both empty (0 bytes; SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`); no result or trace records were completed. The attempt, ledger, and empty outputs are preserved unchanged; no retry, rerun, manual repair, or replacement authorization/attempt is permitted.

Post-failure runner SHA remains `ace3d58005a5c4ce01aeeb17ac54a437c64e4023f7c870e12964a1a5d72b0b7e`; V3 Agent inventory SHA remains `085d338ed95bbef7370c41cf97ca0d6653ffdfd2f1c924eef4b7123dfdea4607`. Prior Step 9.55 failed ledger remains unchanged at SHA-256 `57967d950a3a4c700f3187e3d495ca39b4e01d5700ef31a9ebe36c3380450de6`; Step 9.56 authorization and Step 9.55b freeze artifacts remain unchanged. No adjudication, aggregation, comparison, or V5 activity occurred. `READY_FOR_POST_EXECUTION_V3_FORENSICS=YES — FAILURE FORENSICS ONLY`; do not reconstruct lineage for scoring, adjudicate, aggregate, compare, or retry.

## Step 9.57b — V3 Infrastructure Remediation and Non-Consuming Connectivity Preclearance

`FAIL_CLOSED_DNS`. Configuration preclearance passed for the frozen `deepseek-flash` / DeepSeek OpenAI-compatible configuration (`DEEPSEEK_BASE_URL` resolves to `https://api.deepseek.com`; credential configuration PRESENT, secret not emitted). The local-only `getaddrinfo(api.deepseek.com, 443)` lookup failed with `gaierror` and 0 addresses. Therefore transport verification was NOT_PERFORMED; no HTTPS, API, or inference request was sent. Infrastructure remediation remains required and was not performed; this environment's DNS failure is unresolved. Runner, V3 Agent, and frozen evaluation identities match. Two explicitly inspected offline synthetic test modules passed 20/20 with 0 failures/errors. Post-diagnostic hashes confirm Step 9.57 ledger/results/traces, Step 9.56 authorization artifacts, Step 9.55b r3 freeze, Step 9.57a forensics, runner, and V3 Agent are unchanged. The prior authorization and attempt remain non-reusable. No new authorization/attempt, formal V4 case, model inference, Agent/RAG evaluation, adjudication, aggregation, comparison, or V5 access occurred. `READY_FOR_FRESH_V3_AUTHORIZATION=NO`. Artifacts: `evaluation/v1_2_3/step9_57b_v3_connectivity_preclearance.json`, `step9_57b_v3_connectivity_preclearance.md`, and `step9_57b_v3_connectivity_audit.json`.

## Step 9.57c — V3 Connectivity Recovery Preclearance

`PASS_CONNECTIVITY_RECOVERY_NON_CONSUMING`. Current local system resolver, default `dig`, `dig @1.1.1.1`, `dig @8.8.8.8`, and Python `socket.getaddrinfo("api.deepseek.com", 443)` all pass; Python reports one unique resolved address. DNS answer chain observed: `api.deepseek.com` → `d3bbv8sr76az5s.cloudfront.net` → A record; address value intentionally not retained. A transport-only TCP/TLS check to port 443 passed with TLS 1.3 and certificate verification; no HTTP request, API key, prompt, or inference endpoint was used. V3 Agent, r3 runner, model/tool/RAG and all frozen evaluation identities match; the 40-case identity/order/distribution match the freeze. Historical Step 9.57 DNS failure and Step 9.57b fail-closed result remain preserved, and all pinned history hashes match. No Agent/runner/semantics change, authorization, attempt, V4 case, inference, Agent/RAG evaluation, adjudication, aggregation, comparison, or V5 access occurred. `READY_FOR_FRESH_V3_AUTHORIZATION=YES` is preclearance only, not authorization. Artifacts: `evaluation/v1_2_3/step9_57c_v3_connectivity_recovery.json`, `step9_57c_v3_connectivity_recovery.md`, and `step9_57c_v3_connectivity_recovery_audit.json`.

## Step 9.57a — V3 Failed-Execution Connectivity / Infrastructure Forensics

PASS_READ_ONLY_FORENSICS. The earliest provable failure is **A — DNS / local network environment failure (HIGH confidence)**, not a V3 behavioral failure. The preserved Step 9.57 ledger records the first case `V4-KQ-01` as started and zero completed, with final `APIConnectionError`; the contemporaneous failure record identifies nested `httpx.ConnectError` / `[Errno 8] nodename nor servname provided, or not known`. Results and raw traces remain empty with SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`. Static tracing finds the production request path through the V3 identity adapter, matched runner, Step 9.28 production `/api/chat` case path, Flask `AdaptiveChatService` / `AdaptiveAgentLoop`, and `LLMInputUnderstander.understand` using `langchain_openai.ChatOpenAI` and the OpenAI/httpx transport. Frozen configuration identifies model `deepseek-flash` and `https://api.deepseek.com`, with `DEEPSEEK_BASE_URL` as override. A current local `getaddrinfo` diagnostic for `api.deepseek.com` also fails with `gaierror`; it made no HTTPS/API request and is not treated as proof of historical DNS state. No TCP, TLS, provider delivery, inference, model response, completed Agent action, answer, or persisted trace occurred. Current read-only recomputation matches the frozen V3 Agent, runner, model/tool/RAG configuration and evaluation identities. A fresh authorization could only be considered after remediation in a distinct step; none is issued here, and consumed identities remain non-reusable. No V4 retry/case, production model/Agent/RAG call, score, adjudication, aggregation, comparison, or V5 activity occurred. Artifacts: `evaluation/v1_2_3/step9_57a_v3_execution_failure_forensics.json`, `step9_57a_v3_execution_failure_forensics.md`, and `step9_57a_v3_execution_failure_audit.json`.

## Step 9.58b — Historical Evidence Reconstruction / Attestation

`PASS_POST_HOC_HISTORICAL_ATTESTATION`. The Step 9.58 conclusion is reconstructed only as a clearly labeled post-hoc attestation from preserved Step 9.57 ledger/results/traces, Step 9.55b r3 freeze and guard source, Step 9.56–9.57c provenance artifacts, the prior same-thread read-only preflight output, and a hash-pinned user-supplied screenshot. The evidence shows that Step 9.58 stopped at the existing output namespace guard (`pre-attempt output namespace already exists`): authorization was not issued, no attempt ID was allocated or attempt created, no V4 case/model/Agent/RAG execution occurred. The old failed namespace/attempt remains preserved and non-reusable.

The four expected original Step 9.58 files (manifest, audit, report, freeze) are absent; Step 9.58a remediation outputs are also absent because its historical-integrity precondition failed. This provenance gap is explicitly documented and is not relabeled as historical integrity PASS. These new artifacts are `POST_HOC`; none is represented as an original Step 9.58 artifact, no file was backdated, and no prior historical artifact or record content was rewritten. Evidence is sufficient to resume Step 9.58a infrastructure-only remediation, but this attestation does not authorize any evaluation. No authorization/attempt, V4 execution, model/Agent/RAG call, adjudication, aggregation, comparison, or V5 access occurred. Artifacts: `evaluation/v1_2_3/step9_58b_historical_evidence_inventory.json`, `step9_58b_post_hoc_attestation.json`, `step9_58b_post_hoc_attestation.md`, and `step9_58b_provenance_audit.json`.

## Step 9.58a-r1 — V3 Output Namespace Remediation

`PASS_NAMESPACE_REMEDIATION_ONLY`. Verified the Step 9.58b post-hoc attestation artifacts by exact SHA-256 and accepted them only as post-hoc evidence for remediation. The original Step 9.58 artifact set remains incomplete (`NO`); its provenance gap remains `PRESENT_AND_DOCUMENTED`. The Step 9.57 failed namespace, ledger, empty result file, and empty trace file remain untouched at their pinned hashes; Step 9.55b r3 freeze and Step 9.56/9.57a/b/c pinned artifact files remain unchanged. The r3 adapter source path is now the r4 adapter as explicitly allowed for infrastructure remediation; the r3 freeze itself is preserved and no longer represents the current runner.

Runner r4 (`scripts/run_step9_53_v3_identity_adapter.py`, SHA-256 `5c64ad7918703e9f2364d832963f39fbcd8bd45a7519a1771515b5d62bca4c87`) now binds a separate physical namespace derived from the exact evaluation/authorization/attempt IDs. The allocator (`scripts/v3_namespace_allocator.py`, SHA-256 `e9ec6e25cf9d8f4899176ae7795445911e4b77c42048f8eb3ed515189a7b1288`) uses exclusive reservation, a filesystem lock, recursive prior-ledger/reservation checks, and fsync; interrupted or repeated reservations fail closed. Its layout is `evaluation/v4_runs/<derived-namespace-id>/<frozen-evaluation-id>/`. The occupied historical namespace and Step 9.57 failed namespace are non-reusable. No case-specific namespace logic was found.

Current V3 Agent hash remains `085d338ed95bbef7370c41cf97ca0d6653ffdfd2f1c924eef4b7123dfdea4607`; benchmark, harness, scoring/rubric, metric registry, one-shot rules, model/tool/RAG, case set/order/distribution and evaluation semantics all match their freezes. Read-only r4 preflight passes. Focused synthetic test manifest: `tests.test_step9_55a_namespace_lifecycle` plus `tests.test_step9_58a_r1_namespace_allocator`; 21 passed, 0 failures, 0 errors. No production case, model, Agent/RAG evaluation call, authorization, attempt, adjudication, aggregation, comparison, or V5 access occurred. No historical original Step 9.58 artifact was created or represented as original. `READY_FOR_FRESH_V3_AUTHORIZATION=YES` is eligibility for a separate authorization audit only.

Artifacts: `evaluation/v1_2_3/step9_58a_r1_v3_identity_contract.json`, `step9_58a_r1_v3_runner_freeze_r4.json`, `step9_58a_r1_v3_runner_preclearance.json`, `step9_58a_r1_v3_namespace_allocation_audit.json`, `step9_58a_r1_v3_namespace_lifecycle_test_report.json`, `step9_58a_r1_v3_integrity_audit.json`, and `step9_58a_r1_v3_namespace_remediation_report.md`.

## Step 9.59a — r4 Parent Authorization Identity Binding Repair

`PASS_INFRASTRUCTURE_REPAIR_AND_NON_CONSUMING_PRECLEARANCE`. Step 9.59's fail-closed outcome and all four artifact hashes were reverified and preserved. Its candidate authorization `auth-step9_59-1645056dcfc34afeaac91b643f7621ec` and attempt `attempt-step9_59-f11825421e684b5884d1c09bea957cb8` remain burned/unusable; no attempt was created or authorization consumed. Root cause: r4 delegated to the Step 9.35a parent `validate_authorization()` without supplying the authoritative V3 runner binding map, causing the parent to use its historical default binding and reject the treatment identity.

The adapter now validates the single r5 freeze and passes the same recomputed r5 binding map explicitly to the parent's existing strict validator. Hash equality remains strict; no multiple runner versions are accepted. r4 remains immutable historical identity. r5 runner SHA-256 `7e75a80ad529c3df67a775287ca0aa9ada4f5ae7b18d1a0b85e593006362fe12`; r5 freeze SHA-256 `1007fde3dbfc604383a592523f100dc050fa21c93f23d8c88e9835e29f868314`. The read-only r5 preclearance passes Agent and frozen evaluation identity checks, validator binding, 40-case set/order, connectivity-recovery evidence, exactly-once guards, and namespace isolation. Historical Step 9.55/9.57 attempts and Step 9.57a/b/c, Step 9.58b post-hoc evidence, Step 9.58a-r1, and Step 9.59 files were rehashed: 26 checks, zero mismatches. The Step 9.58 provenance gap remains `PRESENT_AND_DOCUMENTED`; the post-hoc attestation is not represented as an original Step 9.58 artifact.

Focused offline regression manifest ran 60 tests: 60 passed, 0 failures, 0 errors. It covers r5 binding acceptance, stale r4 authorization rejection, fail-closed preflight on runner-pin mismatch, old authorization/attempt non-reuse, namespace lifecycle/collision/derivation, V3 identity and safety/traceability. No Agent, benchmark, or evaluation semantics were modified; no case-specific runner logic was added. No authorization was issued, attempt created, or authorization consumed. No V4 case, evaluation model/Agent/RAG call, adjudication, aggregation, comparison, or V5 access occurred. `READY_FOR_FRESH_V3_AUTHORIZATION=YES` is preclearance only; Step 9.59 retry and Step 9.60 were not executed.

Artifacts: `evaluation/v1_2_3/step9_59a_v3_runner_repair_audit.json`, `step9_59a_v3_runner_regression_test_report.json`, `step9_59a_v3_runner_freeze_r5.json`, `step9_59a_v3_runner_preclearance.json`, and `step9_59a_v3_runner_repair_report.md`.

## Step 9.59b — Fresh V3 One-Shot Authorization for r5

`PASS_AUTHORIZATION_ISSUED_NOT_CONSUMED`. Independently revalidated current r5 runner SHA-256 `7e75a80ad529c3df67a775287ca0aa9ada4f5ae7b18d1a0b85e593006362fe12`, r5 freeze SHA-256 `1007fde3dbfc604383a592523f100dc050fa21c93f23d8c88e9835e29f868314`, V3 Agent SHA-256 `085d338ed95bbef7370c41cf97ca0d6653ffdfd2f1c924eef4b7123dfdea4607`, and all frozen evaluation identities. The r5 adapter pre-attempt guard and parent authorization validator both passed read-only against the exact manifest using the current frozen binding map. Case count/set/order and 10/10/10/10 task distribution match. Step 9.57c connectivity recovery remains hash-valid (`PASS_CONNECTIVITY_RECOVERY_NON_CONSUMING`); no new inference or transport request was made.

Issued one fresh authorization `auth-step9_59b-0f63fb3bd6934e4b9a1c7e5808c24825`, bound only to future attempt identity `attempt-step9_59b-f3a11b5d44914eb9b335ccec4f1bcf86`. Status is `ISSUED_NOT_CONSUMED`, consumption count 0. The attempt identity is prebound only: no physical namespace/reservation marker, attempt ledger, case result, or raw trace was created. Derived namespace `heldout-v4-treatment-v3-run-442d8ee058d32e6ffe21` was absent at issuance. Historical authorization/attempt IDs, including burned Step 9.59 candidates, were not reused. Step 9.59 failure artifacts and Step 9.59a repair artifacts remain unchanged. Historical hash checks passed; Step 9.58 provenance gap remains `PRESENT_AND_DOCUMENTED`, and Step 9.58b remains a post-hoc attestation rather than an original Step 9.58 artifact.

No V4 case was executed; authorization was not consumed; no evaluation model/Agent/RAG call, adjudication, aggregation, comparison, or V5 access occurred. Step 9.60 was not run. `READY_FOR_STEP9_60_V3_FORMAL_EXECUTION=YES` is eligibility only; stop before execution.

Artifacts: `evaluation/v1_2_3/step9_59b_v3_authorization_manifest.json` (SHA-256 `163dc22d36dc97f2159f59f6dfcef9f1497c538149949a94683d00bf84420f44`), `step9_59b_v3_authorization_audit.json` (`8835e2cde24399fb19f37a41071b76d867630a5f0978c4564deffc2daa02640b`), `step9_59b_v3_authorization_report.md` (`163297659ec7505e8d943af2c16a48700aebf08504510f1f51c0184db9597584`), and `step9_59b_v3_authorization_freeze.json` (`5c7a248dcc202a1bd83ac887dbae9abb01348fd9775980277b106853a225cb0b`).

## Step 9.60a — Connectivity Recovery and Authorization Preservation Preclearance

`FAIL_CLOSED_CURRENT_DNS_UNAVAILABLE`. Revalidated r5 runner, V3 Agent, frozen evaluation identities, 40-case set/order/distribution, and authorization-validator binding. The non-consuming DNS diagnostics failed through macOS system resolver, default resolver, 1.1.1.1, 8.8.8.8, and Python `socket.getaddrinfo`; address count was 0. TCP/TLS was not attempted because DNS failed. No HTTP request, API key, prompt, model inference, Agent/RAG evaluation, or case execution occurred.

The Step 9.60 fail-closed-before-consumption outcome is preserved as prior conversation/user-provided evidence, not misrepresented as a persisted historical artifact or a formal attempt. Step 9.59b authorization remains `ISSUED_NOT_CONSUMED` with consumption count 0; its prebound attempt is not created and its derived physical namespace, ledger, results, and traces are absent. The frozen exactly-once contract does not explicitly establish whether manual re-invocation is permitted after a pre-consumption connectivity failure and prohibits automatic retry/resume. Therefore `AUTHORIZATION_STILL_USABLE=NO_NOT_PROVEN_BY_FROZEN_CONTRACT`; no retry was made. Existing historical pins were revalidated; the Step 9.58 provenance gap remains `PRESENT_AND_DOCUMENTED` and no missing original artifacts were synthesized.

No authorization was consumed, attempt/namespace was created, case started/completed, V4 case executed, score generated, or V5 accessed. Artifacts: `evaluation/v1_2_3/step9_60a_v3_connectivity_recovery.json`, `step9_60a_v3_authorization_preservation_audit.json`, `step9_60a_v3_historical_integrity_audit.json`, and `step9_60a_v3_preclearance_report.md`.

## Step 9.60b — Execution-Environment Connectivity Reconciliation and Authorization Lifecycle Audit

`FAIL_CLOSED_ENVIRONMENT_SPECIFIC_DNS_FAILURE`. Re-ran `socket.getaddrinfo("api.deepseek.com", 443)` in the project `.venv` runtime: cwd/project root `/Volumes/Elements/cbti-doctor-main`, Python `/Volumes/Elements/cbti-doctor-main/.venv/bin/python`, version 3.12.14. DNS returned `gaierror` with no addresses; TCP/TLS was not attempted. This execution did not send HTTP, credentials, authorization headers, or prompts. User-provided Mac Terminal evidence reports both system and project Python plus public DNS resolving to `3.173.21.63`; this was not independently reproducible in the Codex execution context. Because the project/runtime identity matches but observed network behavior differs by execution context, the classification is `B_EXECUTION_ENVIRONMENT_SPECIFIC_FAILURE`. Historical Step 9.60 and 9.60a DNS failures are preserved, not overwritten.

Revalidated r5 runner, V3 Agent, frozen identities, validator binding, 40 cases, order and distribution. Step 9.59b authorization `auth-step9_59b-0f63fb3bd6934e4b9a1c7e5808c24825` remains `ISSUED_NOT_CONSUMED` (count 0); prebound attempt `attempt-step9_59b-f3a11b5d44914eb9b335ccec4f1bcf86` is not created. The derived namespace is absent, no ledger contains these bound IDs, and no case started/results/traces exist. Frozen exactly-once artifacts prohibit automatic retry/resume but do not expressly grant reuse after a pre-attempt connectivity failure. Thus `AUTHORIZATION_REUSE_STATUS=NOT_PROVEN_BY_FROZEN_CONTRACT`; no reuse is inferred from the authorization status. If formal execution is again requested, perform a fresh authorization audit; this step neither issues authorization nor runs Step 9.60.

All 34 extant Step 9.60a historical pins revalidated with zero mismatches, and its four artifacts still match their recorded hashes. Original Step 9.60 failure artifact remains absent (conversation evidence only); Step 9.58 original artifact gap remains `PRESENT_AND_DOCUMENTED`. No historical artifact was altered or synthesized. No authorization consumption, new authorization/attempt/namespace, V4 case, model inference, Agent/RAG evaluation, adjudication, aggregation, comparison, or V5 access occurred.

Artifacts: `evaluation/v1_2_3/step9_60b_v3_connectivity_reconciliation.json`, `step9_60b_v3_authorization_lifecycle_audit.json`, `step9_60b_v3_report.md`, and `step9_60b_v3_integrity_audit.json`.

## Step 9.61 — Fresh Authorization Audit for Mac-Local Formal V4 Execution

`FAIL_CLOSED_OLD_AUTHORIZATION_RETIREMENT_NOT_DEFINED`. The r5 runner, V3 Agent, frozen evaluation identities, validator binding, case count/set/order, and 10/10/10/10 task distribution revalidated. Historical audit rechecked 42 pins (including Steps 9.60a/9.60b) with zero mismatches. Step 9.58 provenance gap remains `PRESENT_AND_DOCUMENTED`; missing original Step 9.58 artifacts were not recreated.

Step 9.59b authorization `auth-step9_59b-0f63fb3bd6934e4b9a1c7e5808c24825` remains `ISSUED_NOT_CONSUMED`, consumed `NO`, count `0`; its prebound attempt was not created and its physical namespace remains absent. The frozen manifest forbids authorization reuse, but neither the frozen lifecycle nor runner contract provides a retirement status/transition for an issued, unconsumed authorization. The validator still accepts the issued/not-executed and unconsumed shape. Therefore retirement is not written or inferred, and no new authorization is issued. This is fail-closed; a separately frozen lifecycle-contract amendment and validator behavior are required before another fresh authorization audit.

The requested Mac-local target binding is recorded as intent only: `USER_MAC_LOCAL_PROJECT_VENV`, `/Volumes/Elements/cbti-doctor-main`, `/Volumes/Elements/cbti-doctor-main/.venv/bin/python`. Codex runtime connectivity was not treated as Mac-local connectivity; Step 9.61 did not test DeepSeek. No model/Agent/RAG call, V4 case, authorization consumption, new authorization, attempt, namespace, result, or trace occurred.

Artifacts: `evaluation/v1_2_3/step9_61_v3_authorization_manifest.json` (decision only; explicitly not an authorization), `step9_61_v3_authorization_audit.json`, `step9_61_v3_authorization_report.md`, and `step9_61_v3_authorization_freeze.json` (audit freeze only; not an authorization).

## Step 9.61a — Authorization Retirement Lifecycle Contract Repair

`PASS_INFRASTRUCTURE_REPAIR_AND_OLD_AUTHORIZATION_RETIRED_UNCONSUMED`. Added an explicit append-only, terminal lifecycle state `RETIRED_UNCONSUMED_NON_REUSABLE`, bound by the new r6 runner freeze. The r5 freeze and Step 9.59b authorization artifacts remain unchanged. The lifecycle predicate is serialized with namespace allocation; the parent validator, V3 identity adapter, and allocator fail closed on retired IDs. Parent authorization validation and output namespace creation share the lifecycle lock.

The Step 9.61 audit (`8917201996c69ae7f8ac283fdf49391c771a620fc3e6ba08cb8594122df6888d`) was rehashed and confirmed to bind old authorization `auth-step9_59b-0f63fb3bd6934e4b9a1c7e5808c24825` as non-reusable. After verifying no corresponding attempt, namespace, reservation, result, or trace, one terminal retirement event was appended to `evaluation/v1_2_3/authorization_lifecycle_events.jsonl` and copied to `step9_61a_v3_retirement_event.json`. Its original issued manifest remains unmodified; consumption remains `NO`, count `0`; no attempt or namespace was created. Step 9.58 provenance gap remains `PRESENT_AND_DOCUMENTED`.

The r6 runner freeze is `evaluation/v1_2_3/step9_61a_v3_runner_freeze_r6.json` (SHA-256 `4e6c0bf9ed718546ea1efa12ae48324fd5438129ad3cd3860f93bd33037f1593`). V3 Agent hash remains `085d338ed95bbef7370c41cf97ca0d6653ffdfd2f1c924eef4b7123dfdea4607`; evaluation semantics were unchanged. Focused safe tests: 64 passed, 0 failures, 0 errors. All 34 Step 9.60a inventory pins were rechecked with zero mismatches. No new authorization, formal attempt, V4 case, model/Agent/RAG evaluation, score, adjudication, aggregation, comparison, or V5 access occurred. No executable command was generated.

Artifacts: `step9_61a_v3_authorization_lifecycle_contract.json`, `step9_61a_v3_runner_freeze_r6.json`, `step9_61a_v3_retirement_event.json`, `step9_61a_v3_validator_audit.json`, `step9_61a_v3_safe_test_report.json`, `step9_61a_v3_historical_integrity_audit.json`, `step9_61a_v3_lifecycle_repair_report.md`, and append-only ledger `authorization_lifecycle_events.jsonl`.

## Step 9.62 — Fresh V3 Authorization Audit and Issue Only

`PASS_AUTHORIZATION_ISSUED_NOT_CONSUMED`. Revalidated r6 freeze, current V3 Agent, frozen evaluation identity, lifecycle contract and validator binding. Audited 55 current authoritative historical pins with zero mismatches; Step 9.58 remains `PRESENT_AND_DOCUMENTED`. The old Step 9.59b authorization remains retired, unconsumed (count 0), non-reusable, and validator-rejected. Four prior V3 authorizations were consumed in their recorded histories; the retired fifth was not reused, leaving zero active executable authorizations before this issuance.

Issued fresh one-shot authorization `auth-step9_62-e796755748e14418b9da641f5d6c15e2`, prebound to `attempt-step9_62-6620ce3a79684874a15f5e35eac97938`, with derived namespace `heldout-v4-treatment-v3-run-52b2c0c8ebbb06258291`. Parent and adapter pre-attempt validators passed against the exact r6-bound manifest. Authorization remains `ISSUED_NOT_CONSUMED`, consumed `NO`, count `0`; no formal attempt, namespace, reservation, case output, or trace exists. Pinned Step 9.57c connectivity evidence was audited without a live endpoint probe. Connectivity must be revalidated in the user Mac project venv before consumption.

No DeepSeek/model/Agent/RAG call, formal V4 case, or Step 9.63 action occurred; cases started `0`. Artifacts: `step9_62_v3_authorization_manifest.json`, `step9_62_v3_authorization_audit.json`, `step9_62_v3_identity_namespace_audit.json`, `step9_62_v3_historical_integrity_audit.json`, `step9_62_v3_r6_binding_audit.json`, `step9_62_v3_authorization_freeze.json`, and `step9_62_v3_report.md`.

## Step 9.63 — Formal Execution Runner Construction & Pre-Execution Audit

`FAIL_CLOSED_ATOMIC_COMMIT_CONTRACT_MISSING`. Added a guarded runner shell at `scripts/run_step9_63_v3_formal_execution.py` (SHA-256 `c03da458834c616eff952a4c62a16ad264642ba868646dffb45aec31d7e283f4`): read-only `--audit-only` performs identity/precommit checks, while `--execute-formal-v4` explicitly refuses; no formal execution path is enabled. Read-only audit matched the r6 runner freeze, V3 Agent, frozen evaluation identities, exact 40-case order/set and 10/10/10/10 distribution. The Step 9.62 authorization remains issued/unconsumed (count 0), with no attempt or namespace. 55 historical pins and before/after snapshots matched; Step 9.58 provenance gap remains `PRESENT_AND_DOCUMENTED`.

The frozen lifecycle contract defines consumption at `AUTHORIZATION_CONSUMED`, while namespace reservation, attempt-ledger creation, and consumption events are separate durable operations. No frozen atomic commit boundary or partial-commit crash reconciliation protocol exists. A crash may therefore leave partially committed state; in accordance with the task boundary, no new transaction semantics were invented, so readiness is `NO`. Synthetic offline tests: 23 passed, 0 failures/errors; `py_compile` passed. No fresh connectivity probe was attempted. No authorization consumption/issuance, formal attempt/namespace, result/trace, model/Agent/RAG call, case execution, adjudication, aggregation, comparison, or V5 access occurred.

Artifacts: `step9_63_v3_runner_build_audit.json`, `step9_63_v3_runner_build_audit.md`, `step9_63_offline_test_manifest.json`, and `step9_63_historical_integrity_audit.json`.

## Step 9.63a — Atomic Execution Commit & Crash-Reconciliation Infrastructure Repair

`FAIL_CLOSED_PRODUCTION_INTEGRATION_AND_FREEZE_MISSING`. Audited the existing order: namespace reservation, attempt-ledger creation, `PREPARED`/`AUTHORIZATION_CONSUMED`/`FIRST_EVALUATION_ACCESS` events, and case-start events are separate durable writes. Added a synthetic-tested transaction journal protocol at `scripts/v3_execution_transaction.py` with `PREPARED → COMMITTING → COMMITTED`, terminal recovery classifications, lock-based contender serialization, identity collision detection, fsync calls, and a COMMITTED-gated case-start helper. 32 synthetic tests passed.

The journal remains a prototype and is not wired into the r6 formal adapter, lifecycle validator, allocator, parent runner, or production case-start path. Thus it is not the current authoritative commit point and cannot be represented as repairing production exactly-once behavior. Runner remains r6; no new formal runner freeze was created. The live Step 9.62 authorization remains bound to r6 and is incompatible with any future changed execution path absent a separately authorized identity transition. No attempt to migrate or consume it was made. No power-loss durability claim is made.

Combined focused regression (transaction, Step 9.61a, 9.62b and 9.63): 76 passed, 0 failures/errors; `py_compile` passed. All 55 authoritative historical pins and authorization manifest/freeze hashes match before/after; Step 9.58 gap remains `PRESENT_AND_DOCUMENTED`. The Step 9.62 manifest hash remains `7f97f9e42b8711a6ae745e4626d81fa8787a162bbfa8fdad6fe53c9fd4b975c8`; it remains `ISSUED_NOT_CONSUMED`, count 0. Bound attempt/namespace and all case artifacts remain absent. No network/model/Agent/RAG/evaluation activity occurred. `READY_FOR_STEP9_63B_FINAL_PRECLEARANCE = NO`.

Artifacts in `evaluation/v1_2_3/step9_63a/`: atomic commit contract, crash matrix, implementation audit, test manifest, historical integrity audit, live authorization immutability audit, prototype freeze, and report.

## Step 9.63a-r1 — Production Transaction Integration + r7 Runner Freeze

`PASS_PRODUCTION_TRANSACTION_INTEGRATION_AND_FREEZE` (infrastructure only). The V3 formal path now validates frozen identities and authorization, commits an append-only transaction journal under the shared lifecycle/namespace lock, reserves the exact derived namespace, appends a one-time `ATTEMPT_CLAIMED` event before creating the transaction-bound attempt ledger, and requires exact `COMMITTED` bindings plus a journal `CASE_STARTED` event before the production `/api/chat` case path. Recovery uses the same transaction module and never automatically retries cases or creates a second authorization/attempt. Durability is described as process-crash recoverability with fsynced journal and directories on a filesystem honoring those primitives; power-loss atomicity is not claimed.

The new frozen runner is r7 (`evaluation/v1_2_3/step9_63a_r1_v3_runner_freeze_r7.json`, SHA-256 `99ab870303e45497bf750b55f8382912089c2cf80e737b780922695d9906275c`). r6 remains immutable and is superseded only for future authorization. The Step 9.62 r6-bound authorization remains `ISSUED_NOT_CONSUMED`, consumed `NO`, count `0`, SHA-256 `7f97f9e42b8711a6ae745e4626d81fa8787a162bbfa8fdad6fe53c9fd4b975c8`; its attempt, namespace, transaction, and cases are absent. It does not match r7 and was not migrated, retired, replaced, or consumed.

Thirty-three new synthetic production-wiring tests and 100 related offline regressions passed; `py_compile` passed. Current V3 static bypass audit found zero unguarded execution entrypoints. All 55 historical pins and authorization hashes matched before/after; Step 9.58 provenance gap remains `PRESENT_AND_DOCUMENTED`. V3 Agent and evaluation semantics were not modified. No DeepSeek/model/Agent/RAG call or formal V4 case occurred. `READY_FOR_FRESH_AUTHORIZATION_LIFECYCLE_DECISION = YES`; `READY_FOR_STEP9_63B_FINAL_PRECLEARANCE = NO`.

New artifacts: `step9_63a_r1_production_call_graph.json`, `step9_63a_r1_atomic_commit_contract.json`, `step9_63a_r1_crash_reconciliation_matrix.json`, `step9_63a_r1_bypass_path_audit.json`, `step9_63a_r1_concurrency_test_report.json`, `step9_63a_r1_production_integration_test_manifest.json`, `step9_63a_r1_historical_integrity_audit.json`, `step9_63a_r1_real_authorization_immutability_audit.json`, `step9_63a_r1_v3_runner_freeze_r7.json`, `step9_63a_r1_production_integration_audit.json`, and `step9_63a_r1_production_integration_report.md` in `evaluation/v1_2_3/`.

## Step 9.63a-r2 — Superseded r6 Authorization Retirement & r7 Eligibility

`PASS_SUPERSEDED_AUTHORIZATION_RETIRED_AND_R7_ELIGIBILITY_CONFIRMED`. Before lifecycle mutation, r7 runner SHA-256 `99ab870303e45497bf750b55f8382912089c2cf80e737b780922695d9906275c`, V3 Agent, frozen evaluation identities, exact 40-case set/order and 10/10/10/10 distribution matched. The Step 9.62 authorization was the sole active executable authorization, remained `ISSUED_NOT_CONSUMED`, consumed `NO`, count `0`, bound to r6 rather than r7, and had no transaction, attempt, reservation, namespace, or case start.

The frozen Step 9.61a contract's existing retirement transition was applied once under the shared lock. A terminal `RETIRED_UNCONSUMED_NON_REUSABLE` event was appended to `authorization_lifecycle_events.jsonl`, pinning `step9_63a_r2_superseded_authorization_nonreuse_determination.json` (SHA-256 `b6f431b3369d2040454cfc6790cac40d7272249fd794dfa1d05eb5d6198fcef7`). That determination records `SUPERSEDED_RUNNER_FREEZE` and exact r6/r7 identities. The original Step 9.62 authorization manifest was not rewritten; its SHA remains `7f97f9e42b8711a6ae745e4626d81fa8787a162bbfa8fdad6fe53c9fd4b975c8`. Consumed stays `NO`, count `0`. Lifecycle, V3 adapter and parent runner reject the old ID. Active executable authorization count is now `0`.

The authorized append changed the lifecycle ledger's full SHA to `f573185bc39c26e14306ff1ac7c1a3e3a64e9940cb1e6f089a08942b96cb044d`, while its original 1161-byte prefix still hashes to the frozen `ca168f6939c4697a7a7bccc0b365b414d9a0e632f40de4242eb0a47e2d985285`. The other historical pins and all 11 Step 9.63a-r1 artifacts remained unchanged; the 55-pin prefix-aware integrity audit found zero mismatches. Step 9.58 provenance gap remains `PRESENT_AND_DOCUMENTED`. A future issuer must recognize this append-only extension rather than demand the old ledger's full-file SHA.

Frozen identity policy requires a globally new authorization and attempt ID and a distinct derived namespace. None was allocated or issued here. `READY_FOR_FRESH_R7_AUTHORIZATION_ISSUE = YES`; `READY_FOR_STEP9_63B_FINAL_PRECLEARANCE = NO`. Focused offline tests: 152 passed, 0 failures/errors; `py_compile` passed. No endpoint test, DeepSeek/model/Agent/RAG call, V4 case, authorization consumption, attempt, or namespace creation occurred.

New artifacts in `evaluation/v1_2_3/`: `step9_63a_r2_superseded_authorization_nonreuse_determination.json`, `step9_63a_r2_retirement_lifecycle_event.json`, `step9_63a_r2_old_authorization_retirement_audit.json`, `step9_63a_r2_identity_binding_audit.json`, `step9_63a_r2_fresh_r7_authorization_eligibility_audit.json`, `step9_63a_r2_historical_integrity_audit.json`, `step9_63a_r2_lifecycle_transaction_test_manifest.json`, and `step9_63a_r2_retirement_and_eligibility_report.md`.

## Step 9.63a-r3 — Fresh r7 Authorization Issuance Only

`PASS_FRESH_R7_AUTHORIZATION_ISSUED_NOT_CONSUMED`. Issued exactly one fresh r7-bound authorization, `auth-step9_63a_r3-d53bbaa35b1e4522bc4a5f57d42c8ef7`, with manifest SHA-256 `1514438d0afe23a39de2a696e9ea5bd97faac4dd546a88cdbd7b91f450046345`. The prebound attempt is `attempt-step9_63a_r3-3b66e84b7b1f4f538e87156c85b0e7dd`; the derived namespace is `heldout-v4-treatment-v3-run-2b23978e98ac414ca26e`. These are identities only: no attempt, physical namespace, or reservation was created. Authorization status is `ISSUED_NOT_CONSUMED`, consumed `NO`, count `0`; active executable authorization count changed from `0` to `1`. The old r6 authorization remains terminally retired, unconsumed, non-executable, and non-reusable.

Runner r7, V3 Agent, frozen evaluation identities, exact 40-case set/order/distribution, lifecycle contract, and production transaction commit-point contract matched. A pre-issue AppleDouble sidecar scan failed closed before creating a manifest; the JSON-artifact filter was corrected and synthetic-tested, then the authorization was issued once. Focused offline tests: 170 passed, 0 failures/errors; `py_compile` passed. All 55 historical pins matched using the unchanged frozen prefix of the append-only lifecycle ledger; its full SHA remained the Step 9.63a-r2 value. Step 9.58 provenance gap remains `PRESENT_AND_DOCUMENTED`.

No authorization consumption, transaction commit, network probe, DeepSeek/model/Agent/RAG call, V4 case, adjudication, aggregation, or comparison occurred. `READY_FOR_STEP9_63B_FINAL_PRECLEARANCE = YES` only; Step 9.63b and formal execution were not performed. Separate r3 manifest, freeze, issuance/binding/collision/exactly-once/historical audits, test manifest, and report are under `evaluation/v1_2_3/`.

## Step 9.63b — Mac-Local Final Non-Consuming Preclearance Preparation

`PASS_SCRIPT_BUILT_OFFLINE_MAC_LOCAL_PREFLIGHT_NOT_RUN`. Added `scripts/preflight_step9_63b_mac_local.py` (SHA-256 `fec1e3ec9aa1b0d447e6f90295150cc7416373502771290fc291eb2b7d90a2a4`) for the user to run manually from the specified Mac project `.venv`. It pins the fresh r7 authorization, verifies runtime/project, Agent, runner, evaluation, 40-case set/order, lifecycle and transaction identities, historical pins, and the absence of a consumed authorization, attempt, namespace, reservation, or transaction. Its only live connectivity actions are system/Python/default/Google/Cloudflare DNS checks and TCP/TLS certificate validation. It sends no HTTP bytes, prompt, or API key. A passing manual run exclusively writes a standalone preflight evidence artifact outside the execution namespace.

Offline identity and non-consumption audit passed: the authorization remains `ISSUED_NOT_CONSUMED`, count `0`, with exactly one active executable authorization; the attempt and namespace remain absent. All 55 historical pins matched; Step 9.58 provenance gap remains `PRESENT_AND_DOCUMENTED`. Focused synthetic/offline tests: 59 passed, 0 failures/errors; `py_compile` passed. Codex did not run the real Mac-local preflight or assert Mac DNS/TCP/TLS readiness. No model/Agent/RAG call, authorization consumption, attempt/namespace creation, or V4 case occurred. `READY_FOR_STEP9_63C_ATOMIC_FORMAL_EXECUTION = NOT_DETERMINED_PENDING_USER_MAC_LOCAL_PREFLIGHT`.

New artifacts: `evaluation/v1_2_3/step9_63b_preparation_audit.json`, `step9_63b_offline_test_manifest.json`, and `step9_63b_preparation_report.md`.

## Step 9.63c — Final Atomic Formal V4 Execution Preparation

`PASS_READY_FOR_SINGLE_ATOMIC_FORMAL_EXECUTION` (preparation only). The user-run Mac-local Step 9.63b artifact exists with SHA-256 `69a899df5cef04b605a21f3f07e812c5ecf5ba3f3083a595579aab092c9c0d14` and records DNS, TCP, certificate-verified TLS, project runtime, and credential-presence checks as passing. Its authorization, attempt, namespace, r7 freeze, and manifest bindings match the current files. Current read-only checks reconfirmed the unique r7 authorization is `ISSUED_NOT_CONSUMED`, count `0`, with no attempt, namespace, reservation, or transaction; all 55 historical pins match and Step 9.58 provenance gap remains `PRESENT_AND_DOCUMENTED`.

The audited real CLI is `scripts/run_step9_63_v3_formal_execution.py` in `--execute-formal-v4` mode, with explicit IDs, authorization/preflight files, and seven frozen hashes. Source and frozen integration audit show that this path enters the r7 transaction journal, committed-only namespace and attempt gates, and transaction-gated case-start path; unguarded production execution path count is `0`. The exact command is supplied to the user separately for manual Mac Terminal execution. It was **not run** in this preparation step. No authorization consumption, attempt/namespace creation, DeepSeek/model/Agent/RAG call, or V4 case occurred. Audit: `evaluation/v1_2_3/step9_63c_final_preparation_audit.json`.

## Step 9.63c-r1 — Post-Failure Transaction / Namespace Forensic Audit

Per the user's report, Step 9.63c was invoked once in Mac Terminal, with no retry. The exact exception was `RuntimeError: treatment output namespace collision; rerun forbidden`, via `execute_formal() → adapter.run() → parent.run() → validate_authorization()`. Read-only evidence shows the r7 transaction journal durably reached `PREPARED → COMMITTING → COMMITTED` with an irreversible authorization burn marker. It then reserved the new derived namespace, but no `ATTEMPT_CLAIMED`, attempt ledger, `AUTHORIZATION_CONSUMED`, `CASE_STARTED`, result, trace or case output exists. The manifest remains `ISSUED_NOT_CONSUMED`, `consumed=false`, count `0`; nevertheless the canonical validator now rejects execution due the committed transaction. Authorization and attempt identity are non-reusable. Attempt disposition: `COMMITTED_BUT_EXECUTION_NOT_STARTED`; V4 cases started/completed `0`, model/Agent/RAG evaluation `NO`.

The throwing parent guard checked `/Volumes/Elements/cbti-doctor-main/evaluation/v4_runs/heldout-v4-step9_55a-treatment-v3-20260930-01`, a pre-existing September 30 historical directory. It did **not** check the just-reserved derived namespace. `validate_authorization()` retained its definition-time default global `run_root`, while adapter only rebound `parent.OUT_ROOT`; `parent.run()` omitted an explicit `run_root` argument. Root-cause class: `A_PREEXISTING_HISTORICAL_NAMESPACE` with a parent/default-root binding integration conflict, not a transaction-created checked-path collision. No repair, cleanup or reconciliation was performed. Historical integrity: 55 pins, 0 mismatches; Step 9.58 provenance gap `PRESENT_AND_DOCUMENTED`. `READY_FOR_RERUN = NO`; `READY_FOR_REPAIR_DECISION = YES`. Separate audit and report: `evaluation/v1_2_3/step9_63c_r1_post_failure_forensic_audit.json` and `step9_63c_r1_post_failure_forensic_report.md`.

## Step 9.63c-r2 — Parent Namespace Guard / Transaction Boundary Repair Design

`PASS_DESIGN_ONLY_READY_FOR_R3_IMPLEMENTATION`. Read the actual formal entry → adapter → fsynced transaction `COMMITTED` → derived namespace reservation → parent validation → attempt claim/ledger → per-case `CASE_STARTED` path. The current parent validator checks a definition-time global `run_root/evaluation_id`, while r7 transaction and allocator use an attempt-scoped derived namespace. The current root cause remains the pre-existing historical evaluation directory and a parent/default-root binding integration conflict; the transaction did not create the checked path. `COMMITTED` means the execution identity is irreversibly claimed/authorization burned, not that an attempt ledger, reservation, case, or final result exists.

Recommended design: make the fsynced transaction tuple and frozen namespace derivation the authority, require the parent to receive the exact committed/reserved attempt root explicitly, and retain its exclusive inner-directory/output collision checks. Do not disable guards or move the frozen commit point. Future implementation requires a new runner freeze and fresh authorization/attempt/namespace; the old committed transaction, old reservation, old authorization and old attempt remain immutable and non-reusable. Designed 12 synthetic regression scenarios and a fail-closed F1–F6 crash matrix; no tests were run here. V3 Agent, V4, scoring, metric registry and evaluation semantics require no change. No production code, journal, namespace or historical artifact was modified; no new authorization/attempt was created and no model/Agent/RAG/V4 execution occurred. Design artifacts: `evaluation/v1_2_3/step9_63c_r2_parent_namespace_transaction_repair_design.json` and `.md`.

## Step 9.63c-r3 — Parent Namespace Guard / Transaction Boundary Repair Implementation

`PASS_IMPLEMENTATION_OFFLINE_VALIDATION_ONLY`. Implemented frozen r2 Option A: the adapter passes the transaction-resolved attempt root explicitly; the parent rejects a missing, foreign or incorrectly reserved root before attempt claim or case access, then uses the same root for both authorization checks and exclusive output writes. Historical global evaluation directories no longer produce false collisions. Journal commit semantics, exactly-once claim, namespace ownership, collision and output overwrite guards remain intact. r8 is the new future-authorization runner freeze (`evaluation/v1_2_3/step9_63c_r3_runner_freeze.json`, SHA-256 `86be96061d8c1cfbf769e21aac388cf2a308f53f6380f67c401d4c64b0bf4e6b`); r7 remains historical and immutable.

Thirteen new synthetic scenarios and 217 focused offline tests passed, zero failures/errors; `py_compile` passed. Current V3 Agent and all frozen evaluation identities match the r8 binding. All 55 historical pins match; the Step 9.58 gap remains `PRESENT_AND_DOCUMENTED`. The old committed failed transaction, reservation marker, authorization and attempt are preserved and non-reusable; the old journal and marker SHA-256 values remain `76afd557e4559c50090e9e4939a2e52746cbaefff1d4d6bd886206798b2e96fa` and `37179292afafb149971961f5d50c82bf2ff42f1bfac9f7db56e5701e3017c7e9`. No new authorization/attempt/formal namespace, model/Agent/RAG evaluation or V4 case execution occurred. `READY_FOR_FRESH_AUTHORIZATION_LIFECYCLE = YES` is infrastructure eligibility, not authorization. Independent audit, synthetic report, historical audit, freeze and report are in `evaluation/v1_2_3/`.

## Step 9.63c-r4 — Fresh r8 Authorization Audit & Issue

`PASS_AUTHORIZATION_ISSUED_NOT_CONSUMED`. Independently recomputed all 12 r8 freeze file-member hashes (zero mismatches), current V3 Agent identity, frozen evaluation identities, exact 40-case set/order and 10/10/10/10 task distribution. All 55 historical pins matched with the immutable lifecycle-ledger prefix separately preserved; Step 9.58 provenance gap remains `PRESENT_AND_DOCUMENTED`.

Old executable V3 authorization count is zero by authoritative evidence: Step 9.54 and 9.56 authorization IDs have consumed attempt-ledger events, Step 9.59b and 9.62 have terminal retirement events, and Step 9.63a-r3 is irreversibly burned by its durably committed transaction despite its unchanged historical manifest showing `ISSUED_NOT_CONSUMED`. No old manifest, transaction, namespace or output was altered.

Issued one new r8-bound authorization, `auth-step9_63c_r4-4b2749ce10014634ac6de155d37ec6a9`, with prebound attempt `attempt-step9_63c_r4-190bb797874c468d9d16938e580b712a` and derived namespace `heldout-v4-treatment-v3-run-12010f8e581951edf749`. The immutable manifest is `evaluation/v1_2_3/step9_63c_r4_r8_authorization_manifest.json`, SHA-256 `f02cec713ce0a8aebc109ff898450f0365cf4f8b91b5330e08fae556cc83cc2a`. Read-only adapter and parent validation passed; this is the sole executable V3 authorization, unconsumed with count 0. No attempt, physical namespace, reservation or transaction journal was created. The older Step 9.62 active-authorizations helper uses a narrower filename glob; this audit used the complete authorization manifest set with ledgers, retirement events and transactions, and the future r8 preflight must do likewise.

Fresh Mac-local non-consuming connectivity preflight is required before any authorization consumption; none ran in this step. No DeepSeek/model/Agent/RAG evaluation or formal V4 case occurred. `READY_FOR_R8_MAC_LOCAL_FINAL_PRECLEARANCE = YES` means readiness for that separate preflight only. Independent manifest, audit and report are in `evaluation/v1_2_3/`.

## Step 9.63c-r5a — Preflight Artifact Collision Forensics

`PASS_READ_ONLY_FORENSICS_PROVENANCE_UNCONFIRMED`. The r5 target `evaluation/v1_2_3/step9_63c_r5_mac_local_final_preclearance.json` already exists (SHA-256 `9b4d2c5112b07698b57f149bdb2634b7ee193888f15c97cd65d6bb6c5a86889b`, filesystem birth 2026-10-06 11:12:51 EDT). Its parseable JSON claims a Mac-local r8 preflight PASS and binds the current authorization, attempt and namespace exactly, with DNS/TCP/TLS PASS and all non-consumption fields intact. The timestamp matches file creation, and offline tests target temporary files; a previous successful Mac invocation is plausible but not independently proven. No successful user-terminal transcript or creator attestation was found. Therefore collision classification is `CASE_E_UNKNOWN_PROVENANCE`; accepting this existing evidence is unsafe, and creating a fresh artifact later is not yet proven safe.

Read-only checks found the current authorization `ISSUED_NOT_CONSUMED`, count 0, with no current transaction journal, attempt, reservation, namespace, result, trace, or observed V4 case. The collision artifact was not changed, removed, moved, or rerun. No authorization was consumed and no model/Agent/RAG/V4 execution occurred during this forensic step. Detailed findings are in `step9_63c_r5a_preflight_artifact_collision_forensics.json` and `.md` under `evaluation/v1_2_3/`. `READY_FOR_R5_REPAIR_DECISION = YES` is a decision point only, not formal execution clearance.

## Step 9.63c-r5b — Preflight Provenance Resolution & Artifact Lifecycle Repair

`PASS_CODE_REPAIR_FAIL_CLOSED_PENDING_RUNNER_REFREEZE`. The old fixed-path PASS artifact is preserved at SHA-256 `9b4d2c5112b07698b57f149bdb2634b7ee193888f15c97cd65d6bb6c5a86889b`, matching r5a. The r5b request quoted a one-character-different SHA, recorded as an external request pin discrepancy; the file was not changed. Its timestamp, owner, inode and `com.apple.provenance` xattr do not prove a completed user Mac Terminal invocation. Available zsh history records the exact r5 command once but no result or exit code. Provenance remains `E_STILL_UNPROVEN`, and the old artifact is not formal execution evidence.

The r5 helper now uses fresh UUID4 `PREFLIGHT_ID` values and authorization-scoped, instance-specific evidence filenames; exclusive creation preserves every prior artifact. Synthetic tests write only under temporary directories. The formal entry now requires explicit preflight file/ID/SHA-256 and checks exact authorization, runner, Agent, attempt, namespace, Mac-local PASS, transport/certificate, no-consumption, and post-issuance timestamp bindings. This changed one r8 frozen member: `scripts/run_step9_63_v3_formal_execution.py` now hashes to `a550c2a4cc9e8081dcaa897b19dfea26602120c528de3130fa2d304a4c76836f`, not its r8 pin `95cfa6009ca934ca7007a960a26e1d2af2b5bdf55f9089ca5875b02ad699189d`. The unchanged r8 freeze and r4 authorization cannot be used with the modified runner. No new freeze or authorization was created; the old authorization remains unconsumed, count 0, with no attempt or namespace.

Eighty-seven focused offline tests and `py_compile` passed; no real connectivity or DeepSeek/model/Agent/RAG/V4 execution occurred. No old artifact was deleted or overwritten. `READY_FOR_NEW_R5_MAC_LOCAL_PREFLIGHT = NO` pending separate runner refreeze and authorization lifecycle decision. Independent provenance, lifecycle audit and report artifacts are in `evaluation/v1_2_3/`.

## Step 9.63c-r5c — Fail-Closed Old Artifact Pin Precheck

`FAIL_CLOSED_OLD_R5_ARTIFACT_REQUEST_PIN_MISMATCH` before any retirement or freeze mutation. The r5c request again specified the old r5 artifact SHA-256 as `9b4d2c5112b07698b57f149bdb2634b7ee193888f15c97ca65d6bb6c5a86889b`, but the preserved file computes to `9b4d2c5112b07698b57f149bdb2634b7ee193888f15c97cd65d6bb6c5a86889b`, matching both r5a and r5b local records. The discrepancy is one character in the requested pin, not evidence of artifact modification. The required `OLD_R5_ARTIFACT_SHA256_MATCH = YES` cannot be claimed.

Read-only checks found the r8 authorization still `ISSUED_NOT_CONSUMED`, consumed `NO`, count 0, with no attempt, namespace, or reservation. One r8 freeze member (`scripts/run_step9_63_v3_formal_execution.py`) differs from its frozen hash, so the current runner cannot execute the old authorization. All 55 historical pins still match, and Step 9.58 provenance gap remains `PRESENT_AND_DOCUMENTED`. No retirement event, r9 freeze, new authorization, Mac preflight, HTTP request, model/Agent/RAG call, or formal V4 case was created. The fail-closed audit is in `step9_63c_r5c_fail_closed_precheck.json` and `.md`; continuation requires explicit resolution of the incorrect request pin, not a historical file edit or hash-gate bypass.

## Step 9.63c-r5c1 — Old R5 Artifact SHA Comparison Forensics

`PASS_READ_ONLY_FORENSICS_REQUEST_PIN_VALUE_MISMATCH_CONFIRMED`. The original r5c requested pin is `9b4d2c5112b07698b57f149bdb2634b7ee193888f15c97ca65d6bb6c5a86889b`; the exact artifact's raw-byte SHA-256 is `9b4d2c5112b07698b57f149bdb2634b7ee193888f15c97cd65d6bb6c5a86889b`. Both are 64-character ASCII hex strings, but character 48 differs (`a` requested versus `d` actual). No whitespace, case, Unicode normalization, or type issue explains it. The persisted r5c JSON lines 9–12 recorded these separate operands and `false`; no production comparison function exists. The r5c1 user's restatement repeats the requested value as the purported actual value, whereas the stored r5c report displays distinct values. Root cause is `B_REQUEST_PIN_VALUE_MISMATCH`, not a code-comparison bug.

The r5a and r5b hashes match current raw bytes, so old-artifact byte integrity passes; provenance is still `E_STILL_UNPROVEN` and the artifact remains unsuitable for formal execution. The old authorization stays issued/unconsumed, count 0. No retirement, r9 freeze, new authorization, attempt, namespace, HTTP/model/Agent/RAG activity or V4 case occurred. All 55 historical pins still match. The forensic JSON and report are `step9_63c_r5c1_sha_comparison_forensic.json` and `step9_63c_r5c1_sha_comparison_forensic_report.md`. `READY_FOR_R8_RETIREMENT_AND_R9_FREEZE = NO` until a later instruction resolves the external pin.

## Step 9.63c-r5c2 — Fail-Closed r9 Freeze Viability Precheck

`FAIL_CLOSED_R9_FREEZE_BINDING_INCOMPATIBILITY`. The corrected old-r5 artifact SHA-256 over raw bytes matches the r5a and r5b records: `9b4d2c5112b07698b57f149bdb2634b7ee193888f15c97cd65d6bb6c5a86889b`. Its provenance remains `E_STILL_UNPROVEN` and it is not formal execution evidence. The V3 Agent, frozen evaluation identities and all 55 historical pins match.

Before any irreversible retirement append, a deterministic r9 viability blocker was found. The formal entry and V3 adapter still hard-code the r8 freeze path/revision, so an r9 authorization would be rejected even if a static r9 freeze JSON were created. The available instance-scoped preflight producer is also bound to the old r8 authorization. Moreover, the current historical-pin helper demands the lifecycle ledger's exact pre-retirement whole-file length/hash and would reject a valid append-only retirement extension. The r5c2 instruction requires fail-closed reporting rather than changing r5b production repair when such freeze-construction work is needed. No production code was changed, and no retirement event, r9 freeze, fresh authorization, attempt, namespace, Mac preflight, HTTP/model/Agent/RAG evaluation or V4 case was created.

The old r8 authorization remains `ISSUED_NOT_CONSUMED`, consumed `NO`, count 0, with no attempt or namespace. One of 12 r8 freeze members differs from its pin, making this lifecycle-active authorization non-executable with current code. `READY_FOR_FRESH_R9_AUTHORIZATION_ISSUE = NO`. An explicitly authorized follow-up must repair coherent r9 binding and append-compatible historical verification before retirement/freeze eligibility is retried. Audit: `evaluation/v1_2_3/step9_63c_r5c2_fail_closed_precheck.json`; report: `step9_63c_r5c2_report.md`.

## Step 9.63c-r5c3 — Bootstrap Dependency Repair Design

`PASS_DESIGN_ONLY_BOOTSTRAP_DEPENDENCIES_IDENTIFIED`. Read-only call-graph inspection confirmed r8 hard bindings in the formal entry and V3 identity adapter, r8/old-authorization binding in the available r5 Mac preflight, and an incompatible whole-current-ledger length/SHA equality in `historical_pins_match()` despite its separate historical-prefix check. The retirement helper itself does not compare against the current runner: it validates the pinned lifecycle contract and determination, immutable issued/unconsumed manifest, and absence of transaction/attempt/reservation/namespace under the shared lock, then appends and fsyncs one terminal event. No dedicated freeze-builder or zero-active-authorization gate in a freeze builder was found; active-auth checks apply to authorization eligibility, not proven passive freeze creation.

Recommended design: independent lifecycle authority with proof of the old manifest's historical r8 freeze binding; passive r9 freeze before r8 retirement; then prefix-length + prefix-SHA historical pin validation; fresh r9 authorization only in a later separate step. Keep retirement distinct from consumption, prohibit r8-to-r9 migration, and preserve `TRANSACTION_RESOLVED_EXECUTION_NAMESPACE`. Twenty synthetic regressions are specified but not run. No production code or tests were changed/run; no retirement event, r9 freeze, authorization, attempt, namespace, Mac preflight, HTTP/model/Agent/RAG activity, or V4 case occurred. The old authorization remains unconsumed (count 0), and the Step 9.58 provenance gap and unknown provenance of the old r5 artifact remain documented. Details: `evaluation/v1_2_3/step9_63c_r5c3_bootstrap_dependency_analysis.json`, `step9_63c_r5c3_bootstrap_repair_design.json`, `step9_63c_r5c3_synthetic_test_plan.json`, and `step9_63c_r5c3_report.md`.

## Step 9.63c-r5c4 — Bootstrap Repair Implementation

`PASS_BOOTSTRAP_REPAIR_AND_REFREEZE`. The runner identity bootstrap cycle was resolved with a centralized current-freeze pointer, r9 freeze, append-compatible lifecycle prefix pinning (1,161-byte prefix SHA-256 `ca168f6939c4697a7a7bccc0b365b414d9a0e632f40de4242eb0a47e2d985285`), and retirement authority that validates the old authorization's own r8 freeze proof without requiring current-runner equality. Single namespace authority remains `TRANSACTION_RESOLVED_EXECUTION_NAMESPACE`.

New runner freeze: `evaluation/v1_2_3/step9_63c_r5c4_runner_freeze_r9.json`, 19 members, SHA-256 `4af44711fe984b69c81fc4730f0ca3f69058d1f69123b3b2bd7a570356166f97`; current runner resolves and matches. V3 Agent SHA remains `085d338ed95bbef7370c41cf97ca0d6653ffdfd2f1c924eef4b7123dfdea4607`. The old r8 authorization was append-only retired as `RETIRED_UNCONSUMED_NON_REUSABLE` (event `retire-c1184275045745ce86c084f0106b4632`), while remaining unconsumed/count 0; it is not executable or reusable. Active executable authorization count is 0. All 55 historical pins passed with 0 mismatches; Step 9.58 provenance gap remains `PRESENT_AND_DOCUMENTED`, and the old r5 preflight remains `E_STILL_UNPROVEN`.

The focused offline suite passed: 94 tests, 0 failures, 0 errors (22 new synthetic tests). No new authorization, attempt, namespace, Mac-local preflight, HTTP request, model/Agent/RAG evaluation, formal V4 case, adjudication, aggregation, comparison, or V5 access occurred. V3 Agent, V4 benchmark, and evaluation semantics were unchanged. Infrastructure gates are ready for a separate authorization-only step (`READY_FOR_FRESH_AUTHORIZATION_ISSUE = YES`); no authorization was issued here. See `evaluation/v1_2_3/step9_63c_r5c4_bootstrap_repair_report.md`, `step9_63c_r5c4_bootstrap_repair_audit.json`, `step9_63c_r5c4_lifecycle_transition_audit.json`, and `step9_63c_r5c4_synthetic_test_manifest.json`.

## Step 9.63c-r5c5 — Fresh r9 Authorization Issue

`FAIL_CLOSED_ACTIVE_AUTHORIZATION_EXISTS`. The current r9 freeze passed (19 members; file SHA-256 `4af44711fe984b69c81fc4730fca3f69058d1f69123b3b2bd7a570356166f97`; member aggregate `bd3414b95b88c6ed932f9458a73323ea0f79806ba5ae064ca4a796ec7750ed5c`), as did the V3 Agent, frozen identities, V4 40-case set/order/distribution, and all 55 historical pins. Step 9.58 provenance remains `PRESENT_AND_DOCUMENTED`; the r8 authorization remains retired.

Issuance was blocked by a distinct active Step 9.63a-r3 authorization, `auth-step9_63a_r3-d53bbaa35b1e4522bc4a5f57d42c8ef7`, at `evaluation/v1_2_3/step9_63a_r3_v3_authorization_manifest.json` (SHA-256 `1514438d0afe23a39de2a696e9ea5bd97faac4dd546a88cdbd7b91f450046345`). It remains `ISSUED_NOT_CONSUMED`, unconsumed/count 0, with no retirement event. The observed active executable authorization count was 1, violating the required zero-active precondition. No new authorization/attempt/namespace IDs were allocated; no authorization or issuance event was created. No preflight, connectivity probe, HTTP/model/Agent/RAG activity or V4 case occurred. Historical artifacts and the active authorization were not modified. A separate lifecycle decision is required before retrying issuance. Audit: `evaluation/v1_2_3/step9_63c_r5c5_authorization_issue_audit.json`; report: `evaluation/v1_2_3/step9_63c_r5c5_authorization_issue_report.md`.

## Step 9.63c-r5c5a — Authorization Lifecycle Reconciliation

`PASS_READ_ONLY_LIFECYCLE_ROOT_CAUSE_IDENTIFIED`. The r5c4 retirement event is valid and exists at bytes 2,385–3,856 (1-based inclusive) of the sole `evaluation/v1_2_3/authorization_lifecycle_events.jsonl`; it retired `auth-step9_63c_r4-4b2749ce10014634ac6de155d37ec6a9` (r8), not the r5c5 target `auth-step9_63a_r3-d53bbaa35b1e4522bc4a5f57d42c8ef7` (r7). No duplicate/missing retirement event or alternate lifecycle JSONL ledger was found.

The target r7 manifest remains immutable `ISSUED_NOT_CONSUMED`, but its transaction journal is durably `PREPARED → COMMITTING → COMMITTED` with `authorization_irreversibly_burned=true`, and its exact namespace reservation marker exists. There is no attempt-ledger consumption projection, `ATTEMPT_CLAIMED`, or `CASE_STARTED`; the namespace contains only the reservation marker and no case outputs/traces. The earlier Step 9.63c-r1 forensic audit already documents this committed/burned pre-case state. Thus the r5c5 legacy `active_authorizations()` scanner overcounts by ignoring `.execution_transactions`; it sees stale manifest status plus no attempt consumption or retirement event and reports 1. Current r9 executability is 0, but one committed pre-case transaction requires manual no-resume disposition. r5c4's report says active count 0 without recording its enumeration method, so that count's derivation is not reproducible from that report alone.

Lifecycle facts are composite rather than held in one physical source: manifests record issuance identity, the lifecycle JSONL records retirement, transaction journals record irreversible commit/burn, attempt ledgers project consumption, and namespace markers record reservation. The r5c5 scanner and current formal/issuer paths do not all reduce the transaction evidence identically. Root cause: `LEGACY_ACTIVE_AUTH_ENUMERATOR_OMITS_AUTHORITATIVE_COMMITTED_TRANSACTION_BURN`. All 55 historical pins match; Step 9.58 provenance gap remains `PRESENT_AND_DOCUMENTED`. No repair, retirement append, authorization issuance, attempt/namespace creation, preflight, model/Agent/RAG/HTTP call, or V4 case occurred. `READY_TO_RETRY_R5C5 = NO`; implement a separately authorized unified fail-closed reducer and preserve the committed transaction/marker without auto-resume. Artifacts: `evaluation/v1_2_3/step9_63c_r5c5a_authorization_lifecycle_reconciliation_audit.json`, `step9_63c_r5c5a_authorization_lifecycle_reconciliation_report.md`, and `step9_63c_r5c5a_authorization_inventory.json`.

## Step 9.63c-r5c5b — Unified Fail-Closed Lifecycle Reducer Repair

`PASS_LIFECYCLE_REDUCER_REPAIR_OFFLINE_VALIDATED`. `scripts/authorization_lifecycle.py` now owns the single read-only lifecycle reducer; legacy `active_authorizations()`, the r5 current preflight, issuance gating, and pre-transaction execution authorization validation call through that reducer. Derived states include executable issuance, retirement, committed/burned pre-case, consumed, and inconsistent fail-closed. A durable COMMITTED burn is never resumed or treated as executable. Unknown/contradictory evidence fails closed.

The r7 target derives to `COMMITTED_BURNED_PRE_CASE_NON_REUSABLE`; the r8 target derives to `RETIRED_UNCONSUMED_NON_REUSABLE`. Both are non-executable/non-reusable and excluded from active authorization. Active executable authorization count is 0. The r7 manifest SHA remains `1514438d0afe23a39de2a696e9ea5bd97faac4dd546a88cdbd7b91f450046345`; its transaction journal SHA remains `76afd557e4559c50090e9e4939a2e52746cbaefff1d4d6bd886206798b2e96fa`. Neither bytes nor lifecycle history were altered. All 55 historical pins match; the Step 9.58 provenance gap remains documented.

Because r9 included changed lifecycle members, it is superseded for future authorization. New r10 freeze: `evaluation/v1_2_3/step9_63c_r5c5b_runner_freeze_r10.json`, SHA-256 `d24244235e51e7bf6c8567880c654fe3fd73b87fa1bfe1ab0f10dfdc94db2693` (20 members); current pointer and all member hashes verify. Offline validation passed 21 new synthetic tests plus 47 focused regressions (68 total), with 0 failures/errors; syntax compilation passed. No Agent/benchmark/scoring/metrics/evaluation semantics changed. No authorization, attempt, namespace, preflight, network request, model/Agent/RAG evaluation, V4 case, adjudication, aggregation, comparison, or V5 activity occurred. See `evaluation/v1_2_3/step9_63c_r5c5b_lifecycle_reducer_repair_audit.json`, `evaluation/v1_2_3/step9_63c_r5c5b_lifecycle_reducer_repair_report.md`, and `evaluation/v1_2_3/step9_63c_r5c5b_lifecycle_reducer_test_matrix.json`.

## Step 9.63c-r5c6 — Fresh r10 Authorization Issuance

`PASS_FRESH_R10_AUTHORIZATION_ISSUED_NOT_CONSUMED`. Read-only eligibility passed before ID generation: r10 freeze/member checks, Agent and frozen evaluation/validator identity, exact 40-case set/order/distribution, historical pins 55/55, and Step 9.58 provenance status all matched. The unified reducer retained r7 as `COMMITTED_BURNED_PRE_CASE_NON_REUSABLE` and r8 as `RETIRED_UNCONSUMED_NON_REUSABLE`; active executable count before issuance was 0.

One fresh authorization was exclusively created: `evaluation/v1_2_3/step9_63c_r5c6_r10_v3_authorization_manifest.json`, SHA-256 `beac52d1ed3bc11efa02b1a924a8abc7b210171bf5cc1b7910011a6ef9741241`. `AUTHORIZATION_ID=auth-step9_63c_r5c6-aff5c4b96bb74278a14d3fd08bf8a84e`; `ATTEMPT_ID=attempt-step9_63c_r5c6-3401b701486c4fdeb4019b461d024bd4`; `NAMESPACE_ID=heldout-v4-treatment-v3-run-8e4bd0fd803f31b9e0da`. Post-issuance reducer state is `ISSUED_EXECUTABLE`, executable true, reducer reusable true (eligible for its single one-shot use only, not replay); active executable count is 1. Consumption remains false/count 0.

Post-issuance offline regression run passed 67 applicable tests with 0 failures/errors. The pre-issuance-only assertion `test_18_active_count_is_zero` was excluded; the correct post-issuance count of 1 was independently validated. An initial unfiltered run had one expected stale-state assertion failure. No attempt ledger, namespace directory/marker, transaction, result/trace, preflight, connectivity probe, HTTP, model/Agent/RAG call, or V4 case occurred. The authorization awaits a separate Step 9.63c-r5c7 authorization. Audit/report: `evaluation/v1_2_3/step9_63c_r5c6_r10_authorization_issuance_audit.json` and `step9_63c_r5c6_r10_authorization_issuance_report.md`.

## Step 9.63c-r5c7 — R10 Mac-local final non-consuming preflight preparation

`PASS_READY_FOR_MAC_LOCAL_NON_CONSUMING_PREFLIGHT`. Created the separate Mac-only preflight script `scripts/preflight_step9_63c_r5c7_mac_local.py` (SHA-256 `75d8c52e50874afe1d6202a39bd636b1888937cf854b249b19c681188229cc86`) and 5 focused offline tests. `py_compile` and all tests passed. An offline snapshot verified current r10 (20 freeze members; zero mismatches), Step 9.63c-r5c6 authorization `auth-step9_63c_r5c6-aff5c4b96bb74278a14d3fd08bf8a84e` remains `ISSUED_EXECUTABLE`, unconsumed/count 0; its exact attempt and namespace do not exist and no transaction is present. The 40-case identity/order and 10/10/10/10 task distribution match; all 55 historical pins match and Step 9.58 remains `PRESENT_AND_DOCUMENTED`.

The new preflight ID is `preflight-step9_63c-r10-10c2f1537cc44da7b40e95a1ea819028`; its instance-scoped output target was absent at preparation and is written only with exclusive create plus fsync. Work did not execute DNS/TCP/TLS, HTTP, model/Agent/RAG, or any V4 case; no authorization was consumed and no attempt/namespace/transaction was created. Preparation artifacts: `evaluation/v1_2_3/step9_63c_r5c7_preflight_preparation_audit.json` and `step9_63c_r5c7_preflight_preparation_report.md`.

## Step 9.63c-r5c7a — Preflight error read-only forensics

`PASS_READ_ONLY_FORENSICS_ROOT_STAGE_UNKNOWN`. The supplied Mac Terminal output reports only `FAIL_CLOSED_PREFLIGHT_ERROR`. Source inspection confirms a broad `except Exception` maps uncaptured failures to that generic status without preserving exception type/message/stage. No matching failure log, stderr capture, partial artifact, or preflight target exists; therefore the concrete stage/type/message are unknown and confidence is low. No rerun was made. Read-only lifecycle reduction confirms authorization `auth-step9_63c_r5c6-aff5c4b96bb74278a14d3fd08bf8a84e` remains `ISSUED_EXECUTABLE`, unconsumed/count 0; attempt, namespace, reservation, and transaction are absent. Historical pins remain 55/55 with zero mismatches; Step 9.58 provenance remains `PRESENT_AND_DOCUMENTED`. Root cause class is diagnostic suppression, not an identified network or execution defect. Repair is required but limited to diagnostics; safe retry remains NO pending that repair. Artifacts: `evaluation/v1_2_3/step9_63c_r5c7a_preflight_error_forensics.json` and `step9_63c_r5c7a_preflight_error_forensics_report.md`.

## Step 9.63c-r5c7b — Diagnostic instrumentation repair

`PASS_DIAGNOSTIC_REPAIR_OFFLINE_VALIDATED`. The Mac-local preflight now records a stable stage, exception type, and sanitized diagnostic message while preserving fail-closed outputs and all non-consuming invariants. DNS/TCP/TLS instrumentation is an optional stage callback around the existing transport calls; call ordering and network semantics are unchanged. Runtime credential presence uses process-environment presence only. The existing `load_dotenv(absolute_path, override=False)` behavior is retained for a future separately authorized Mac-local run; this repair does not call `dotenv_values()` or directly read `.env`.

Offline verification: 13 focused synthetic diagnostics tests passed; 33 applicable offline regression tests passed; `py_compile` passed. Tests mock all external/network effects. An unfiltered exploratory run included the stale pre-issuance-only assertion `test_18_active_count_is_zero` and it failed because the r5c6 authorization is intentionally the one active executable authorization; the assertion was excluded from the final applicable regression selection and is documented in the audit. Both modified preflight files are outside the 20-member r10 freeze; all frozen member hashes remain valid, so `RUNNER_EXECUTION_IDENTITY_CHANGED=NO` and no runner re-freeze is required. The prior r5c7a credential-handling event is recorded as `PROCESS_BOUNDARY_VIOLATION=DOTENV_VALUES_PARSED_DURING_READ_ONLY_FORENSICS`; no secret was printed, persisted, or known disclosed. No preflight rerun, network call, inference, authorization consumption, attempt/namespace/transaction creation, or V4 case occurred. Audit/report: `evaluation/v1_2_3/step9_63c_r5c7b_diagnostic_repair_audit.json` and `step9_63c_r5c7b_diagnostic_repair_report.md`.

## Step 9.63c-r5c7c — Instrumented Mac-local preflight retry preparation

`PASS_READY_FOR_INSTRUMENTED_MAC_LOCAL_PREFLIGHT`. Read-only eligibility passed: current r10 freeze (20 members) and hash match; r5c6 authorization state `ISSUED_EXECUTABLE`, active count 1, unconsumed/count 0; attempt, namespace, reservation, and transaction absent; historical pins 55/55 with zero mismatches; Step 9.58 gap remains `PRESENT_AND_DOCUMENTED`. Generated fresh instance ID `preflight-step9_63c-r10-c0f9957584c9443fa8ef5a70b3712bed`, distinct from the failed r5c7 invocation. New target `evaluation/v1_2_3/step9_63c_r5c7c_preflight-step9_63c-r10-c0f9957584c9443fa8ef5a70b3712bed_mac_local_final_preclearance.json` is absent and exclusive-create only. The diagnostics-repaired script now reports r5c7c status names. Offline validation passed: 13 focused synthetic tests, 33 applicable regressions, and py_compile. Work did not run preflight or perform network/inference/V4 activity. Audit/report: `evaluation/v1_2_3/step9_63c_r5c7c_retry_preparation_audit.json` and `step9_63c_r5c7c_retry_preparation_report.md`.

## Step 9.63c-r5c7d — Mac-local import-context root-cause and repair

`PASS_IMPORT_CONTEXT_REPAIR_OFFLINE_VALIDATED`. The reported `ModuleNotFoundError: No module named 'scripts'` came from direct-script `sys.path[0]` being the `scripts/` directory while the repository root was absent. The first failing import was `from scripts import authorization_lifecycle as lifecycle` at line 198 in the failed revision's `_snapshot`. The project’s established invocation convention is direct script execution with an in-file `ROOT = Path(__file__).resolve().parents[1]` bootstrap; the formal runner, V3 adapter, and 9.63b preflight use this convention. The r5c7 wrapper now matches it.

Two focused synthetic import-context tests passed, 18 related offline regression tests passed, and `py_compile` passed. Tests reproduced direct-script path context, verified helper imports and read-only R10 freeze validation, and compared module/direct identity snapshots without invoking main/network. Exactly two code/test files changed; neither is an r10 freeze member. All 20 freeze members match, so runner execution identity is unchanged and no new runner freeze is required. The failed r5c7c preflight identity must not be reused; a later preparation must assign a new ID. No real preflight, authorization consumption, attempt/namespace/transaction, model/Agent/RAG/HTTP call, or V4 case occurred. Audit/report: `evaluation/v1_2_3/step9_63c_r5c7d_import_context_repair_audit.json` and `step9_63c_r5c7d_import_context_repair_report.md`.

## Step 9.63c-r5c7e — Fresh Mac-local preflight preparation

`PASS_READY_FOR_FRESH_MAC_LOCAL_PREFLIGHT`. Read-only validation confirmed the current r10 freeze has 20 members and zero member mismatches; the frozen V3 Agent/evaluation identities, exact 40-case set and order, 10/10/10/10 distribution, all 55 historical pins, and documented Step 9.58 provenance gap match. The unified lifecycle reducer reports the sole r5c6 authorization as `ISSUED_EXECUTABLE`, unconsumed/count 0; no attempt, namespace/reservation, or transaction exists.

The direct-script `__file__` repository-root bootstrap is validated; `PYTHONPATH` is unnecessary. The failed r5c7c invocation is non-reusable. Fresh ID `preflight-step9_63c-r10-7decee88a4c8439fb3f30ffb68240b31` is bound to absent target `evaluation/v1_2_3/step9_63c_r5c7e_preflight-step9_63c-r10-7decee88a4c8439fb3f30ffb68240b31_mac_local_final_preclearance.json`; preparation did not create it. Forty-two focused offline tests passed with zero failures/errors and `py_compile` passed. The stale pre-issuance-only lifecycle assertion was excluded because the active r5c6 authorization correctly makes the current active count one. The canonical manual Mac command is `cd /Volumes/Elements/cbti-doctor-main && .venv/bin/python scripts/preflight_step9_63c_r5c7_mac_local.py`. Work did not run preflight/network/HTTP/inference, consume authorization, create attempt/namespace/transaction, or execute V4. Details: `evaluation/v1_2_3/step9_63c_r5c7e_preflight_preparation_audit.json` and `evaluation/v1_2_3/step9_63c_r5c7e_preflight_preparation_report.md`.

## Step 9.63c-r5c8 — Final execution preparation audit

`FAIL_CLOSED_FROZEN_PREFLIGHT_CONTRACT_MISMATCH`. Disk revalidation confirms the r10 freeze (20/20 members), formal entry, Agent and frozen evaluation identities, 40-case identity/order/distribution, r5c6 lifecycle state (`ISSUED_EXECUTABLE`, unconsumed/count 0, active count 1), and retired/burned r7/r8 states. No attempt, namespace/reservation, or transaction exists. The pinned r5c7e artifact raw-byte SHA-256 matches `f07d8380e0d445938e0a4bd7b212380459a983ccfe8f04bc49ab2996b43cf4b7`, its bound identities match, and its stored DNS/TCP/TLS checks are all PASS; Work did not repeat connectivity checks.

The frozen formal entry's read-only validator rejects that artifact with `invalid preflight instance identity`: it expects a different preflight ID pattern and authorization-scoped path, plus different uppercase contract fields. Therefore artifact hash/content identity is confirmed but frozen-consumer contract compatibility is NO. No formal command was generated. Historical pins remain 55/55 with zero mismatches under `PREFIX_LENGTH_PLUS_PREFIX_SHA256`; Step 9.58 provenance remains documented. Atomic-commit, lifecycle-reducer, production-journal, zero-unguarded-path, and crash-reconciliation prerequisites match frozen records. No authorization was consumed, and no attempt, namespace, transaction, case, inference, HTTP, adjudication, aggregation, comparison, or V5 activity occurred. Audit/report: `evaluation/v1_2_3/step9_63c_r5c8_final_execution_preparation_audit.json` and `evaluation/v1_2_3/step9_63c_r5c8_final_execution_preparation_report.md`.

## Step 9.63c-r5c8a — Read-only preflight contract forensics

`PASS_READ_ONLY_PREFLIGHT_CONTRACT_FORENSICS`. The actual r5c7e producer is `scripts/preflight_step9_63c_r5c7_mac_local.py::main`; it emits 57 top-level fields with no declared `schema_version`. The formal consumer path is `main(--execute-formal-v4) → execute_formal → preflight top-level guard → validate_preflight_evidence → adapter.run`. The normal formal-entry guard first rejects at `run_step9_63_v3_formal_execution.py:178` because producer `status=PASS_MAC_LOCAL_FINAL_NON_CONSUMING_PRECLEARANCE` differs from required `PASS_NON_CONSUMING_PREFLIGHT`; `dns_ready`, `tcp_ready`, and `tls_ready` are also absent. The prior `invalid preflight instance identity` comes from directly invoking the later validator: its first predicate at lines 51–53 rejects the r10-style ID before path/field/connectivity checks. The 19-item matrix has 13 mismatches; 21 exact uppercase keys required by that validator are absent. Six nested evaluation identity hashes have the frozen values, but the validator does not inspect those nested fields itself.

Authority is classified `A`: the formal consumer and predecessor r5 preflight producer/schema are pinned by r10 freeze and r5b audit/tests; current r5c7 producer is not an r10 member and has no schema version. The consumer has a hybrid earlier guard and later validator, and both reject this artifact. Recommended design-only repair is Option A: adapt the producer to the frozen path/schema and both gates. This would not modify r10 or require a new runner freeze/authorization, but would require a fresh Mac preflight; preserve r5c7e as historical evidence. No repair was implemented. Authorization remains unconsumed/count 0; active count is 1; no attempt/namespace/transaction exists; historical pins remain 55/55, Step 9.58 gap remains documented. No model/Agent/RAG/HTTP/V4 activity occurred. Audit, diff and report: `evaluation/v1_2_3/step9_63c_r5c8a_preflight_contract_forensic_audit.json`, `step9_63c_r5c8a_preflight_contract_diff.json`, and `step9_63c_r5c8a_preflight_contract_forensic_report.md`.

## Step 9.63c-r5c8b — Frozen-consumer-compatible preflight producer repair

`PASS_PREFLIGHT_PRODUCER_CONTRACT_REPAIR_OFFLINE_VALIDATED`. Only non-frozen producer `scripts/preflight_step9_63c_r5c7_mac_local.py` and focused tests changed. Producer now creates a fresh UUID4 ID in the frozen `preflight-step9_63c_r5-<tag>-<32 hex>` format and the authorization-scoped path expected by the consumer. It emits all exact uppercase fields for `validate_preflight_evidence` plus the lower-case status/readiness values checked by `execute_formal`'s earlier guard. DNS readiness requires all five DNS results; TCP readiness additionally requires TCP PASS; TLS readiness additionally requires TLS PASS and certificate present+verified. These are derived from the same transport evidence.

Twenty-five contract tests use the frozen validator directly and pass; focused import/preparation/preflight/diagnostic tests also pass, for 48 passing tests total. `py_compile` passes. A legacy r5b suite attempt produced 17 pre-existing fixture setup errors because the old `preflight_step9_63c_r5_mac_local` module does not expose the fixture's expected `AUTH_ID`; that untouched historical producer/test is not included in the passing count. All 20 r10 members still match with zero mismatches; current runner, Agent, and frozen evaluation identities remain valid. No new freeze is needed. Old r5c7e artifact remains byte-identical at SHA-256 `f07d8380e0d445938e0a4bd7b212380459a983ccfe8f04bc49ab2996b43cf4b7`; it remains historical connectivity evidence but is not formal-consumer compatible.

Authorization remains `ISSUED_EXECUTABLE`, unconsumed/count 0, with active count 1. No attempt, namespace/reservation, transaction, fresh preflight artifact, network call, model/Agent/RAG/HTTP execution, or V4 case occurred. Ready for a separate fresh contract-compatible preflight preparation: YES; formal execution is not authorized by this step. Artifacts: `evaluation/v1_2_3/step9_63c_r5c8b_preflight_producer_contract_repair_audit.json`, `step9_63c_r5c8b_preflight_producer_contract_repair_report.md`, and `step9_63c_r5c8b_contract_test_matrix.json`.

## Step 9.63c-r5c8c — Fresh contract-compatible preflight preparation

`FAIL_CLOSED_NO_CLI_IDENTITY_BINDING`. Read-only identity checks passed: current r10 freeze 20/20 members, current V3 Agent and frozen evaluation identities, exact 40-case set/order and 10/10/10/10 distribution, 55/55 historical pins, and the documented Step 9.58 provenance gap. The unified lifecycle reducer reports the sole authorization as `ISSUED_EXECUTABLE`, unconsumed/count 0; no attempt, namespace/reservation, or transaction exists. The r5c8b producer contract remains compatible (zero mismatch); its 25 offline validator tests passed, including producer-generated fixture acceptance.

Fresh ID `preflight-step9_63c_r5-r5c8b-46ff20fd22b349c19d359d7903b35c70` maps to absent target `evaluation/v1_2_3/step9_63c_r5_auth-step9_63c_r5c6-aff5c4b96bb74278a14d3fd08bf8a84e_preflight-step9_63c_r5-r5c8b-46ff20fd22b349c19d359d7903b35c70_mac_local_preclearance.json`. The producer has no CLI identity/target parameters and generates both internally in `main()`, so no command can bind this prepared identity using the actual interface. Per fail-closed instruction, producer was not changed and no command was issued. No Work preflight, credential access, network/HTTP/model/Agent/RAG activity, authorization consumption, attempt/namespace/transaction, or formal V4 case occurred. Artifacts: `evaluation/v1_2_3/step9_63c_r5c8c_fresh_preflight_preparation_audit.json` and `step9_63c_r5c8c_fresh_preflight_preparation_report.md`.

## Step 9.63c-r5c8d — Preflight invocation identity ownership

`PASS_INVOCATION_IDENTITY_OWNERSHIP_RESOLVED`. Code-level audit selected `OPTION_A_PRODUCER_OWNED`: the producer generates the fresh ID and authorization scoped target at invocation, then prints the actual ID/path/SHA. The frozen formal consumer requires all three explicitly at formal execution and compares them with the artifact; it does not require the ID before preflight. The authorization prebinds attempt/namespace only. Thus the r5c8c prepared ID was unnecessary; its historical fail-closed record remains unchanged. No CLI identity feature or new runner freeze is required.

Thirty-one offline tests passed, including runtime-generated fixture acceptance by the frozen validator and existing target collision rejection. UUID4 freshness plus exclusive target creation rejects existing-artifact collisions; failed invocations without artifacts have no persistent ID ledger. r10 remains 20/20 matched, all 55 historical pins match, the documented Step 9.58 gap remains, and the sole authorization is `ISSUED_EXECUTABLE`, unconsumed/count 0, with no attempt/namespace/reservation/transaction. No real preflight, network, inference, Agent/RAG evaluation, or V4 case occurred. Ready for a separate producer-owned preflight preparation. Artifacts: `evaluation/v1_2_3/step9_63c_r5c8d_invocation_identity_ownership_audit.json`, `step9_63c_r5c8d_invocation_identity_ownership_report.md`, and `step9_63c_r5c8d_test_matrix.json`.

## Step 9.63c-r5c8e — Producer owned fresh Mac local preflight preparation

`FAIL_CLOSED_HISTORICAL_INVOCATION_COLLISION_CHECK_NOT_PROVEN`. Read only checks passed for the r10 freeze (20/20), V3 Agent, frozen 40 case set/order/distribution, all 55 historical pins, and the documented Step 9.58 gap. The unified reducer reports one `ISSUED_EXECUTABLE` authorization, unconsumed/count 0; r7 is burned, r8 retired, and no attempt, namespace/reservation, or transaction exists. The producer generated offline fixture passes the frozen consumer (contract mismatch count 0); 41 focused offline tests and `py_compile` passed.

The producer checks the derived target path and writes exclusively, but it has no historical preflight invocation ID lookup. An earlier failed invocation that left no artifact is not detectable. Since this step explicitly requires that check and prohibits producer modification, no Mac Terminal command was issued. No Work preflight, network/HTTP/model/Agent/RAG activity, authorization consumption, formal artifact, or V4 case occurred. Audit and report: `evaluation/v1_2_3/step9_63c_r5c8e_producer_owned_preflight_preparation_audit.json` and `step9_63c_r5c8e_producer_owned_preflight_preparation_report.md`.

## Step 9.63c-r5c8f — Historical invocation collision proof repair

`PASS_HISTORICAL_INVOCATION_COLLISION_PROOF_OFFLINE_VALIDATED`. Forensics found no complete historical preflight invocation source: existing authorization, transaction, attempt and namespace histories do not record preflight IDs, while artifacts/audits miss a call that fails before artifact write. A minimal append-only registry was initialized at `evaluation/v1_2_3/step9_63c_r5c8f_preflight_invocations.jsonl` with zero real claims. The non-frozen producer now checks the registry and target independently under a file lock, then appends and fsyncs the ID claim before returning it. Failed calls after this claim remain non-reusable even without an artifact; malformed, unreadable or duplicate history fails closed. No secret or case data is recorded.

Sixteen new registry tests and 54 focused contract, diagnostics and lifecycle tests passed (70 total); `py_compile` passed. Current r10 freeze remains 20/20 with zero changed members; the frozen consumer, V3 Agent, evaluation identities, 55 historical pins and old preflight artifact remain unchanged. Authorization is still `ISSUED_EXECUTABLE`, unconsumed/count 0; no attempt, namespace/reservation or transaction exists. No real Mac preflight, network, model/Agent/RAG evaluation or V4 case occurred. Ready for a separate preflight preparation; no Terminal command was issued. Artifacts: `evaluation/v1_2_3/step9_63c_r5c8f_historical_invocation_collision_audit.json`, `step9_63c_r5c8f_historical_invocation_collision_report.md`, and `step9_63c_r5c8f_test_matrix.json`.

## Step 9.63c-r5c8g — Fresh registry aware Mac local preflight preparation

`PASS_READY_FOR_REGISTRY_AWARE_MAC_LOCAL_PREFLIGHT`. Read only qualification confirmed r10 20/20 members, V3 Agent, frozen 40-case set/order/distribution, 55/55 historical pins, documented Step 9.58 gap, and a single `ISSUED_EXECUTABLE` authorization, unconsumed/count 0. r7 is burned, r8 retired; no attempt, namespace/reservation or transaction exists. The new registry parses strictly and has one initialization row, zero real invocation claims, zero duplicate IDs, zero malformed entries and no credential content. The initialization row is not a preflight execution.

The producer owns the fresh ID and target at real invocation. It separately rejects historical ID and target collisions, fsyncs the claim before continuing, and its offline fixture passes the frozen consumer contract (41 fields, zero mismatch). The r5c8d freshness claim previously covered only existing target collision; this registry additionally covers failed invocations without artifacts. Seventy focused offline tests and `py_compile` passed. No code, freeze or historical artifact was changed in this step. Work did not generate an ID/target, run preflight/network/HTTP/model/Agent/RAG/V4, consume authorization, create attempt/namespace/transaction, or issue formal execution command. One canonical Mac Terminal producer command is recorded in the audit and supplied to the user separately. Audit and report: `evaluation/v1_2_3/step9_63c_r5c8g_fresh_registry_aware_preflight_preparation_audit.json` and `step9_63c_r5c8g_fresh_registry_aware_preflight_preparation_report.md`.

## Step 9.63c-r5c9 — Fresh Mac-local preflight handoff verification

`PASS_READ_ONLY_HANDOFF_READY_FOR_SINGLE_ATOMIC_FORMAL_EXECUTION`. The reported fresh artifact exists and its raw SHA-256 equals `fbb2f3dfe964bbe500459c4ba58e016f7318bd2ca61c439d902030fd3cb2f35a`; embedded ID and authorization scoped path match. The registry has one genesis row and exactly one real claim for this ID. The claim timestamp is after authorization issuance and before artifact creation. The frozen formal runner's actual `validate_preflight_evidence()` accepted the artifact, path, explicit ID and SHA, all frozen bindings, and recorded DNS/TCP/TLS evidence. Its earlier payload guard fields match as well.

Current r10 freeze remains 20/20, V3 Agent/evaluation identities and the exact 40-case set/order/distribution match, all 55 historical pins match, and the documented Step 9.58 gap is unchanged. The unified reducer still reports one `ISSUED_EXECUTABLE` authorization, unconsumed/count 0, with no attempt/namespace/reservation/transaction. The frozen argparse interface supports all required preflight binding flags and seven frozen hash flags. A single next-stage manual formal execution command is in the handoff report; Work did not run it, rerun preflight, send network/inference traffic, consume authorization or execute V4. Audit and report: `evaluation/v1_2_3/step9_63c_r5c9_handoff_audit.json` and `step9_63c_r5c9_handoff_report.md`.

## Step 9.63c-r5c10a — Post-failure transaction / authorization read-only forensics

The user reports the single formal Mac Terminal command failed with `UnicodeDecodeError` in `begin_and_commit → _find_identity → read_events`, at UTF-8 byte offset 37. Binary-only inspection identifies `evaluation/v4_runs/.execution_transactions/._auth-step9_63a_r3-d53bbaa35b1e4522bc4a5f57d42c8ef7.jsonl` as a 4,096-byte AppleDouble metadata companion, SHA-256 `b3f6f26076673352c35b796cdea465d173ef353978b1e6d5ae1417ee2cc25574`. The frozen scanner's `glob("*.jsonl")` matches that non-event file and calls `read_events` without filtering. Root cause is `A_TRANSACTION_SCANNER_READS_NON_EVENT_BINARY_FILE` (HIGH confidence); no file was removed or modified.

The current r5c6 journal is absent, with zero `PREPARED`, `COMMITTING`, `COMMITTED`, `ATTEMPT_CLAIMED` or `CASE_STARTED` events, so failure was before PREPARED and before the irreversible commit point. The unified lifecycle reducer reports `ISSUED_EXECUTABLE`, consumed `NO`, count `0`; nevertheless the frozen one-shot authorization forbids reuse/automatic retry, and this command must not be rerun. No exact attempt ledger, namespace/reservation, result or trace exists; cases started/completed/executed are all zero. The frozen call ordering did not reach case/model/Agent/RAG/HTTP inference. r10 freeze 20/20, V3 Agent/evaluation identities, all 55 historical pins, preflight and registry hashes still match; Step 9.58 provenance gap remains documented. `SAFE_TO_RERUN_FORMAL_COMMAND = NO`; `READY_FOR_REPAIR_DESIGN = YES`. Only read-only checks and these new audit/report/record artifacts were produced. See `evaluation/v1_2_3/step9_63c_r5c10a_post_failure_transaction_forensics.json` and `step9_63c_r5c10a_post_failure_transaction_forensics_report.md`.

## Step 9.63c-r5c10b — Transaction scanner repair design only

`PASS_DESIGN_ONLY_READY_FOR_REPAIR_IMPLEMENTATION`. The authoritative transaction event file is a direct regular non-symlink child named `<SAFE_ID authorization_id>.jsonl` with nonempty validated UTF-8 JSONL events and filename/event authorization binding; `.jsonl` suffix alone is insufficient. The r10 `_find_identity()` broad `glob("*.jsonl")` includes a verified AppleDouble `._` companion. Proposed minimal repair is a strict journal-path classifier before the unchanged `read_events()` and collision checks: verified AppleDouble companion may be excluded; unrelated non-JSONL binary files do not participate; malformed or ambiguous journal-looking files fail closed. The offline plan covers normal, corrupt, duplicate, historical, order, symlink/directory and macOS metadata cases. No tests were run in this design step.

`scripts/v3_execution_transaction.py` is an r10 frozen member, so implementation requires a separate new runner freeze and identity binding; r10 remains untouched. The previously invoked formal command is non-reusable despite the old authorization's unconsumed reducer state. A separate exact-ID, predicate-validated non-consuming retirement is designed before any fresh authorization. A future fresh authorization, attempt ID, namespace and Mac-local preflight are required because the old identities/preflight are bound to r10 and cannot be reused. No lifecycle event, authorization, attempt, namespace, transaction, preflight, model call or V4 execution occurred. Historical evidence and Step 9.58 provenance gap remain unchanged. Artifacts: `evaluation/v1_2_3/step9_63c_r5c10b_transaction_scanner_repair_design.json`, `step9_63c_r5c10b_transaction_scanner_repair_design_report.md`, and `step9_63c_r5c10b_synthetic_test_plan.json`.

## Step 9.63c-r5c10c — Offline transaction scanner repair, not frozen

`PASS_OFFLINE_SCANNER_REPAIR_UNFROZEN`. Implemented the approved narrow `_find_identity()` repair in `scripts/v3_execution_transaction.py`: before event decoding, require a real transaction root, enumerate sorted direct children, exclude unrelated non-JSONL entries, verify and exclude only genuine AppleDouble `._` companions with canonical real journals, and fail closed for suspicious JSONL paths, corrupt canonical contents, empty journals and filename/identity mismatch. The scan checks all candidates before returning a collision match; it does not ignore decode errors. No transaction append, commit-point, authorization lifecycle, one-shot or Agent/evaluation semantics were changed.

Offline tests: 18 new scanner + 32 existing transaction + 14 selected synthetic lifecycle = 64 passed, 0 failures/errors/skips. All use temporary roots; production transaction journals were not read or modified by tests. r10 freeze remains intact, but exactly one of 20 members now differs in the working copy: transaction module SHA-256 changed from `f1a253730953abf51307f4e9404bf59d7856c15d2367b7a62d6809dbb64b2797` to `f0e74a49d152053b5455951c507edb8f7849a9e4708835711e5975a82e690e91`. `CURRENT_RUNNER_MATCHES_R10_FREEZE = NO`; no new freeze was created. Read-only lifecycle state remains `ISSUED_EXECUTABLE`, consumed `NO`/count 0, but the old formal command must not be rerun. No authorization, attempt, namespace, transaction, preflight, model/Agent/RAG/HTTP or V4 activity occurred. Ready only for a separate new-runner-freeze review. Artifacts: `evaluation/v1_2_3/step9_63c_r5c10c_scanner_repair_audit.json`, `step9_63c_r5c10c_scanner_repair_report.md`, and `step9_63c_r5c10c_test_matrix.json`.

## Step 9.63c-r5c10d — New runner freeze eligibility review, draft only

`PASS_REVIEW_DRAFT_ONLY_NO_FREEZE_CREATED`. Read-only verification found the original r10 freeze manifest unchanged at SHA-256 `d24244235e51e7bf6c8567880c654fe3fd73b87fa1bfe1ab0f10dfdc94db2693`; 19 of 20 current member files match, with only `scripts/v3_execution_transaction.py` differing as approved. Agent, benchmark, harness, scoring, rubric, metric registry, one-shot rules, tool adapter, dependency lock and all 55 historical pins match their frozen identities. Historical committed journal, AppleDouble companion, old authorization, preflight and registry hashes remain unchanged; Step 9.58 provenance gap remains documented. A repeat of 64 temporary-root offline tests passed with zero failures/errors/skips. Scanner, commit-point, lifecycle and one-shot review passed; no credential value or network was accessed.

The version inventory contains r3–r10 and no r11; `r11` is proposed only. `evaluation/v1_2_3/step9_63c_r5c10d_candidate_freeze_manifest.json` is a non-executable `DRAFT_NOT_FROZEN_NOT_AUTHORIZED` 20-member snapshot, SHA-256 `d00126ea3616bd1a51b0a8a33dc49a93bd7a142fdd46c98d8a1041069ccd04bc`, **not** a final r11 freeze hash. It retains the historical r10 pointer and lists required future rebindings, including a new r11 identity pointer, transaction/validator pins, preflight producer compatibility and separate old-authorization retirement. The old r10 command remains non-reusable. No freeze, authorization, consumption, attempt, preflight or V4 execution was created. Review audit/report: `evaluation/v1_2_3/step9_63c_r5c10d_runner_freeze_review_audit.json` and `step9_63c_r5c10d_runner_freeze_review_report.md`. Await separate approval for freeze construction.

## Step 9.63c-r5c10e — r11 freeze construction qualification, fail closed

`FAIL_CLOSED_EXISTING_FREEZE_CONSTRUCTION_CONTRACT_R10_ONLY`. The r10 historical freeze manifest remains SHA-256 `d24244235e51e7bf6c8567880c654fe3fd73b87fa1bfe1ab0f10dfdc94db2693`. Its 20 members exist; 19 match and only the approved transaction scanner differs. The existing builder is hardcoded to create the already existing r10 file from r9, while the single current pointer is an r10 frozen member and still names r10. No existing safe r11 construction/identity-binding mechanism was found; promoting the r5c10d draft would be invalid. Construction stopped before freeze creation or offline testing. No r11 freeze, authorization, attempt, namespace, preflight, network, model/Agent/RAG activity or formal V4 case was created or run. Prior 64/64 synthetic scanner evidence remains historical, not a new test result. See `evaluation/v1_2_3/step9_63c_r5c10e_runner_freeze_construction_audit.json`, `step9_63c_r5c10e_runner_freeze_integrity_report.md`, and `step9_63c_r5c10e_offline_test_matrix.json`. A separately reviewed compatible freeze-bootstrap/identity-binding mechanism is required before another construction attempt.

## Step 9.63c-r5c10f — r11 freeze construction compatibility review

`PASS_READ_ONLY_DESIGN_WITH_SCOPE_CONFLICT`. The r10 manifest remains byte-identical at SHA-256 `d24244235e51e7bf6c8567880c654fe3fd73b87fa1bfe1ab0f10dfdc94db2693`; only the approved scanner differs among its 20 current member paths. Source review confirmed that the sole builder is fixed to r10/r9, the resolver loads a single r10 pointer, and pointer and builder themselves are frozen members. Runtime authorization and preflight bind current revision and raw freeze SHA. A compatible executable r11 with 20 members requires a separately approved versioned pointer/builder and resolver switch, creating additional infrastructure-member deltas; “only scanner member changes” cannot simultaneously hold. The design rejects in-place r10 mutation, draft promotion and r10 command reuse. No code, freeze, authorization, lifecycle event, preflight, attempt, transaction or V4 case was changed or created, and no tests were run. Design-only artifacts: `evaluation/v1_2_3/step9_63c_r5c10f_freeze_compatibility_audit.json`, `step9_63c_r5c10f_freeze_compatibility_report.md`, `step9_63c_r5c10f_minimal_extension_design.json`, `step9_63c_r5c10f_file_change_risk_rollback.json`, and `step9_63c_r5c10f_offline_test_plan.json`. Await human review of expanded infrastructure scope before implementation.

## Step 9.63c-r5c10g — Infrastructure scope approval and implementation planning

`PASS_PLANNING_ONLY_WITH_PREFLIGHT_CONTRACT_DECISION_PENDING`. Reviewed the r5c10f design against actual builder, resolver, adapter, lifecycle, formal consumer and preflight producer paths. Versioned r11 builder/pointer plus strict resolver switch would require more than the approved scanner member delta; old r10 manifest, pointer, builder and all historical evidence remain unchanged. New finding: the frozen generic preflight producer's ID grammar differs from the frozen formal consumer's accepted grammar and has no invocation claim registry, while the successful registry-aware producer is hard-bound to r10 and is outside r10's 20-member freeze. A separately approved r11 producer/registry contract, or an equivalently reviewed alternative, is required before end-to-end r11 readiness can be claimed. A 20-row inventory remains possible by replacing the obsolete r10 preflight wrapper row with a versioned producer, but that is a proposal only. The exact future authorization issuer and retirement prerequisites also remain pending. No code, freeze, authorization, lifecycle event, preflight, network, model/Agent/RAG or V4 case was changed or executed. Outputs: `evaluation/v1_2_3/step9_63c_r5c10g_implementation_scope_review_report.md`, `step9_63c_r5c10g_file_implementation_plan.json`, `step9_63c_r5c10g_r10_r11_identity_compatibility_matrix.json`, and `step9_63c_r5c10g_offline_acceptance_rollback_plan.json`. Await a separate decision on the expanded preflight scope before implementation.

## Step 9.63c-r5c10h — Preflight producer and invocation registry boundary decision

`PASS_READ_ONLY_BOUNDARY_DESIGN_CONDITIONAL_IMPLEMENTATION_REVIEW`. The producer is an independent pre-formal evidence dependency, not a direct formal-runner import. The observed r10 registry-aware producer was outside the 20-member freeze, self-reported its script SHA in the artifact, and durably claimed a unique invocation ID before preflight; the frozen consumer presently validates artifact path/SHA and identity/safety fields but does not verify producer SHA or registry claim. The generic frozen producer's ID grammar is incompatible with that consumer. Recommended future option A puts a new r11 registry-aware producer in the 20-member freeze, replaces the old preflight-wrapper row, and adds a frozen-consumer provenance gate. The mutable append-only registry remains outside immutable freeze members; its schema/path validation belongs in frozen code and its claim prefix is audited. Proposed 20-row accounting: 14 unchanged r10 paths, changed scanner/resolver/consumer paths, new builder/pointer/producer replacement paths. Option B remains possible only with a separate immutable producer pin enforced by future authorization and consumer, which current code lacks. Exact future registry schema and issuer contract remain pending separate review. No code, r11 freeze, authorization, real preflight, network, inference, Agent/RAG or V4 execution occurred. Outputs: `evaluation/v1_2_3/step9_63c_r5c10h_preflight_registry_boundary_report.md`, `step9_63c_r5c10h_ab_decision.json`, `step9_63c_r5c10h_end_to_end_identity_matrix.json`, `step9_63c_r5c10h_final_file_scope.json`, and `step9_63c_r5c10h_offline_implementation_plan.json`. Await explicit implementation approval.

## Step 9.63c-r5c10i — Registry schema and provenance contract finalization

`PASS_DESIGN_ONLY_REGISTRY_SCHEMA_AND_PRECOMMIT_GUARD_FINALIZED`. Read-only audit confirmed the r10 registry has one initialization event and one real invocation claim; its current producer code strictly parses the log and fsyncs the claim before preflight, but the frozen formal consumer presently checks artifact path/SHA and safety fields without validating the producer SHA or claim. The new r11 design specifies a separate version-2 exact-path append-only registry with one genesis, unique pre-work claim, post-artifact persistence event, and optional terminal failure event. A claim remains used after failure even without an artifact; an artifact without a persistence event is rejected. The consumer provenance guard is placed in `validate_preflight_evidence()` before `adapter.run()`, checking actual r11 producer member bytes, exact claim/prefix, persistence digest, authorization/freeze/case identity and existing connectivity/safety fields. Mutable registry bytes remain outside the freeze. The proposed member matrix was checked against all 20 r10 paths and SHA values: 14 unchanged, 3 changed existing paths, 3 replacement paths, all r11 paths unique. This is design-only; no r11 member SHA or freeze is claimed. Old r10 authorization remains issued/unconsumed in history, but its invoked command remains non-reusable; retirement and future issuance require separate predicate audit/approval. No code, historical evidence, authorization, real preflight, network/model/Agent/RAG or V4 execution was changed or run. Artifacts: `evaluation/v1_2_3/step9_63c_r5c10i_registry_schema_contract.json`, `step9_63c_r5c10i_consumer_provenance_guard_design.md`, `step9_63c_r5c10i_r11_frozen_member_identity_matrix.json`, `step9_63c_r5c10i_authorization_issuance_retirement_review.md`, and `step9_63c_r5c10i_offline_acceptance_test_plan.json`. Await separate implementation approval.

## Step 9.63c-r5c10j — r11 infrastructure implementation and offline validation

`IMPLEMENTED_FOCUSED_OFFLINE_PASS_LEGACY_IMPORT_REGRESSION_BLOCKED_NO_FORMAL_FREEZE`. Implemented a versioned r11 freeze builder, strict r11-only identity resolver, versioned preflight producer and append-only Registry protocol, plus a formal-consumer provenance guard before `adapter.run()`. The r11 member accounting is 14 unchanged + 3 changed + 3 replaced = 20. A synthetic pointer and freeze were built and validated only in a temporary directory; no production r11 pointer, freeze or Registry was created. The r10 historical freeze manifest remains byte-identical at SHA-256 `d24244235e51e7bf6c8567880c654fe3fd73b87fa1bfe1ab0f10dfdc94db2693`; 17 current r10 member paths still match historical bytes and the three planned changed paths are scanner (previous r5c10c), resolver and formal consumer. Historical r10 pointer, builder, authorization and evidence were not modified. The 78-test focused offline suite passed with 0 failures/errors; two additionally attempted historical suites could not import because the future r11 production pointer is intentionally absent. These are recorded as unresolved, not waived or counted as passing; full regression and separate freeze-review readiness remain unproven. No formal r11 freeze, authorization, consumption, attempt, namespace, transaction, real preflight, network/model/Agent/RAG or V4 case execution occurred. Audit: `evaluation/v1_2_3/step9_63c_r5c10j_infrastructure_implementation_audit.json`; report, file inventory and test matrix share the `step9_63c_r5c10j_` prefix. Await separate review; old r10 formal command remains non-reusable.

## Step 9.63c-r5c10k — regression import compatibility diagnosis and repair

`FAIL_CLOSED_FULL_REGRESSION_NOT_GREEN_SCOPE_EXPANSION_REQUIRED`. Diagnosis found that a historical preflight test unnecessarily imported an r7 transport module which transitively imported the unchanged frozen V3 adapter; that adapter eagerly reads the absent production r11 pointer at import time. Two historical lifecycle tests instead queried live current-authorization state without a synthetic pointer. Changed only those two test fixtures: the preflight contract test now uses SHA-checked historical r10 metadata and intercepts network primitives, while lifecycle version-filtering tests use a clearly marked temporary r11 pointer with copied historical manifests. Their 46 tests pass; the r5c10j focused 78 tests pass. Full unittest discovery ran 615 items, comprising 603 actual collected methods and 12 failed module-import placeholders. Result: 577 passed, 20 failures, 18 errors, 0 skipped. Additional historical modules still hit the adapter's import-time pointer read; other failures involve old lifecycle assumptions, a V2 parent-runner pin, the historical fixed test inventory and r10-specific bootstrap assumptions. No production/frozen code or historical artifact was modified to force a pass. The r10 manifest remains SHA-256 `d24244235e51e7bf6c8567880c654fe3fd73b87fa1bfe1ab0f10dfdc94db2693`; no formal r11 pointer/freeze/registry, authorization, attempt, preflight or V4 execution was created. Outputs: `evaluation/v1_2_3/step9_63c_r5c10k_root_cause_report.md`, `step9_63c_r5c10k_regression_report.md`, `step9_63c_r5c10k_regression_audit.json`, `step9_63c_r5c10k_regression_test_matrix.json`, `step9_63c_r5c10k_r10_r11_identity_isolation.json`, and `step9_63c_r5c10k_minimal_repair_diff.json`. Full regression acceptance and r11 freeze-review readiness remain NO; await separate approval for expanded compatibility work.

## Step 9.63c-r5c10l — Full regression failure attribution and scope review

`FAIL_CLOSED_READ_ONLY_SCOPE_REVIEW_WITH_HISTORICAL_TRACE_INTEGRITY_GAP`. Attributed all 20 failed test methods, 6 runtime errors and 12 import-error placeholders to six shared root-cause clusters: stale synthetic authorization lifecycle fixture (18 items), frozen adapter import-time current-pointer read (12), r9 bootstrap tests against r11 resolver (3), archival r10 live-snapshot expectations (3), archived V2 parent SHA drift (1), and pinned Step 9.51a test inventory drift (1). Arithmetic: 603 actual collected methods = 577 passed + 20 failed + 6 runtime errors; unittest's 615 run items add 12 failed-import placeholders, giving 18 total errors. No pytest output artifact exists; the source result was unittest. The r10 freeze manifest remains SHA-256 `d24244235e51e7bf6c8567880c654fe3fd73b87fa1bfe1ab0f10dfdc94db2693`; no formal r11 freeze/pointer, authorization or V4 execution was created. During the diagnostic repeat, two older mechanism tests were found to write fixed historical trace paths in `evaluation/v1_2/` and `evaluation/v1_2_1/`; mtimes updated. Their current SHA values are recorded in the Step 9.63c-r5c10l impact assessment, but pre-run bytes were not captured, so unchanged content is NOT_PROVEN. No restoration was attempted. Further test execution stopped. Outputs: `evaluation/v1_2_3/step9_63c_r5c10l_root_cause_attribution_report.md`, `step9_63c_r5c10l_failure_cluster_matrix.json`, `step9_63c_r5c10l_minimal_repair_scope_proposal.md`, `step9_63c_r5c10l_freeze_boundary_impact.json`, and `step9_63c_r5c10l_test_count_reconciliation.json`. Await separate approval and trace-provenance review; r11 freeze readiness remains NO.

## Step 9.63c-r5c10m — Historical trace provenance and repair boundary audit

`FAIL_CLOSED_CONTENT_INTEGRITY_UNPROVEN_AND_REPAIR_SCOPE_PENDING`. Static/read-only audit confirmed two untracked historical trace files, outside r10's 20 freeze members, with current SHA-256 `e09321c89b75a4330799e4a4c286652cee82ed0e0d4fa1b8478c970dd7f6d8e5` and `5518eb4b0b7e8880c5f84e59ba0264013bed99e25edb8da93dca558304d4f084`; both have mtime 2026-10-09 11:37:42 -0400. No repository Git object, independent pre-run trace hash, or trusted original copy was found; external backups were not checked. `CONTENT_INTEGRITY_UNPROVEN` remains the only supported conclusion. The two historical test methods select fixed repository-root paths through module constants and directly call `Path.write_text()` during full-suite discovery/execution. Reviewed all six r5c10l failure clusters and 12 blocked-module import chains: 7 direct imports, 1 through the frozen issuer, 4 via transport/preflight; all converge on frozen adapter import-time r11 pointer resolution. A test-only repair is plausible for some clusters but not proven for all; a frozen-member change is `NOT_DETERMINED` and would require independent approval. No test, historical trace restoration, code repair, real preflight, formal r11 freeze, authorization activity or V4 case was run in this step. r10 manifest SHA remains `d24244235e51e7bf6c8567880c654fe3fd73b87fa1bfe1ab0f10dfdc94db2693`. Outputs: `evaluation/v1_2_3/step9_63c_r5c10m_historical_trace_integrity_audit.json`, `step9_63c_r5c10m_historical_write_path_root_cause_report.md`, `step9_63c_r5c10m_six_cluster_repair_boundary_matrix.json`, `step9_63c_r5c10m_import_blocker_dependency_analysis.md`, `step9_63c_r5c10m_proposed_safe_test_isolation_plan.md`, and `step9_63c_r5c10m_historical_trace_provenance_and_boundary_report.md`. `READY_FOR_SCOPED_REPAIR_APPROVAL = NO`; wait for human review.

## Step 9.63c-r5c10n — Safe test isolation implementation review

`PASS_PLAN_ONLY_READY_FOR_LIMITED_TEST_ISOLATION_APPROVAL`. Rechecked the two writer test modules: `tests/test_v1_2_mechanism_validation.py` SHA-256 `2d5d8fcc4919b798b907903bdd61bf8d3cb987351195b61b397ac379fa3739b5` and `tests/test_v1_2_1_mechanism_validation.py` SHA-256 `2d92acdfe7923c631d950d1f4bf1efc99ae333f41f3981c12371d6def8ed8307`; neither appears in r10's 20-member freeze. Prepared a two-file-only candidate patch to replace fixed `evaluation/v1_2*/` trace writes with method-local `tempfile.TemporaryDirectory()` output outside the repository, retaining all scenario assertions and refusing protected-root output. The tests are `unittest`, so this standard-library fixture also remains compatible when pytest runs them. Recorded current trace SHA/size/mtime solely as forward preservation pins, not as original pre-r5c10l hashes; `HISTORICAL_TRACE_CONTENT_INTEGRITY = CONTENT_INTEGRITY_UNPROVEN`. Proposed before/after byte and inventory checks for both protected directories, exact two-method offline verification, r10 member-hash checks, and fail-closed handling of any protected-file delta. Twelve import blockers and the six failure clusters remain separate; no full-regression or r11 freeze readiness is claimed. No tests, code repair, trace restoration, formal r11 freeze, authorization, preflight or V4 case occurred. Outputs: `evaluation/v1_2_3/step9_63c_r5c10n_safe_test_isolation_patch_plan.md`, `step9_63c_r5c10n_file_level_approval_matrix.json`, `step9_63c_r5c10n_historical_evidence_protection_baseline.json`, `step9_63c_r5c10n_offline_acceptance_plan.md`, and `step9_63c_r5c10n_remaining_blockers_report.md`. Wait for separate human approval of the two-file test-only patch.

## Step 9.63c-r5c10o — Limited test isolation repair and offline verification

`PASS_LIMITED_TEST_ISOLATION_SCOPED_OFFLINE_VERIFIED_FULL_REGRESSION_NOT_RUN`. Modified only the two approved non-frozen `unittest` files: replaced fixed historical trace targets with method-local `TemporaryDirectory` paths and pre-write repository-containment rejection; preserved original 18/19 scenario assertions and added one no-write historical-path negative test in each module. Pre-patch hashes matched r5c10n approvals; post-patch SHA-256 values are `e079a059b22388d0d40abbf7962e0fa3e25e4c3d565069133496b82676f6d2d9` (V1.2 test) and `cd8b2c5bcb657ef3dd848cedbfc27034c03a1c4a8ccb41fa9452805e103f6cf2` (V1.2.1 test). This step ran and passed 4/4 target tests, 78/78 scoped r11 infrastructure/transaction/Registry tests, and 46/46 historical fixture/lifecycle tests, each with 0 failures/errors/skips/import errors. Full regression was **NOT_RUN**; previous 603/577/20/18 results are not current results. Both historical trace hashes and the 110-file protected-directory path/hash aggregate remained unchanged before/after tests; this does not prove pre-r5c10l original content (`CONTENT_INTEGRITY_UNPROVEN`). All 20 r10 member bytes and the production Python source aggregate were unchanged before/after. No production semantics, formal r11 freeze, authorization, real preflight, or V4 case was touched. Outputs: `evaluation/v1_2_3/step9_63c_r5c10o_implementation_report.md`, `step9_63c_r5c10o_exact_file_diff_sha256_audit.md`, `step9_63c_r5c10o_historical_trace_before_after_integrity_check.json`, `step9_63c_r5c10o_offline_test_results_failure_matrix.json`, and `step9_63c_r5c10o_remaining_blockers_and_recommendation.md`. Six prior failure clusters and 12 blocked modules remain for separate scope review.

## Step 9.63c-r5c10p — Remaining failure and import-blocker review

`PASS_READ_ONLY_REVIEW_HISTORICAL_FAILURES_NOT_RETESTED`. Reviewed r5c10k–o reports, test matrices and static code without running tests or changing production/test code. Historical full regression was 603 collected methods: 577 passed, 20 failed, 6 runtime errors; 12 additional failed-import placeholders yielded 18 reported errors. The 4/4 target and 124/124 scoped r5c10o passes do not cover any of those 38 historical failed/error items. Current full-regression outcome remains unknown. Per-item matrix preserves all 38 test/module names, historical exception type, earliest known trigger and shared six-cluster attribution; original full tracebacks were not saved, so static call chains are labeled as such. The frozen adapter still resolves the strict r11 pointer at import time and the formal r11 pointer/freeze remain absent; the shared cause of the historical 12-module import block is statically present, but no new import result was measured. Proposed six independent, separately approvable batches; only B2 test-only feasibility/collection is recommended as the immediate next decision, with any frozen adapter change blocked pending further approval. Both traces remain at present-day SHA-256 `e09321c89b75a4330799e4a4c286652cee82ed0e0d4fa1b8478c970dd7f6d8e5` and `5518eb4b0b7e8880c5f84e59ba0264013bed99e25edb8da93dca558304d4f084`, but pre-r5c10l original content integrity is `CONTENT_INTEGRITY_UNPROVEN`. r10 freeze manifest SHA remains `d24244235e51e7bf6c8567880c654fe3fd73b87fa1bfe1ab0f10dfdc94db2693`; old authorization and lifecycle evidence were only read. No test rerun, frozen-member edit, trace modification, formal r11 freeze, authorization or V4 case occurred. Outputs: `evaluation/v1_2_3/step9_63c_r5c10p_remaining_failure_review_report.md`, `step9_63c_r5c10p_failure_import_root_cause_matrix.json`, `step9_63c_r5c10p_proposed_minimal_repair_batches.json`, `step9_63c_r5c10p_frozen_boundary_historical_evidence_risk_audit.json`, and `step9_63c_r5c10p_next_repair_approval_recommendation.md`. Await separate human scope approval.

## Step 9.63c-r5c10q — B2 test-only repair feasibility and collection contract review

`PASS_READ_ONLY_B2_REVIEW_FULL_TEST_ONLY_REPAIR_NOT_PROVEN`. Reviewed the exact B2 12 test modules and their import chains without code changes or test execution. Seven import the frozen adapter directly, one through the r10-frozen issuer, and four through `scripts/preflight_step9_63b_mac_local.py`, which is **non-frozen infrastructure** (earlier r5c10m wording called this transport frozen; the r10 20-member list disproves that description). All converge on the frozen adapter's module-global `load_identity_config(ROOT)` at line 25 and the missing exact formal r11 pointer; that pointer and freeze are still absent. Static source inspection finds 183 test-method definitions in the 12 blocked modules, not collected/passed methods. Moving imports into test setup could permit collection but may only move errors to runtime; module-global adapter constants, frozen issuer imports, historical root assumptions, and tests invoking `adapter.run()` mean a full test-only passing repair is `NOT_PROVEN`. No fake formal r11 identity, r10 fallback, import-time mock leakage, authorization or consumer guard relaxation is approved. Designed separate collection-pass and test-pass gates with temporary roots, no protected evidence writes, and missing/invalid-pointer negatives. Current trace hashes remain `e09321c89b75a4330799e4a4c286652cee82ed0e0d4fa1b8478c970dd7f6d8e5` and `5518eb4b0b7e8880c5f84e59ba0264013bed99e25edb8da93dca558304d4f084`; original content integrity remains `CONTENT_INTEGRITY_UNPROVEN`. No frozen member or production semantics was changed, no full regression was rerun, and no formal r11 freeze, authorization or V4 case was created. Outputs: `evaluation/v1_2_3/step9_63c_r5c10q_b2_feasibility_review_report.md`, `step9_63c_r5c10q_b2_file_dependency_matrix.json`, `step9_63c_r5c10q_proposed_test_only_patch_design.md`, `step9_63c_r5c10q_collection_negative_acceptance_plan.json`, and `step9_63c_r5c10q_frozen_boundary_historical_evidence_audit.json`. Do not approve all-12 B2 implementation on this evidence; a separate small collection-only pilot could be considered by the human.

## Step 9.63c-r5c10r — Minimal collection feasibility spike

`PASS_ONE_FILE_COLLECTION_SPIKE_B2_EXPANSION_REVIEW_ONLY`. Changed only the non-frozen `tests/test_step9_58a_r1_namespace_allocator.py`: moved its existing frozen-adapter import from module scope into the sole method that actually uses the adapter. Before/after test-file SHA-256: `a4706b8317a5ceca4452d09e5bfe550436d771fade51aeafad54ad676cc6d666` → `6f1295cffce4391884ab4b2c65b044f6380507cee60314f1ca7ec4491dea6de2`. Collection-only discovered 9 methods, 0 import errors; 8 statically safe allocator-only methods ran and passed, while the ninth remains execution-blocked by the absent formal r11 pointer. Negative checks confirmed the real resolver and frozen adapter still reject that missing identity. Current r10 20-member and production-source before/after hash aggregates, both historical Trace hashes/sizes/mtimes, and the protected 110-file directory inventory stayed unchanged; historical original Trace integrity remains `CONTENT_INTEGRITY_UNPROVEN`. No formal r11 pointer/freeze, authorization, real preflight, model/Agent/RAG, or V4 case was created or run. Full regression and the other 11 B2 modules were not rerun. Outputs: `evaluation/v1_2_3/step9_63c_r5c10r_feasibility_spike_report.md`, `step9_63c_r5c10r_exact_one_file_diff_hash_audit.json`, `step9_63c_r5c10r_collection_only_results.json`, `step9_63c_r5c10r_safe_execution_negative_results.json`, and `step9_63c_r5c10r_b2_expansion_recommendation.md`. Stop for human review; this is not authorization for B2-wide repair.

## Step 9.63c-r5c10s — B2 expansion scope review

`PASS_READ_ONLY_SCOPE_REVIEW_MINIMAL_BATCH_PROPOSED`. Statically reviewed each of the 11 remaining historical import-blocked test modules and their current import/runtime chains. Their 174 static test-method definitions were **not collected or executed** in this step. Conservative collection-patch classifications: A=2 (`test_step9_63c_r3_parent_namespace_repair.py`, `test_step9_63c_r5c7b_diagnostics.py`), B=0, C=1 (frozen issuer on path; no issuer edit approved), D=8 (safe one-file patch not yet proven). Proposed next approval batch is only the non-frozen `tests/test_step9_63c_r5c7b_diagnostics.py`: a future reviewed patch could defer its transport import, then separately measure expected 13-method collection and execute only statically safe local diagnostic methods; four transport tests remain identity-dependent. No code or tests changed or ran here. r10 freeze manifest SHA `d24244235e51e7bf6c8567880c654fe3fd73b87fa1bfe1ab0f10dfdc94db2693`, current 20-member path/hash aggregate, old authorization/ledger observations, and both historical Trace SHA/size/mtime match previous observations; original Trace content remains `CONTENT_INTEGRITY_UNPROVEN`. No formal r11 freeze, authorization or V4 case occurred. Outputs: `evaluation/v1_2_3/step9_63c_r5c10s_remaining_modules_dependency_matrix.json`, `step9_63c_r5c10s_risk_classification_report.md`, `step9_63c_r5c10s_minimal_expansion_batch_proposal.json`, `step9_63c_r5c10s_historical_evidence_protection_audit.json`, and `step9_63c_r5c10s_review_report.md`. Stop for human approval; no batch implementation is authorized by this review.

## Step 9.63c-r5c10t — Single-file test isolation repair

`PASS_ONE_FILE_COLLECTION_AND_SAFE_SUBSET_OFFLINE_ONLY`. Modified only the approved, non-frozen `tests/test_step9_63c_r5c7b_diagnostics.py`: moved its top-level non-frozen transport import into the four transport-dependent test paths. That transport transitively loads the frozen issuer/adapter and missing formal r11 pointer; the diagnostic preflight itself remains independently importable. Target-file SHA-256 changed from `68657dc4d9d1cc6220811c227361fa4067f2226390002de5f1e77e426c05e345` to `655a45c09b3751d24ea9f006649ecb5a9620b1f2acc744f4a2965fbb195f615c`. Static syntax passed; collection-only found 13 methods and 0 import errors. Nine statically safe local diagnostic methods passed; four transport-dependent methods were not run. The actual resolver, frozen adapter and transport import all continue to reject the absent formal r11 pointer. The current r10 20-member aggregate, r10 freeze manifest, production Python aggregate and both historical Trace SHA/size/mtime stayed unchanged before/after; earlier original Trace content remains `CONTENT_INTEGRITY_UNPROVEN`. No second test file, frozen/production code, formal r11 freeze, authorization, real preflight, model/Agent/RAG, or V4 case was touched. Full regression and all other B2 modules were not run. Outputs: `evaluation/v1_2_3/step9_63c_r5c10t_implementation_report.md`, `step9_63c_r5c10t_single_file_diff_audit.json`, `step9_63c_r5c10t_focused_test_matrix.json`, and `step9_63c_r5c10t_frozen_boundary_historical_evidence_audit.json`. Stop for the next human scope review; the second A-class module is not auto-approved.

## Step 9.63c-r5c10u — Remaining scope review

`PASS_READ_ONLY_SECOND_A_CANDIDATE_PROPOSED`. Recomputed the dependency and risk classification for the 10 remaining historical import-blocked test modules from current source and SHA-256 values; their 161 static test definitions were **not collected or executed** in this step. Categories: A=1 (`tests/test_step9_63c_r3_parent_namespace_repair.py`), B=0, C=1 (frozen issuer on path), D=8. The sole remaining A candidate is a non-frozen test file whose only adapter use is in T12; a future separately approved one-file relocation of the top-level adapter import into T12 should address the known collection blocker, but no collection result is claimed now. T12 remains r11-identity-dependent and the thirteenth synthetic parent-run sentinel test reaches a `CASE_STARTED` event, so neither is approved for safe-subset execution. The r5c10t target remains at its post-patch SHA, with no new import dependency or write/network side effect found. The r10 manifest SHA `d24244235e51e7bf6c8567880c654fe3fd73b87fa1bfe1ab0f10dfdc94db2693`, current 20-member aggregate, old authorization/ledger hashes and both historical Trace SHA/size/mtime remain at prior observed values; original Trace content integrity is still `CONTENT_INTEGRITY_UNPROVEN`. No code, historical evidence, r11 freeze, authorization, preflight, test, model/Agent/RAG or formal V4 case changed or ran. Outputs: `evaluation/v1_2_3/step9_63c_r5c10u_scope_review_report.md`, `step9_63c_r5c10u_remaining_module_dependency_matrix.json`, `step9_63c_r5c10u_updated_risk_classification.json`, `step9_63c_r5c10u_second_a_candidate_review.md`, and `step9_63c_r5c10u_historical_evidence_boundary_audit.json`. Stop for explicit human approval before any patch.

## Step 9.63c-r5c10v — Second A-class single-file import isolation

`PASS_COLLECTION_ONLY_TEST_EXECUTION_DEFERRED_BY_TRANSACTION_BOUNDARY`. Modified only the approved non-frozen `tests/test_step9_63c_r3_parent_namespace_repair.py`, relocating its sole top-level frozen-adapter import into T12, the only method that references adapter. Target SHA-256 changed from `c863410fccc43364c810d4e6d7ac22630d890e61798641a66c50dd0e1aa8f1d3` to `f8c5b2e255ceda15c7d76e2f6b3a6a5af4afbfdcadbcae2f83cb6f5b3951262e`. Static syntax passed; collection-only found 13 tests and 0 import errors, with **0 methods executed or passed**. T1–T11 invoke the real `begin_and_commit` implementation on synthetic temporary roots, while T12 and the final sentinel test invoke `parent.run`; under this step's boundary all 13 were left unexecuted. Read-only negative checks confirmed that the real r11 resolver and frozen adapter still reject the missing formal pointer. Current r10 20-member and production-code hash aggregates, r10 freeze manifest and both historical Trace SHA/size/mtime were unchanged before/after; historical original Trace content remains `CONTENT_INTEGRITY_UNPROVEN`. No parent run, transaction commit, formal r11 freeze, authorization, real preflight, model/Agent/RAG, V4 case, full regression or third-module patch occurred. Outputs: `evaluation/v1_2_3/step9_63c_r5c10v_implementation_report.md`, `step9_63c_r5c10v_single_file_diff_audit.json`, `step9_63c_r5c10v_test_collection_matrix.json`, `step9_63c_r5c10v_safe_test_execution_matrix.json`, `step9_63c_r5c10v_frozen_boundary_audit.json`, and `step9_63c_r5c10v_historical_evidence_audit.json`. Stop for human scope review; collection success does not imply executable r11 identity or method pass.

## Step 9.63c-r5c10w — Post-isolation readiness and blocker review

`PASS_READ_ONLY_REVIEW_R11_FREEZE_NOT_READY`. Re-inspected nine unprocessed historical test modules and their present import/side-effect paths: nine static collection-blocker paths remain through the frozen adapter, issuer, or non-frozen transport to the absent formal r11 pointer; none were freshly collected or executed, and their 148 static method definitions are not pass counts. r5c10t remains 13 collected / nine safe passed / four unexecuted; r5c10v remains 13 collected / zero executed, with eleven real synthetic-root transaction methods and two `parent.run` methods deferred. Both patches are limited to non-frozen test imports and add no new dependency or production behavior. The r11 formal pointer and freeze are absent (19/20 proposed member paths exist), publication-boundary identities and final hashes remain to be verified, and full regression remains historically non-green; freeze prerequisites are therefore not met. r10 historical freeze SHA remains `d24244235e51e7bf6c8567880c654fe3fd73b87fa1bfe1ab0f10dfdc94db2693`. Both affected historical Trace files match forward SHA baselines, but original content integrity remains `CONTENT_INTEGRITY_UNPROVEN`. No test, code patch, formal r11 freeze, authorization, preflight or V4 case was run or created. Outputs: `evaluation/v1_2_3/step9_63c_r5c10w_readiness_review_report.md`, `step9_63c_r5c10w_remaining_blocker_matrix.json`, `step9_63c_r5c10w_test_collection_execution_status_matrix.json`, `step9_63c_r5c10w_r11_freeze_prerequisite_checklist.json`, `step9_63c_r5c10w_historical_evidence_integrity_risk_summary.json`, and `step9_63c_r5c10w_next_minimal_scope_recommendation.md`. Stop for separate human scope approval.

## Step 9.63c-r5c10x — Remaining import-blocker minimal feasibility review

`PASS_READ_ONLY_ONE_COLLECTION_ONLY_CANDIDATE`. Independently re-read the nine still-unprocessed test modules, their present SHA-256 values, direct/transitive import chains and static side-effect call sites. All nine static collection-blocker paths share one import-time dependency: the frozen V3 adapter calls `load_identity_config(ROOT)` for the absent formal r11 pointer. This is not nine current test failures or nine independent production defects; no test collection/execution was run. The only recommended next candidate is non-frozen `tests/test_step9_63b_mac_local_preflight.py`, whose single top-level transport import could, after separate approval, be deferred within that file's eight methods for **collection-only** validation. This predicts collection, not runtime pass: all eight methods still import transport at execution and remain subject to the real identity guard, with connectivity/preflight side effects requiring separate review. Frozen issuer tests and the other seven modules retain separate/unknown boundaries; no issuer, resolver or production change is approved here. The r10 freeze manifest and two affected historical Trace files match forward SHA observations, but original Trace content remains `CONTENT_INTEGRITY_UNPROVEN`. No code, test, historical artifact, formal r11 freeze, authorization, preflight or V4 case was changed or run. Outputs: `evaluation/v1_2_3/step9_63c_r5c10x_feasibility_review_report.md`, `step9_63c_r5c10x_remaining_9_dependency_matrix.json`, `step9_63c_r5c10x_shared_root_cause_analysis.json`, `step9_63c_r5c10x_single_file_candidate_recommendation.md`, and `step9_63c_r5c10x_collection_execution_safety_boundary.json`. Stop for separate human approval before any patch.

## Step 9.63c-r5c10y — Single-file collection isolation implementation

`FAIL_CLOSED_COLLECTION_UNVERIFIED_PYTEST_UNAVAILABLE`. Only approved, non-frozen `tests/test_step9_63b_mac_local_preflight.py` was edited: its existing top-level transport import was moved into each of its eight methods, with no assertion, fixture or production-call change. The target was pre-existing Git-untracked, so ordinary `git diff --` was empty; a pre-edit in-memory baseline and `git diff --no-index` confirmed the content-only import relocation. Target SHA changed from `0a81c59db2969fc6b4fb7f09a5b4ed04b24422dd5f633620f49a4d61934ef191` to `bcf9b8289336d575a184bf3dfb4cd2b6583f05a2f7d205ed4c6d852c06784052`. Static AST syntax passed, showing eight test definitions and eight method-local imports, but these are not collected tests. The command `PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest --collect-only -q -p no:cacheprovider tests/test_step9_63b_mac_local_preflight.py` exited before test-module import with `No module named pytest`. System and bundled Python checks also found no pytest; no install or substitute discovery was run. Consequently collection, import errors and collection exceptions remain **NOT_MEASURED**, and zero test methods executed. The r10 historical freeze manifest SHA, current 20-member path/hash aggregate, and two historical Trace forward SHA baselines were unchanged; original Trace integrity remains `CONTENT_INTEGRITY_UNPROVEN`. No identity guard, r11 freeze, authorization, preflight, production code or V4 case was touched. Outputs: `evaluation/v1_2_3/step9_63c_r5c10y_single_file_modification_report.md`, `step9_63c_r5c10y_diff_hash_audit.json`, `step9_63c_r5c10y_collection_result.json`, and `step9_63c_r5c10y_boundary_audit.json`. Stop pending a separate environment with pytest for the required target-file collection-only verification; do not advance scope on static counts.

## Step 9.63c-r5c10z — Pytest 环境恢复可行性审查

`PASS_READ_ONLY_RECOVERY_PLAN_PYTEST_ABSENT`。本步仅调查环境，没有安装依赖、运行 pytest 或执行测试。重要位置：`.venv/pyvenv.cfg` 说明项目虚拟环境使用 Python 3.12.14 的基础解释器；`README.md` 的 Getting started / Offline regression tests 说明项目安装锁定依赖并使用 `unittest`；`.github/workflows/tests.yml` 说明 CI 同样安装 `requirements-lock.txt` 并使用 `unittest.TestLoader`；`tests/test_step9_63b_mac_local_preflight.py` 是待验证的单文件收集隔离补丁，当前 SHA 仍为 `bcf9b8289336d575a184bf3dfb4cd2b6583f05a2f7d205ed4c6d852c06784052`。依赖链为“项目 `.venv` → Python 3.12.14 → 未声明、未安装 pytest → r5c10y 命令在导入测试模块前退出”，不是虚拟环境不存在或已证实损坏。项目 `.venv` 有 pip 25.0.1 和 101 个 distribution；已检查的系统与 bundled Python 也没有 pytest。关键决定：建议下一阶段经单独批准后，在仓库外 `/private/tmp/cbti-r5c10z-pytest-venv` 建立一次性、精确 pin 的 pytest 环境，仅做 collect-only；不向项目 `.venv` 装包，不改锁文件。开发者应能回答：为何 8 个静态方法不等于收集通过？为何优先隔离环境而非修改既有 `.venv`？已知限制：pytest 精确版本及 wheel 来源尚待批准，常见路径调查不是全盘证明，本阶段未执行任何恢复；历史 Trace 原始内容完整性仍为 `CONTENT_INTEGRITY_UNPROVEN`。产物：`evaluation/v1_2_3/step9_63c_r5c10z_pytest_environment_audit_report.md`、`step9_63c_r5c10z_interpreter_dependency_matrix.json`、`step9_63c_r5c10z_minimal_recovery_recommendation.md`、`step9_63c_r5c10z_environment_change_risk_assessment.json`。等待人工审批，不进入安装或测试。

## Step 9.63c-r5c10aa — 原生 unittest 收集可行性审查

`PASS_READ_ONLY_NATIVE_UNITTEST_COLLECTION_DESIGNED_NOT_RUN`。本步只读检查 `tests/test_step9_63b_mac_local_preflight.py`：其中 `MacLocalPreflightTests(unittest.TestCase)` 定义 8 个 `test_` 方法；生产 transport 的导入全在方法体内，顶层仅导入标准库，`unittest.main()` 有 `__main__` 守卫。相关位置：目标测试文件决定模块导入和测试方法边界；`.github/workflows/tests.yml` 展示项目现有的 `TestLoader` 流程；`scripts/run_step9_53_v3_identity_adapter.py` 的导入时 r11 指针读取解释为何方法内 transport 导入必须保持不执行。设计了使用项目 `.venv` 标准库 `TestLoader.loadTestsFromName` 加载模块、枚举测试 ID 并检查 `loader.errors` 的后续命令；本阶段**没有运行**该命令，也未调用 `TextTestRunner`、`setUp`、`tearDown` 或任何测试方法。r5c10z 的 5 个文件核对为 4 份新审计产物加 `record.md`；它们均未被 Git 跟踪，普通 `git diff` 为空、no-index diff 只显示当前全文件新增，不能仅凭 Git 独立重建以前的追加差异。开发者应能回答：为何静态 8 方法不等于实际收集 8 个？为什么必须检查 `loader.errors`？为何成功收集也不授权执行 `run_preflight()`？限制：模块导入安全是静态审查结论，仍待单独批准的实测；历史 Trace 原始内容完整性保持 `CONTENT_INTEGRITY_UNPROVEN`。本步无代码、依赖、冻结成员、历史 Trace、r11 Freeze、授权或 V4 修改/执行。产物：`evaluation/v1_2_3/step9_63c_r5c10aa_native_unittest_collection_feasibility_report.md`、`step9_63c_r5c10aa_import_side_effect_audit.json`、`step9_63c_r5c10aa_collection_command_proposal.md`、`step9_63c_r5c10aa_five_file_git_diff_audit.json`。等待人工批准后才能仅做收集。

## Step 9.63c-r5c10ab — 测试基础设施恢复与 r11 Freeze 阻断审查

`PASS_GUARDED_FULL_REGRESSION_MEASURED_C1_FIXED_R11_FREEZE_NOT_READY`。

**测试方法：**
- 使用项目 `.venv`（Python 3.12.14）和原生 `unittest`，未安装 pytest，未改动依赖。
- 所有测试在审计钩子 guard 下运行。guard 通过 `PYTHONPATH` 注入，子解释器同样继承。它阻断并记录：仓库内任何写入、改名、删除或元数据变更（含 `dir_fd` 相对路径），非回环网络，以及非 Python 子进程。
- 另以全仓 2,333 个文件的 SHA、大小和 mtime 快照作为独立兜底。
- 实测结果：
  - 收集阶段 0 guard 事件，0 文件变化。
  - 全量回归 0 仓库写入、0 网络访问，仅 2 个被允许的 `python -c` 子进程。

**收集结果：**
- 66 个模块，0 语法错误，收集 648 个方法，8 个导入阻断。
- 对账：603 + 43（r5c10r/t/v/y 隔离后可收集的 9+13+13+8）+ 2（r5c10o 负向测试）= 648。
- r5c10y 遗留项已用原生 unittest 完成验证：`tests/test_step9_63b_mac_local_preflight.py` 收集 8 个，0 导入错误。
- 新发现：`loadTestsFromName` 只把 `ImportError` 转为占位项。适配器抛出的 `RuntimeError` 会中止整次加载，因此 CI 工作流会在第一个阻断模块处直接崩溃。CI 未修改。

**全量回归：**
- 修复前：594 pass、20 fail、34 error。其中 14 个是 guard 把仓库→临时目录的只读复制误判为写入。修正 guard 后，这两个模块重跑 33/33 通过。

**C1 修复：**
- 冻结父 runner 在不传 manifest 时调用 lifecycle reducer。reducer 会读取真实仓库的授权 manifest，因此合成 ID 必然得到 `INCONSISTENT_FAIL_CLOSED`。生产守卫本身正确。
- 只修改了非冻结的 `tests/test_step9_35a_treatment_runner.py`（SHA `793070e74d79ed4156f8f017633a4d82f47edfdd4d2736114121dc2019980068` → `8934cbeee1e93555e56b8778fe1ece248840e366bd034395eb3f44c12c61f781`，+40 行，0 删除）。
- 做法：在临时 lifecycle 根目录放一份合成的已签发证据，用 `patch.object` 隔离 lifecycle 和 transaction 的根路径。真实 reducer 仍完整执行，断言未改动，无 skip、xfail 或异常吞噬。
- 新增 2 个负向测试：缺失签发证据必须得到 `INCONSISTENT_FAIL_CLOSED`，退役事件必须得到 `RETIRED_UNCONSUMED_NON_REUSABLE`。
- 该模块 23/23 通过，读取真实授权或 `v4_runs` 文件 0 次。

**最终全量结果（两次独立运行一致）：** 650 collected / 628 passed / 4 failed / 18 errors / 8 import-blocked modules。剩余 22 项全部归因，0 项未归因：
- C2R：14 项，运行时缺失正式 r11 指针。
- C3：3 项，r9 bootstrap 测试对应 r11-only resolver。
- C4：3 项，归档 r10 快照测试期待 r10 仍可执行。
- C5：1 项，V2 父 runner SHA 漂移。
- C6：1 项，Step 9.51a 固定测试清单漂移。
- 8 个导入阻断模块都源于冻结适配器第 25 行在导入时读取 r11 指针，属于预期的 fail-closed。

**冻结与证据状态：**
- r10 freeze manifest SHA 仍为 `d24244235e51e7bf6c8567880c654fe3fd73b87fa1bfe1ab0f10dfdc94db2693`。17 个成员不变，3 个是已批准的变更。
- 两份历史 Trace 的 SHA 和 mtime 不变，原始内容完整性仍为 `CONTENT_INTEGRITY_UNPROVEN`。
- 全仓快照只显示目标测试文件及其 exFAT AppleDouble 伴随文件变化。

**r11 就绪性：** `READY_FOR_R11_FREEZE_REVIEW = NO`。缺口如下：
- 缺少正式指针的创建机制。
- builder 对 resolver 和 consumer 只检查“与 r10 不同”，未钉住评审后的 SHA。
- `build_candidate()` 依赖不属于 r11 成员的 r5c4 builder。
- 不存在 r11 授权签发器。
- 旧 r10 授权的退役尚待审批。
- C3–C6 测试契约待人工决定。

**本步未发生：** 未创建 r11 Freeze、指针或 Registry；无新授权；无授权消费；无真实事务；无网络或模型调用；无正式 V4 case。

**产物：**
- `evaluation/v1_2_3/step9_63c_r5c10ab_test_infrastructure_report.md`
- `step9_63c_r5c10ab_test_results_matrix.json`
- `step9_63c_r5c10ab_c1_fixture_fix.diff`
- `step9_63c_r5c10ab_test_harness/`（guard、逐模块 runner、快照比对工具）

## Step 9.63c-r5c10ac — 完整回归独立复现、根因归类、最小安全修复与 r11 前置条件验收

`PASS_BASELINE_REPRODUCED_TWO_TEST_INFRA_REPAIRS_R11_FREEZE_NOT_READY`。

**基线复现**
- 先确认仓库相对上一步结束时零漂移（2,355 个文件），并核对保护框架 SHA 未变。
- 新写 guard 自测，18/18 通过（15 条阻断路径，含子进程写仓库和 `dir_fd`；3 条允许路径）。
- 用受保护运行器独立复现得到 650/628/4/18/8 import-blocked，22 个非通过项的 ID 与结果与前任矩阵逐项一致。**628/650 已复现。**

**新发现**
- GitHub CI 只能看到 Git 跟踪的 38/66 个测试模块，8 个导入阻断模块都未被跟踪，所以“CI 崩溃”只在本地工作树上出现。
- 在干净的 `git archive HEAD` 上运行 CI 原脚本，得到 277 tests / 2 errors：HEAD 中的 v1_2 mechanism 测试仍会写历史 Trace，被 guard 阻断。r5c10o 的修复尚未提交。
- 工作树上 CI 脚本因未捕获的 `RuntimeError` 中止，0 tests。
- Git HEAD 中的父 runner blob（`920486b1…`）正是 V2 pin 的归档字节。
- 只读 reducer 显示 r10 授权 `auth-step9_63c_r5c6-…` 仍为 `ISSUED_EXECUTABLE`，尚未退役。

**修复 R1：CI loader**
- 修改 `.github/workflows/tests.yml`（`3d064509…` → `b98554b4…`）：模块级任意异常不再中止加载，而是作为具名的 `import_<module>` 失败测试报告，CI 仍以非零退出。
- 工作树：修复前中止；修复后运行 576 项，4 failures / 25 errors，含 8 个具名导入失败，与 harness 吻合。
- 干净 HEAD：修复前后 test-id 集合完全相同，覆盖未变。

**修复 R2：4 个模块的导入延迟**
- 4 个非冻结、Git 未跟踪的测试模块，把唯一的身份相关顶层 import 原样移入使用它的函数：删 4 行、增 12 行，42 处引用全部覆盖。
- 修改后文件与 scratch 试运行副本逐字节一致。
- 没有用 `LazyLoader`：导入失败时它会在 `sys.modules` 中留下执行了一半的 adapter，属于 fail-open 风险。
- 剩余 4 个导入阻断模块中，0 个方法独立于身份模块，未修改。

**最终受保护回归（两次逐项一致）**
- 745 collected / 659 passed / 8 failed / 78 errors / 4 import-blocked modules。
- 对账：650 + 95；628 + 31；22 + 64 项新显现。
- Guard 阻断 0 次；仓库只出现 5 个预期文件及其 AppleDouble 伴随文件的变化。

**根因归类（86 个非通过项 + 4 个导入阻断模块，0 Unknown，0 已证实的生产回归）**
- RC1 身份依赖：32 项。
- RC3 r9 bootstrap 契约：3 项。
- RC4 归档 r10 live 快照：3 项。
- RC5 V2 父 runner SHA：1 项。
- RC6 9.51a 测试清单：1 项。
- RC7 reducer 消息契约：2 项。
- RC8 r2 fixture 重复键（r8/r6，属于测试缺陷，但取值是语义决定；两种变体实测均为 13 pass）：12 项。
- RC9 r5 producer API 已被兼容 shim 取代，原先被导入阻断掩盖：36 项。

**未改动**：未删除、跳过或弱化测试；未修改断言；冻结成员、历史 Trace、授权、账本、Registry 均未改动；未创建 r11 Freeze、指针或授权；未执行 V4；未 commit。
- r10 manifest 仍为 `d24244…2693`，17/20 个成员一致。
- Trace SHA 不变，原始内容仍为 `CONTENT_INTEGRITY_UNPROVEN`。

**r11 就绪性**：8 PASS / 6 FAIL / 3 BLOCKED / 1 NOT_VERIFIED，`READY_FOR_R11_FREEZE_REVIEW = NO`。缺口：
- 正式指针及其创建流程。
- resolver 和 consumer 的 SHA 未钉住。
- builder 依赖 r5c4 builder。
- 没有 r11 签发器。
- r10 授权未退役。
- 回归未全绿。

**下一步**：审批请求 AR-1 至 AR-16。

**产物**（均在 `evaluation/v1_2_3/`）
- `step9_63c_r5c10ac_baseline_verification_report.md`
- `step9_63c_r5c10ac_failure_root_cause_matrix.json`
- `step9_63c_r5c10ac_repair_change_report.md`
- `step9_63c_r5c10ac_r1_ci_loader.diff`
- `step9_63c_r5c10ac_r2_import_deferral.diff`
- `step9_63c_r5c10ac_regression_results.json`
- `step9_63c_r5c10ac_repository_integrity_report.json`
- `step9_63c_r5c10ac_r11_freeze_readiness_matrix.json`
- `step9_63c_r5c10ac_remaining_blockers_approval_requests.md`

## Step 9.63c-r5c10ad — 测试契约决定 AR-1 ~ AR-7 落实

`PASS_A_GROUP_APPLIED_WITH_4_RESIDUAL_DECISIONS_R11_FREEZE_NOT_READY`。开始时快照与上一步结束时零漂移（2,373 个文件）。

**回归结果**：使用新版 guard v2（符号链接目录项操作只解析父目录，自测 21/21），两次全量回归逐项一致：742 collected / 709 passed / 2 failed / 31 errors / 4 import-blocked；guard 阻断 0 次。

**各项决定**
- **AR-1**：删除重复键中的 r6（变体 A），docstring 写明理由。
- **AR-3**：r1 两个方法改为断言 `INCONSISTENT_FAIL_CLOSED`，并附加显式 manifest 下的派生状态断言（已提交被拒绝、已退役 = `RETIRED_UNCONSUMED_NON_REUSABLE`），每项都有签发态对照组。同一处理也用于 AR-1 后显现的第三个 RC7 方法，已单独标注。
- **AR-2**：36 项逐项映射，覆盖只计入当前能通过、且作用于 r11 清单成员的测试，r5c7 producer 不计入。结果为 15 项退役（逐字节归档到 `tests/retired/*.py.retired`，原 SHA 记于 `RETIRED_INDEX.json`）、19 项改写（新模块 22/22 通过）、2 项 UNCOVERED 原地保留。
- **AR-4**：r5c10j 对 test_09 仅隐式覆盖，test_10、test_18 未覆盖；三项均归档，并用临时根 r11 fixture 重写（3/3 通过）。
- **AR-5**：r5c7d/e 改为断言 r10 归档 hash 等于记录值（`d24244…`、`beac52d1…`、`0f908fb5…`），且 live 快照只能 fail-closed（4/4 通过）。
- **AR-6**：用纯 Python 读取 Git HEAD 中 5 个与 V2 pin 一致的 blob，在临时根子进程中重放 V2 校验（2/2 通过，工作树不变）。
- **AR-7**：新增版本化清单（69 个模块：41 个逐字沿用 + 28 个机械推导风险等级；允许列表未扩大）、新 validator 和新测试（7/7 通过）。

**有效性证据**：9 个内存变异全部被检测到。RC1 原 32 项全部保留并 fail-closed；AR-1 揭示 1 项原被掩盖的身份依赖测试，RC1 总数变为 33。

**残余 4 项非身份失败**
- `test_step9_43a…test_01a`：文件被 V2 freeze 钉住。
- 旧 9.51a 清单测试：文件被 r10/r11 冻结成员 development freeze 钉住。
- 2 项 UNCOVERED。

均按边界未修改，提交你决定（D-1 ~ D-4）。

**新发现**（就绪矩阵新增 R19–R21）
- r11 执行路径上没有 55 个历史 pin 的执行点。
- “恰好 1 个活跃授权”只在需要身份的 producer 中执行。
- `validate_precommit()` 未接入 `execute_formal()`。

**完整性**：未改动任何 r10/r11 冻结成员、受保护 pin、Trace、授权账本、Registry 或历史清单；未执行 AR-8 ~ AR-16；未 commit/push。每项一个 diff；按 ar7 → ar1 逆序 `git apply -R` 在副本上 17/17 恢复基线；BSD `patch -R --dry-run` 对 ar2 以外全部干净（ar2 含文件移动）。

**产物**（`evaluation/v1_2_3/`）
- `step9_63c_r5c10ad_change_report.md`
- `step9_63c_r5c10ad_regression_results.json`
- `step9_63c_r5c10ad_r5_coverage_mapping.json`
- `step9_63c_r5c10ad_repository_integrity_report.json`
- `step9_63c_r5c10ad_r11_freeze_readiness_matrix.json`
- `step9_63c_r5c10ad_remaining_blockers.md`
- `step9_63c_r5c10ad_ar1..7.diff`
- `step9_63c_r5c10ad_test_boundary_manifest.json`
- `step9_63c_r5c10ad_test_harness/`

**r11 就绪性**：`READY_FOR_R11_FREEZE_REVIEW = NO`。

## Step 9.63c-r5c10ae — AR-17 consumer 预提交接线，AR-10/AR-11 builder 前置条件

`PASS_AR17_AR10_AR11_IMPLEMENTED_TWO_ITEMS_STOPPED_FOR_APPROVAL_R11_FREEZE_NOT_READY`。开始时快照与上一步结束时零漂移（2,434 个文件）。

**对上一步的决定已落实**：RC1=33、RC5、RC6 标为 ACCEPTED_KNOWN；AR-3 第三个方法已追认；guard v2 未改动，其与 v1 的差异列入变更报告。

**AR-17 只读审计**（`step9_63c_r5c10ae_consumer_path_audit.md`）共列出 G1–G8 八处缺口，主要包括：
- `validate_precommit` 未接线。
- 55 个历史 pin 在 r11 路径上没有检查点。
- “恰好 1 个活跃授权”只在 producer 检查。
- `main()` 输出含写死值。
- r6 时代的死代码含写死值。
- 旧授权仍可执行时没有阻断。
- 62b 把只追加账本的整个文件 SHA 当作 pin。

**AR-17 修复**：只修改 consumer（`cd0d0706…` → `297558393e56…`），未触及 adapter、`authorization_lifecycle.py`、账本或任何 r10 字节。
- 新增 `prepare_formal_gates()`，在冻结 adapter 导入和 `adapter.run()` 之前，用真实结果执行 `validate_precommit(state, R11_PRECOMMIT_KEYS)`。任一检查失败或未执行都会 fail-closed。
- consumer 独立重新统计活跃授权，并按前缀语义校验 55 个 pin（真实仓库 55/55）。
- 新增“非当前版本授权不可执行”检查：在 AR-14 之前，正式执行会因此被阻断（R22）。
- 发现：r6 审计读取的 `formal_execution_commit_protocol` 字段并不存在；原子提交和崩溃恢复两项改为读取 r11 freeze 钉住的原子提交合约。
- 新测试 28/28 通过，每个检查点都有负向测试并断言无写入。

**AR-10**：builder 钉住 resolver `a0f5670d3834d5f91391b41a33fbac669d6162587bc620e9bd3acf202aa3c6a5` 和 consumer `297558393e56c645fb02b4ec45d4af41486b504034bdd717237b7738a21f4879`（scanner 维持原值），删除“与 r10 不同即接受”的逻辑，并强制 pin 表完整。

**AR-11**：`verify_frozen_inputs` 及其两个 helper 逐字内联进 builder，成员数仍为 20；静态文本一致，14 个场景的差分结果完全一致。builder SHA 变为 `eaa113da…`。

**变异测试**：29/29 KILLED，全部由行为测试判定。

**全量回归**（两次逐项一致）：776 collected / 741 passed / 4 failed / 31 errors / 4 import-blocked；RC1 仍为 33，且与上一步是同一集合；生产回归 0，未知 0。

**未达验收、按规则停下的两项**：
- AR-7 清单因本步新增 2 个测试模块而漂移（2 项失败，同时使 RC6 的等价覆盖暂时失效）。
- 2 项 RC9 现在已有 consumer 侧覆盖，可以退役。

两者都需要你批准（E-1、E-2）。

**完整性**：r10 manifest、adapter、lifecycle、r5c4 builder、Trace、9.51a 清单、r5c10ad 清单和账本均未改动；未创建 r11 指针、freeze、registry 或授权；未 commit。按 ar11 → ar10 → ar17 逆序执行 `git apply -R`，4/4 恢复基线。

**就绪性**：R06、R07、R19、R20、R21 变为 PASS；新增 R22 BLOCKED（等待 AR-14）。矩阵为 13 PASS / 4 FAIL / 4 BLOCKED / 1 NOT_VERIFIED，`READY_FOR_R11_FREEZE_REVIEW = NO`。

**产物**（`evaluation/v1_2_3/`）
- `step9_63c_r5c10ae_consumer_path_audit.md`
- `step9_63c_r5c10ae_change_report.md`
- `step9_63c_r5c10ae_regression_results.json`
- `step9_63c_r5c10ae_mutation_results.json`
- `step9_63c_r5c10ae_repository_integrity_report.json`
- `step9_63c_r5c10ae_r11_freeze_readiness_matrix.json`
- `step9_63c_r5c10ae_remaining_blockers.md`
- `step9_63c_r5c10ae_ar17.diff`、`ar10.diff`、`ar11.diff`

## Step 9.63c-r5c10af — r5c10ae 遗留项收尾，AR-12/AR-13 设计草案

`PASS_FIVE_DECISIONS_APPLIED_GUARD_V3_CANDIDATE_NOT_APPROVED_DESIGN_DRAFTS_ONLY`。开始时快照与上一步结束时零漂移（2,458 个文件）。AR-10 钉住的 resolver `a0f5670d…` 与 consumer `29755839…` 全程未变。

**回归**（两次逐项一致）：805 collected / 774 passed / 2 failed / 29 errors / 4 import-blocked。RC1 仍是与上一步相同的 33 项；非身份类失败只剩已接受的 RC5、RC6；未知 0，生产回归 0。用 v2 guard 的 harness 做对照运行，除 guard 负向测试模块外其余 793 项逐项一致。

**1. AR-7**：新建 r5c10ae 版本化测试清单（73 个模块，允许列表仍是 31 个）和 validator。清单路径与版本号是常量，没有任何目录发现类调用，旧 r5c10ad 清单 SHA（`acf0b429…`）被钉住；旧清单中沿用的行，其决定字段不可变。5 个变异全部被检测到。**推论**：因为新增测试模块使 r5c10ad 清单不再覆盖当前清单，把它自己的两个测试限定在它记录的 69 个模块上（重新推导的 69 行与旧清单逐行一致）。该改动单独成 diff，待你确认。

**2. 退役 2 项 r5 UNCOVERED**：已归档（原文件字节在 `tests/retired/` 中）。新 coverage mapping 为 17 项退役已覆盖、19 项改写、0 项 UNCOVERED。为精确对应旧的 54/55 属性，新增 2 个 consumer 门测试；9 个变异全部被检测到。已如实记录一处差异：旧测试还断言了评估顺序，这个细节没有对应物。

**3. AR-11 测试替身**：项目没有 pytest，用显式的 `scoped_adapter_stub`（总是还原并断言恢复）代替 `monkeypatch.setitem`。当前真实 adapter 因缺少 r11 指针无法导入，所以"恢复"表现为恢复为不存在。builder 接口未改。

**4. guard v2 负向测试**：119 个场景（硬链接、rename/replace、符号链接、各类写入入口、子进程、已知限制），在临时假仓库上运行，并先不带 guard 跑一遍证明场景有效。v1：30 绕过 + 4 误报；**v2：31 绕过**；v3 候选：0 绕过，118 PASS + 1 项已记录的不可阻断（`ctypes` 直接调用 libc）。v2 失守的 11 类包括：已存在的硬链接、符号链接之后的 `..`、尾随斜杠穿透符号链接（v2 相对 v1 的新回退）、描述符形式的 chmod/utime、`mkfifo`/`mknod`、`sqlite3`、`os.open(dir_fd=)`、大小写别名、**重命名/删除/锁定仓库的上级目录**、子进程逃逸（`-I`/`-S`/`-E`、清空或改写环境、`exec`/`posix_spawn`）。guard 变异 22/23 被检测到，剩下 1 个是冗余的纵深防御。**v2 未批准，v3 候选待你批准**；v1、v2 文件字节不变。我曾误写一个"v1 对 copymode/copystat 失守"的类别，经核实是早期场景的缺陷，已从结果中删除。

**5. AR-14**：未执行。顺序记录为 AR-12/AR-13 设计审定 → AR-14 → 激活。已核实退役函数不检查判定文件里的"当前 Freeze"字段，可在 r11 Freeze 不存在时执行。

**6. 设计草案**（只有文档）：AR-12（指针创建，含规范字节 SHA `4e077781…`、前置条件、幂等与原子策略、失败矩阵、人工确认点、验证方法、8 个决定点）；AR-13（签发器，含 12 项签发条件、签发侧"恰好 1 个活跃授权"的四层保证、与 r7 签发器的差异、账本事件格式、撤销/退役路径、9 项威胁及防御、7 个决定点）。写草案时核实并修正了自己的两处错误：Registry 的 claim 不记录授权清单 SHA；`assemble_candidate` 在 Freeze 已存在时会拒绝，因此需要 builder 新增只读的验证入口。实测发现 exFAT 不支持硬链接且 `rename` 会静默覆盖，所以无覆盖的原子创建只能依赖 `O_EXCL`。

**未做**：未创建 r11 指针、Freeze、Registry 或授权；未执行 AR-14；未修改 r10/r11 冻结成员、adapter、`authorization_lifecycle.py`、账本、历史 Trace、历史清单；未 commit。回滚：五份 diff，按反序 `git apply -R` 在副本上 17/17 路径逐字节恢复。

**就绪性**：`READY_FOR_R11_FREEZE_REVIEW = NO`。矩阵 14 PASS / 5 FAIL / 5 BLOCKED / 1 NOT_VERIFIED（新增 R23 清单 PASS、R24 guard 批准 BLOCKED、R25 builder 激活入口 FAIL）。

**产物**（`evaluation/v1_2_3/`）：`step9_63c_r5c10af_change_report.md`、`_regression_results.json`、`_guard_negative_results.json`、`_ar12_identity_pointer_design.md`、`_ar13_authorization_issuer_design.md`、`_r11_freeze_readiness_matrix.json`、`_remaining_blockers.md`、`_r5_coverage_mapping.json`、`_repository_integrity_report.json`、`_ar7e.diff`、`_ar7e_adtest.diff`、`_ar2r.diff`、`_ar11t.diff`、`_ar4g.diff`、`_test_boundary` 相关的 r5c10ae 清单、`_test_harness/`、`_mutation_tools/`。

## Step 9.63c-r5c10ag — AR-12 指针创建与 AR-13 授权签发器（一次 builder 修订），不激活

`PASS_IMPLEMENTED_AND_REHEARSED_ON_TEMPORARY_ROOTS_NOTHING_ACTIVATED`。真实仓库里没有 r11 指针、Freeze、Registry、授权、批准记录或 AR-14 判定文件；真实账本仍是 3856 字节、没有增加任何字节；没有 commit、没有 push。`READY_FOR_R11_FREEZE_REVIEW = NO`（矩阵 21 PASS / 4 FAIL / 6 BLOCKED）。

**新 SHA**：consumer `362eb4467fdadd29edc056ecf7b446f2cab99a2d3c407d350b4e91494c5b9528`（原 `29755839…`）；builder `7f72a17c584efe7ee66ee95290d28b6c55daf83ccc08ebebeb3f9319dec30f81`（原 `eaa113da…`）；r11 签发器 `f41763f5c82e04360b3d9bcf694e6d05a6fcfa42ae8d71ada29be4ab204e32ab`（新，第 7 号成员）。resolver 仍是 `a0f5670d3834d5f91391b41a33fbac669d6162587bc620e9bd3acf202aa3c6a5`。

**做了什么**：①AR-12——规范指针字节（389 字节，SHA `4e077781…f696fe`，测试里同时断言长度和 SHA）；唯一的写入口 `--create-pointer` 要求交互终端（stdin 和 stdout 都是 TTY）、人工键入令牌、前置条件 PP1/2/4/5/6/7/9、`O_EXCL`+fsync+回读、幂等与断点续写，绝不覆盖；默认只读 `--plan/--status/--verify/--verify-freeze/--print-approval-draft`；②AR-13——r11 签发器替换第 7 号成员，条件 I0–I13/IX1，每个 Freeze 修订只允许一份授权，账本追加 `AUTHORIZATION_ISSUED`，写入口 `--issue` 与恢复入口 `--complete-record` 同样要终端+令牌；③D13-4——consumer 预提交门核对账本里恰好一个签发事件且与磁盘清单一致（缺失/重复/任一字段不符/清单被改全部 fail-closed）；④新增 r5c10ag 批准记录（确定性：预测的 Freeze SHA、整仓聚合哈希、预生成的签发身份）与 `--verify-freeze`。

**验证**：141 个新测试全部通过；变异验证 93 个变异体，77 个被杀，16 个幸存者全部是冗余对（组合变异体被杀）或等价变异；端到端演练（临时根）AR-14 → 批准 → 指针 → Freeze → 签发 → consumer 门通过，恰好 1 个活动授权，未进入正式执行，三个负向演练（删签发事件/手写清单/重复签发）均被 consumer 拒绝。变异验证与测试还发现并修复了签发器的两个真缺陷（悬空符号链接使 `--plan` 崩溃；`--complete-record` 被自己的清单挡住）。

**回归**（guard v3，两次逐项一致）：945 项 = 908 通过 / 8 失败 / 29 错误 / 4 导入阻断。RC1 仍是同一个 33 项集合；生产回归 0、未知 0。8 个失败：RC1 1、RC6 1（已接受）、r5c10ad 清单 2（已接受）、r5c10ae 清单 2（被 r5c10ag 清单取代，待你确认）、r5c10ae builder-pins 字面量与 gate 正向对照各 1（新的耦合，**未修改历史测试**，附未应用的提案 diff）。整仓哈希两次回归前/中/后零变化。

**偏离与待决**：令牌由 `授权 ID|Freeze SHA|批准记录 SHA` 派生（设计 H3 的清单 SHA 不可行）；未变成员实为 13 个而不是 14（第 7 号成员被替换）；AR-14 与创建 Freeze 都没有门禁入口（D-A、D-B，建议下一次 builder 修订加入）；guard v3 是防误操作护栏不是安全边界；回滚了 `ar7e_adtest.diff`（ad 测试恢复为 `eaa60942…`）。

**产物**（`evaluation/v1_2_3/`）：`step9_63c_r5c10ag_change_report.md`、`_regression_results.json`、`_mutation_results.json`、`_e2e_rehearsal_report.json`、`_repository_integrity_report.json`、`_r11_freeze_readiness_matrix.json`、`_remaining_blockers.md`、`_guard_scope.md`、`_consumer.diff`、`_builder.diff`、`_issuer.diff`、`_tests.diff`、`_manifest.diff`、`_PROPOSED_ae_test_updates.diff`（未应用）、`_mutation_tools/`、`_test_boundary_manifest.json`；`step9_63c_r11_activation_runbook.md`、`step9_63c_r11_activation_approval_checklist.md`、`step9_63c_r11_activation_approval.DRAFT.json`（**未签署**，AR-14 之后必须重新生成）。新代码：`scripts/issue_step9_63c_r11_authorization.py`、`scripts/validate_step9_63c_r5c10ag_test_boundary.py`、`tests/r11_activation_fixtures.py` 与 5 个 `tests/test_step9_63c_r5c10ag_*.py`。

## Step 9.63c-r5c10ah — AR-14 与 Freeze 创建的门禁入口（D-A、D-B），清理被取代的历史测试，重新生成批准记录草案

`PASS_GATED_ENTRIES_IMPLEMENTED_AND_REHEARSED_ON_TEMPORARY_ROOTS_NOTHING_ACTIVATED`。真实仓库里没有 r11 指针、Freeze、Registry、授权或已签署的批准记录；没有执行 AR-14；真实账本仍是 3856 字节、没有增加任何字节；我没有 commit、没有 push。`READY_FOR_R11_FREEZE_REVIEW = NO`（矩阵 26 PASS / 2 FAIL / 6 BLOCKED）。

**SHA**：builder `9cfaf75a1c7ab2b2a6b0c0126c77692e02144f8483f9384fb361f3b92f832ea9`（原 `7f72a17c…`，**唯一变化**）；consumer `362eb446…9528`、签发器 `f41763f5…32ab`、resolver `a0f5670d…c6a5` 均未变。

**做了什么**：①builder 新增 `--plan-retire/--verify-retire/--retire-r10`（只调用冻结的退役函数；写前核对账本钉值、r10 仍为 ISSUED_EXECUTABLE、判定文件引用批准记录；写后核对旧字节不变、恰好一行、等于模板、reducer 已退役）和 `--plan-freeze/--create-freeze`（AR-14 与指针为前置；O_EXCL+fsync+读回；SHA 必须等于预测）；②批准记录改成只需在 AR-14 之前签一次（整仓聚合哈希排除各步骤产物并单独钉住它们）；③H3：`--issue` 写入前证明清单与计划逐字节一致（除 issued_at_utc），放在 builder 的独占写原语里，签发器未动；④常设规则：九个被取代的钉值/清单/读回测试按 AR-2 归档退役，取代测试用变异证明（13/13）；⑤新的运行手册（每步只调用门禁入口）、核对清单、批准记录草案；“14 个未变成员”在本步所有文档里统一为 13。

**验证**：107 个新测试通过；变异 77 个，63 被杀，14 个幸存者全部归类；门禁端到端演练 PASS，31 个负向演练全部被拒绝且无写入；回归两次逐项一致：1043 项 = 1010 通过 / 4 失败 / 29 错误 / 4 导入阻断，RC1 同一个 33 项集合，整仓哈希零变化。

**待决**：检查点提交 `23994b2` 把 HEAD 移到了当前字节，使 r5c10ad 归档重放的 2 个测试失败（非本步引起；未应用的提案 `PROPOSED_ad_archival_replay_update.diff` 已验证）；我多退役了 r5c10ag 的 3 个测试（后果性的）；AR-14 之后账本只能钉规则+模板；仓库里放了一个惰性的 AR-14 判定文件。

**产物**（`evaluation/v1_2_3/step9_63c_r5c10ah_*`）：`change_report.md`、`regression_results.json`、`mutation_results.json`、`e2e_gated_rehearsal_report.json`、`repository_integrity_report.json`、`r11_freeze_readiness_matrix.json`、`remaining_blockers.md`、`coverage_mapping.json`、`activation_runbook.md`、`activation_approval_checklist.md`、`test_boundary_manifest.json`、`builder.diff`、`tests.diff`、`retirement.diff`、`manifest.diff`、`determination_file.diff`、`PROPOSED_ad_archival_replay_update.diff`（未应用）、`mutation_tools/`；`step9_63c_r11_activation_approval.DRAFT.json`（**未签署**）、`step9_63c_r11_ar14_determination.json`（惰性）。

**勘误（r5c10ai 追加）**：更早步骤的文档和就绪矩阵（r5c10c–r5c10af 的若干记录）里的“14 个未变成员”是当时的口径（把 r7 签发器算作与 r10 相同）。自 r5c10ag 起第 7 号成员被 r11 签发器替换，20 个成员的构成是：13 个与 r10 逐字相同 + 3 个已批准变更（scanner、resolver、consumer）+ 4 个新增/替换（指针、r11 producer、r11 builder、r11 签发器）。本步及之后的所有文档和批准记录统一写 13；历史文档按你的决定不改。

## Step 9.63c-r5c10ai — 最终待签署的激活批准记录；归档重放、退役令牌、AR-15、提交钉

`PASS_FINAL_APPROVAL_PACKAGE_PREPARED_NOTHING_ACTIVATED`。真实仓库里没有 r11 指针、Freeze、授权或已签署的批准记录；没有执行 AR-14；真实账本仍是 3856 字节；我没有 commit、没有 push。`READY_FOR_R11_FREEZE_REVIEW = NO`（矩阵 29 PASS / 6 BLOCKED（等待人工激活）/ 2 ACCEPTED_EXCEPTION / 0 FAIL）。

**SHA**：builder `99031a9156da87164c16b71eff9e2a9961428c52bbf7bc2590741e51e55f950e`（原 `9cfaf75a…`，唯一变化）；consumer `362eb446…9528`、签发器 `f41763f5…32ab`、resolver `a0f5670d…c6a5` 均未变。

**做了什么**：①R16/R33：不应用提案；r5c10ad 重放模块整体归档退役，新模块固定读取提交 201ef5c 并断言它是 HEAD 的祖先；②退役令牌第一段改为 r10 ID 的 uuid 前 12 位 `aff5c4b96bb7`，第二段为批准记录内容哈希（四个签名字段置空后的 SHA；这样令牌现在就能写全，且签署后不变），补了“另一个 step9_6x 前缀被拒绝”等负向测试；③“14→13”勘误；④批准记录新增 `accepted_exceptions`（AR-15）、`signed_at_commit`/`commit_pin`（签署时填，所有入口核对 HEAD 不变）、`content_sha256`；R15 为 ACCEPTED_EXCEPTION；⑤AR-14 之后账本按“模板 + 前缀不变 + 恰好多一行”验证。

**验证**：36 个新测试通过；变异 33/33 被杀；最终版本的门禁演练 PASS，46 个负向演练全部被拒绝且无写入；回归两次逐项一致：1074 项 = 1043 通过 / 2 失败（RC1 的 1 个 + RC6）/ 29 错误 / 4 导入阻断；非身份类失败只剩 RC5、RC6，RC1 同一个 33 项集合，整仓哈希零变化。

**产物**（`evaluation/v1_2_3/step9_63c_r5c10ai_*`）：`change_report.md`、`regression_results.json`、`mutation_results.json`、`final_form_rehearsal_report.json`、`repository_integrity_report.json`、`r11_freeze_readiness_matrix.json`、`remaining_blockers.md`、`coverage_mapping.json`、`activation_approval_checklist.md`、`activation_runbook.md`、`test_boundary_manifest.json`、`builder.diff`、`tests.diff`、`retirement.diff`、`manifest.diff`、`mutation_tools/`；`step9_63c_r11_activation_approval.DRAFT.json`（最终待签署，未签署）。

**r5c10ai-fix**：只修正激活核对清单（第 8、9 节有 3 条期望输出是在 builder 最后一次修改之前对旧草案生成的，含 KeyError 和旧内容哈希）。未改任何代码、未 commit、未执行写入入口。在最终仓库上重新生成清单，新增生成器和自检（重跑全部 44 条命令并逐字比对，44/44 一致）；因清单变化重新生成了草案的 `repository_aggregate`，内容哈希和三个令牌不变。见 `step9_63c_r5c10ai_fix_report.md`。
