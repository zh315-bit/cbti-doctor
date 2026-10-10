# r11 激活运行手册（Step 9.63c-r5c10ah）

**状态：草案。本步没有执行其中任何一步。** 它取代上一步的运行手册（那份有“照演练手工操作”的步骤，已删除）。

**每一步只调用对应的门禁入口，顺序固定：`--plan`（只读）→ 人工核对 → 写入入口 → `--verify`（只读）。** 没有任何手工拼凑的 Python、没有手工编辑账本、没有手工放文件（唯一的手工编辑是第 1 步给批准记录签名的三个字段）。

通用约定：

- 写入入口只能在**交互终端**里运行（Claude Code 内置 Terminal 面板就是；管道、脚本、CI、代理调用都会被拒绝，退出码 2）。令牌要你**亲手输入**。
- 工作目录 `/Volumes/Elements/cbti-doctor-main`，解释器 `.venv/bin/python`。生产环境**不要**设置 `CBTI_ALLOW_SYNTHETIC_ROOT`。
- 下文命令里 builder 简写为 `B`，签发器简写为 `I`：

```bash
B=".venv/bin/python -m scripts.build_step9_63c_r11_runner_freeze"
I=".venv/bin/python -m scripts.issue_step9_63c_r11_authorization"
```

- **停止点规则**：任何一步的“预期输出”不符、退出码不符、或出现 `REFUSED` / `POSTCONDITION_FAILED` / `ANOMALY_*`，**立刻停下**，不重试、不手工修补，把输出原样交给我。账本只追加，任何已经写入的字节都不能撤销，所以停下比继续更安全。
- 预期输出的**形状**来自临时根上的完整演练（`step9_63c_r5c10ah_e2e_gated_rehearsal_report.json` 逐条记录了真实输出）；令牌、哈希、ID、时间会不同。第 0 步里标明“真实仓库”的值是在真实仓库上实测的。

## 0. 起点检查（只读）

```bash
$B --status
$I --status
wc -c evaluation/v1_2_3/authorization_lifecycle_events.jsonl
shasum -a 256 evaluation/v1_2_3/authorization_lifecycle_events.jsonl
```

预期（真实仓库）：`"state": "S0_NOT_ACTIVATED"`；签发器 `"state": "NOT_ISSUED"`；账本 `3856` 字节，SHA-256 `aaa2e9898a8869db052a1248a0ca2b0574d9c36093aee608db59457f24c2a60e`。

**停止点**：任何不同 → 停（仓库已不是批准时的状态）。

## 1. 核对并签署批准记录（唯一的手工编辑）

1. 按 `step9_63c_r5c10ah_activation_approval_checklist.md` 逐项核对 `step9_63c_r11_activation_approval.DRAFT.json`。
2. （可选的独立核对）重新生成一份，比较 `repository_aggregate.sha256`（`approval_id` 和签发 ID 会不同，聚合哈希必须相同）：

```bash
$B --print-approval-draft --created-at "<草案里的 freeze.created_at_utc>" \
   --regression-result evaluation/v1_2_3/step9_63c_r5c10ah_regression_results.json | grep -A1 '"repository_aggregate"'
```

3. 复制并只改三个字段：

```bash
cp evaluation/v1_2_3/step9_63c_r11_activation_approval.DRAFT.json evaluation/v1_2_3/step9_63c_r11_activation_approval.json
```

编辑新文件：`"status": "SIGNED"`、`"approver": "<你的名字>"`、`"signed_at_utc": "<当前 UTC ISO 时间>"`。**其余任何字节都不要动。**

4. 立刻用只读入口确认签署有效（它会验证所有钉住的值）：

```bash
$B --plan-retire
```

预期：退出码 0，`"ready": true`，`RT1`–`RT7` 全部 `"ok": true`，并显示 `"confirmation_token": "RETIRE-R10-auth-step9_6-<批准记录 SHA 前 12 位>"` 以及将要追加的事件模板。

**停止点**：`ready` 为 false，或任何 `RT*` 为 false → 停。常见原因：`RT1`=签署缺字段或有人改了仓库；`RT3`=账本不是 3856 字节那份；`RT5`=判定文件被改动。

## 2. AR-14：退役 r10 授权（不可逆，向真实账本追加一行）

`--plan-retire` 已在上一步跑过；写入前**人工核对**它显示的事件模板：

| 字段 | 必须是 |
|---|---|
| `authorization_id` | `auth-step9_63c_r5c6-aff5c4b96bb74278a14d3fd08bf8a84e` |
| `event_type` / `final_status` | `AUTHORIZATION_RETIRED_UNCONSUMED_NON_REUSABLE` / `RETIRED_UNCONSUMED_NON_REUSABLE` |
| `authorization_manifest_sha256` | `beac52d1ed3bc11efa02b1a924a8abc7b210171bf5cc1b7910011a6ef9741241` |
| `reuse_determination_sha256` | 批准记录核对清单 E 节里的判定文件 SHA |
| `authorization_consumed` / `authorization_consumption_count` / `cases_started` | `false` / `0` / `0` |
| `terminal` | `true` |

```bash
$B --retire-r10
```

终端会重复令牌提示：`Type exactly RETIRE-R10-auth-step9_6-<12 位> to proceed:`，**你自己输入**并回车。预期输出末尾：

