# r11 激活批准记录逐项核对清单（r5c10ai，最终版，供你逐字核对）

对应文件：`evaluation/v1_2_3/step9_63c_r11_activation_approval.DRAFT.json`（**未签署**：`status` = `DRAFT_NOT_SIGNED`，`approver` / `signed_at_utc` / `signed_at_commit` 为 null）。它取代 r5c10ah 的草案、核对清单和运行手册。

**使用方法**：在仓库根目录 `/Volumes/Elements/cbti-doctor-main` 的终端里，逐条运行下面的命令，输出必须与“期望输出”逐字相同。“期望输出”是我在本步结束时的仓库上实际运行同一条命令得到的。**全部一致才 commit、才签。**

两个无法在本清单里写死的值（循环依赖：整仓聚合哈希覆盖本清单文件，草案的 SHA 又包含该哈希）：整仓聚合哈希和草案文件自己的 SHA-256。对前者给出的是“重新计算的值必须等于草案里记录的值”的比较命令；两者的具体值写在我交给你的最终说明里。

## 1. 仓库状态与归档提交

- **归档提交 201ef5c 存在且是提交对象**
  - 命令：`git cat-file -t 201ef5c2d406b0eaf2ebf5ce12db912b3caf5762`
  - 期望输出：
    ```
    commit
    ```
- **归档提交是当前 HEAD 的祖先（退出码 0）**
  - 命令：`git merge-base --is-ancestor 201ef5c2d406b0eaf2ebf5ce12db912b3caf5762 HEAD; echo $?`
  - 期望输出：
    ```
    0
    ```
- **commit 之后工作树必须干净**：`git status --short` → 期望输出：空（无任何输出）。现在它**不是**空的（本步的改动还没提交），这正是你要先 commit 的原因。
- **签署时的提交**：`git rev-parse HEAD` → 就是你要填进批准记录 `signed_at_commit` 的 40 位十六进制；签署之后任何门禁入口都会核对 HEAD 仍等于它。

## 2. 指针

- **规范字节长度与 SHA-256**（你批准的 389 字节）
  - 命令：`.venv/bin/python -c "from scripts import build_step9_63c_r11_runner_freeze as b; import hashlib; x=b.canonical_pointer_bytes(); print(len(x), hashlib.sha256(x).hexdigest())"`
  - 期望输出：
    ```
    389 4e077781faeecee57da02f37d1d3ad8cdc9dfa895d3eb72b1b4ab1f1d3f696fe
    ```
## 3. 命名文件

- **builder：`scripts/build_step9_63c_r11_runner_freeze.py`**
  - 命令：`shasum -a 256 scripts/build_step9_63c_r11_runner_freeze.py`
  - 期望输出：
    ```
    99031a9156da87164c16b71eff9e2a9961428c52bbf7bc2590741e51e55f950e  scripts/build_step9_63c_r11_runner_freeze.py
    ```
- **consumer：`scripts/run_step9_63_v3_formal_execution.py`**
  - 命令：`shasum -a 256 scripts/run_step9_63_v3_formal_execution.py`
  - 期望输出：
    ```
    362eb4467fdadd29edc056ecf7b446f2cab99a2d3c407d350b4e91494c5b9528  scripts/run_step9_63_v3_formal_execution.py
    ```
- **issuer：`scripts/issue_step9_63c_r11_authorization.py`**
  - 命令：`shasum -a 256 scripts/issue_step9_63c_r11_authorization.py`
  - 期望输出：
    ```
    f41763f5c82e04360b3d9bcf694e6d05a6fcfa42ae8d71ada29be4ab204e32ab  scripts/issue_step9_63c_r11_authorization.py
    ```
- **producer：`scripts/preflight_step9_63c_r11_mac_local.py`**
  - 命令：`shasum -a 256 scripts/preflight_step9_63c_r11_mac_local.py`
  - 期望输出：
    ```
    460ede115b319baf35f434915cce1c4a89e4d7ba912e02e1bc3919ef2fbcc05f  scripts/preflight_step9_63c_r11_mac_local.py
    ```
- **resolver：`scripts/v3_runner_identity.py`**
  - 命令：`shasum -a 256 scripts/v3_runner_identity.py`
  - 期望输出：
    ```
    a0f5670d3834d5f91391b41a33fbac669d6162587bc620e9bd3acf202aa3c6a5  scripts/v3_runner_identity.py
    ```
