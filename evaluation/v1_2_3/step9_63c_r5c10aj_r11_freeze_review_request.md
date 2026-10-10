# r11 Freeze 审查申请材料（Step 9.63c-r5c10aj）

提交人：huzhuoyang。状态：激活后只读复核完成。**本材料只请求审查已创建的 r11 Freeze 及其激活证据；不请求 preflight 或正式执行的批准。**

## 1. 审查范围

1. r11 Freeze（`step9_63c_r11_runner_freeze.json`，SHA `bafcec8d2ae0bad6c3cb43e89bd49171b85374957ec6ce173071fef5248357b3`，9365 字节）：20 个成员的构成与字节、绑定的身份、与批准记录预测值相等。
2. 激活顺序的执行证据：已签署的批准记录 → AR-14（退役 r10 授权）→ 身份指针 → Freeze → r11 授权签发。
3. 激活后的状态：恰好一个活动授权（`auth-step9_63c_r11-1a399434ec0e4494b0045734846b2042`），未消费，执行目录不存在；r10 授权已不可执行。
4. 不在范围：preflight、正式执行（尚未运行）；AR-15 的内容完整性（已作为例外接受）。

Git：当前 HEAD `ef3753435c4ab095f1753122ab720eb0ce041dfa`（激活提交）；批准记录 `signed_at_commit` `dcaa98d78a9a61e998ac4b5affa61f44edc21997`（最终激活包提交）；V2 归档提交 `201ef5c2d406b0eaf2ebf5ce12db912b3caf5762`（HEAD 的祖先）。复核时工作树干净。

## 2. 复核结论（只读；原文见 `step9_63c_r5c10aj_post_activation_verification.json` 与 `step9_63c_r5c10aj_readonly_entry_outputs.txt`）

- builder `--status`/`--verify`/`--verify-retire`/`--verify-freeze`、签发器 `--status`/`--verify`：全部通过（`S2_FREEZE_PERSISTED`、`RETIRED_AS_APPROVED`、`ISSUED_RECORDED`，V1–V5 全部 true）。
- 31 项独立校验全部通过：账本前 3856 字节 = `aaa2e989…`；其后恰好 2 行（`AUTHORIZATION_RETIRED_UNCONSUMED_NON_REUSABLE` 与 `AUTHORIZATION_ISSUED`），前者等于批准记录的模板（除两个生成字段，时间晚于所有已有事件）；清单 SHA `33bd99b9…` 与签发事件互相绑定；活动授权恰好 1 个；r10 `RETIRED_UNCONSUMED_NON_REUSABLE` 且不可执行；r11 授权 `ISSUED_EXECUTABLE`、未消费；`evaluation/v4_runs` 下没有 r11 的 attempt、事务、命名空间；55 个历史钉成立；签署记录与草案仅在四个签名字段上不同；创建记录绑定指针与签署记录。
- consumer 预提交门（真实根，真实冻结 adapter，只读的 `prepare_formal_gates`，未进入 `execute_formal`）：25 项预提交检查与签发交叉核对全部为真，`precommit_failures = []`。唯一替身是 preflight 证据检查（尚未运行 preflight）。
- 未运行：任何写入入口、preflight、正式执行、commit。整仓哈希在本步前后零变化。

## 3. 证据索引（路径与 SHA-256）

