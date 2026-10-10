# Step 9.63c-r5c10ah 变更报告

**一句话**：为 AR-14（D-A）和 Freeze 创建（D-B）补齐了门禁入口；九个被取代的钉值/清单/读回测试按常设规则归档退役；H3 增加“写入前证明清单等于计划”；批准记录改成**只需在 AR-14 之前签一次**；运行手册改成每步只调用门禁入口。**没有任何真实激活**：真实仓库里没有 r11 指针、Freeze、Registry、授权、已签署的批准记录；没有执行 AR-14；真实账本仍是 3856 字节、没有增加任何字节；我没有 commit、没有 push。`READY_FOR_R11_FREEZE_REVIEW = NO`。

## 1. 新值（请逐字核对）

| 文件 | SHA-256 | 状态 |
|---|---|---|
| `scripts/build_step9_63c_r11_runner_freeze.py`（builder） | `9cfaf75a1c7ab2b2a6b0c0126c77692e02144f8483f9384fb361f3b92f832ea9` | **已变**（原 `7f72a17c…0f81`）——**唯一变化的冻结相关文件** |
| `scripts/run_step9_63_v3_formal_execution.py`（consumer） | `362eb4467fdadd29edc056ecf7b446f2cab99a2d3c407d350b4e91494c5b9528` | 未变 |
| `scripts/issue_step9_63c_r11_authorization.py`（签发器） | `f41763f5c82e04360b3d9bcf694e6d05a6fcfa42ae8d71ada29be4ab204e32ab` | 未变 |
| `scripts/v3_runner_identity.py`（resolver） | `a0f5670d3834d5f91391b41a33fbac669d6162587bc620e9bd3acf202aa3c6a5` | 未变 |

adapter、`authorization_lifecycle.py`、r7 签发器文件、r10 成员、历史 Trace、历史清单：未改（完整性报告 C1–C13 全部通过）。

## 2. 变更清单（每项一份独立 diff，回滚已验证）

| 变更 | diff |
|---|---|
| builder（+356/−3） | `step9_63c_r5c10ah_builder.diff` |
| 新测试模块与夹具 | `step9_63c_r5c10ah_tests.diff` |
| 九个方法的归档退役（活动文件删除方法 + `.retired` 归档 + `RETIRED_INDEX.json`） | `step9_63c_r5c10ah_retirement.diff` |
| r5c10ah 清单、校验器、其测试 | `step9_63c_r5c10ah_manifest.diff` |
| AR-14 不可重用判定文件（惰性文件） | `step9_63c_r5c10ah_determination_file.diff` |
| **未应用**的提案：归档重放测试固定到 V2 提交 | `step9_63c_r5c10ah_PROPOSED_ad_archival_replay_update.diff` |

回滚验证：把“之后”的文件放进临时目录，按 `manifest → determination_file → retirement → tests → builder` 的逆序 `git apply -R`，结果是 builder、`RETIRED_INDEX.json`、六个被退役的测试文件与改前备份/归档逐字节相同，所有新文件消失。

## 3. builder 里新增了什么

