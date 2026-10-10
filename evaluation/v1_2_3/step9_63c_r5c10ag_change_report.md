# Step 9.63c-r5c10ag 变更报告

**一句话**：AR-12（r11 身份指针创建）与 AR-13（r11 授权签发器）作为**一次** builder 修订实现并全部在临时根上验证；consumer 增加 D13-4 账本交叉核对；**没有激活**——真实仓库里没有 r11 指针、Freeze、Registry、授权、批准记录或 AR-14 判定文件，真实账本没有增加任何字节，没有 commit、没有 push。`READY_FOR_R11_FREEZE_REVIEW = NO`。

## 1. 新值（请逐字核对）

| 文件 | SHA-256 | 状态 |
|---|---|---|
| `scripts/run_step9_63_v3_formal_execution.py`（consumer） | `362eb4467fdadd29edc056ecf7b446f2cab99a2d3c407d350b4e91494c5b9528` | **已变**（原 `29755839…f4879`，D13-4） |
| `scripts/build_step9_63c_r11_runner_freeze.py`（builder） | `7f72a17c584efe7ee66ee95290d28b6c55daf83ccc08ebebeb3f9319dec30f81` | **已变**（原 `eaa113da…`；与签发器 SHA 互相钉住） |
| `scripts/issue_step9_63c_r11_authorization.py`（签发器，第 7 号成员） | `f41763f5c82e04360b3d9bcf694e6d05a6fcfa42ae8d71ada29be4ab204e32ab` | **新** |
| `scripts/v3_runner_identity.py`（resolver） | `a0f5670d3834d5f91391b41a33fbac669d6162587bc620e9bd3acf202aa3c6a5` | **未变**（按你的要求） |
| `scripts/v3_execution_transaction.py`（scanner） | `f0e74a49d152053b5455951c507edb8f7849a9e4708835711e5975a82e690e91` | 未变 |
| `scripts/preflight_step9_63c_r11_mac_local.py`（producer） | `460ede115b319baf35f434915cce1c4a89e4d7ba912e02e1bc3919ef2fbcc05f` | 未变 |
| 指针规范字节（尚不存在） | `4e077781faeecee57da02f37d1d3ad8cdc9dfa895d3eb72b1b4ab1f1d3f696fe`，389 字节 | 测试里同时断言长度和 SHA |

没有改动：r10 冻结成员、adapter、`authorization_lifecycle.py`、r7 签发器文件、历史 Trace/清单、`tests/` 里的历史测试（唯一例外是按你的命令回滚 `ar7e_adtest.diff`，见 §6）。

## 2. 变更清单（每项一份独立 diff，回滚已验证）

| 变更 | diff | 内容 |
|---|---|---|
| consumer | `step9_63c_r5c10ag_consumer.diff`（+54/−2） | `verify_issuance_event`、`validate_issuance_cross_check`、`ISSUANCE_KEY`；`collect_r11_precommit_state` 末尾 `check(ISSUANCE_KEY, …)`；`prepare_formal_gates` 追加交叉核对失败项。`R11_PRECOMMIT_KEYS` 仍是 25 项 |
| builder | `step9_63c_r5c10ag_builder.diff`（+488/−5） | 成员 #7 改为 r11 签发器并钉 `ISSUER_SHA256`；`assemble_candidate(allow_existing_target)`；规范指针字节；`predict_freeze`；`verify_persisted_candidate`（I4）；批准记录的构造与校验；指针创建（门禁写入）；命令行 `--plan/--status/--verify/--verify-freeze/--print-approval-draft/--create-pointer` |
| 签发器 | `step9_63c_r5c10ag_issuer.diff`（+415，新文件） | I0–I13/IX1、`--plan/--status/--verify`（只读）、`--issue`、`--complete-record`（门禁写入） |
| 测试与夹具 | `step9_63c_r5c10ag_tests.diff`（新文件） | 4 个测试模块 + `tests/r11_activation_fixtures.py`（不被收集） |
| 清单 | `step9_63c_r5c10ag_manifest.diff`（新文件） | r5c10ag 清单、校验器、其测试 |
| 未应用的提案 | `step9_63c_r5c10ag_PROPOSED_ae_test_updates.diff` | **没有应用**，见 §6 |

回滚验证：在临时目录放入这些“之后”的文件，按 `manifest → tests → issuer → builder → consumer` 的逆序 `git apply -R`，结果是 consumer 与 builder 与本步开始前的备份逐字节相同（`cmp` 通过），所有新文件消失。

依赖关系（回滚时要一起）：builder 钉着签发器和 consumer 的 SHA，所以 builder、签发器、consumer 三个 diff 应作为一组回滚；测试和清单 diff 可以单独回滚。

## 3. AR-12 实现要点