| 项 | 路径 | SHA-256 |
|---|---|---|
| 签署的批准记录 | `evaluation/v1_2_3/step9_63c_r11_activation_approval.json` | `46cd40f4c780d45bd2d108c531f4da7815dfe20c5df7dd398a21cecad52e31fb` |
| 批准记录草案（签署前） | `evaluation/v1_2_3/step9_63c_r11_activation_approval.DRAFT.json` | `74b01351c635b34920f224b44081fd17bff06fc6d7199c7714b77219542b8399` |
| 身份指针 | `evaluation/v1_2_3/step9_63c_r11_current_runner_identity.json` | `4e077781faeecee57da02f37d1d3ad8cdc9dfa895d3eb72b1b4ab1f1d3f696fe` |
| 指针创建记录 | `evaluation/v1_2_3/step9_63c_r11_identity_pointer_creation_record.json` | `c7e71a36fce785a7bc555220746dd30a8ed62d5603a5e8ec33e3e84bf496788c` |
| r11 Freeze | `evaluation/v1_2_3/step9_63c_r11_runner_freeze.json` | `bafcec8d2ae0bad6c3cb43e89bd49171b85374957ec6ce173071fef5248357b3` |
| r11 授权清单 | `evaluation/v1_2_3/step9_63c_r11_v3_authorization_manifest.json` | `33bd99b9f7fba0bde0fc6a40d0c6a3b570b9f59d1e4c0158c1d4b5e8d82f5ea1` |
| AR-14 不可重用判定 | `evaluation/v1_2_3/step9_63c_r11_ar14_determination.json` | `41b524d09a258505cf036d7987b6cf2076bc0ad041a3545b5fdb563420da01d2` |
| 授权生命周期账本（3856 字节前缀 + 2 行） | `evaluation/v1_2_3/authorization_lifecycle_events.jsonl` | `aa7c21819a182c3b35aa32ab0c06995734185c9a89eb239bfd0ee44e4c392b31` |
| builder | `scripts/build_step9_63c_r11_runner_freeze.py` | `99031a9156da87164c16b71eff9e2a9961428c52bbf7bc2590741e51e55f950e` |
| consumer | `scripts/run_step9_63_v3_formal_execution.py` | `362eb4467fdadd29edc056ecf7b446f2cab99a2d3c407d350b4e91494c5b9528` |
| 签发器 | `scripts/issue_step9_63c_r11_authorization.py` | `f41763f5c82e04360b3d9bcf694e6d05a6fcfa42ae8d71ada29be4ab204e32ab` |
| resolver | `scripts/v3_runner_identity.py` | `a0f5670d3834d5f91391b41a33fbac669d6162587bc620e9bd3acf202aa3c6a5` |
| scanner | `scripts/v3_execution_transaction.py` | `f0e74a49d152053b5455951c507edb8f7849a9e4708835711e5975a82e690e91` |
| producer | `scripts/preflight_step9_63c_r11_mac_local.py` | `460ede115b319baf35f434915cce1c4a89e4d7ba912e02e1bc3919ef2fbcc05f` |
| r10 Freeze 清单 | `evaluation/v1_2_3/step9_63c_r5c5b_runner_freeze_r10.json` | `d24244235e51e7bf6c8567880c654fe3fd73b87fa1bfe1ab0f10dfdc94db2693` |
| r10 授权清单 | `evaluation/v1_2_3/step9_63c_r5c6_r10_v3_authorization_manifest.json` | `beac52d1ed3bc11efa02b1a924a8abc7b210171bf5cc1b7910011a6ef9741241` |
| r5c10ai 回归结果（激活前） | `evaluation/v1_2_3/step9_63c_r5c10ai_regression_results.json` | `cb183d96a689c68212d0dfac86bf8b17140f7db4d09b114c2f7a89beb2eb9b10` |
| r5c10ai 变异结果 | `evaluation/v1_2_3/step9_63c_r5c10ai_mutation_results.json` | `0173fa0b3df225720fe8232b9c94954ae3a3be38e43ba9b60ae98632d9893a90` |
| r5c10ai 门禁演练报告 | `evaluation/v1_2_3/step9_63c_r5c10ai_final_form_rehearsal_report.json` | `22ec4fd29264f61a6c9a987f35853e014031138041da1d49121112153967d176` |
| r5c10ai 测试清单 | `evaluation/v1_2_3/step9_63c_r5c10ai_test_boundary_manifest.json` | `07be6cd197e95290d3270b1f8b3d0052e97af238b94ad1e46093d8ee1176bf0d` |
| 核对清单（激活前） | `evaluation/v1_2_3/step9_63c_r5c10ai_activation_approval_checklist.md` | `1842d1512b5f58bf1b7fc57e84e3c547584d0fc92addc9ff3d6b87b06e34026d` |
| 运行手册 | `evaluation/v1_2_3/step9_63c_r5c10ai_activation_runbook.md` | `5f91f53a0b977b42eb592589e54b4727b9ec9d752d3c488abfac2729f1777a49` |
| 激活后复核记录 | `evaluation/v1_2_3/step9_63c_r5c10aj_post_activation_verification.json` | `1b479560fd2ec32bde6cf42b6f0e1f0564a6e1761b424e077608263abeff8d65` |
| 激活后回归结果 | `evaluation/v1_2_3/step9_63c_r5c10aj_regression_results.json` | `3e9112d6a6c9c144f87485acab10c469ee37969d5b86fc6bc5ca5ec8f61d3e78` |

## 4. 已接受的例外

