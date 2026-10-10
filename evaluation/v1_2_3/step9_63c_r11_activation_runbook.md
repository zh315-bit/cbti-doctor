# r11 激活运行手册（Step 9.63c-r5c10ag）

**状态：草案。本步没有执行其中任何一步。** 每一步都在你批准后由你在**交互终端**里自己执行（Claude Code 内置 Terminal 面板就是交互终端；管道、脚本、CI、代理调用会被写入入口拒绝）。

通用约定：

- 工作目录：`/Volumes/Elements/cbti-doctor-main`；解释器：`.venv/bin/python`。生产环境**不要**设置环境变量 `CBTI_ALLOW_SYNTHETIC_ROOT`（合成根开关只用于临时目录）。
- 顺序固定：**AR-14 → 签批准记录 → 指针 → Freeze → 签发**。任何一步的“预期输出”不符，就停下，不要继续。
- 每个写入步骤之后的“回读检查”都是只读命令，可以随时重复运行。
- 下列“预期输出”来自两处：**步骤 0 的输出是在真实仓库上实测的当前状态**；其余步骤的输出来自临时根上的完整演练（`step9_63c_r5c10ag_e2e_rehearsal_report.json` 逐条记录了真实输出），令牌、哈希、ID、时间会不同，形状相同。

## 需要你先做的决定（没有它们，手册的第 1 和第 4 步无法按“门禁写入”执行）

| 编号 | 事项 | 说明 |
|---|---|---|
| D-A | AR-14 没有门禁入口 | 冻结的 `retire_unconsumed_authorization` 是库函数，没有命令行入口，也没有令牌/终端门禁。演练里用同一个函数在临时根上完成。选项：（1）接受下面第 1 步的“手工受控步骤”；（2）下一次 builder 修订里加一个带令牌的 `--retire-r10` 入口（builder SHA 会再变，批准记录要重新钉）。**建议（2）。** |
| D-B | Freeze 创建没有门禁入口 | builder 只有库函数 `persist_candidate`（`O_EXCL` + fsync）；r5c10ag 的批准范围只含“指针创建”和“验证已落盘 Freeze”。同样两个选项；**建议（2）**，与 D-A 合并成同一次 builder 修订。 |
| D-C | Freeze 的 `created_at_utc` | 批准记录钉住它；签发要求签发时间晚于它。重新生成草案时用 `--created-at` 指定，应取签批准记录的当天。 |

## 0. 起点检查（只读）

先记录账本的当前状态，AR-14 之后要对照：

```bash
wc -c evaluation/v1_2_3/authorization_lifecycle_events.jsonl; wc -l evaluation/v1_2_3/authorization_lifecycle_events.jsonl
shasum -a 256 evaluation/v1_2_3/authorization_lifecycle_events.jsonl
```

预期（本步结束时的真实值）：`3856` 字节，`3` 行，SHA-256 为 `aaa2e9898a8869db052a1248a0ca2b0574d9c36093aee608db59457f24c2a60e`。

```bash
.venv/bin/python -m scripts.build_step9_63c_r11_runner_freeze --status
```

预期（真实仓库当前输出）：

```json
{ "creation_record_present": false, "freeze_present": false, "pointer_canonical": false, "pointer_present": false,
  "r11_authorization_present": false, "registry_present": false, "state": "S0_NOT_ACTIVATED" }
```

```bash
.venv/bin/python -m scripts.issue_step9_63c_r11_authorization --status
```

预期：`"state": "NOT_ISSUED"`，退出码 0。

## 1. AR-14：退役 r10 授权（不可逆，向真实账本追加一行）

门禁：**无**（见 D-A）。如果选择第（1）种：

1. 新建判定文件 `evaluation/v1_2_3/step9_63c_r11_ar14_determination.json`，内容（冻结函数只检查前两个字段，其余是审计信息）：

```json
{
  "artifact_type": "V3_SUPERSEDED_AUTHORIZATION_NONREUSE_DETERMINATION",
  "step": "9.63c-r5c10ag",
  "old_authorization_id": "auth-step9_63c_r5c6-aff5c4b96bb74278a14d3fd08bf8a84e",
  "old_authorization_reuse_status": "PROVEN_NON_REUSABLE_BY_FROZEN_CONTRACT",
  "retirement_reason": "SUPERSEDED_BY_APPROVED_R11_ACTIVATION",
  "old_authorization_manifest_path": "evaluation/v1_2_3/step9_63c_r5c6_r10_v3_authorization_manifest.json",
  "old_authorization_manifest_sha256": "beac52d1ed3bc11efa02b1a924a8abc7b210171bf5cc1b7910011a6ef9741241",
  "authorization_consumed": false,
  "authorization_consumption_count": 0,
  "attempt_or_transaction_exists": false,
  "namespace_or_reservation_exists": false,
  "case_results_or_traces_exist": false,
  "current_runner_equality_required": false
}
```

