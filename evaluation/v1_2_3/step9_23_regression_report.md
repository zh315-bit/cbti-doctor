# Step 9.23 Regression Report

- 新增合成专项：14/14 PASS（离线 mock）。
- 完整非外部模型测试（排除 `tests.test_model_configuration`）：232 total，229 passed、3 failed、0 skipped。未运行 Benchmark；未调用真实模型。
- 3 个失败：`test_step9_13a_authorization_infrastructure.AuthorizationInfrastructureTests.test_historical_and_step9_17_freezes_remain_intact_current_matches_step9_18_candidate`；`test_step9_20a_v3_runner.V3RunnerPreparationTests.test_locked_inputs_and_new_runner_match`；同模块 `test_unissued_template_cannot_start_an_attempt`。当前回答层文件在历史 Step 9.18/V3 冻结之后获授权修改，因此“当前哈希仍等于旧候选/V3”断言失效，V3 runner 如设计 fail closed；后一个测试预期授权错误却先遇到冻结不匹配。三者是历史身份迁移断言，不是观察到的回答行为回归；**不能记作测试通过**。
- 未改写历史 manifest、评分、Runner 或冻结测试以制造 PASS。进入下一阶段前应单独建立 Step 9.23 后候选身份并审计授权变更链，保持原冻结身份不可变。