| 例外 | 内容 | 依据 |
|---|---|---|
| AR-15 | 历史 Trace 原始内容完整性 `CONTENT_INTEGRITY_UNPROVEN`：只能证明当前哈希未变，无法证明原始内容 | 批准记录 `accepted_exceptions[0]`；签署即接受 |
| RC5 | `test_step9_43a…test_01a`：被 V2 runner freeze 钉住，不修改；等价覆盖（r5c10ai V2 归档重放，读取提交 201ef5c）通过 | 回归结果文件被批准记录钉住 |
| RC6 | `test_step9_51a…test_current_manifest_passes_pinned_allowlist`：被 r10/r11 development freeze 钉住，不修改；等价覆盖是 r5c10ai 清单测试 | 同上 |

## 5. 已知限制

1. **guard v3 是防误操作护栏，不是安全边界**（范围声明：`step9_63c_r5c10ag_guard_scope.md`）。本次回归中它拦截了 2 次写入尝试（见 6.3），说明需要它；但 ctypes、不加载 sitecustomize 的进程、子进程逃逸等不受保护。
2. **激活后回归不是全绿**（第 6 节）。没有一项是生产回归，但测试侧有需要决定的问题。
3. 签发令牌无法在签署前写全（由已签署文件字节派生，签发器不允许改），只能在签署后由 `--plan` 显示。
4. AR-14 之后的账本按“模板 + 原前缀不变 + 恰好多一行”验证，而不是整文件 SHA（事件里的 uuid 与时间戳由冻结函数在调用时生成）。
5. builder 命令行里仍保留 `--approval` 参数（下一次 builder 修订再去掉）。
6. preflight（网络连通）与正式执行尚未运行，它们的结果不属于本次审查。
7. 历史文档里的“14 个未变成员”是当时的口径；现行口径是 13（`record.md` 有勘误）。

## 6. 激活后的全量回归（两次逐项一致；详见 `step9_63c_r5c10aj_regression_results.json`）

激活前（r5c10ai）：1074 项 / 1043 通过 / 2 失败 / 29 错误 / 4 导入阻断。**激活后：892 项 / 857 通过 / 12 失败 / 23 错误 / 0 导入阻断。**

1. **原 33 个 RC1 项**：4 个导入阻断模块已全部能导入；25 项（21 个测试 + 4 个模块）转为通过；仍失败 8 个测试（58a 1、63a_r1 2、63a_r2 2、63c_r5 预检 3），原因见下。
2. **新增的失败，全部在测试侧**：
   - 9 个模块的 `setUpModule` 失败、共 **236 个测试没有运行**（r5c10ag–ai 的指针/签发器/consumer/演练套件；另有 ag 演练模块里 5 个测试失败）：它们的夹具复制“当前真实仓库”来造演练根，激活后真实账本已含退役与签发事件（`authorization already has a terminal retirement event`）。**提案 `step9_63c_r5c10aj_PROPOSED_fixture_update.diff`（未应用）**：夹具改为只取账本被钉住的 3856 字节前缀、排除 r11 清单；在内存中验证后 241 个测试里 239 个通过，剩下 2 个断言“真实仓库里不存在 r11 指针”，只在激活前成立，需要改写。
   - 13 个遗留测试（55a×4、58a、59a×5、63a_r1、63a_r2×2）：它们的模块原来导入失败或在身份处就失败，现在第一次真正运行；它们对合成授权 ID 调用生命周期 reducer（默认走真实路径，合成 ID 没有清单 → `INCONSISTENT_FAIL_CLOSED`），或期望旧的错误措辞。生产代码在每种情形下都 fail-closed。
   - 3 个 `test_step9_63c_r5_mac_local_preflight` 测试：打补丁的属性（`artifact_path`、`ARTIFACT_DIR`）在已不属于 r11 成员的 r5 预检模块里不存在 → 适合按 AR-2 退役。
   - 2 个 ae gate 测试：断言“真实 r10 授权仍可执行/真实 adapter 不可用”，激活后不再成立（consumer 本身未变）。
3. **一个值得警惕的发现**：`test_real_parent_rejects_prepared_before_agent_boundary` 现在能走到真正的 parent runner，并尝试创建/打开 `evaluation/v4_runs/.namespace-allocation.lock`——**guard 拦截了它（2 次拦截）**，整仓哈希没有变化。**绝不要在没有 guard 的情况下运行这个遗留测试。**

## 7. 建议

- **可以提交 r11 Freeze 审查**：Freeze、授权、账本、指针和批准记录的证据完整、互相一致，consumer 预提交门在真实根上通过，没有任何证据指向生产缺陷。
- **同时随材料明示**第 6 节的测试侧问题；建议在 preflight 之前先决定：应用夹具提案并改写那 2 个“激活前”断言；把 3 个过时 r5 测试按 AR-2 退役；对 13 个遗留测试逐个修订或退役。这些不阻止审查，但会让“回归全绿”在审查通过后才成立。
