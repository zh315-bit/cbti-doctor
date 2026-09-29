# Step 9.24 — Information Value Gate 设计

## 范围

只修复信息价值估计对可选信息过度乐观、进而产生低价值 ASK 的问题。生产改动仅限 `adaptive_agent/information_value.py` 与 `adaptive_agent/acquisition_gate.py`。不改 Input Understanding、Goal/Dependency/Sufficiency 语义、候选排序、Decision Policy、工具实现、回答生成、Benchmark 或评分。

## 机制

对 ASK target，先验证 goal→USER_FACTS dependency→missing field 的现存 lineage。缺少 lineage 或该字段并非当前 goal 下 decision-relevant 时，不将它升级为高价值。再比较未知与合理已知两种情形：只有可能改变下一步行动/建议方向，或改变用户明确要求的回答范围时，才视为可行动；仅改善细节的目标给 LOW，并由 acquisition gate 阻止 ASK。决策改变型信息可为 HIGH；比较范围/纳入维度型信息可为 MEDIUM，并继续受已有交互成本和 diminishing-return ordinal threshold 约束。

估值是可解释的序数启发式，不是概率、期望收益标量或经过统计校准的预测。`counterfactual_outcomes`、`impact_dimensions`、dependency ID 和 lineage 完整性会进入 acquisition trace。

RETRIEVE / READ_DIARY 仍由既有 active dependency、满足/不可用状态决定；不改变其策略。来自 Hard Preconditions 的候选不受可选 acquisition gate 拦截。

## 顺序

Goal + State + effective Requirement/Dependency lineage → estimate information value → acquisition gate annotate/filter → Decision Policy。信息获取门控只影响可选 acquisition candidates，不重写候选生成/排序或最终 Policy。

## 代码阅读路径

1. `adaptive_agent/information_value.py`：目标语义、missing target lineage、反事实影响等级、交互成本。
2. `adaptive_agent/acquisition_gate.py`：候选动作的接纳/拒绝、Hard Precondition 豁免以及 trace 可观测字段。
3. `tests/test_step9_24_information_value.py`：A–J 合成/反事实行为契约。

### 我的理解


### 仍然不理解的问题

