# r11 激活批准记录逐项核对清单（r5c10ah，供你逐字核对）

对应文件：`evaluation/v1_2_3/step9_63c_r11_activation_approval.DRAFT.json`（**未签署**：`status` = `DRAFT_NOT_SIGNED`，`approver` / `signed_at_utc` 为 null）。它取代上一步的草案（SHA `91fd0f68…`）；上一步的清单与运行手册同样被本步的取代。

**这份草案只需要签一次，而且在 AR-14 之前签。** 本步把批准记录改成在整个顺序里都有效：整仓聚合哈希排除了各门禁步骤会创建或追加的文件（账本、锁文件、指针及其创建记录、Freeze、签发清单、Registry），这些文件各自被单独钉住（退役前账本、规范指针、预测的 Freeze、签发身份）。

不在本清单里写出的两个值（循环依赖：聚合哈希覆盖本清单文件）：**整仓聚合哈希**和**草案文件自己的 SHA-256**。它们在我给你的最终说明里；独立核对聚合哈希的办法：运行手册第 1 步的 `--print-approval-draft` 命令重新生成一份，比较 `repository_aggregate.sha256`（`approval_id` 和签发 ID 会不同，聚合哈希必须相同）。

核对方法：对表中每个路径运行 `shasum -a 256 <路径>`，与“草案中的值”逐字比较。**全部一致才签。** 签署只改 `status`（`SIGNED`）、`approver`、`signed_at_utc` 三个字段，其余一个字节都不要动。

## A. 指针

| 项 | 草案中的值 |
|---|---|
| 路径 | `evaluation/v1_2_3/step9_63c_r11_current_runner_identity.json` |
| 规范字节 SHA-256 | `4e077781faeecee57da02f37d1d3ad8cdc9dfa895d3eb72b1b4ab1f1d3f696fe` |
| 规范字节长度 | 389 |

## B. 命名文件

| 角色 | 路径 | 草案中的 SHA-256 |
|---|---|---|
| builder | `scripts/build_step9_63c_r11_runner_freeze.py` | `9cfaf75a1c7ab2b2a6b0c0126c77692e02144f8483f9384fb361f3b92f832ea9` |
| consumer | `scripts/run_step9_63_v3_formal_execution.py` | `362eb4467fdadd29edc056ecf7b446f2cab99a2d3c407d350b4e91494c5b9528` |
| issuer | `scripts/issue_step9_63c_r11_authorization.py` | `f41763f5c82e04360b3d9bcf694e6d05a6fcfa42ae8d71ada29be4ab204e32ab` |
| producer | `scripts/preflight_step9_63c_r11_mac_local.py` | `460ede115b319baf35f434915cce1c4a89e4d7ba912e02e1bc3919ef2fbcc05f` |
| resolver | `scripts/v3_runner_identity.py` | `a0f5670d3834d5f91391b41a33fbac669d6162587bc620e9bd3acf202aa3c6a5` |
| scanner | `scripts/v3_execution_transaction.py` | `f0e74a49d152053b5455951c507edb8f7849a9e4708835711e5975a82e690e91` |

本步的预期：resolver `a0f5670d…c6a5`、consumer `362eb446…9528`、issuer `f41763f5…32ab`、scanner `f0e74a49…0e91`、producer `460ede11…c05f` 都**未变**；**builder 是唯一变化的文件**。

## C. r11 的 20 个成员

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
| 10 | `scripts/build_step9_63c_r11_runner_freeze.py` | `9cfaf75a1c7ab2b2a6b0c0126c77692e02144f8483f9384fb361f3b92f832ea9` | 新增/替换/已批准的变更 |
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

与 r10 逐字相同的成员共 **13** 个（统一口径：13，不是 14——第 7 号成员已被 r11 签发器替换）。

## D. 历史钉

| 项 | 草案中的值 |
|---|---|
| r10 Freeze 清单 `evaluation/v1_2_3/step9_63c_r5c5b_runner_freeze_r10.json` | `d24244235e51e7bf6c8567880c654fe3fd73b87fa1bfe1ab0f10dfdc94db2693` |
| r10 授权清单 `evaluation/v1_2_3/step9_63c_r5c6_r10_v3_authorization_manifest.json` | `beac52d1ed3bc11efa02b1a924a8abc7b210171bf5cc1b7910011a6ef9741241` |
| 账本冻结前缀 | 长度 1161，SHA-256 `ca168f6939c4697a7a7bccc0b365b414d9a0e632f40de4242eb0a47e2d985285` |