2. 记下它的 SHA-256：`shasum -a 256 evaluation/v1_2_3/step9_63c_r11_ar14_determination.json`
3. 调用冻结函数（与演练中的调用完全相同；把 `<SHA>` 换成上一步的值）：

```bash
.venv/bin/python - <<'PY'
from pathlib import Path
from scripts import authorization_lifecycle as lc
root = Path.cwd()
d = root / "evaluation/v1_2_3/step9_63c_r11_ar14_determination.json"
import hashlib
sha = hashlib.sha256(d.read_bytes()).hexdigest()
print(lc.retire_unconsumed_authorization(
    authorization_path=root / "evaluation/v1_2_3/step9_63c_r5c6_r10_v3_authorization_manifest.json",
    expected_authorization_id="auth-step9_63c_r5c6-aff5c4b96bb74278a14d3fd08bf8a84e",
    run_root=root / "evaluation/v4_runs", ledger_path=root / "evaluation/v1_2_3/authorization_lifecycle_events.jsonl",
    lock_path=root / "evaluation/v4_runs/.namespace-allocation.lock",
    contract_path=root / "evaluation/v1_2_3/step9_61a_v3_authorization_lifecycle_contract.json",
    determination_path=d, determination_sha256=sha))
PY
```

回读检查（只读）：账本比第 0 步记录的**恰好多一行**，新增那一行的 `event_type` 是退役事件、`authorization_id` 是上面的 r10 ID，原有的 3856 字节逐字不变（前 1161 字节的钉住值同时保持）：

```bash
.venv/bin/python - <<'PY'
import hashlib, json
raw = open("evaluation/v1_2_3/authorization_lifecycle_events.jsonl","rb").read()
print("prefix ok:", hashlib.sha256(raw[:1161]).hexdigest() == "ca168f6939c4697a7a7bccc0b365b414d9a0e632f40de4242eb0a47e2d985285")
print("old bytes preserved:", hashlib.sha256(raw[:3856]).hexdigest() == "aaa2e9898a8869db052a1248a0ca2b0574d9c36093aee608db59457f24c2a60e")
print("total lines:", len(raw.decode().splitlines()))
print(raw[3856:].decode())
PY
```

预期：`prefix ok: True`，`old bytes preserved: True`，`total lines: 4`，最后打印出恰好一行新事件。

## 2. 重新生成并签署批准记录

AR-14 和判定文件改变了整仓哈希，所以现有草案**一定**过期。重新生成（只读命令，输出重定向到文件）：

```bash
.venv/bin/python -m scripts.build_step9_63c_r11_runner_freeze --print-approval-draft \
  --created-at "$(date -u +%Y-%m-%dT%H:%M:%S+00:00)" \
  --regression-result evaluation/v1_2_3/step9_63c_r5c10ag_regression_results.json \
  > evaluation/v1_2_3/step9_63c_r11_activation_approval.DRAFT.json
```

按 `step9_63c_r11_activation_approval_checklist.md` 逐项核对草案；确认后复制为正式记录并**手工**填三个字段：

```bash
cp evaluation/v1_2_3/step9_63c_r11_activation_approval.DRAFT.json evaluation/v1_2_3/step9_63c_r11_activation_approval.json
```

编辑 `step9_63c_r11_activation_approval.json`：`"status": "SIGNED"`，`"approver": "<你的名字>"`，`"signed_at_utc": "<当前 UTC ISO 时间>"`。除这三个字段外**不要**改任何内容（任何其他改动都会使某个钉住值失配，后面的步骤会拒绝）。

## 3. 创建指针（门禁写入）

```bash
.venv/bin/python -m scripts.build_step9_63c_r11_runner_freeze --plan
```

预期：退出码 0，`"ready": true`，`"canonical_size": 389`，`"canonical_sha256": "4e077781faeecee57da02f37d1d3ad8cdc9dfa895d3eb72b1b4ab1f1d3f696fe"`，`"confirmation_token": "CREATE-R11-POINTER-4e077781faee"`，所有 `PPn` 都是 `"ok": true`。任何 `false` 就停下。

