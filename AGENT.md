# CBTI-Doctor Agent Development Guidelines

> 本文件定义 CBTI-Doctor 项目的长期 AI Coding Agent（AI
> 编程智能体）开发规范。\
> 所有由 ChatGPT Work、Codex、Claude Code 或其他 Coding
> Agent（编程智能体）执行的代码修改，应优先遵循本文件。\
> 本文件描述长期稳定的工程原则；具体版本功能需求应放在独立的设计文档或任务提示词中。

------------------------------------------------------------------------

## 1. Project Goal（项目目标）

CBTI-Doctor 是一个基于 CBT-I（失眠认知行为治疗）知识的智能睡眠辅助系统。

当前系统正在从 Fixed Workflow（固定工作流）升级为：

**Cost-Aware Adaptive Agent（成本感知自适应智能体）**

核心目标不是增加更多 Agent（智能体），而是让系统根据当前
Goal（目标）、Facts（事实）、Evidence（外部证据）和 Information
Sufficiency（信息充分性），动态决定下一步最值得执行的 Action（行动）。

核心 Agent Loop（智能体循环）：

``` text
User Query
    ↓
Input Understanding
    ↓
Goal + Facts + Task Type
    ↓
Requirements
    ↓
AgentState
    ↓
Sufficiency Estimation
    ↓
Candidate Actions
    ↓
Decision Policy
    ↓
ASK / RETRIEVE / READ_DIARY / ANSWER
    ↓
State Update
    ↓
Re-evaluate
    ↓
...
    ↓
ANSWER
```

------------------------------------------------------------------------

## 2. Core Architecture Principles（核心架构原则）

### 2.1 Task Type does NOT directly determine Action

`task_type` 只用于帮助确定 Requirements（信息需求），不得直接映射为
Action（行动）。

禁止：

``` python
if task_type == "KNOWLEDGE_QA":
    action = "RETRIEVE"
```

正确的数据流：

``` text
Task Type
    ↓
Requirements
    ↓
Current State
    ↓
Sufficiency
    ↓
Candidate Actions
    ↓
Decision Policy
    ↓
Action
```

------------------------------------------------------------------------

### 2.2 Missing Information does NOT mean Must Ask

必须遵循：

``` text
Missing Information ≠ Must Ask
```

存在缺失信息并不意味着必须向用户询问。

系统应判断该信息是否会显著帮助完成当前 Goal（目标）。

尤其是 Secondary Missing
Information（次要缺失信息），不得为了"补齐字段"而全部询问。

------------------------------------------------------------------------

### 2.3 All decisions must remain Goal-Aligned

所有以下 Action：

``` text
ASK
RETRIEVE
READ_DIARY
ANSWER
```

都必须围绕当前 `goal` 进行判断。

不得因为某个睡眠因素通常"很重要"就自动获取。

必须避免：

**Goal Drift（目标漂移）**

例如：

``` text
Goal:
判断是否应该调整上床时间
```

不得无必要地把任务扩展为：

``` text
寻找所有可能导致失眠的原因
```

------------------------------------------------------------------------

### 2.4 Separate User Information and Evidence

必须区分：

``` text
User Information（用户信息）
```

与：

``` text
Evidence（外部知识证据）
```

分别维护：

``` text
user_info_sufficiency

evidence_sufficiency
```

用户信息不足和外部知识不足是不同的问题，不得混为一个"信息不足"。

------------------------------------------------------------------------

### 2.5 One Action at a Time

系统当前支持四种 Action：

``` text
ASK
RETRIEVE
READ_DIARY
ANSWER
```

每次 Decision Policy（决策策略）只选择一个 Action。

执行：

``` text
RETRIEVE
READ_DIARY
```

之后必须：

``` text
Update State
→ Recalculate Missing Information
→ Re-estimate Sufficiency
→ Generate Candidate Actions
→ Decide Again
```

`ASK` 通常结束当前交互回合，保存
State（状态），等待用户提供新信息后继续。

------------------------------------------------------------------------

### 2.6 Never Fabricate Missing Information

未知用户信息必须保持：

``` text
null
unknown
unavailable
```

不得根据常识、上下文猜测或补全用户没有提供的数据。

特别禁止伪造：

-   sleep diary data（睡眠日记数据）
-   bedtime / wake time（上床/起床时间）
-   sleep duration（睡眠时长）
-   stress level（压力程度）
-   caffeine use（咖啡因使用）
-   clinical history（临床历史）

------------------------------------------------------------------------

## 3. Task Taxonomy（任务分类体系）

V1 默认支持四种 Task Type（任务类型）：

