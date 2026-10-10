# Step 9.63c-r5c10ad — 剩余阻断清单

A 组（AR-1 ~ AR-7）已执行完毕。剩余项分为两类：B 组原有审批项，以及执行 A 组过程中产生、需要你决定的 4 项残余。
`READY_FOR_R11_FREEZE_REVIEW = NO`（见 `step9_63c_r5c10ad_r11_freeze_readiness_matrix.json`：8 PASS / 8 FAIL / 3 BLOCKED / 2 NOT_VERIFIED）。

## A 组执行中产生的待决事项

| 编号 | 事项 | 当前状态 | 可选处理 |
|---|---|---|---|
| D-1 | RC1 由 32 增为 33：AR-1 揭示了 `test_step9_63a_r2_retirement_eligibility…test_active_authorization_count_becomes_zero` | 原 32 项全部保留，并以身份缺失 fail-closed | 接受 33 并记录；或回滚 `ar1.diff`，恢复 12 项 RC8 失败 |
| D-2 | RC5 `test_step9_43a…test_01a` 仍失败；原文件被 V2 runner freeze 钉住 | 等价属性已由 AR-6 重放模块覆盖并通过 | 维持现状（CI 已排除该模块）；或批准修改这个被 V2 钉住的文件，使其改用重放方式 |
| D-3 | RC6 旧 `test_current_manifest_passes_pinned_allowlist` 仍失败；文件被 r10/r11 冻结成员 development freeze 钉住 | 等价属性已由 AR-7 新清单测试覆盖并通过 | 维持现状并在 harness 中标记为已知历史契约失败；或批准未来 freeze 修订时重新钉住 |
| D-4 | 2 项 UNCOVERED（r5 `test_multiple_active_authorizations`、`test_historical_pin_mismatch`）原地保留 | 无 r11 执行点或无法测试（R19、R20） | 先决定 r11 执行路径是否要执行这两项检查（涉及 B 组 AR-17） |

## B 组（来自 r5c10ac，未执行）

| 编号 | 事项 |
|---|---|
| AR-8 | 冻结 adapter 在导入时解析身份：不修改，等待正式 r11（推荐） |
| AR-9 | reducer 在抛出的异常中丢弃 `result['error']`（冻结成员）：记录为已知限制 |
| AR-10 | builder 钉住 resolver（`a0f5670d…`）和 consumer（`cd0d0706…`）的已审 SHA |
| AR-11 | builder 依赖 r5c4 builder 的 `verify_frozen_inputs`，该依赖不在 r11 冻结闭包内 |
| AR-12 | 经审核的正式 r11 指针创建流程 |
| AR-13 | 正式 r11 Authorization Issuer |
| AR-14 | 退役 r10 授权 `auth-step9_63c_r5c6-…`：当前 `ISSUED_EXECUTABLE`，退役不可逆 |
| AR-15 | 历史 Trace 原始内容完整性仍为 `CONTENT_INTEGRITY_UNPROVEN` |
| AR-16 | 提交本地修复，让 GitHub CI 受益（commit/push） |
| AR-17（新） | r11 执行路径缺口：55 个历史 pin 无执行点；`validate_precommit()` 未接入 `execute_formal()`。修复会改动 r11 成员 formal consumer，需单独批准 |
