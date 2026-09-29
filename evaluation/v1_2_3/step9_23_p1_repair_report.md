# Step 9.23 P1 State-to-Answer Integrity Repair

## 结果

只修改 State→Answer 路径：`adaptive_agent/answer_generation.py` 建立统一上下文、证据投影与最终事实一致性检查；`adaptive_agent/state_update.py` 给检索证据附同 goal/query 血缘；`adaptive_agent/state.py` 和 `runner.py` 保留回答上下文审计。新增 14 个合成测试。本阶段没有修改 Input Understanding、Sufficiency、Information Value Gate、ASK 排序、Decision Policy、RAG 排序、日记契约、Benchmark、评分或 Harness。

显式事实仅从已验证 State 进入回答，不再由原始话语作为旁路；相关检索证据可依检索血缘进入上下文，排除均留原因；日记日期存在、字段缺失/无效、资源不可用分开表示；最终回答前移除可检测的矛盾事实、无证据数字规则和越界处方。证据进入上下文不强制模型逐字引用。

## 验证与限制

专项 14/14 PASS；完整非外部模型套件 229/232 PASS，3 个历史冻结身份断言失败（见回归报告）。因此不能标记完整回归 PASS，也不能在本阶段宣布准备实施 P2。通用词面回退不等于语义相关性证明；同 goal 检索血缘也不能独立证明 RAG 内容正确。最终守卫覆盖显式可检测冲突，不保证识别所有中文隐含断言。V3 正式成绩 60.91、1 Critical、6 Harmful、19 低价值 ASK、10 次 retrieved-but-unused、9 次真实 grounding failure 均为历史冻结事实，不因本修复改变；V3 已进入开发诊断流程，不再可复用为修复后 final held-out。

本阶段未调用模型、未运行 V2/V3、未实施 P2、未创建 V4。下一步应先做授权变更链与新候选冻结身份审计，并复核 3 个历史断言；这是建议，不在本阶段执行。