``` text
KNOWLEDGE_QA
知识问答

CAUSE_ASSESSMENT
原因评估

PERSONALIZED_DECISION
个性化方案决策

DATA_ANALYSIS
数据分析
```

不要在没有明确需求的情况下增加新的 Task Type。

如需增加或修改 Task Type，应同步检查：

``` text
Requirements Library
Evaluation Cases
Prompts
State Schema
Decision Policy
Tests
```

------------------------------------------------------------------------

## 4. Requirements System（信息需求系统）

Requirements（信息需求）应独立于 Action（行动）。

推荐区分：

``` text
User Requirements
（用户信息需求）

├── Critical Requirements
│   （核心信息需求）
│
└── Secondary Requirements
    （次要信息需求）

Evidence Requirements
（外部证据需求）
```

Missing Information（缺失信息）应根据当前 Facts（事实）动态计算：

``` text
Missing Information
=
Requirements - Known Facts
```

不得在代码中维护另一套与 Requirements 不一致的固定缺失字段列表。

------------------------------------------------------------------------

## 5. AgentState（智能体状态）

Adaptive Agent（自适应智能体）的核心信息应集中在明确、可测试的 State
Schema（状态结构）中。

建议至少维护：

``` python
AgentState = {
    "goal": None,
    "task_type": None,

    "facts": {},

    "critical_missing": [],
    "secondary_missing": [],

    "evidence": [],

    "user_info_sufficiency": "LOW",
    "evidence_sufficiency": "LOW",

    "available_diary": False,

    "candidate_actions": [],
    "action_history": []
}
```

具体实现可以根据现有代码使用：

-   dataclass（数据类）
-   TypedDict（类型化字典）
-   Pydantic Model（数据验证模型）
-   其他清晰的 typed structure（类型化结构）

但不得让关键状态散落在多个不可追踪的全局变量中。

------------------------------------------------------------------------

## 6. Sufficiency Estimation（充分性判断）

V1 使用：

``` text
LOW
MEDIUM
HIGH
```

分别判断：

``` text
User Information Sufficiency
（用户信息充分性）

Evidence Sufficiency
（外部证据充分性）
```

V1 不允许输出未经验证的精确概率，例如：

``` text
0.82
87%
0.91 confidence
```

除非后续 Benchmark（基准测试）和 Calibration（校准）已经提供数据依据。

Sufficiency（充分性）必须针对当前 Goal
判断，而不是根据"字段是否全部填写"判断。

------------------------------------------------------------------------

## 7. Candidate Actions（候选行动）

Candidate Action（候选行动）必须具体。

不要只生成：

``` json
{
  "action": "ASK"
}
```

应该明确 Target（目标信息）：

``` json
{
  "action": "ASK",
  "target": "wake_time"
}
```

RETRIEVE（检索）也应该提供与当前 Goal 直接相关的 Query（查询）：

``` json
{
  "action": "RETRIEVE",
  "query": "CBT-I evidence relevant to bedtime adjustment with prolonged sleep onset latency"
}
```

不得为了"多获取一些知识"执行与 Goal 无关的广泛检索。

------------------------------------------------------------------------

## 8. Decision Policy（决策策略）

V1 使用：

**Heuristic Policy（启发式决策策略）**

不要在 V1 中引入：

-   Reinforcement Learning（强化学习）
-   Learned Policy（学习型策略）
-   新训练的决策模型
-   未经校准的成功概率

Candidate Action 可以使用粗粒度评价：

``` text
Expected Benefit:
LOW / MEDIUM / HIGH

Cost:
LOW / MEDIUM / HIGH
```

概念目标：

``` text
Utility ≈ Expected Benefit - Cost
```

但 V1 不需要把这些等级强行转换为虚假的精确数字。

Decision Policy 应优先考虑：

1.  当前信息是否已经足以完成 Goal。
2.  Critical Missing Information 是否真的会改变当前决策。
3.  所需信息是否已经存在于 Sleep Diary（睡眠日记）。
4.  是否必须通过 ASK（询问）才能获取。
5.  是否缺少完成 Goal 所需的 Evidence（外部证据）。
6.  新 Action 的预期收益是否值得其 Cost（成本）。

不得简单选择 Requirements 列表中的第一个 Missing Field（缺失字段）。

------------------------------------------------------------------------

## 9. Tool Rules（工具规则）

### RETRIEVE

优先复用现有 RAG（检索增强生成）系统。

推荐统一接口：

``` text
RETRIEVE(query)
→ evidence
```

检索 Query 必须与当前 Goal 相关。

------------------------------------------------------------------------

### READ_DIARY

推荐统一接口：