- **默认只读**：`--plan`（默认）、`--status`、`--verify`、`--verify-freeze`、`--print-approval-draft` 不写任何东西（测试逐模式比较整树哈希）。
- **唯一的写入口** `--create-pointer`：①交互终端检测——stdin 和 stdout 都必须是 TTY，管道、只有一端是 TTY、环境变量（`CI`、`YES` 等）都不能替代（真实 pty / 管道 / 半 pty 子进程测试）；②生产根要求 macOS、`.venv`、cwd=项目根；非生产根要求 `CBTI_ALLOW_SYNTHETIC_ROOT=1`；③前置条件 PP1/PP2/PP4/PP5/PP6/PP7/PP9 全部通过（编号对应设计草案第 5 节：第 3 项“整仓聚合哈希”并入 PP2，第 8 项“取得锁”不是前置条件而是写路径里的动作，所以没有 PP3、PP8）；④人工键入令牌 `CREATE-R11-POINTER-<规范 SHA 前 12 位>`；⑤取 `lifecycle_lock` 后复核；⑥`O_CREAT|O_EXCL` 写入 + fsync + 回读；⑦再用 `O_EXCL` 写创建记录。
- **幂等与恢复**（D12-6）：规范指针和记录都在 → `ALREADY_CREATED`（零写入）；指针在、记录缺 → 只补记录（`RECORD_COMPLETED`，指针 inode/mtime 不动）；指针存在但不规范 → 拒绝，**绝不覆盖或删除**；读回不一致 → `POINTER_READBACK_MISMATCH`，不自动删除。源码里没有 `remove/unlink/rename/replace/rmtree`（仅作源码检查，不计入变异证据）。
- **状态机** `--status`：`S0_NOT_ACTIVATED` / `S1_POINTER_ONLY` / `S2_FREEZE_PERSISTED` 与五种 `ANOMALY_*`，只报告不修复。
- **批准记录**：`R11_ACTIVATION_APPROVAL`，确定性设计——预测的 Freeze SHA（`predict_freeze` 在临时目录用规范指针和固定 `created_at_utc` 组装）、整仓聚合哈希（排除批准记录与草案本身）、签发身份预先生成并钉入。演练中落盘的 Freeze SHA **等于**批准记录里的预测值。

## 4. AR-13 实现要点

- 条件 I0 批准记录已签且全部钉住值与当前字节一致；I1 指针规范且创建记录绑定本批准；I2 `resolve_current_freeze` 成功；I3 Freeze SHA = 批准记录预测值；I4 已落盘 Freeze 逐字节可重新组装；I5 变更成员与签发器等于审定的钉；I6 所有非当前 V3 授权不可执行；I7 当前修订的活动授权恰为预期集合（签发前为空）；I8 55 个历史钉成立；I9 身份全局新鲜且唯一（含对批准记录以外所有 `*.json*` 的字节扫描）；I10 清单目标不存在；I12 签发时间晚于 Freeze 和账本最后一个事件；I13 每个修订只允许一份授权（无签发事件、无 r11 Registry）；IX1 环境。
- 写入顺序：条件复核（在锁内）→ 清单 `O_EXCL` 写入并回读 → 事后条件“活动授权恰为本授权” → **之后**才追加账本事件 `AUTHORIZATION_ISSUED`。事后条件失败 → 不写事件、保留清单（`POSTCONDITION_FAILED`）。
- 清单形状与 r10 模板逐键相同（测试断言）；`evaluation_id` 等身份值沿用 r10。
- 恢复 `ISSUED_UNRECORDED`（清单已写、事件缺失）：只能走 `--complete-record`（同样要终端+令牌+重新验证全部条件）。
- 只读 `--verify`：V1 恰有一个匹配事件、V2 reducer=`ISSUED_EXECUTABLE`、V3 活动授权恰为本授权、V4 键集等于模板、V5 未消耗/无 attempt/无命名空间。

## 5. D13-4 consumer 交叉核对

consumer 预提交门要求账本里**恰好一个** `AUTHORIZATION_ISSUED` 事件，其 `authorization_id/attempt_id/evaluation_id/manifest 路径与 SHA/Freeze 修订与 SHA/未消耗/消耗次数` 与磁盘上的清单一致；另一个事件复用同一 attempt、缺失、重复、任一字段不符、清单事后被改、账本不可读，全部 fail-closed。`execute_formal` 在门失败时抛错，并且不调用 adapter（行为测试：替身 adapter 的 `run` 未被调用；正向对照：无失败时才被调用）。

## 6. 需要你决定 / 偏离设计的地方（请逐条看）

