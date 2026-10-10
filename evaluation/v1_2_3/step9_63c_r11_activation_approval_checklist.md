# r11 激活批准记录逐项核对清单（供你逐字核对）

对应文件：`evaluation/v1_2_3/step9_63c_r11_activation_approval.DRAFT.json`（**未签署**，`status` = `DRAFT_NOT_SIGNED`，`approver` / `signed_at_utc` 为 null）。

草案文件本身的 SHA-256 **不写在本清单里**：草案钉着整仓聚合哈希，聚合哈希覆盖本清单文件，把草案的 SHA 写进来会形成循环。草案的 SHA 在我交给你的最终说明里给出，你也可以自己 `shasum -a 256` 它。

核对方法：在终端里对每个文件运行 `shasum -a 256 <路径>`，把结果与下表“草案中的值”逐字比较；表中“来源/含义”说明这个值从哪里来。**全部一致才签。** 签署只改 `status`、`approver`、`signed_at_utc` 三个字段。

> 草案是在 AR-14 之前生成的：AR-14 会向账本追加一行并新增判定文件，所以整仓哈希和账本相关值**一定会失配**。AR-14 之后要用 `--print-approval-draft` 重新生成（运行手册第 2 步），并用本清单的同一方法重新核对。

## A. 指针

| 项 | 草案中的值 | 说明 |
|---|---|---|
| 指针路径 | `evaluation/v1_2_3/step9_63c_r11_current_runner_identity.json` | 创建后才存在 |
| 规范字节 SHA-256 | `4e077781faeecee57da02f37d1d3ad8cdc9dfa895d3eb72b1b4ab1f1d3f696fe` | 你批准的值 `4e077781…f696fe` |
| 规范字节长度 | 389 | 你批准的值 389 |

## B. 命名文件（路径 → SHA-256）

| 角色 | 路径 | 草案中的 SHA-256 |
|---|---|---|
| builder | `scripts/build_step9_63c_r11_runner_freeze.py` | `7f72a17c584efe7ee66ee95290d28b6c55daf83ccc08ebebeb3f9319dec30f81` |
| consumer | `scripts/run_step9_63_v3_formal_execution.py` | `362eb4467fdadd29edc056ecf7b446f2cab99a2d3c407d350b4e91494c5b9528` |
| issuer | `scripts/issue_step9_63c_r11_authorization.py` | `f41763f5c82e04360b3d9bcf694e6d05a6fcfa42ae8d71ada29be4ab204e32ab` |
| producer | `scripts/preflight_step9_63c_r11_mac_local.py` | `460ede115b319baf35f434915cce1c4a89e4d7ba912e02e1bc3919ef2fbcc05f` |
| resolver | `scripts/v3_runner_identity.py` | `a0f5670d3834d5f91391b41a33fbac669d6162587bc620e9bd3acf202aa3c6a5` |
| scanner | `scripts/v3_execution_transaction.py` | `f0e74a49d152053b5455951c507edb8f7849a9e4708835711e5975a82e690e91` |

本步的预期：resolver 必须是 `a0f5670d…c6a5`（未变）；scanner 必须是 `f0e74a49…0e91`（未变）；consumer、builder、issuer 是本步产生的新值（`362eb446…`、`7f72a17c…`、`f41763f5…`）；producer 未变。

## C. r11 的 20 个成员（逐个 SHA-256）