``` text
READ_DIARY(requirements)
→ diary facts
```

如果当前版本尚未接入真实 Sleep Diary（睡眠日记），允许使用明确的
Mock（模拟实现）或 Session Data（会话数据）。

如果数据不存在：

``` text
available_diary = False
```

必须明确返回不可用，不得生成虚假日记数据。

------------------------------------------------------------------------

### ASK

ASK 应只询问当前最有价值的信息。

避免一次提出大量问题。

ASK 后必须保存当前 Session State（会话状态），等待用户下一轮输入后继续。

------------------------------------------------------------------------

### ANSWER

ANSWER 应使用：

``` text
Goal
+
Relevant Facts
+
Relevant Evidence
```

生成最终回答。

如果 Critical
Information（核心信息）不足以支持个性化结论，不得为了完成流程而伪装成确定结论。

------------------------------------------------------------------------

## 10. Loop Safety（循环安全）

Adaptive Agent 必须具有：

``` text
max_steps
```

等循环保护机制。

不得允许：

``` text
ASK → ASK → ASK → ...
```

或：

``` text
RETRIEVE → RETRIEVE → RETRIEVE → ...
```

无限执行。

达到 `max_steps`
后，应安全结束当前循环，并根据已有信息给出有限度的响应或明确说明信息不足。

------------------------------------------------------------------------

## 11. Existing Code Preservation（现有代码保护）

优先复用现有：

-   RAG pipeline（RAG 流程）
-   API endpoints（API 接口）
-   model clients（模型客户端）
-   Flask infrastructure（Flask 基础设施）
-   session handling（会话管理）
-   retrieval data（检索数据）
-   已通过测试的功能

除非确有必要，不要大规模重写已有模块。

新增 Adaptive Agent Logic（自适应智能体逻辑）应：

``` text
modular
low-coupling
testable
replaceable
```

即模块化、低耦合、可测试、可替换。

不要为了"代码更漂亮"进行与当前任务无关的大规模重构。

------------------------------------------------------------------------

## 12. Development Workflow（开发流程）

执行较大的代码修改前：

1.  阅读相关现有代码。
2.  说明当前行为。
3.  明确准备修改的模块。
4.  列出新增/修改文件。
5.  解释修改原因。
6.  实现最小可工作的改动。
7.  添加或更新测试。
8.  运行相关测试。
9.  检查 Regression（回归问题）。
10. 总结修改结果。

如果需求可以通过小范围修改完成，不得主动扩大修改范围。

每完成一个核心模块，应说明：

-   修改了什么；
-   为什么这样设计；
-   输入是什么；
-   输出是什么；
-   在 Agent Loop 中的位置；
-   关键代码在哪里；
-   如何测试；
-   当前仍有哪些限制。

------------------------------------------------------------------------

## 13. Testing Requirements（测试要求）

Adaptive Agent 相关修改至少应考虑：

``` text
Goal Extraction
Fact Extraction
Task Classification
Requirements Lookup
Missing Information Calculation
Sufficiency Estimation
Candidate Action Generation
Decision Policy
State Update
Session Persistence
max_steps
```

同时必须执行 Regression Testing（回归测试），确保已有：

``` text
RAG
API
Session
existing conversation behavior
```

没有因新架构被无意破坏。

------------------------------------------------------------------------

## 14. Core V1 Acceptance Cases（核心验收案例）

### Case 1 --- Personalized Decision

``` text
我每天11点上床，一个小时才能睡着，我应该早点上床吗？
```

期望：

``` text
PERSONALIZED_DECISION
→ identify missing critical user information
→ ASK or READ_DIARY when appropriate
→ do not immediately fabricate personalized advice
```

------------------------------------------------------------------------

### Case 2 --- Knowledge QA

``` text
什么是刺激控制？
```

期望：

``` text
KNOWLEDGE_QA
→ no unnecessary personal questions
→ RETRIEVE when evidence is insufficient
→ ANSWER
```

------------------------------------------------------------------------

### Case 3 --- Data Analysis

``` text
帮我分析最近7天的睡眠日记。
```

期望：

``` text
DATA_ANALYSIS
→ READ_DIARY when diary is available
→ State Update
→ Re-evaluate
→ ANSWER or RETRIEVE if additional evidence is necessary
```

------------------------------------------------------------------------

## 15. Evaluation & Logging（评估与日志）

Agent 的决策过程应尽可能记录：

``` text
case_id
goal
task_type
initial_facts
state_history
critical_missing
secondary_missing
user_info_sufficiency
evidence_sufficiency
candidate_actions
chosen_action
action_history
tool_calls
retrieved_evidence
total_turns
token_usage
latency
final_answer
```

