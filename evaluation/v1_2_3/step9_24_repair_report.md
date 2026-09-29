# Step 9.24 — Information Value Repair Report

## 结果

实施目标条件化、可追溯的信息价值估计，以及 Candidate Generation 后、Decision Policy 前的可选 acquisition gate。LOW/无反事实影响的次要 ASK 不再仅因字段缺失而被放行；HIGH 的真实决策改变信息和 MEDIUM 的回答范围改变信息仍可依现有序数成本/边际收益规则进入决策。Hard Precondition 候选明确绕过可选门控。

此处的 value/cost 是可解释序数启发式，不是经统计校准的概率/期望收益。本阶段没有运行 Benchmark，不能声称分数或获取率改善。

## 范围与身份

- 生产行为改动仅在 `adaptive_agent/information_value.py`、`adaptive_agent/acquisition_gate.py`。
- 没有改 Input Understanding、Requirements/Dependency/Sufficiency、Candidate Ranking、Decision Policy、Tools、Answer Generation、RAG、Benchmark 或 Scoring。
- 测试辅助同步流程用于匹配真实 runner；历史 freeze 测试现在区分旧身份完整性与当前身份。新 Step 9.24 freeze 从历史授权链派生，26/26 文件哈希、aggregate、继承的 Benchmark/Scoring/Harness 哈希均匹配。Step 9.11/9.18/9.23a 文件未覆盖。
- 无 case-specific 分支、无真实模型调用、无 Benchmark V2 重跑或 V3 访问。

## 测试

Step 9.24 A–J：10/10 PASS；合并 focused mechanism group：67/67 PASS；完整离线 non-Benchmark regression：244 passed / 0 failed / 0 skipped。`tests.test_model_configuration` 因 Transformers import-time package metadata scan 阻塞而保持 `NOT_VERIFIED`，未纳入 244 项统计。详见 `step9_24_regression_report.md`。

V3 已用于先前失败分析，不可作为本次候选的新 held-out 证据；本步未产生性能或泛化结论。

### 我的理解


### 仍然不理解的问题