1. **签发令牌的派生方式偏离 AR-13 设计 H3**：设计里令牌由清单 SHA 派生，但清单含签发时间，`--plan` 与 `--issue` 之间永远对不上。现在令牌由 `授权 ID | Freeze SHA | 批准记录 SHA` 派生（都是批准记录固定的值）；签发器**只**从规范路径读取批准记录（没有 `--approval` 参数）。
2. **builder 的 `--approval` 参数仍保留**（指针创建记录里记着批准记录的 SHA，签发器只认规范路径的那一份，所以两者必须是同一个文件，否则 I1 拒绝）。如果你不想要这个参数，要在下一次 builder 修订里去掉。
3. **“14 个未变成员”实为 13 个**：你的指令里的 14 把第 7 号成员（r7 签发器）算在内；按 D13-1(a) 它被 r11 签发器替换，所以与 r10 逐字相同的是 13 个。批准草案里写的是 13。
4. **没有门禁入口的两个不可逆步骤**：AR-14（冻结的退役函数只是库函数）和**创建 Freeze**（`persist_candidate` 只是库函数）。它们不在本步批准范围，所以我没有加。运行手册里给出了照演练原样的手工做法，但这两步没有令牌门禁。建议下一次 builder 修订加入带令牌的入口（决定 D-A / D-B，builder SHA 会再变，批准记录要重钉）。
5. **harness 的 guard 之外的前置步骤**（按你的确认已接受）：负向目录在 guard 之外运行，因为 guard 拒绝清空环境的 Python 子进程。
6. **guard v3 = 防误操作护栏，不是安全边界**（按你的批准语）；范围声明见 `step9_63c_r5c10ag_guard_scope.md`（ctypes、不加载 sitecustomize 的进程、子进程逃逸等未保护项已列出）。新的测试会在 guard 下启动临时根里的 Python 子进程（74 条放行记录，0 条拦截）。
7. **回滚 `ar7e_adtest.diff`**（按你的命令）：`tests/test_step9_63c_r5c10ad_test_boundary_manifest.py` 恢复为 `eaa60942…`；该文件里原有的 2 个失败（清单覆盖旧库存）按你的决定记为 ACCEPTED_KNOWN；r5c10af 加进去的 3 个测试随之消失。
8. **历史 r5c10ae 测试出现 4 个耦合失败——我没有改它们，按你重申的规则停下来报告**：
   - `test_step9_63c_r5c10ae_test_boundary_manifest` 两个：新增的测试模块使 r5c10ae 清单的库存过期，被 r5c10ag 清单取代（与 r5c10ad 的做法相同）。
   - `test_step9_63c_r5c10ae_builder_pins.BuilderPinTests.test_pins_equal_reviewed_constants_and_current_bytes`：测试里写死了**旧** consumer SHA `29755839…`。
   - `test_step9_63c_r5c10ae_consumer_precommit_gate.ExecuteFormalOrderingTests.test_prepare_formal_gates_reports_real_precommit_failures`：正向对照期望“无失败”，它的夹具没有签发事件，所以新的交叉核对（正确地）报告 `authorization_issuance_event_recorded`。
   - 后两个我准备了**未应用**的最小提案 `step9_63c_r5c10ag_PROPOSED_ae_test_updates.diff`（一处 SHA 字面量；一处在该测试里替身 `verify_issuance_event`），在不改仓库的前提下执行过，两个模块全绿。要不要应用由你决定。
9. **验收口径**：“非身份类失败只能是 ACCEPTED_KNOWN”**未完全满足**——上面第 8 条里有 2 个耦合失败（builder-pins 字面量、gate 正向对照）不属于已接受清单；它们不是生产回归。

## 7. 测试中发现并修复的两个真缺陷（均在签发器里，已在 SHA 中）

- 清单目标是悬空符号链接时，`--plan` 因 `FileNotFoundError` 崩溃；现在报告 `ANOMALY_MANIFEST_NOT_A_REGULAR_FILE`。
- `--complete-record` 在 I9 被**自己的清单**挡住（冻结的新鲜度函数把它当成身份复用），恢复路径根本走不通；现在恢复模式下对“其他所有清单”的临时副本做新鲜度检查。

## 8. 验证摘要

| 项 | 结果 |
|---|---|
| 新测试 | 141 个，全部通过（指针 61、签发器 52、consumer 12、演练 5、清单 11） |
| 变异验证 | 93 个变异体：77 被杀；16 个幸存者全部归类——冗余对（组合变异体被杀）或等价变异，无未解释项。源码检查类测试不计入。详见 `step9_63c_r5c10ag_mutation_results.json` |
| 端到端演练 | PASS：AR-14 → 批准 → 指针 → Freeze → 签发 → consumer 门，恰好 1 个活动授权，门通过，未进入正式执行；三个负向演练（删签发事件 / 手写清单 / 重复签发）consumer 均拒绝。`step9_63c_r5c10ag_e2e_rehearsal_report.json` |
| 全量回归（guard v3，两次） | 945 项：908 通过 / 8 失败 / 29 错误 / 4 导入阻断；两次逐项一致；RC1 仍是 33 项、同一集合；生产回归 0、未知 0。失败 8 项分类见 `step9_63c_r5c10ag_regression_results.json` |
| 整仓哈希 | 两次回归前/中/后：0 新增、0 删除、0 内容变化、0 仅 mtime 变化 |
| 完整性 | `step9_63c_r5c10ag_repository_integrity_report.json`：C1–C12 全部通过（resolver 未变、历史钉 55、账本 3856 字节未变、无 r11 产物等） |

## 9. 没有做的事

指针、Freeze、Registry、授权、批准记录签署、AR-14、AR-15、preflight、正式执行、commit、push：全部没有做。批准记录只有**未签署草案**，且在 AR-14 之后必然过期，要重新生成。