Evaluation Log（评估日志）不得污染现有 RAG 数据或业务数据。

如果使用本地文件，优先放置在：

``` text
evaluation/runs/
```

并使用 JSONL（逐行 JSON）等便于后续 Benchmark 分析的格式。

------------------------------------------------------------------------

## 16. Evaluation Objective（评估目标）

不要只优化 Answer Quality（回答质量）。

CBTI-Doctor 的 Adaptive Agent 同时关注：

``` text
Task Success
Answer Quality
Tool Calls
Conversation Turns
Token Cost
Latency
Redundant Actions
Goal Relevance
```

系统不应通过无限增加：

``` text
ASK
RETRIEVE
READ_DIARY
```

来换取微小的回答质量提升。

核心目标是：

> 在维持可靠任务完成质量的同时，减少没有足够价值的额外行动。

------------------------------------------------------------------------

## 17. Medical Safety（医疗安全）

CBTI-Doctor 是辅助型睡眠与 CBT-I 系统，不应被实现为自动医疗诊断系统。

开发时必须：

-   不伪造临床结论。
-   不把不确定信息描述为确定事实。
-   不根据有限信息生成确定性诊断。
-   个性化建议必须受到 Information Sufficiency（信息充分性）约束。
-   Safety-Critical Situation（安全关键情况）应进入独立的 Safety
    Routing（安全路由），而不是作为普通 CBT-I
    Recommendation（建议）处理。
-   不应为了提升测试通过率绕过安全限制。

Safety Logic（安全逻辑）应与普通 Decision Policy 清晰分离。

------------------------------------------------------------------------

## 18. Code Quality（代码质量）

优先使用：

-   small modules（小模块）
-   explicit interfaces（明确接口）
-   typed data structures（类型化数据结构）
-   structured LLM outputs（结构化大模型输出）
-   testable functions（可测试函数）
-   explicit state transitions（明确状态转换）
-   clear error handling（清晰错误处理）

避免：

-   hidden global state（隐藏全局状态）
-   duplicated workflow（重复工作流）
-   giant prompts containing business
    logic（把业务逻辑全部塞进超长提示词）
-   deeply nested if/else trees（深层嵌套条件树）
-   unnecessary dependencies（不必要依赖）
-   silent exception swallowing（静默吞掉异常）

------------------------------------------------------------------------

## 19. Scope Control（范围控制）

在没有明确要求时，不要：

-   重写整个项目。
-   重构所有旧代码。
-   更换 Web Framework（Web 框架）。
-   更换现有 RAG 技术栈。
-   新增多个 Agent。
-   增加复杂前端。
-   引入新的数据库。
-   引入 Reinforcement Learning。
-   训练新模型。
-   增加与当前 Goal 无关的功能。

优先原则：

> **Implement the smallest correct change that moves the current
> architecture forward.**\
> 实现能够正确推进当前架构的最小改动。

------------------------------------------------------------------------

## 20. Future Evolution（未来演进）

V1：

``` text
Heuristic Policy
+
LOW / MEDIUM / HIGH Sufficiency
+
Structured State
```

后续版本可以在有 Benchmark Data（基准测试数据）之后逐步升级：

``` text
V2
→ Calibration
→ measured action outcomes
→ calibrated confidence / success estimation

V3
→ Learned Policy
→ Cost-Aware Decision Optimization
```

不得为了提前实现 V2/V3 而破坏 V1 的简单性和可测试性。

------------------------------------------------------------------------

## Final Principle（最终原则）

每次修改 Adaptive Agent 前，都应检查：

> **这个修改是否让 Agent 更好地根据当前 Goal 和 State
> 判断"下一步行动是否值得"？**

如果一个修改只是：

-   增加更多步骤；
-   增加更多 Agent；
-   增加更多检索；
-   增加更多用户问题；

但没有提高 Decision Quality（决策质量）或降低不必要的
Cost（成本），则不应默认认为它是改进。
-----------------------------------------------------------------------------
## Development Learning Record

After completing each development step, using chinese to update `record.md`.

The update must APPEND a new section and must not overwrite
previous development records.

Each step should record:

1. What was implemented.
2. The 2–5 most important code locations the developer should read.
3. Why each code location matters.
4. The important execution flow.
5. Key design decisions.
6. Questions the developer should be able to answer after reading.
7. Known limitations or technical debt.

Do not fill the following sections on behalf of the developer:

- My Understanding
- Questions I Still Have

These sections should remain for the developer to complete manually.

`record.md` is a learning document, not a full changelog.
Avoid recording trivial formatting changes, boilerplate,
generated files, or unimportant implementation details.