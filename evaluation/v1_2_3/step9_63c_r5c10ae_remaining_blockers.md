# Step 9.63c-r5c10ae — 剩余阻断清单

`READY_FOR_R11_FREEZE_REVIEW = NO`（13 PASS / 4 FAIL / 4 BLOCKED / 1 NOT_VERIFIED，见 `step9_63c_r5c10ae_r11_freeze_readiness_matrix.json`）。

## 已接受的已知失败（ACCEPTED_KNOWN）

| 项 | 状态 | 等价覆盖测试 |
|---|---|---|
| RC1 = 33 | ACCEPTED_KNOWN；与上一步完全相同的 33 项，全部以身份缺失 fail-closed | 不适用（需要正式 r11） |
| RC5 `test_step9_43a…test_01a` | ACCEPTED_KNOWN；文件被 V2 runner freeze 钉住，不修改 | `test_step9_63c_r5c10ad_v2_archival_replay.V2ArchivalReplayTests.test_01a_frozen_v2_identity_preflight_passes_on_archived_bytes` 和 `test_head_blobs_equal_v2_pins_and_differ_from_working_tree` |
| RC6 `test_step9_51a…test_current_manifest_passes_pinned_allowlist` | ACCEPTED_KNOWN；文件被 r10/r11 development freeze 钉住，不修改 | `test_step9_63c_r5c10ad_test_boundary_manifest.Step963cTestBoundaryManifestTests.test_current_manifest_covers_inventory_and_passes_audit` 和 `test_step9_51a_artifacts_remain_byte_identical`。**注意：前者目前因 E-1（清单漂移）失败，所以 RC6 的等价覆盖要等 E-1 处理后才恢复；后者通过。** |

## 需要你决定（本步按规则停下，未执行）

| 编号 | 事项 | 选项 |
|---|---|---|
| E-1 | AR-7 清单漂移：本步新增 2 个测试模块后，r5c10ad 清单测试有 2 项失败（正确检测到漂移） | (a) 原地重新生成 r5c10ad 清单；(b) 新建 r5c10ae 版本化清单，并让 validator 选择最新版本（需修改 r5c10ad validator）；(c) 改为“每次新增测试都必须同时更新清单”的流程约定 |
| E-2 | 2 项 RC9（`test_multiple_active_authorizations`、`test_historical_pin_mismatch`）现在已有 consumer 侧覆盖 | 按 AR-2 流程归档退役（逐字节归档 + 映射），或保留 |
| E-3 | AR-11 差分测试使用了 `sys.modules` 作用域内的 adapter 替身 | 接受；或要求改成参数注入（这需要修改内联函数的签名，与“逐字复制”冲突） |
| E-4 | guard v2 与 v1 的差异（见变更报告） | 审查后接受或要求修改 |

## B 组（未执行）

| 编号 | 事项 |
|---|---|
| AR-12 | 经审核的正式 r11 指针创建流程（R01、R02、R05） |
| AR-13 | 正式 r11 Authorization Issuer（R11、R12） |
| AR-14 | 退役 r10 授权 `auth-step9_63c_r5c6-…`（R13）。**现在已被 consumer 检查强制要求：不退役，正式执行一律 fail-closed（R22）** |
| AR-15 | 历史 Trace 原始内容完整性为 `CONTENT_INTEGRITY_UNPROVEN`（R15） |
| AR-16 | commit/push |
| AR-8/AR-9 | 维持不修改（冻结 adapter 在导入时解析身份；reducer 消息丢弃错误原因） |
| 观察 | r11 producer（REPLACED 成员）未在 builder 中钉住 SHA。consumer 在运行时会把 producer 的 SHA 与 freeze 记录比对，freeze 建立时也会记录它；如需在 builder 中钉住，需单独批准 |