## E. AR-14（退役 r10 授权）

| 项 | 草案中的值 |
|---|---|
| 待退役的 r10 授权 | `auth-step9_63c_r5c6-aff5c4b96bb74278a14d3fd08bf8a84e`（清单 SHA-256 `beac52d1ed3bc11efa02b1a924a8abc7b210171bf5cc1b7910011a6ef9741241`） |
| **退役前账本**（写入前必须逐字相等） | `evaluation/v1_2_3/authorization_lifecycle_events.jsonl`，3856 字节，SHA-256 `aaa2e9898a8869db052a1248a0ca2b0574d9c36093aee608db59457f24c2a60e` |
| 不可重用判定文件（已在仓库中，内容与批准记录互相钉住） | `evaluation/v1_2_3/step9_63c_r11_ar14_determination.json`，949 字节，SHA-256 `41b524d09a258505cf036d7987b6cf2076bc0ad041a3545b5fdb563420da01d2`；内含 `approval_id` = `approval-step9_63c_r11-6ec0ca3e42a641e8b7b92ed6c64e66f2` |
| 预期追加事件模板 SHA-256（`lifecycle_event_id` 与 `timestamp_utc` 置 null） | `eb36196532100764b3d715a0bf3feef255163bbbce03840e32c43a6cb937b233` |

**AR-14 之后的预期账本**：不能钉死整个文件的 SHA——事件里的 `lifecycle_event_id` 和 `timestamp_utc` 是冻结函数在调用时生成的。钉住的是：规则 + 模板。

> the pre-retirement ledger bytes unchanged, followed by exactly ONE line: the template with a fresh lifecycle_event_id (retire-<32 hex>) and a timestamp_utc later than every earlier event; the exact SHA-256 of the post-retirement ledger cannot be pinned because those two fields are generated inside the frozen function at call time

预期追加行的规范字节（`sort_keys`、`ensure_ascii=False`、单个换行结尾；两个生成字段是变量，两个路径字段在生产根下是绝对路径）：

```json
{"artifact_type": "AUTHORIZATION_LIFECYCLE_EVENT", "attempt_created": false, "attempt_id": "attempt-step9_63c_r5c6-3401b701486c4fdeb4019b461d024bd4", "authorization_consumed": false, "authorization_consumption_count": 0, "authorization_id": "auth-step9_63c_r5c6-aff5c4b96bb74278a14d3fd08bf8a84e", "authorization_manifest_sha256": "beac52d1ed3bc11efa02b1a924a8abc7b210171bf5cc1b7910011a6ef9741241", "cases_completed": 0, "cases_started": 0, "evaluation_id": "heldout-v4-step9_55a-treatment-v3-20260930-01", "event_type": "AUTHORIZATION_RETIRED_UNCONSUMED_NON_REUSABLE", "final_status": "RETIRED_UNCONSUMED_NON_REUSABLE", "historical_runner_freeze_path": "evaluation/v1_2_3/step9_63c_r5c5b_runner_freeze_r10.json", "historical_runner_freeze_revision": "r10", "historical_runner_freeze_sha256": "d24244235e51e7bf6c8567880c654fe3fd73b87fa1bfe1ab0f10dfdc94db2693", "lifecycle_contract_path": "/Volumes/Elements/cbti-doctor-main/evaluation/v1_2_3/step9_61a_v3_authorization_lifecycle_contract.json", "lifecycle_contract_sha256": "addb3880e7141ca14d7b3011cadb439ac83076fa6b7c2b9f28f3b024d3fd1174", "lifecycle_event_id": "retire-<32 位十六进制>", "namespace_created": false, "original_status": "ISSUED_NOT_CONSUMED", "reuse_determination": "/Volumes/Elements/cbti-doctor-main/evaluation/v1_2_3/step9_63c_r11_ar14_determination.json", "reuse_determination_sha256": "41b524d09a258505cf036d7987b6cf2076bc0ad041a3545b5fdb563420da01d2", "terminal": true, "timestamp_utc": "<ISO 时间，晚于账本里所有已有事件>"}
```

入口在写入后会重新读取账本并验证：旧字节逐字节不变、恰好多一行、该行等于上面的模板（除两个生成字段）、reducer 判定 r10 已退役且不可执行；任何一项不符 → `POSTCONDITION_FAILED`，什么都不删（账本只追加），停在那里报告。

## F. 回归、整仓聚合、预测的 Freeze

