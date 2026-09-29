# Step 9.25 — 修复后机制验证协议

## 范围与冻结

验证对象固定为 `post-step9_24-candidate-20260924-01`。验证器重建 Step 9.18 + 9.23a + 9.24 的 26 项 Agent inventory，并逐文件核对当前哈希及 aggregate；任何不匹配即停止。案例为 synthetic mechanism scenarios，不属于任何 Benchmark。执行只调用本地的 Requirements、Sufficiency、DependencyResolver、Candidate Generation、Information Value Gate、Preconditions 与 Heuristic Policy；不经过 Flask，不请求模型，不访问 Benchmark 数据。

## 预注册判定

- A：仅细节改进的可选 ASK 应被 gate 拒绝；状态已知或无关字段不得再 ASK。
- B：反事实值可能改变决策方向/回答范围时，相应 ASK 应保留。
- C：有效 Hard Precondition 必须保留；证据依赖应 RETRIEVE；日记授权、可用且未读时 READ_DIARY；不可用/已尝试资源不得伪装或重试。
- D：混合状态优先 hard precondition；已知信息不重复问；只保留当前目标上有决策影响的可选获取。
- 成功判据分别看低价值 ASK 抑制、必要 ASK/工具获取保留、under-acquisition 和 hard-precondition violation，不以 ASK 越少越好作为判据。
- 若没有可执行的 pre-P2 候选源码，只能报告 `NOT_MEASURED`，不得用 hash 或 V3 历史结果臆造消融对照。
- 工具动作在本受控 harness 中只被选择、不实际执行；工具调用、turn、完整 loop step、时延和 token usage 不从动作数推算。

可复现命令：`.venv/bin/python scripts/run_step9_25_mechanism_validation.py`

### 我的理解


### 仍然不理解的问题
