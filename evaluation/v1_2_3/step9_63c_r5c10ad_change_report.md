# Step 9.63c-r5c10ad — 测试契约决定 AR-1 ~ AR-7 落实报告

状态：`PASS_A_GROUP_APPLIED_WITH_4_RESIDUAL_DECISIONS_R11_FREEZE_NOT_READY`

基线（r5c10ac）：745 collected / 659 passed / 8 failed / 78 errors / 4 import-blocked。
结果（两次运行逐项一致）：**742 collected / 709 passed / 2 failed / 31 errors / 4 import-blocked**。
详见 `step9_63c_r5c10ad_regression_results.json`。

## 逐项结果

| AR | 改了什么 | 为什么 | 覆盖变化 | 结果 |
|---|---|---|---|---|
| AR-1（RC8） | `tests/test_step9_63a_r2_retirement_eligibility.py`：删除重复键中的 `"runner_freeze_revision": "r6"`，并在 docstring 中写明选择理由 | 采用变体 A：fixture 绑定的 freeze 路径、SHA 和 `runner_sha256` 都读自 r8 freeze，保留 r8 才能自洽 | 不变：断言未改 | 12 项 RC8 中 10 项通过；1 项转为 RC1（见下）；1 项转为 RC7，由 AR-3 处理 |
| AR-3（RC7） | r1 两个方法改为断言 `INCONSISTENT_FAIL_CLOSED`，并附加两类断言：显式 manifest 下“已提交”被拒绝，“已退役”= `RETIRED_UNCONSUMED_NON_REUSABLE`；每项都带“签发未使用 = ISSUED_EXECUTABLE”对照组 | 冻结 reducer 只给出派生状态，不再传出 transaction 层的消息 | 增强：新增对照组与派生状态断言 | 通过。**同一处理也用于 AR-1 后显现的第三个 RC7 方法**（r2 `test_retired_auth_cannot_enter_new_transaction`），已单独标注，可通过 `ar3.diff` 否决 |
| AR-2（RC9） | 36 项逐项映射（`step9_63c_r5c10ad_r5_coverage_mapping.json`）：15 项已覆盖 → 归档退役；19 项改写到新模块 `tests/test_step9_63c_r5c10ad_r5_producer_equivalence.py`；2 项 UNCOVERED 原地保留 | r5 producer 已是 6 行兼容 shim，旧 API 不再存在 | 已覆盖项不减少；改写项转为针对 r11 producer、resolver 和 consumer，范围更广，例如 DNS 由 1 个门控扩展到 5 个 | 新模块 22/22 通过（19 项改写 + 3 个正向对照） |
| AR-4（RC3） | r5c4 中 test_09/10/18 归档退役，在 `tests/test_step9_63c_r5c10ad_r11_resolver_contract.py` 中按 r11 契约、用临时根 fixture 重写 | 核实 r5c10j 的覆盖：test_09 仅隐式覆盖；test_10、test_18 未覆盖 | 不变或增强 | 3/3 通过；r5c4 剩余 19/19 通过 |
| AR-5（RC4） | r5c7d 两项、r5c7e 一项：不再断言 live r10 可执行，改为断言 r10 归档 hash 等于记录值（`d24244…`、`beac52d1…`、`0f908fb5…`），且 live 快照只能以两种 fail-closed 消息之一失败，快照前后字节不变 | live r10 在 r11-only resolver 下按设计不可执行 | 导入上下文属性保留，归档完整性为新增 | 4/4 通过 |
| AR-6（RC5） | 新模块 `tests/test_step9_63c_r5c10ad_v2_archival_replay.py`：用纯 Python zlib 读 Git HEAD blob，在临时根的子进程中重放 V2 身份校验 | 父 runner 及 3 个 agent 文件已演进；它们在 Git HEAD 中的 blob 字节等于 V2 pin | 新增 | 2/2 通过，工作树不变。**原 `test_01a` 未修改**（见剩余决定 D-2） |
| AR-7（RC6） | 新增 `scripts/validate_step9_63c_test_boundary.py`、`evaluation/v1_2_3/step9_63c_r5c10ad_test_boundary_manifest.json`、`tests/test_step9_63c_r5c10ad_test_boundary_manifest.py`；旧 9.51a 清单、validator 和测试一字未动 | 新清单覆盖当前全部 69 个模块：41 个旧模块逐字沿用 + 28 个新模块机械推导风险等级 | 新增 | 7/7 通过；允许列表仍为 31 个，未扩大。**旧 RC6 测试仍失败**（见 D-3） |

## 发现的边界冲突（均按“不修改”处理）

1. `tests/test_step9_51a_validation_boundary.py` 和 `scripts/validate_step9_51a_test_boundary.py` 的 SHA 记录在 `step9_51_v3_development_freeze_r1.json` 中，而后者是 **r10/r11 冻结成员**。修改它们会让冻结证据与工作树不再自洽。因此 AR-7 只用新文件实现。
2. `tests/test_step9_43a_treatment_identity.py` 被 V2 runner freeze 钉住（`9936772a…`）。AR-6 改为在新模块中实现。
3. RC1 计数：原 32 项全部保留并 fail-closed。AR-1 揭示了 1 项原本被 fixture 缺陷掩盖的身份依赖测试，RC1 总数因此变为 33。这在字面上不同于“数量不得变化”，已单独上报。

## 新发现（影响 r11 就绪性，详见就绪矩阵 R19–R21）

- **55 个历史 pin 在 r11 执行路径上没有执行点**：只有 r7 签发器和 r10 时代的 62b preflight 有这项检查。
- **“恰好 1 个活跃授权”只在 producer 中执行**：不伪造身份就无法测试。
- **formal consumer 的 `validate_precommit()` 没有接入 `execute_formal()`**：`main()` 输出中的 `precommit_failures` 是硬编码的空列表。

## 测试有效性证据

- 变异测试（仅在内存中进行，不改文件）：r11 连通性检查、resolver 的 aggregate/member/pointer 绑定、指针 revision、consumer freshness、`write_artifact` 排他性、reducer 退役识别、V2 归档字节，共 **9 个变异全部被检测到（KILLED）**。
- 映射表中引用的所有覆盖测试，都已用程序核对在本次运行中通过。
- 没有使用 skip、xfail 或异常吞噬。

## Guard v2

上一版 guard 会把“删除临时目录中指向仓库的符号链接”误判为删除仓库文件。v2 对目录项级操作只解析父目录；经过符号链接的写入仍解析到目标并阻断。自测 21/21 通过。新版本放在 `step9_63c_r5c10ad_test_harness/`，r5c10ab 版本原样保留。

## 回滚

- 每个 AR 有独立的 diff：`step9_63c_r5c10ad_ar1.diff` … `ar7.diff`。
- 推荐命令：按 ar7 → ar1 的逆序执行 `git apply -R <diff>`。已在 scratch 副本上验证，17/17 个路径逐字节恢复到本步基线。
- macOS 自带的 BSD `patch -R --dry-run` 对 ar1、ar3–ar7 验证干净；ar2 需要重建被移走的 r5b 文件，BSD patch 2.0 不支持在 `-R` 模式下重建文件。
- 依赖关系：ar4 修改了 ar2 创建的 `tests/retired/RETIRED_INDEX.json`；ar7 的清单编码了最终测试清单，所以应先回滚 ar7。