- **scanner：`scripts/v3_execution_transaction.py`**
  - 命令：`shasum -a 256 scripts/v3_execution_transaction.py`
  - 期望输出：
    ```
    f0e74a49d152053b5455951c507edb8f7849a9e4708835711e5975a82e690e91  scripts/v3_execution_transaction.py
    ```
本步的预期：resolver、consumer、issuer、scanner、producer 都**未变**；**builder 是唯一变化的文件**。

## 4. r11 的 20 个成员

- **#1 `evaluation/v1_2_3/step9_51_v3_development_freeze_r1.json`**（与 r10 逐字相同）
  - 命令：`shasum -a 256 evaluation/v1_2_3/step9_51_v3_development_freeze_r1.json`
  - 期望输出：
    ```
    106e18707aa66806c3953c8d5f38484f534d78e4fd230cbd6c491304aaf8cd27  evaluation/v1_2_3/step9_51_v3_development_freeze_r1.json
    ```
- **#2 `evaluation/v1_2_3/step9_52_v3_pre_evaluation_validation.json`**（与 r10 逐字相同）
  - 命令：`shasum -a 256 evaluation/v1_2_3/step9_52_v3_pre_evaluation_validation.json`
  - 期望输出：
    ```
    7f2a5e43f4131feec1fed51121e0a398a9c9ca0ab1679073be8a91c19c4940d3  evaluation/v1_2_3/step9_52_v3_pre_evaluation_validation.json
    ```
- **#3 `evaluation/v1_2_3/step9_58a_r1_v3_identity_contract.json`**（与 r10 逐字相同）
  - 命令：`shasum -a 256 evaluation/v1_2_3/step9_58a_r1_v3_identity_contract.json`
  - 期望输出：
    ```
    16b6cd71cd75ea231ed3a10d3f43546e31cded9d1be120ce5d16c000391ae95f  evaluation/v1_2_3/step9_58a_r1_v3_identity_contract.json
    ```
- **#4 `evaluation/v1_2_3/step9_61a_v3_authorization_lifecycle_contract.json`**（与 r10 逐字相同）
  - 命令：`shasum -a 256 evaluation/v1_2_3/step9_61a_v3_authorization_lifecycle_contract.json`
  - 期望输出：
    ```
    addb3880e7141ca14d7b3011cadb439ac83076fa6b7c2b9f28f3b024d3fd1174  evaluation/v1_2_3/step9_61a_v3_authorization_lifecycle_contract.json
    ```
- **#5 `evaluation/v1_2_3/step9_63a_r1_atomic_commit_contract.json`**（与 r10 逐字相同）
  - 命令：`shasum -a 256 evaluation/v1_2_3/step9_63a_r1_atomic_commit_contract.json`
  - 期望输出：
    ```
    4c63855bf08cb420436f5fce80d32e5ca4c6151d642571db9a9c9665194b66bd  evaluation/v1_2_3/step9_63a_r1_atomic_commit_contract.json
    ```
- **#6 `evaluation/v1_2_3/step9_63a_r1_v3_runner_freeze_r7.json`**（与 r10 逐字相同）
  - 命令：`shasum -a 256 evaluation/v1_2_3/step9_63a_r1_v3_runner_freeze_r7.json`
  - 期望输出：
    ```
    99ab870303e45497bf750b55f8382912089c2cf80e737b780922695d9906275c  evaluation/v1_2_3/step9_63a_r1_v3_runner_freeze_r7.json
    ```
- **#7 指针（尚不存在，钉的是规范字节）**
  - 命令：`.venv/bin/python -c "from scripts import build_step9_63c_r11_runner_freeze as b; print(b.POINTER_SHA256)"`
  - 期望输出：
    ```
    4e077781faeecee57da02f37d1d3ad8cdc9dfa895d3eb72b1b4ab1f1d3f696fe
    ```
- **#8 `scripts/append_only_ledger.py`**（与 r10 逐字相同）
  - 命令：`shasum -a 256 scripts/append_only_ledger.py`
  - 期望输出：
    ```
    5fd9f13b9aafbb8617c582ba1ed7de93d3814aefc30e8b442afe881bcd26825f  scripts/append_only_ledger.py
    ```