| # | 路径 | 草案中的 SHA-256 | 与 r10 相比 |
|---|---|---|---|
| 1 | `evaluation/v1_2_3/step9_51_v3_development_freeze_r1.json` | `106e18707aa66806c3953c8d5f38484f534d78e4fd230cbd6c491304aaf8cd27` | 与 r10 逐字相同 |
| 2 | `evaluation/v1_2_3/step9_52_v3_pre_evaluation_validation.json` | `7f2a5e43f4131feec1fed51121e0a398a9c9ca0ab1679073be8a91c19c4940d3` | 与 r10 逐字相同 |
| 3 | `evaluation/v1_2_3/step9_58a_r1_v3_identity_contract.json` | `16b6cd71cd75ea231ed3a10d3f43546e31cded9d1be120ce5d16c000391ae95f` | 与 r10 逐字相同 |
| 4 | `evaluation/v1_2_3/step9_61a_v3_authorization_lifecycle_contract.json` | `addb3880e7141ca14d7b3011cadb439ac83076fa6b7c2b9f28f3b024d3fd1174` | 与 r10 逐字相同 |
| 5 | `evaluation/v1_2_3/step9_63a_r1_atomic_commit_contract.json` | `4c63855bf08cb420436f5fce80d32e5ca4c6151d642571db9a9c9665194b66bd` | 与 r10 逐字相同 |
| 6 | `evaluation/v1_2_3/step9_63a_r1_v3_runner_freeze_r7.json` | `99ab870303e45497bf750b55f8382912089c2cf80e737b780922695d9906275c` | 与 r10 逐字相同 |
| 7 | `evaluation/v1_2_3/step9_63c_r11_current_runner_identity.json` | `4e077781faeecee57da02f37d1d3ad8cdc9dfa895d3eb72b1b4ab1f1d3f696fe` | 新增/替换/已批准的变更 |
| 8 | `scripts/append_only_ledger.py` | `5fd9f13b9aafbb8617c582ba1ed7de93d3814aefc30e8b442afe881bcd26825f` | 与 r10 逐字相同 |
| 9 | `scripts/authorization_lifecycle.py` | `f0d8b7e04fa2710765b74f4f293436b051af005d11851bf9583da14ff6612744` | 与 r10 逐字相同 |
| 10 | `scripts/build_step9_63c_r11_runner_freeze.py` | `7f72a17c584efe7ee66ee95290d28b6c55daf83ccc08ebebeb3f9319dec30f81` | 新增/替换/已批准的变更 |
| 11 | `scripts/issue_step9_63c_r11_authorization.py` | `f41763f5c82e04360b3d9bcf694e6d05a6fcfa42ae8d71ada29be4ab204e32ab` | 新增/替换/已批准的变更 |
| 12 | `scripts/preflight_step9_62b_mac_local.py` | `c4af2640e0e61a0b84a56b6a6c24f2cb3ceeaa4bb1d552d7180d8c5c54a8eda4` | 与 r10 逐字相同 |
| 13 | `scripts/preflight_step9_63c_current_mac_local.py` | `820cc2b6cc0e4f4569b2c8d8d7b19514ac233d6fa8e2cd96ddd58f14d3aefba6` | 与 r10 逐字相同 |
| 14 | `scripts/preflight_step9_63c_r11_mac_local.py` | `460ede115b319baf35f434915cce1c4a89e4d7ba912e02e1bc3919ef2fbcc05f` | 新增/替换/已批准的变更 |
| 15 | `scripts/run_step9_35a_matched_treatment.py` | `b79bc78a8439021023ee1d190919f5b519de49d3f1931789f788cdaad7776508` | 与 r10 逐字相同 |
| 16 | `scripts/run_step9_53_v3_identity_adapter.py` | `3a4ec3e526bde19e318e271a24569223087c8a6aadc77fd144b061825c0da282` | 与 r10 逐字相同 |
| 17 | `scripts/run_step9_63_v3_formal_execution.py` | `362eb4467fdadd29edc056ecf7b446f2cab99a2d3c407d350b4e91494c5b9528` | 新增/替换/已批准的变更 |
| 18 | `scripts/v3_execution_transaction.py` | `f0e74a49d152053b5455951c507edb8f7849a9e4708835711e5975a82e690e91` | 新增/替换/已批准的变更 |
| 19 | `scripts/v3_namespace_allocator.py` | `3ee484e52eb67003e0ae3b5548b821156e7ebc399c227df0b55dcd0fad385bc5` | 与 r10 逐字相同 |
| 20 | `scripts/v3_runner_identity.py` | `a0f5670d3834d5f91391b41a33fbac669d6162587bc620e9bd3acf202aa3c6a5` | 新增/替换/已批准的变更 |

与 r10 逐字相同的成员共 **13** 个（你的指令里写的是 14：当时第 7 号成员 `issue_step9_63a_r3_authorization.py` 还算在内；按 D13-1(a) 它被 r11 签发器替换，所以是 13）。