- **`--plan-retire` / `--verify-retire`（只读）与 `--retire-r10`（写入）**。写入前条件 RT1–RT7：已签署批准记录且所有钉住值成立；没有任何 r11 产物；**账本当前字节 = 批准记录里钉住的“退役前账本”**（3856 字节，`aaa2e989…`）；r10 授权仍是 `ISSUED_EXECUTABLE`；不可重用判定文件存在、字节等于由批准记录推出的规范字节、并引用批准记录的 `approval_id`；55 个历史钉；环境。令牌 `RETIRE-R10-<r10 授权 ID 前 12 位>-<批准记录 SHA 前 12 位>`。**内部只调用冻结的 `retire_unconsumed_authorization`，没有复制、没有修改它。** 写入后重新读取账本：旧字节逐字节不变、恰好多一行（其后只允许一条 `AUTHORIZATION_ISSUED`）、该行等于批准的模板（除 `lifecycle_event_id` 与 `timestamp_utc`）、reducer 判定已退役且不可执行；不符 → `POSTCONDITION_FAILED`，什么都不删。
- **`--plan-freeze`（只读）与 `--create-freeze`（写入）**。前置条件 FZ1–FZ7：批准记录；**AR-14 已完成（reducer 判定 r10 已退役）**；指针存在且字节正确、创建记录绑定本批准；Freeze/Registry/r11 授权都不存在；现在组装出的 Freeze 的 SHA 与长度等于批准记录里的预测值；55 个历史钉；环境。令牌 `CREATE-R11-FREEZE-<预测 Freeze SHA 前 12 位>-<批准记录 SHA 前 12 位>`。写入用 `O_EXCL`+fsync+读回；落盘 SHA 不等于预测 → `FREEZE_SHA_MISMATCH`，附恢复步骤，不删除。不使用库函数 `persist_candidate`（测试里把它换成会报错的替身）。
- **稳定的整仓聚合哈希**：批准记录里的 `repository_aggregate` 现在排除各门禁步骤会创建或追加的文件（账本、锁文件、指针及其创建记录、Freeze、Registry、r11 授权清单），这些文件各自被单独钉住。所以**批准记录只签一次、在 AR-14 之前签**，整个顺序里都有效（演练里每一步之后都重新验证了它）。
- **批准记录新增字段**：`approval_id`、`ar14`（判定文件的路径/长度/SHA、退役前账本、预期事件模板及其 SHA、AR-14 之后账本的规则）、`tokens`（四个入口的令牌格式）。
- **H3 附加要求**：`--issue` 写入前证明待写清单与重新生成的计划**逐字节一致（除 `issued_at_utc`）**，否则 `MANIFEST_DIFFERS_FROM_PLAN` 且什么都不写。这个证明放在 builder 的独占写原语 `_write_exclusive` 里——因为签发器的 SHA 不许变，而它调用的正是这个原语。

## 4. 退役（常设规则）：九个方法

按 AR-2 流程：原文件字节复制到 `tests/retired/*.retired`（SHA 记在 `RETIRED_INDEX.json`），活动文件里只删除列出的方法，取代它们的测试在 `step9_63c_r5c10ah_coverage_mapping.json` 里逐项指明，并**用变异证明取代测试能检测对应属性**（superseding 组 13/13 被杀）。

| 被退役 | 取代它的测试 |
|---|---|
| r5c10ad 清单测试 2 个、r5c10ae 清单测试 2 个 | `test_step9_63c_r5c10ah_test_boundary_manifest`（含缺失/多余模块、版本、前版本字节钉、携带决定、`added_since_previous`、可复现） |
| r5c10ae builder-pins 1 个 | `test_step9_63c_r5c10ah_superseding_tests::BuilderPinTests` |
| r5c10ae gate 正向对照 1 个 | `…::ConsumerGateTests`（正向通过、篡改历史钉 fail-closed、`execute_formal` 在 adapter 前停止、缺签发事件） |
| **额外 3 个（见 §6.1）**：r5c10ag 清单测试 2 个、r5c10ag 签发器读回测试 1 个 | 同上 / `test_step9_63c_r5c10ah_issuance_plan_proof` |

`PROPOSED_ae_test_updates.diff` 未应用（对应方法已退役，提案作废）。

## 5. 验证

| 项 | 结果 |
|---|---|
| 新测试 | 107 个，全部通过：AR-14 入口 41、Freeze 入口 26、签发计划证明 11、门禁端到端演练 11、取代测试 5、清单 13 |
| 变异验证 | 77 个变异体，63 被杀，14 个幸存者全部归类（冗余对——组合变异体被杀——或不可达），无未解释项。含 superseding 组 13/13 |
| 端到端演练（临时根，只用门禁入口） | PASS：签署的批准记录 → `--retire-r10` → `--create-pointer` → `--create-freeze` → `--issue` → consumer 门；恰好 1 个活动授权；落盘 Freeze 的 SHA 等于批准记录的预测值；没有进入正式执行。**31 个负向演练**（未签署批准记录、令牌错误/为空、账本被预先追加一行、三种非交互调用方式、Freeze 预测 SHA 不符、跳过 AR-14 直接创建指针/Freeze、跳过 Freeze 直接签发、各步骤重放）每一个都被拒绝，并且整树哈希证明没有任何写入 |
| 全量回归（guard v3，两次） | 1043 项 = 1010 通过 / 4 失败 / 29 错误 / 4 导入阻断，两次逐项一致；RC1 仍是同一个 33 项集合；生产回归 0、未知 0 |
| 整仓哈希 | 两次回归前/中/后：0 新增、0 删除、0 内容变化、0 仅 mtime 变化；guard 日志 181 条，全是放行的 `subprocess.Popen`，0 条拦截 |
| 完整性 | `step9_63c_r5c10ah_repository_integrity_report.json` C1–C13 全部通过 |