| 项 | 草案中的值 |
|---|---|
| 回归结果文件 | `evaluation/v1_2_3/step9_63c_r5c10ah_regression_results.json`，SHA-256 `2463c83a290f2f2d4a077e7e38c8e3cdff8bc0531be0f27e0bbe5367c191ae4c` |
| 整仓聚合哈希 | **见最终说明**（循环依赖）；排除项：.git, .venv, __pycache__, models, evaluation/v1_2_3/step9_63c_r11_activation_approval.json, evaluation/v1_2_3/step9_63c_r11_activation_approval.DRAFT.json, ._*, evaluation/v1_2_3/authorization_lifecycle_events.jsonl, evaluation/v4_runs/.namespace-allocation.lock, evaluation/v1_2_3/step9_63c_r11_current_runner_identity.json, evaluation/v1_2_3/step9_63c_r11_identity_pointer_creation_record.json, evaluation/v1_2_3/step9_63c_r11_runner_freeze.json, evaluation/v1_2_3/step9_63c_r11_preflight_invocations.jsonl, evaluation/v1_2_3/step9_63c_r11_v3_authorization_manifest.json |
| Freeze `created_at_utc`（签发时间必须晚于它） | `2026-10-10T12:38:55+00:00` |
| 预测的 Freeze SHA-256 / 长度 | `a5362683172a2c566bfa90e4427b8d7ebc6d6ec6f41e8f5190144915674a890a` / 9365 字节 |

## G. 令牌格式（每个写入入口都要你亲手输入）

| 入口 | 令牌格式 | 草案可确定的部分 |
|---|---|---|
| `--retire-r10` | `RETIRE-R10-<first 12 characters of the r10 authorization id>-<first 12 hex of the approval record SHA-256>` | `RETIRE-R10-auth-step9_6-` + 批准记录 SHA 前 12 位（签署后才确定；`--plan-retire` 会显示完整令牌） |
| `--create-pointer` | `CREATE-R11-POINTER-<first 12 hex of the canonical pointer SHA-256>` | `CREATE-R11-POINTER-4e077781faee` |
| `--create-freeze` | `CREATE-R11-FREEZE-<first 12 hex of the predicted Freeze SHA-256>-<first 12 hex of the approval record SHA-256>` | `CREATE-R11-FREEZE-a5362683172a-` + 批准记录 SHA 前 12 位 |
| `issue_step9_63c_r11_authorization --issue` | `ISSUE-R11-AUTH-<first 12 hex of SHA-256(authorization id | freeze SHA-256 | approval record SHA-256)>` | 签署后 `--plan` 会显示 |

说明：`RETIRE-R10-` 后的第一段按你的指令取授权 ID 的前 12 个字符，即常量 `auth-step9_6`；真正把令牌绑定到这份批准记录的是第二段（批准记录 SHA 前 12 位）。

## H. 将要签发的身份（草案里预先生成，签发时原样使用）

| 项 | 草案中的值 |
|---|---|
| authorization_id | `auth-step9_63c_r11-1a399434ec0e4494b0045734846b2042` |
| attempt_id | `attempt-step9_63c_r11-2312daefa1364bfd83ff3948d101c765` |
| evaluation_id | `heldout-v4-step9_55a-treatment-v3-20260930-01` |
| namespace_id | `heldout-v4-treatment-v3-run-9ec9c305cc4de01e6538` |

`namespace_id` = `SHA256(evaluation_id\0authorization_id\0attempt_id)` 前 20 个十六进制字符，可独立验证。

## I. 签署前自问

- [ ] 草案里的 builder SHA 就是我核对过的那个（`9cfaf75a…`），其余命名文件都与上一步相同。
- [ ] 判定文件已经在仓库里，且内容与 E 节的 SHA 一致，其中 `approval_id` 与草案一致。
- [ ] 退役前账本的 SHA 与 `shasum -a 256 evaluation/v1_2_3/authorization_lifecycle_events.jsonl` 一致（3856 字节）。
- [ ] 我接受 E 节对“AR-14 之后账本”的表述（规则+模板，不是整文件 SHA）。
- [ ] 我接受回归结果文件里的已知失败（RC5、RC6，以及 HEAD 移动导致的 2 个归档重放测试，见变更报告）。
- [ ] 草案生成之后没有人改过仓库里的任何文件（聚合哈希会拒绝）。
- [ ] 签署只改了 `status`、`approver`、`signed_at_utc` 三个字段。