```json
{ "lifecycle_event_id": "retire-<32 位十六进制>", "result": "RETIRED", "state": "RETIRED_AS_APPROVED" }
```

退出码 0。然后：

```bash
$B --verify-retire
wc -c evaluation/v1_2_3/authorization_lifecycle_events.jsonl
```

预期：`"ok": true`，`"state": "RETIRED_AS_APPROVED"`，V1–V5 全部 true；账本比 3856 字节**恰好多一行**（`V2` 显示 `<N> bytes appended, 0 later line(s)`）。

**停止点**：
- 令牌被拒（`confirmation token mismatch`）→ 没有任何写入，可以重新运行。
- `refused by the frozen function` → 账本未变（入口已核对），停并报告原因。
- `POSTCONDITION_FAILED` → 账本可能已被追加但不符合批准的形状；**不要再运行 `--retire-r10`**，运行 `--verify-retire` 并把输出交给我。
- 再次运行 `--retire-r10` 会被 `RT3/RT4` 拒绝（账本已不是退役前那份），不会重复追加。

## 3. 创建身份指针（门禁写入）

```bash
$B --plan
```

预期：退出码 0，`"ready": true`，`"canonical_size": 389`，`"canonical_sha256": "4e077781faeecee57da02f37d1d3ad8cdc9dfa895d3eb72b1b4ab1f1d3f696fe"`，`"confirmation_token": "CREATE-R11-POINTER-4e077781faee"`，所有 `PP*` 为 true（其中 `PP4` 就是 AR-14 已完成）。

人工核对 `canonical_bytes` 就是你批准的 389 字节。然后：

```bash
$B --create-pointer
```

输入 `CREATE-R11-POINTER-4e077781faee`。预期：`"result": "CREATED"`，`"state": "S1_POINTER_ONLY"`。

```bash
$B --verify
shasum -a 256 evaluation/v1_2_3/step9_63c_r11_current_runner_identity.json
```

预期：`"ok": true`；SHA 为 `4e077781…f696fe`。

**停止点**：`--plan` 不就绪（尤其 `PP4`）→ 说明 AR-14 没有完成，不要继续；`POINTER_READBACK_MISMATCH` → 停并报告（不会自动删除）。中断后重跑 `--create-pointer` 只补创建记录（`RECORD_COMPLETED`），不动指针。

## 4. 创建 r11 Freeze（门禁写入）

```bash
$B --plan-freeze
```

预期：退出码 0，`"ready": true`，`FZ1`–`FZ7` 全部 true（`FZ5` = 现在组装出的 Freeze 等于批准的预测值），`"confirmation_token": "CREATE-R11-FREEZE-<预测 Freeze SHA 前 12 位>-<批准记录 SHA 前 12 位>"`。

人工核对：令牌第一段等于核对清单 F 节“预测的 Freeze SHA”的前 12 位。然后：

```bash
$B --create-freeze
```

输入令牌。预期：`"result": "CREATED"`，`"freeze_sha256"` **等于**批准记录里的预测值，`"state": "S2_FREEZE_PERSISTED"`。

```bash
$B --verify-freeze
$B --status
```

预期：`"ok": true`、`"reason": "ok"`；`"state": "S2_FREEZE_PERSISTED"`。

**停止点**：`FZ5` 失败（预测不符）→ 没有写入；停，说明成员字节在签署后变化。`FREEZE_SHA_MISMATCH` → 文件已落盘但 SHA 不等于预测：**不要签发**，不要删除，运行 `--verify-freeze` 与 `--status` 并报告，由你决定是否把文件移开并从修正后的批准记录重来。

## 5. 签发 r11 授权（门禁写入）

```bash
$I --plan
```

预期：退出码 0，`"ready": true`，`I0`–`I13`、`IX1` 全部 true，显示令牌 `ISSUE-R11-AUTH-<12 位>` 和清单预览。

```bash
$I --issue
```

终端打印清单全文和清单 SHA-256，然后提示令牌；**你自己输入**。写入前入口会证明：待写入的清单与重新生成的计划逐字节一致（除 `issued_at_utc`），否则 `MANIFEST_DIFFERS_FROM_PLAN` 并且什么都不写。预期：`"result": "ISSUED"`，`"state": "ISSUED_RECORDED"`。

```bash
$I --verify
$I --status
```

预期：`"ok": true`（V1–V5），`"state": "ISSUED_RECORDED"`。

**停止点与恢复**（都由你在交互终端执行）：

| `--status` 状态 | 含义 | 处理 |
|---|---|---|
| `ISSUED_UNRECORDED` | 清单已写、账本事件没写成 | `$I --complete-record`，输入 `COMPLETE-R11-ISSUANCE-RECORD-<12 位>` |
| `ANOMALY_*` | 篡改或严重故障 | 不要重试；保留现场，报告 |
| `MANIFEST_READBACK_MISMATCH` / `POSTCONDITION_FAILED` | 清单已落盘但未写事件 | 不要删除；报告 |

## 6. 之后（本手册不包含）

preflight 与正式执行是另外的步骤，各自需要你的批准。签发之后 consumer 的预提交门会通过（演练里 `prepare_formal_gates` 返回空失败列表，全程没有进入正式执行）。
