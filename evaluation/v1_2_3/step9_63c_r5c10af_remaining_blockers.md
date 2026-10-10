# Step 9.63c-r5c10af 剩余阻断清单

`READY_FOR_R11_FREEZE_REVIEW = NO`（就绪矩阵：14 PASS / 5 FAIL / 5 BLOCKED / 1 NOT_VERIFIED，见 `step9_63c_r5c10af_r11_freeze_readiness_matrix.json`）。

A 组（测试契约）已全部落实，不再有 A 组待办。

## 已接受的已知失败（ACCEPTED_KNOWN）

| 项 | 状态 | 等价覆盖测试（本次运行均通过） |
|---|---|---|
| RC1 = 33 | 与上一步是**完全相同**的集合（29 个运行时错误 + 4 个导入阻断模块），全部以"缺少正式 r11 身份"fail-closed | 不适用，等待正式 r11 |
| RC5 `test_step9_43a…test_01a` | 文件被 V2 runner freeze 钉住，不修改 | `test_step9_63c_r5c10ad_v2_archival_replay…test_01a_frozen_v2_identity_preflight_passes_on_archived_bytes`、`…test_head_blobs_equal_v2_pins_and_differ_from_working_tree` |
| RC6 `test_step9_51a…test_current_manifest_passes_pinned_allowlist` | 文件被 r10/r11 development freeze 钉住，不修改 | `test_step9_63c_r5c10ae_test_boundary_manifest…test_manifest_covers_current_inventory_and_passes_audit`、`…test_step9_51a_artifacts_remain_byte_identical`（上一步因清单漂移而暂时失效的等价覆盖，现已恢复） |

## 等待你决定

### 本步产生

| 编号 | 事项 | 选项 |
|---|---|---|
| G-1 | **guard v3 候选是否批准** | 批准：作为后续回归的 guard；不批准：回归继续使用 v2，但 v2 已知有 31 处可被绕过的场景；或指定修改 |
| X-1 | 对 r5c10ad 旧测试的限定改动 | 接受，或回退 `ar7e_adtest.diff` 并告诉我如何处理那两个失败 |
| X-2 | AR-11 用显式还原上下文代替 `monkeypatch.setitem` | 接受（项目没有 pytest），或指定别的做法 |
| X-3 | harness 的"guard 之外的前置步骤" | 接受，或指定别的方式运行 guard 的负向测试 |
| X-4 | consumer 门测试新增 2 个对应测试 | 接受 |

### AR-12（决定点详见设计草案）

D12-1 创建逻辑放哪里（建议放进 r11 builder）；D12-2 规范字节格式（SHA `4e077781…`）；D12-3 原子性策略（`O_EXCL`）；D12-4 是否接受"仅指针"中间状态；D12-5 批准记录由谁起草；D12-6 残缺指针的恢复策略；D12-7 回归预期表的验收口径；D12-8 顺序。

### AR-13（决定点详见设计草案）

D13-1 签发器放哪里（建议替换第 7 号成员）；D13-2 每个 Freeze 修订只允许一份授权；D13-3 是否在账本追加 `AUTHORIZATION_ISSUED`；D13-4 consumer 是否交叉核对；D13-5 清单模板白名单来源；D13-6 授权 ID 前缀；D13-7 顺序。

## 之后的步骤（本步均未执行）

| 编号 | 事项 | 状态 |
|---|---|---|
| AR-14 | 退役 r10 授权 `auth-step9_63c_r5c6-…`（账本追加不可逆事件） | 顺序已定：在 AR-12/AR-13 设计审定之后、激活之前。已核实可以在 r11 Freeze 不存在时执行。**它现在是正式执行的硬性前提**：consumer 的预提交检查会因 r10 授权仍可执行而拒绝一切执行 |
| AR-12 实现 | 指针创建（builder 修订） | 等待 D12 系列决定 |
| AR-13 实现 | r11 签发器 | 等待 D13 系列决定 |
| builder 修订 | AR-12 的指针创建与 AR-13 的"验证已落盘 Freeze"入口建议合并为**一次** builder 修订 | 等待上面的决定；builder 的 SHA 会变化，需要重新审定并写入批准记录 |
| 激活 | 指针 → Freeze（各自单独批准） | 在上述之后 |
| AR-15 | 历史 Trace 原始内容完整性仍是 `CONTENT_INTEGRITY_UNPROVEN` | 接受为已记录的缺口，或检查外部备份 |
| AR-16 | commit/push | 未执行。仍有未提交的改动：r5c10o 的 Trace 隔离、CI 加载器修复等，GitHub 上的 CI 看不到它们 |
| AR-8/AR-9 | 冻结 adapter 的导入时身份解析；reducer 丢弃错误原因 | 维持不修改（AR-8 推荐等待正式 r11） |

## 新增的观察

- 本仓库所在的 exFAT 盘不支持硬链接，`rename` 会覆盖已存在的目标。这影响任何"先写临时文件再原子发布"的方案，也意味着 guard 的硬链接绕过在本机的仓库卷上不会发生，但在别的磁盘布局上会。
- 一旦 r11 指针创建，4 个导入阻断模块和 29 个运行时错误项会开始真正执行；它们的结果目前是 `NOT_MEASURED`，不应预设为通过。