## 6. 需要你知道和决定的

1. **超出你列的六个，我多退役了三个（r5c10ag 的两个清单测试和一个读回测试）**。原因不是我的选择而是后果：新增 r5c10ah 测试模块使 r5c10ag 清单的库存过期（与 r5c10ad/ae 完全同模式）；H3 的写前证明会在 r5c10ag 那个读回测试到达读回之前就拒绝它故意损坏的数据，它原本要测的属性现在由新测试覆盖（改为在写入过程中损坏字节）。都按同一条常设规则处理、都有变异证明。如果你不同意，退回是 `retirement.diff` 的反向应用。
2. **回归里有 2 个不是我引起的新失败，且使“非身份类失败只剩 RC5、RC6”这条验收没有达成**：`test_step9_63c_r5c10ad_v2_archival_replay` 的两个测试从 Git HEAD 读取 V2 字节。检查点提交 `23994b2`（在本步开始之前创建，不是我做的）把 HEAD 移到了当前字节上，V2 字节现在在 `201ef5c`。它们在上一步通过，是因为那时 HEAD 还是旧的。我准备了未应用的提案 `PROPOSED_ad_archival_replay_update.diff`（把重放固定到 `201ef5c…`），在不改仓库的前提下执行过，两个测试通过。这属于改 r5c10ad 的测试，所以我停在这里，等你决定。
3. **令牌第一段**：按你的指令取 r10 授权 ID 的前 12 个字符，结果是常量 `auth-step9_6`；真正把令牌绑定到这份批准记录的是第二段。
4. **AR-14 之后的账本不能钉成整个文件的 SHA**：事件里的 `lifecycle_event_id`（uuid）和 `timestamp_utc` 是冻结函数在调用时生成的，我不能在不修改冻结函数的前提下固定它们。所以批准记录钉的是：退役前账本（3856 字节 + SHA）、预期追加行的模板（及模板 SHA）、以及规则（旧字节不变 + 恰好一行 + 等于模板 + 时间晚于所有已有事件）。入口在写入后逐项验证这条规则，核对清单 E 节写出了预期追加行的规范字节。
5. **H3 的证明比较的是“写入时重新生成的计划”，不是你之前跑 `--plan` 时看到的那一份**——两者本来就不同进程。但因为签发身份、Freeze、批准记录都是固定的，唯一会变的就是 `issued_at_utc`；证明保证“要写的字节”和“现在重新规划得到的字节”只差这一个字段，从而挡住预览与写入之间的任何分歧。
6. **builder 在调用冻结的退役函数时不持有 lifecycle 锁**（该函数自己取锁，锁不可重入），所以“写前账本等于钉住值”与“函数里的追加”之间有极小的竞争窗口；写后验证（旧字节不变、恰好一行）会发现任何插入，但不会撤销它（账本只追加）。
7. **我在仓库里放了一个惰性文件** `evaluation/v1_2_3/step9_63c_r11_ar14_determination.json`（AR-14 的不可重用判定，字节由批准记录的 `approval_id` 推出）。你要求“判定文件存在且引用批准记录”，它必须先于入口存在，而且批准记录要钉它的 SHA。它不是 AR-14 的执行，没有被任何东西读取，除非你运行 `--retire-r10`。
8. **“14 个未变成员”统一为 13**：本步所有新文档和批准记录都写 13（20 个成员 = 13 逐字相同 + 3 已批准变更 + 4 新增/替换）。更早步骤的历史文档里“14”是当时的另一种口径（把 r7 签发器算作未变），我没有改动那些历史记录；如果你要全部统一，需要单独批准一次扫描。
9. `--approval` 参数（D-E）、令牌 H3（D-F）：按你的决定 H3 已接受；`--approval` 本步未动。
10. 上一步的批准记录草案（SHA `91fd0f68…`）被本步的草案**覆盖**（同一个规范路径）；上一步的运行手册和核对清单被本步同名的 `r5c10ah_*` 取代，原文件保留不动。
11. 退役事件里的 `reuse_determination` 与 `lifecycle_contract_path` 是冻结函数按调用时的路径原样记录的绝对路径；批准记录里的模板存相对路径，验证时接受“相对路径，或以它结尾的绝对路径”。

## 7. 没有做的事

AR-14、指针、Freeze、Registry、授权、批准记录签署、preflight、正式执行、AR-15、commit、push：全部没有做。