## D. 历史钉

| 项 | 草案中的值 |
|---|---|
| r10 Freeze 清单 `evaluation/v1_2_3/step9_63c_r5c5b_runner_freeze_r10.json` | `d24244235e51e7bf6c8567880c654fe3fd73b87fa1bfe1ab0f10dfdc94db2693` |
| r10 授权清单 `evaluation/v1_2_3/step9_63c_r5c6_r10_v3_authorization_manifest.json` | `beac52d1ed3bc11efa02b1a924a8abc7b210171bf5cc1b7910011a6ef9741241` |
| 账本 `evaluation/v1_2_3/authorization_lifecycle_events.jsonl` 冻结前缀 | 长度 1161，SHA-256 `ca168f6939c4697a7a7bccc0b365b414d9a0e632f40de4242eb0a47e2d985285` |

## E. 回归结果、整仓聚合、预测的 Freeze

| 项 | 草案中的值 |
|---|---|
| 回归结果文件 | `evaluation/v1_2_3/step9_63c_r5c10ag_regression_results.json`，SHA-256 `505663fcab46fd6375bfb21f019eb7dcd743e151c1b486e398963d87e0e346e8` |
| 整仓聚合哈希 | **不写在本清单里**（循环依赖，同上）。看草案里的 `repository_aggregate.sha256`；独立核对方法：运行手册第 2 步的 `--print-approval-draft` 命令重新生成一份，比较其中 `repository_aggregate.sha256` 是否相同（身份 ID 会不同，聚合哈希必须相同）。排除项：.git, .venv, __pycache__, models, evaluation/v1_2_3/step9_63c_r11_activation_approval.json, evaluation/v1_2_3/step9_63c_r11_activation_approval.DRAFT.json, ._* |
| Freeze `created_at_utc`（Freeze 内会写入这个时间；签发时间必须晚于它） | `2026-10-10T03:56:44+00:00` |
| 预测的 Freeze SHA-256 | `872274d411e20d9797714f461bcea7e4a6d92684feba6b8084edd357fdee07b8`（9365 字节） |

## F. 将要签发的身份（草案里预先生成，签发时原样使用）

| 项 | 草案中的值 |
|---|---|
| authorization_id | `auth-step9_63c_r11-f21ad78ac3404eff9b92e5cf013ec70b` |
| attempt_id | `attempt-step9_63c_r11-ff4f4029a43b48338db75dc95c1dfcce` |
| evaluation_id | `heldout-v4-step9_55a-treatment-v3-20260930-01` |
| namespace_id | `heldout-v4-treatment-v3-run-d17d217d3c918d62d6ba` |

`namespace_id` 由 `SHA256(evaluation_id\0authorization_id\0attempt_id)` 的前 20 个十六进制字符推出，可独立验证。每次重新运行 `--print-approval-draft` 会生成**新的**随机 ID，所以只能保留你最终核对的那一份。

## G. AR-14

- 待退役的 r10 授权：`auth-step9_63c_r5c6-aff5c4b96bb74278a14d3fd08bf8a84e`（清单 SHA-256 `beac52d1ed3bc11efa02b1a924a8abc7b210171bf5cc1b7910011a6ef9741241`）
- `must_be_retired_before_pointer_creation` = True：指针创建的前置条件之一就是账本里该授权已有终态退役事件。

## H. 签署前必须为真的事实（逐条自问）

- [ ] AR-14 已完成（账本多一行，旧字节不变）。
- [ ] D-A、D-B（AR-14 与 Freeze 创建的门禁入口）已有决定；运行手册第 1、4 步的做法你接受。
- [ ] 草案是在 AR-14 之后重新生成的，且你重新核对过上面所有值。
- [ ] 回归结果文件 SHA 与你手里的文件一致，并且你接受其中列出的已知失败。
- [ ] 没有人在草案生成之后改过仓库里的任何文件（整仓聚合哈希会拒绝）。
- [ ] 签署只改了 `status`（`SIGNED`）、`approver`、`signed_at_utc` 三个字段。
