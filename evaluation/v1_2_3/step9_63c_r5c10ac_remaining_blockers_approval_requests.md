# Step 9.63c-r5c10ac — 剩余阻断与审批请求（Remaining Blockers & Approval Requests）

当前结果：745 collected / 659 passed / 8 failed / 78 errors / 4 import-blocked modules（含 45 个静态未收集方法）。
根因：
- RC1 身份依赖：32 项（28 个运行时错误 + 4 个模块）
- RC3：3 项
- RC4：3 项
- RC5：1 项
- RC6：1 项
- RC7：2 项
- RC8：12 项
- RC9：36 项

已确认的生产回归为 0，Unknown 为 0。逐项明细见 `step9_63c_r5c10ac_failure_root_cause_matrix.json`。

`READY_FOR_R11_FREEZE_REVIEW = NO`（见 `step9_63c_r5c10ac_r11_freeze_readiness_matrix.json`：8 PASS / 6 FAIL / 3 BLOCKED / 1 NOT_VERIFIED）。

## A. 测试契约决定（不涉及冻结成员修改）

| 编号 | 事项 | 影响文件 | 风险 | 方案 | 验证 |
|---|---|---|---|---|---|
| AR-1 | RC8：r2 fixture 中重复键 `runner_freeze_revision`（r8/r6） | `tests/test_step9_63a_r2_retirement_eligibility.py` 第 40/45 行 | 选错值会改变测试叙述（r6 被取代 → r7） | 变体 A：保留 r8 + r3 freeze；变体 B：保留 r6 + 改为 `step9_61a_v3_runner_freeze_r6.json` | 两种已实测：13 pass / 5 RC1 / 1 RC7 |
| AR-2 | RC9：r5/r5b 测试针对 r8 时代的 r5 producer API（现为 6 行兼容 shim） | `tests/test_step9_63c_r5_mac_local_preflight.py`、`tests/test_step9_63c_r5b_preflight_lifecycle.py` | 退役会减少 36 个历史测试 | 退役，或改写为针对 current/r11 producer 的等价属性测试 | 等价属性覆盖清单逐项核对 |
| AR-3 | RC7：期望 reducer 之前的错误消息 | `tests/test_step9_63a_r1_production_integration.py` 两个方法 | 更新期望消息属于“修改预期结果” | 改为断言 reducer 的 `derived_state`，行为仍是 fail-closed | 已提交或已退役的授权仍被拒绝 |
| AR-4 | RC3：r9 bootstrap 测试对应 r11-only resolver | `tests/test_step9_63c_r5c4_bootstrap_repair.py` test_09/10/18 | 改写会改变断言的版本与成员数 | 退役（等价属性已由 r5c10j 覆盖），或按 r11 契约重写 | r11 临时根 fixture |
| AR-5 | RC4：断言 live r10 仍可执行 | `test_step9_63c_r5c7d_import_context`、`test_step9_63c_r5c7e_preparation` | r11 设计下永远无法通过 | 退役，或转为归档 hash 检查 | 无测试断言 live r10 |
| AR-6 | RC5：V2 父 runner 归档 SHA | `test_step9_43a_treatment_identity` | CI 已将其排除 | 维持排除，或用 Git HEAD blob（`920486b1…`）在临时根重放 | 临时根重放通过，仓库不变 |
| AR-7 | RC6：Step 9.51a 固定测试清单缺少 25 个模块 | 新建版本化清单 + `scripts/validate_step9_51a_test_boundary.py` 路径 | 历史清单不得改写 | 新建 Step 9.63c 清单，逐一标注风险 | 清单覆盖全部 66 个模块 |

## B. 需要冻结成员、身份或授权变更的决定

| 编号 | 事项 | 影响 | 风险 | 替代方案 |
|---|---|---|---|---|
| AR-8 | 冻结 adapter 在导入时解析身份（`run_step9_53_v3_identity_adapter.py:25`） | r10/r11 冻结成员 | 修改即改变冻结身份 | 不修改，等待正式 r11（推荐） |
| AR-9 | reducer 在抛出的异常中丢弃 `result['error']`，诊断性差 | `scripts/authorization_lifecycle.py:108`（冻结成员） | 修改冻结成员 | 不修改，记录为已知限制 |
| AR-10 | builder 钉住 resolver（当前 `a0f5670d…`）与 consumer（当前 `cd0d0706…`）的已审 SHA | `scripts/build_step9_63c_r11_runner_freeze.py`（r11 成员） | 必须在冻结前审定 | 审定后写入常量，或在 freeze 审查记录中逐字核对 |
| AR-11 | builder 依赖 r5c4 builder 的 `verify_frozen_inputs` | 同上 | 依赖不在 r11 冻结闭包内 | 内联进 r11 builder，或把 r5c4 builder 纳入成员（需改动 20 成员计数） |
| AR-12 | 经审核的正式 r11 指针创建流程 | 新流程 + 指针文件 | 身份创建 | 提交一份脚本或流程草案供审 |
| AR-13 | 正式 r11 Authorization Issuer | 新增签发器 | 授权机制 | 单独设计与审查 |
| AR-14 | 旧 r10 授权退役：`auth-step9_63c_r5c6-aff5c4b96bb74278a14d3fd08bf8a84e` 当前 `ISSUED_EXECUTABLE` | 授权生命周期账本追加事件 | 不可逆 | 使用现有 retirement 函数，单独批准后执行 |
| AR-15 | 历史 Trace 原始内容完整性 `CONTENT_INTEGRITY_UNPROVEN` | 无文件修改 | 不能证明 | 接受为已记录的缺口，或检查外部备份 |
| AR-16 | 提交本地修复（r5c10o、C1、R1、R2 等），让 GitHub CI 受益 | git commit/push | 外部可见 | 由用户自行提交，或明确授权 |

## 建议顺序

1. AR-1、AR-3、AR-2（测试侧决定，可最快把非身份类失败降为 0）。
2. AR-10、AR-11、AR-12、AR-13（r11 冻结前置条件）。
3. AR-14（退役 r10 授权）。
4. 提交 r11 Freeze 审查申请。
