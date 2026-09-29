# Step 9.24 — 信息价值测试记录

新增 `tests/test_step9_24_information_value.py`，覆盖：

| 场景 | 验证重点 |
|---|---|
| A | 与目标无关的缺失事实评为 NONE，不 ASK |
| B | 仅改善细节的缺失字段被拒绝，走受限 ANSWER |
| C | 同一事实在比较目标下改变回答范围，MEDIUM 可通过 |
| D | 同一事实在明确决策目标下改变行动方向，HIGH ASK 可通过 |
| E/F | 已有 approximate/range 信息不追问精确值 |
| G | 已知或语义上已询问的信息不重复获取 |
| H | 同字段在不同 goal 下价值不同，非 field→fixed-value |
| I | Trace 暴露反事实及“答案/下一行动不变”的拒绝理由 |
| J | Hard Precondition ASK 不被低序数价值、高成本或历史 ASK 数拦截 |

新增测试共 10 项。相关 focused 测试组 67/67 通过；完整非外部模型 suite 最终结果见 `step9_24_regression_report.md`。未调用真实模型、未执行 Benchmark。

### 我的理解


### 仍然不理解的问题

