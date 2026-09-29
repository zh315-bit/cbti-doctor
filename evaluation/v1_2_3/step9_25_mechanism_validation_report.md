# Step 9.25 — Post-Repair Mechanism Validation Report

## 结果概览

当前 Step 9.24 冻结核对通过：26/26 文件哈希匹配，aggregate 匹配。12 个受控场景全部符合预期（12/12）；案例按统一本地 Agent 机制路径执行一次决策，不含模型、Flask、Benchmark 内容或评分。相关 Information Value / Policy / Dependency / Sufficiency / freeze focused regression 为 76/76 PASS。

| 指标 | 观测 |
|---|---:|
| 可选低价值 ASK 候选抑制 | 3/3 = 100% |
| 被接受的低价值 ASK / case | 0 / 12 = 0.000 |
| 必要 Hard-Precondition ASK 保留 | 2/2 = 100% |
| decision-relevant ASK 保留（含 HIGH/MEDIUM 和 hard ASK） | 5/5 = 100% |
| Hard-Precondition acquisition 保留 | 4/4 = 100% |
| Required RETRIEVE 保留 | 1/1 = 100% |
| Required READ_DIARY 保留 | 1/1 = 100% |
| 选择的 RETRIEVE / READ_DIARY 动作 | 2 / 1 |
| 选择的工具动作 / case | 3/12 = 0.250（动作选择，不是工具调用）|
| Under-acquisition failures | 0 |
| Hard-Precondition violations | 0 |
| ASK / synthetic case | 5/12 = 0.417 |

低价值 ASK 抑制率的分母仅含实际进入 gate 的 optional ASK 候选：A-01、A-02、D-02 的次要 nap ASK。A-03 的 caffeine 本身不产生 ASK 候选，A-04 信息已知不产生重复候选，因此不计入 gate 抑制率分母。工具仅比较被选出的行动，没有真实调用；tool calls、turns、loop steps、latency、tokens 均 NOT_MEASURED。

## Counterfactual Pair

CF-CAFFEINE 两例保持任务类型、requirements、facts 与 target 一致，仅改变 goal：概括既有安排时 caffeine ASK 为 LOW 并被拒绝，咨询 caffeine 是否改变调整方向时升为 HIGH 并被接纳。观测到 ANSWER 与 ASK 的路径分化，支持价值依赖 goal/context，而非字段固定映射。

## 分组轨迹

- A（A-01…A-04）：低价值 optional、无关知识字段、已知事实均没有造成冗余 ASK；知识 goal 所需 RETRIEVE 仍被保留。
- B（B-01…B-02）：决策方向改变型 HIGH ASK 与比较范围改变型 MEDIUM ASK 均保留。
- C（C-01…C-04）：有效性关键缺失触发 ASK；错误 task signal 下知识目标触发 RETRIEVE；授权可用日记触发 READ_DIARY；unavailable 且已有读取历史时走 ANSWER 限制路径，不重读。
- D（D-01…D-02）：多个事实缺失时优先询问唯一 validity-critical wake-time；混合已知/次要/决策相关信息时保留咖啡因询问，不重复问已知 screen，也不追加低价值 nap 问题。

逐例候选、依赖、precondition、拒绝理由和 stop reason 见 `step9_25_mechanism_results.json`；配对轨迹见 `step9_25_counterfactual_pairs.json`。

## Pre-P2 对照与限制

Pre-P2 候选代码快照不在可执行工作区中；历史 freeze 只有 hash，不能据此安全重建旧执行语义。因此 mechanism ablation 为 `NOT_MEASURED`，无法证明当前 100% gate 抑制率高于 9.23 前机制。该结果只证明当前场景下修复机制按设计工作，不是 benchmark 性能或泛化结论。turns、完整 Agent Loop steps、tool latency、LLM latency 和 token usage 均 `NOT_MEASURED`；这是一次单状态决策验证，不包含 HTTP 会话或模型调用。

## 安全边界与停止

没有发现测试场景中的 first-divergence failure。未修改 Agent；V3 历史 Overall 60.91 未重新评分或改写。V2 未运行，V3 未访问/重跑，V4 未创建/运行。本阶段的结果不能单独证明临床安全或统计上有效。

**判定：**机制级 post-repair 行为 PASS；相对修复前的机制改进仍未测量。可进入 V4 evaluation protocol design 的规划讨论，但不得把本报告当作 V4 设计/运行授权。

### 我的理解


### 仍然不理解的问题