- **#9 `scripts/authorization_lifecycle.py`**（与 r10 逐字相同）
  - 命令：`shasum -a 256 scripts/authorization_lifecycle.py`
  - 期望输出：
    ```
    f0d8b7e04fa2710765b74f4f293436b051af005d11851bf9583da14ff6612744  scripts/authorization_lifecycle.py
    ```
- **#10 `scripts/build_step9_63c_r11_runner_freeze.py`**（新增/替换/已批准的变更）
  - 命令：`shasum -a 256 scripts/build_step9_63c_r11_runner_freeze.py`
  - 期望输出：
    ```
    99031a9156da87164c16b71eff9e2a9961428c52bbf7bc2590741e51e55f950e  scripts/build_step9_63c_r11_runner_freeze.py
    ```
- **#11 `scripts/issue_step9_63c_r11_authorization.py`**（新增/替换/已批准的变更）
  - 命令：`shasum -a 256 scripts/issue_step9_63c_r11_authorization.py`
  - 期望输出：
    ```
    f41763f5c82e04360b3d9bcf694e6d05a6fcfa42ae8d71ada29be4ab204e32ab  scripts/issue_step9_63c_r11_authorization.py
    ```
- **#12 `scripts/preflight_step9_62b_mac_local.py`**（与 r10 逐字相同）
  - 命令：`shasum -a 256 scripts/preflight_step9_62b_mac_local.py`
  - 期望输出：
    ```
    c4af2640e0e61a0b84a56b6a6c24f2cb3ceeaa4bb1d552d7180d8c5c54a8eda4  scripts/preflight_step9_62b_mac_local.py
    ```
- **#13 `scripts/preflight_step9_63c_current_mac_local.py`**（与 r10 逐字相同）
  - 命令：`shasum -a 256 scripts/preflight_step9_63c_current_mac_local.py`
  - 期望输出：
    ```
    820cc2b6cc0e4f4569b2c8d8d7b19514ac233d6fa8e2cd96ddd58f14d3aefba6  scripts/preflight_step9_63c_current_mac_local.py
    ```
- **#14 `scripts/preflight_step9_63c_r11_mac_local.py`**（新增/替换/已批准的变更）
  - 命令：`shasum -a 256 scripts/preflight_step9_63c_r11_mac_local.py`
  - 期望输出：
    ```
    460ede115b319baf35f434915cce1c4a89e4d7ba912e02e1bc3919ef2fbcc05f  scripts/preflight_step9_63c_r11_mac_local.py
    ```
- **#15 `scripts/run_step9_35a_matched_treatment.py`**（与 r10 逐字相同）
  - 命令：`shasum -a 256 scripts/run_step9_35a_matched_treatment.py`
  - 期望输出：
    ```
    b79bc78a8439021023ee1d190919f5b519de49d3f1931789f788cdaad7776508  scripts/run_step9_35a_matched_treatment.py
    ```
- **#16 `scripts/run_step9_53_v3_identity_adapter.py`**（与 r10 逐字相同）
  - 命令：`shasum -a 256 scripts/run_step9_53_v3_identity_adapter.py`
  - 期望输出：
    ```
    3a4ec3e526bde19e318e271a24569223087c8a6aadc77fd144b061825c0da282  scripts/run_step9_53_v3_identity_adapter.py
    ```
- **#17 `scripts/run_step9_63_v3_formal_execution.py`**（新增/替换/已批准的变更）
  - 命令：`shasum -a 256 scripts/run_step9_63_v3_formal_execution.py`
  - 期望输出：
    ```
    362eb4467fdadd29edc056ecf7b446f2cab99a2d3c407d350b4e91494c5b9528  scripts/run_step9_63_v3_formal_execution.py
    ```
- **#18 `scripts/v3_execution_transaction.py`**（新增/替换/已批准的变更）
  - 命令：`shasum -a 256 scripts/v3_execution_transaction.py`
  - 期望输出：
    ```
    f0e74a49d152053b5455951c507edb8f7849a9e4708835711e5975a82e690e91  scripts/v3_execution_transaction.py
    ```
