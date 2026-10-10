# Step 9.63c-r5c10ag 剩余阻断清单

`READY_FOR_R11_FREEZE_REVIEW = NO`（就绪矩阵：21 PASS / 4 FAIL / 6 BLOCKED，见 `step9_63c_r5c10ag_r11_freeze_readiness_matrix.json`）。

本步完成：AR-12（指针创建）、AR-13（签发器）、D13-4（consumer 交叉核对）、验证已落盘 Freeze 的只读入口、端到端演练、变异验证、r5c10ag 清单、未签署的批准记录草案与运行手册。**没有激活。**

## 需要你决定

| 编号 | 事项 | 建议 |
|---|---|---|
| D-A | **AR-14 没有门禁入口**：冻结的 `retire_unconsumed_authorization` 只是库函数，没有令牌/终端门禁 | 下一次 builder 修订加带令牌的 `--retire-r10` 入口；或接受运行手册第 1 步的手工受控做法 |
| D-B | **创建 r11 Freeze 没有门禁入口**：只有库函数 `persist_candidate`（`O_EXCL`+fsync） | 与 D-A 合并进同一次 builder 修订；或接受运行手册第 4 步的手工做法 |
| D-C | Freeze 的 `created_at_utc`：批准记录钉住，签发时间必须晚于它 | 重新生成草案时 `--created-at` 取签批准记录的当天 |
| D-D | 4 个历史 r5c10ae 测试的耦合失败（我没有改） | 接受清单两个被 r5c10ag 清单取代；对另外两个应用 `step9_63c_r5c10ag_PROPOSED_ae_test_updates.diff`（已验证，未应用），或指定别的处理 |
| D-E | `--approval` 参数是否保留 | 我倾向在下一次 builder 修订里去掉，只认规范路径 |
| D-F | 签发令牌派生方式偏离设计 H3（见变更报告 §6.1） | 接受 |
| D-G | “14 个未变成员”实为 13（第 7 号成员被替换） | 确认草案里的 13 |

## 之后的步骤（本步均未执行）

| 事项 | 状态 |
|---|---|
| AR-14：退役 r10 授权（向真实账本追加一行，不可逆） | 顺序：先于批准记录签署和指针。r10 授权仍是 `ISSUED_EXECUTABLE`；它是 consumer 预提交门和指针/签发前置条件的共同阻断 |
| 重新生成并核对批准记录，然后签署 | 现有草案在 AR-14 后必然过期（整仓聚合哈希、账本） |
| 创建指针 → 创建 Freeze → 签发 | 见 `step9_63c_r11_activation_runbook.md`；各自在交互终端里由你输入令牌 |
| preflight、正式执行 | 之后；各自需要批准 |
| AR-15 历史 Trace 原始内容完整性 | 仍是 `CONTENT_INTEGRITY_UNPROVEN` |
| AR-16 commit/push | 未执行。工作树里仍有大量未提交内容；GitHub CI 看不到新的测试模块 |
| AR-8/AR-9 | 维持不修改 |

## 已接受的已知失败（ACCEPTED_KNOWN）

| 项 | 说明 |
|---|---|
| RC1 = 33 | 与上一步是**完全相同**的集合（28 个运行时错误 + 1 个失败 + 4 个导入阻断），全部以“缺少正式 r11 身份”fail-closed。r11 指针创建后这些项才会真正执行，结果目前是 `NOT_MEASURED` |
| RC5 `test_step9_43a…test_01a` | 被 V2 runner freeze 钉住，不修改；等价覆盖通过 |
| RC6 `test_step9_51a…test_current_manifest_passes_pinned_allowlist` | 被 r10/r11 development freeze 钉住，不修改；等价覆盖是 r5c10ae/ag 清单测试 |
| r5c10ad 清单测试 2 个 | 你在回滚 `ar7e_adtest.diff` 时已接受；被 r5c10ae/ag 清单取代 |

## 新的、尚未被接受的失败（见 D-D）

| 项 | 性质 |
|---|---|
| `test_step9_63c_r5c10ae_test_boundary_manifest` 2 个 | 库存过期，被 r5c10ag 清单取代（与 r5c10ad 同模式） |
| `test_step9_63c_r5c10ae_builder_pins…test_pins_equal_reviewed_constants_and_current_bytes` | 测试里写死旧 consumer SHA |
| `test_step9_63c_r5c10ae_consumer_precommit_gate…test_prepare_formal_gates_reports_real_precommit_failures` | 正向对照的夹具没有签发事件；新交叉核对正确地拒绝 |

## 新增的观察

- 变异验证发现并推动修复了两个签发器缺陷（悬空符号链接使 `--plan` 崩溃；`--complete-record` 被自己的清单挡住）以及几处“两道门互相掩盖”的测试缺口（`--complete-record` 的终端门与令牌门、approval 成员钉与整仓聚合）。这类缺口只有变异验证看得见。
- I12 在 Freeze 缺失时报告的错误是 `KeyError: 'freeze'`（结果正确但信息不友好）；不影响安全性，未修改以免再次改变 SHA。
- 一旦指针创建，4 个导入阻断模块和 29 个运行时错误项会开始真正执行，应单独评估而不是预设通过。