```bash
.venv/bin/python -m scripts.build_step9_63c_r11_runner_freeze --create-pointer
```

终端会显示 `Type exactly CREATE-R11-POINTER-4e077781faee to proceed:`；**你自己输入**这串令牌并回车。预期输出：`"result": "CREATED"`，`"state": "S1_POINTER_ONLY"`，退出码 0。

回读检查：

```bash
.venv/bin/python -m scripts.build_step9_63c_r11_runner_freeze --verify
shasum -a 256 evaluation/v1_2_3/step9_63c_r11_current_runner_identity.json
wc -c evaluation/v1_2_3/step9_63c_r11_current_runner_identity.json
```

预期：`"ok": true`；SHA 是 `4e077781…f696fe`；大小 389。

如果中途被打断（指针在、创建记录不在）：重新运行 `--create-pointer` 会输出 `RECORD_COMPLETED`，不会改动指针。

## 4. 创建 r11 Freeze（门禁写入；见 D-B）

门禁：**无**（库函数 `persist_candidate`）。如果你选择第（1）种，在交互终端里：

```bash
.venv/bin/python - <<'PY'
import json
from pathlib import Path
from scripts import build_step9_63c_r11_runner_freeze as b
root = Path.cwd()
approval = b.load_approval(root)
assert b.verify_approval(root, approval, check_aggregate=False) == [], "approval no longer matches"
candidate = b.assemble_candidate(root, created_at_utc=approval["freeze"]["created_at_utc"])
print(b.persist_candidate(candidate, root))
PY
```

预期输出一行 SHA-256，**必须等于**批准记录里的 `freeze.predicted_sha256`。

回读检查：

```bash
.venv/bin/python -m scripts.build_step9_63c_r11_runner_freeze --verify-freeze
.venv/bin/python -m scripts.build_step9_63c_r11_runner_freeze --status
```

预期：`"ok": true` / `"state": "S2_FREEZE_PERSISTED"`。

## 5. 签发 r11 授权（门禁写入）

```bash
.venv/bin/python -m scripts.issue_step9_63c_r11_authorization --plan
```

预期：退出码 0，`"ready": true`，I0–I13 与 IX1 全部 `"ok": true`，并显示令牌（形如 `ISSUE-R11-AUTH-<12 位十六进制>`）和即将写入的授权清单预览。

```bash
.venv/bin/python -m scripts.issue_step9_63c_r11_authorization --issue
```

终端会打印清单全文和清单 SHA-256，然后提示 `Type exactly ISSUE-R11-AUTH-… to proceed:`；**你自己输入**令牌。预期：`"result": "ISSUED"`，`"state": "ISSUED_RECORDED"`，退出码 0。

回读检查：

```bash
.venv/bin/python -m scripts.issue_step9_63c_r11_authorization --verify
.venv/bin/python -m scripts.issue_step9_63c_r11_authorization --status
```

预期：`"ok": true`（V1–V5 全部通过：恰好一个匹配的账本事件、reducer 状态 `ISSUED_EXECUTABLE`、活动授权恰好一个且就是它、清单键集合等于 r10 模板、未消耗/无 attempt/无命名空间）；`"state": "ISSUED_RECORDED"`。

**失败后的恢复**（都只由你在交互终端执行，不会自动删除任何东西）：

| 状态（`--status`） | 含义 | 处理 |
|---|---|---|
| `ISSUED_UNRECORDED` | 清单已写入，账本事件没写成（磁盘满、断电等） | `--complete-record`：核对后输入 `COMPLETE-R11-ISSUANCE-RECORD-<12 位>` 补写事件 |
| `ANOMALY_EVENT_WITHOUT_MANIFEST` / `ANOMALY_DUPLICATE_EVENT` / `ANOMALY_EVENT_MISMATCH` / `ANOMALY_MANIFEST_NOT_A_REGULAR_FILE` | 人为篡改或严重故障 | 不要重试；保留现场，找我分析。账本是只追加的，不能“撤销”事件 |

## 6. 之后（本手册不包含）

preflight 与正式执行是另外的步骤，各自需要你的批准。签发之后 consumer 的预提交门会通过；`prepare_formal_gates` 在演练里返回空失败列表，且全程没有进入正式执行。