- **#19 `scripts/v3_namespace_allocator.py`**（与 r10 逐字相同）
  - 命令：`shasum -a 256 scripts/v3_namespace_allocator.py`
  - 期望输出：
    ```
    3ee484e52eb67003e0ae3b5548b821156e7ebc399c227df0b55dcd0fad385bc5  scripts/v3_namespace_allocator.py
    ```
- **#20 `scripts/v3_runner_identity.py`**（新增/替换/已批准的变更）
  - 命令：`shasum -a 256 scripts/v3_runner_identity.py`
  - 期望输出：
    ```
    a0f5670d3834d5f91391b41a33fbac669d6162587bc620e9bd3acf202aa3c6a5  scripts/v3_runner_identity.py
    ```

与 r10 逐字相同的成员共 **13** 个（统一口径 13）。

## 5. 历史钉与账本（AR-14 的起点）

- **r10 Freeze 清单**
  - 命令：`shasum -a 256 evaluation/v1_2_3/step9_63c_r5c5b_runner_freeze_r10.json`
  - 期望输出：
    ```
    d24244235e51e7bf6c8567880c654fe3fd73b87fa1bfe1ab0f10dfdc94db2693  evaluation/v1_2_3/step9_63c_r5c5b_runner_freeze_r10.json
    ```
- **r10 授权清单**
  - 命令：`shasum -a 256 evaluation/v1_2_3/step9_63c_r5c6_r10_v3_authorization_manifest.json`
  - 期望输出：
    ```
    beac52d1ed3bc11efa02b1a924a8abc7b210171bf5cc1b7910011a6ef9741241  evaluation/v1_2_3/step9_63c_r5c6_r10_v3_authorization_manifest.json
    ```
- **账本冻结前缀（前 1161 字节）**
  - 命令：`head -c 1161 evaluation/v1_2_3/authorization_lifecycle_events.jsonl | shasum -a 256`
  - 期望输出：
    ```
    ca168f6939c4697a7a7bccc0b365b414d9a0e632f40de4242eb0a47e2d985285  -
    ```
- ****退役前账本**字节数（写入前必须逐字相等）**
  - 命令：`wc -c < evaluation/v1_2_3/authorization_lifecycle_events.jsonl`
  - 期望输出：
    ```
    3856
    ```
- ****退役前账本** SHA-256**
  - 命令：`shasum -a 256 evaluation/v1_2_3/authorization_lifecycle_events.jsonl`
  - 期望输出：
    ```
    aaa2e9898a8869db052a1248a0ca2b0574d9c36093aee608db59457f24c2a60e  evaluation/v1_2_3/authorization_lifecycle_events.jsonl
    ```
## 6. AR-14

- **待退役的 r10 授权 ID**
  - 命令：`python3 -c "import json;print(json.load(open('evaluation/v1_2_3/step9_63c_r5c6_r10_v3_authorization_manifest.json'))['authorization_id'])"`
  - 期望输出：
    ```
    auth-step9_63c_r5c6-aff5c4b96bb74278a14d3fd08bf8a84e
    ```
- **不可重用判定文件（已在仓库中）**
  - 命令：`shasum -a 256 evaluation/v1_2_3/step9_63c_r11_ar14_determination.json`
  - 期望输出：
    ```
    41b524d09a258505cf036d7987b6cf2076bc0ad041a3545b5fdb563420da01d2  evaluation/v1_2_3/step9_63c_r11_ar14_determination.json
    ```
- **判定文件引用的 approval_id 等于草案的 approval_id**（两行相同）
  - 命令：`python3 -c "import json;print(json.load(open('evaluation/v1_2_3/step9_63c_r11_ar14_determination.json'))['approval_id']); print(json.load(open('evaluation/v1_2_3/step9_63c_r11_activation_approval.DRAFT.json'))['approval_id'])"`
  - 期望输出：
    ```
    approval-step9_63c_r11-6ec0ca3e42a641e8b7b92ed6c64e66f2
    approval-step9_63c_r11-6ec0ca3e42a641e8b7b92ed6c64e66f2
    ```
- **预期追加事件模板的 SHA-256**
  - 命令：`python3 -c "import json,hashlib;d=json.load(open('evaluation/v1_2_3/step9_63c_r11_activation_approval.DRAFT.json'));print(hashlib.sha256(json.dumps(d['ar14']['expected_retirement_event_template'],sort_keys=True,ensure_ascii=False).encode()).hexdigest())"`
  - 期望输出：
    ```
    eb36196532100764b3d715a0bf3feef255163bbbce03840e32c43a6cb937b233
    ```

