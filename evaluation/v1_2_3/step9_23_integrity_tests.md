# Step 9.23 Synthetic Integrity Tests

`tests/test_step9_23_state_answer_integrity.py` 共 14 个离线合成测试，覆盖 A–J：显式事实及来源进入 Context；相关检索证据进入 Context；无关证据带理由排除；有记录但字段缺失、资源不可用、字段无效均不得说成记录不存在；State 不含的用户事实不得重引入；有/无证据的量化医学规则分别保留/拒绝；answer_scope 继续限制处方。另测原始用户话语不能作为第二事实通道、全部日记记录被错误否认、排除审计不会把被排除文本发给模型。

测试只使用人工 State、合成日记工具结果与 mock 回答模型；未读取 V3 case、未调用 DeepSeek、未重跑 V2/V3。现有 `test_answer_generation_grounding.py`、`test_v1_1_answer_tool_grounding.py`、`test_step9_17_tool_projection.py` 仍覆盖量化、确定性派生与非法日记投影。