**AR-14 之后的预期账本**：不能钉成整个文件的 SHA（事件里的 `lifecycle_event_id` 与 `timestamp_utc` 由冻结函数在调用时生成）。按你的决定 5，验证方式是：模板 + 原前缀逐字节不变 + 恰好多一行。预期追加行的规范字节（`sort_keys`、`ensure_ascii=False`、单个换行结尾；两个生成字段是变量，两个路径字段在生产根下是绝对路径）：

```json
{"artifact_type": "AUTHORIZATION_LIFECYCLE_EVENT", "attempt_created": false, "attempt_id": "attempt-step9_63c_r5c6-3401b701486c4fdeb4019b461d024bd4", "authorization_consumed": false, "authorization_consumption_count": 0, "authorization_id": "auth-step9_63c_r5c6-aff5c4b96bb74278a14d3fd08bf8a84e", "authorization_manifest_sha256": "beac52d1ed3bc11efa02b1a924a8abc7b210171bf5cc1b7910011a6ef9741241", "cases_completed": 0, "cases_started": 0, "evaluation_id": "heldout-v4-step9_55a-treatment-v3-20260930-01", "event_type": "AUTHORIZATION_RETIRED_UNCONSUMED_NON_REUSABLE", "final_status": "RETIRED_UNCONSUMED_NON_REUSABLE", "historical_runner_freeze_path": "evaluation/v1_2_3/step9_63c_r5c5b_runner_freeze_r10.json", "historical_runner_freeze_revision": "r10", "historical_runner_freeze_sha256": "d24244235e51e7bf6c8567880c654fe3fd73b87fa1bfe1ab0f10dfdc94db2693", "lifecycle_contract_path": "/Volumes/Elements/cbti-doctor-main/evaluation/v1_2_3/step9_61a_v3_authorization_lifecycle_contract.json", "lifecycle_contract_sha256": "addb3880e7141ca14d7b3011cadb439ac83076fa6b7c2b9f28f3b024d3fd1174", "lifecycle_event_id": "retire-<32 位十六进制>", "namespace_created": false, "original_status": "ISSUED_NOT_CONSUMED", "reuse_determination": "/Volumes/Elements/cbti-doctor-main/evaluation/v1_2_3/step9_63c_r11_ar14_determination.json", "reuse_determination_sha256": "41b524d09a258505cf036d7987b6cf2076bc0ad041a3545b5fdb563420da01d2", "terminal": true, "timestamp_utc": "<ISO 时间，晚于账本里所有已有事件>"}
```

## 7. 回归、聚合、预测的 Freeze

- **回归结果文件 SHA-256**
  - 命令：`shasum -a 256 evaluation/v1_2_3/step9_63c_r5c10ai_regression_results.json`
  - 期望输出：
    ```
    cb183d96a689c68212d0dfac86bf8b17140f7db4d09b114c2f7a89beb2eb9b10  evaluation/v1_2_3/step9_63c_r5c10ai_regression_results.json
    ```
- **整仓聚合哈希**（稳定口径，排除各门禁步骤的产物与批准记录）：
  - 命令（重新计算）：`.venv/bin/python -c "from scripts import build_step9_63c_r11_runner_freeze as b; a=b.stable_aggregate(b.ROOT); print(a['sha256'], a['files'])"`
  - 命令（草案中的值）：`python3 -c "import json;a=json.load(open('evaluation/v1_2_3/step9_63c_r11_activation_approval.DRAFT.json'))['repository_aggregate'];print(a['sha256'], a['files'])"`
  - 期望：两条命令的输出**逐字相同**（具体值见最终说明）。

- **预测的 Freeze（`created_at_utc`、SHA-256、长度）**
  - 命令：`.venv/bin/python -c "from scripts import build_step9_63c_r11_runner_freeze as b; import json; print(json.dumps(b.predict_freeze(b.ROOT, '2026-10-10T13:10:38+00:00'), sort_keys=True))"`
  - 期望输出：
    ```
    {"created_at_utc": "2026-10-10T13:10:38+00:00", "predicted_sha256": "bafcec8d2ae0bad6c3cb43e89bd49171b85374957ec6ce173071fef5248357b3", "predicted_size": 9365}
    ```
## 8. 签发身份、内容哈希、令牌

- **namespace_id 可由另外三个 ID 独立推出**
  - 命令：`.venv/bin/python -c "from scripts.v3_namespace_allocator import derive_namespace_id as g; print(g('heldout-v4-step9_55a-treatment-v3-20260930-01','auth-step9_63c_r11-1a399434ec0e4494b0045734846b2042','attempt-step9_63c_r11-2312daefa1364bfd83ff3948d101c765'))"`
  - 期望输出：
    ```
    heldout-v4-treatment-v3-run-9ec9c305cc4de01e6538
    ```
  - 草案里记录的身份：authorization `auth-step9_63c_r11-1a399434ec0e4494b0045734846b2042`；attempt `attempt-step9_63c_r11-2312daefa1364bfd83ff3948d101c765`；evaluation `heldout-v4-step9_55a-treatment-v3-20260930-01`。

- **批准记录内容哈希（签名字段置空后的 SHA-256）**（两行相同；签署只改四个签名字段，所以签署前后这个值不变，令牌因此现在就能写全）
  - 命令：`.venv/bin/python -c "import json; from scripts import build_step9_63c_r11_runner_freeze as b; d=json.load(open('evaluation/v1_2_3/step9_63c_r11_activation_approval.DRAFT.json')); print(b.approval_content_sha256(d)); print(d['content_sha256'])"`
  - 期望输出：
    ```
    af433dc27b5d1747c16c813e32af0282ff3bba83bebd1a717bafdcd009f29ad2
    af433dc27b5d1747c16c813e32af0282ff3bba83bebd1a717bafdcd009f29ad2
    ```

**三个写入入口的令牌（完整具体值，签署前后不变）：**

| 入口 | 令牌 |
|---|---|
| `--retire-r10`（AR-14） | `RETIRE-R10-aff5c4b96bb7-af433dc27b5d` |
| `--create-pointer` | `CREATE-R11-POINTER-4e077781faee` |
| `--create-freeze` | `CREATE-R11-FREEZE-bafcec8d2ae0-af433dc27b5d` |

（签发入口 `issue_step9_63c_r11_authorization --issue` 的令牌 `ISSUE-R11-AUTH-<12 位>` 由已签署文件的字节派生，签发器不允许改，所以要等签署后由 `--plan` 显示；它不能提前写全。）

- **退役令牌的构成可复算**
  - 命令：`.venv/bin/python -c "import json; from scripts import build_step9_63c_r11_runner_freeze as b; d=json.load(open('evaluation/v1_2_3/step9_63c_r11_activation_approval.DRAFT.json')); print(b.retire_token(d['content_sha256'])); print(b.freeze_token(d['freeze']['predicted_sha256'], d['content_sha256'])); print(b.POINTER_TOKEN)"`
  - 期望输出：
    ```
    RETIRE-R10-aff5c4b96bb7-af433dc27b5d
    CREATE-R11-FREEZE-bafcec8d2ae0-af433dc27b5d
    CREATE-R11-POINTER-4e077781faee
    ```

## 9. 已接受的例外（AR-15）

- **批准记录里的 accepted_exceptions**（签署即表示接受）
  - 命令：`python3 -c "import json;e=json.load(open('evaluation/v1_2_3/step9_63c_r11_activation_approval.DRAFT.json'))['accepted_exceptions'];print(e[0]['id']);print(e[0]['state']);print(e[0]['text'])"`
  - 期望输出：
    ```
    AR-15
    CONTENT_INTEGRITY_UNPROVEN
    Historical Trace original content integrity is CONTENT_INTEGRITY_UNPROVEN: only that the current hashes are unchanged can be proven, not the original content. Signing this record means accepting that.
    ```

## 10. 签署前自问

- [ ] 上面每条命令的输出都与期望逐字相同。
- [ ] 我接受 AR-15 的例外说明。
- [ ] 我接受回归结果文件里的已知失败（RC5、RC6）和 33 个等待 r11 身份的 RC1 项。
- [ ] 我接受“AR-14 之后账本”的验证方式（模板 + 原前缀不变 + 恰好多一行）。
- [ ] 我已 commit，`git status --short` 为空，且这个 commit 包含草案、判定文件、清单和运行手册。
