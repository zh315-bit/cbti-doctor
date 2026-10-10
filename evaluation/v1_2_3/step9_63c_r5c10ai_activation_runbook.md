# r11 激活运行手册（Step 9.63c-r5c10ai，最终版）

**状态：草案。本步没有执行其中任何一步。** 它取代 r5c10ah 的运行手册。

**每一步只调用对应的门禁入口：`--plan`（只读）→ 人工核对 → 写入入口 → `--verify`（只读）。** 唯一的手工编辑是第 3 步给批准记录签名的四个字段。

通用约定：

- 写入入口只能在**交互终端**里运行（管道、脚本、CI、代理调用都被拒绝，退出码 2）；令牌由你**亲手输入**。
- 工作目录 `/Volumes/Elements/cbti-doctor-main`；解释器 `.venv/bin/python`；**不要**设置 `CBTI_ALLOW_SYNTHETIC_ROOT`。
- 签署之后到激活结束之间**不要再 commit**：每个入口都会核对 Git HEAD 仍等于批准记录里的 `signed_at_commit`。
- **停止点规则**：任何一步的输出与“预期”不符、或出现 `REFUSED` / `POSTCONDITION_FAILED` / `ANOMALY_*`，立刻停下，不重试、不手工修补，把输出原样交给我。账本只追加，已写入的字节不能撤销。

```bash
B=".venv/bin/python -m scripts.build_step9_63c_r11_runner_freeze"
I=".venv/bin/python -m scripts.issue_step9_63c_r11_authorization"
```

## 0. 前置检查（两项，缺一不可）

1. 逐项完成 `step9_63c_r5c10ai_activation_approval_checklist.md`（每条命令输出都与期望相同）。
2. **commit**，使工作树干净：

```bash
git add -A
git commit -m "Final r11 activation package (r5c10ai)"
git status --short
```

预期：`git status --short` **没有任何输出**。**停止点**：有任何输出（未跟踪或已修改的文件）→ 停，不要签署。

（准备草案时 HEAD 是 `23994b21582641c653fd3ca777291a013d473a7d`；commit 之后 HEAD 会变成新的 SHA，那个新 SHA 就是 `signed_at_commit`。）

## 1. 起点检查（只读）

```bash
$B --status
$I --status
wc -c evaluation/v1_2_3/authorization_lifecycle_events.jsonl
shasum -a 256 evaluation/v1_2_3/authorization_lifecycle_events.jsonl
```

预期：`"state": "S0_NOT_ACTIVATED"`；`"state": "NOT_ISSUED"`；`3856` 字节；SHA-256 `aaa2e9898a8869db052a1248a0ca2b0574d9c36093aee608db59457f24c2a60e`。**停止点**：任何不同。

## 2. （可选）独立重新生成草案

```bash
$B --print-approval-draft --created-at "2026-10-10T13:10:38+00:00" --regression-result evaluation/v1_2_3/step9_63c_r5c10ai_regression_results.json | grep -A2 '"repository_aggregate"'
```

`sha256` 必须等于草案里的（`approval_id` 和签发 ID 会不同，聚合哈希必须相同）。

## 3. 签署（唯一的手工编辑）

```bash
cp evaluation/v1_2_3/step9_63c_r11_activation_approval.DRAFT.json evaluation/v1_2_3/step9_63c_r11_activation_approval.json
git rev-parse HEAD
```

编辑新文件 `step9_63c_r11_activation_approval.json`，**只改这四个字段**，其余任何字节都不要动：

| 字段 | 填写 |
|---|---|
| `status` | `SIGNED` |
| `approver` | 你的名字 |
| `signed_at_utc` | 当前 UTC 时间，ISO 格式（如 `2026-10-11T09:30:00+00:00`） |
| `signed_at_commit` | 上面 `git rev-parse HEAD` 输出的 40 位十六进制 |

（`content_sha256` 会核对“除这四个字段外与草案一致”，所以填错别的字段、或多一个空格都会被拒绝。）

立刻用只读入口确认签署有效：
```bash
$B --plan-retire
```

预期：退出码 0，`"ready": true`，`RT1`–`RT7` 全部 `"ok": true`，`"confirmation_token": "RETIRE-R10-aff5c4b96bb7-af433dc27b5d"`，并显示将要追加的事件模板。

**停止点**：`ready` 为 false。常见原因：`RT1`=四个字段以外被改动，或 HEAD 不等于 `signed_at_commit`（签署后又 commit 了）；`RT3`=账本不是退役前那份；`RT5`=判定文件被改动。

## 4. AR-14：退役 r10 授权（不可逆，向真实账本追加一行）

写入前人工核对 `--plan-retire` 显示的模板：`authorization_id` = `auth-step9_63c_r5c6-aff5c4b96bb74278a14d3fd08bf8a84e`；`authorization_manifest_sha256` = `beac52d1…1241`；`reuse_determination_sha256` = 核对清单第 6 节的判定文件 SHA；`authorization_consumed` false、`authorization_consumption_count` 0、`cases_started` 0；`terminal` true。

```bash
$B --retire-r10
```

终端提示 `Type exactly ... to proceed:`，**你自己输入** `RETIRE-R10-aff5c4b96bb7-af433dc27b5d` 并回车。预期末尾：`"result": "RETIRED"`，`"state": "RETIRED_AS_APPROVED"`，退出码 0。

```bash
$B --verify-retire
wc -c evaluation/v1_2_3/authorization_lifecycle_events.jsonl
```

预期：`"ok": true`，V1–V5 全部 true；账本比第 1 步的字节数大，且**恰好多一行**。

**停止点**：令牌被拒 → 没有写入，可重来；`refused by the frozen function` → 账本未变，停并报告；`POSTCONDITION_FAILED` → **不要再运行** `--retire-r10`，运行 `--verify-retire` 并把输出交给我；重复运行 `--retire-r10` 会被 `RT3/RT4` 拒绝。

## 5. 创建身份指针

```bash
$B --plan
```

预期：`"ready": true`（`PP4` 即 AR-14 已完成），`"canonical_size": 389`，`"canonical_sha256": "4e077781faeecee57da02f37d1d3ad8cdc9dfa895d3eb72b1b4ab1f1d3f696fe"`，`"confirmation_token": "CREATE-R11-POINTER-4e077781faee"`。

```bash
$B --create-pointer
```
输入 `CREATE-R11-POINTER-4e077781faee`。预期：`"result": "CREATED"`，`"state": "S1_POINTER_ONLY"`。

```bash
$B --verify
shasum -a 256 evaluation/v1_2_3/step9_63c_r11_current_runner_identity.json
```

预期：`"ok": true`；SHA `4e077781…f696fe`。**停止点**：`PP4` 失败=AR-14 没完成；`POINTER_READBACK_MISMATCH`；中断后重跑只补记录（`RECORD_COMPLETED`）。

## 6. 创建 r11 Freeze

```bash
$B --plan-freeze
```

预期：`"ready": true`，`FZ1`–`FZ7` 全部 true（`FZ5`=现在组装出的 Freeze 等于批准的预测），`"confirmation_token": "CREATE-R11-FREEZE-bafcec8d2ae0-af433dc27b5d"`。核对令牌第一段 `bafcec8d2ae0` 就是预测 Freeze SHA `bafcec8d2ae0bad6c3cb43e89bd49171b85374957ec6ce173071fef5248357b3` 的前 12 位。

```bash
$B --create-freeze
```
输入 `CREATE-R11-FREEZE-bafcec8d2ae0-af433dc27b5d`。预期：`"freeze_sha256"` = `bafcec8d2ae0bad6c3cb43e89bd49171b85374957ec6ce173071fef5248357b3`，`"state": "S2_FREEZE_PERSISTED"`。

```bash
$B --verify-freeze
$B --status
```

预期：`"ok": true`、`"reason": "ok"`；`"state": "S2_FREEZE_PERSISTED"`。**停止点**：`FZ5` 失败=成员字节在签署后变化，没有写入；`FREEZE_SHA_MISMATCH`=文件已落盘但 SHA 不等于预测——**不要签发**、不要删除，运行 `--verify-freeze` 与 `--status` 并报告。

## 7. 签发 r11 授权

```bash
$I --plan
```

预期：`"ready": true`，`I0`–`I13`、`IX1` 全部 true；显示令牌 `ISSUE-R11-AUTH-<12 位>`（由已签署文件字节派生，只能现在读出）和清单预览。清单里的 `authorization_id` 必须是 `auth-step9_63c_r11-1a399434ec0e4494b0045734846b2042`，`attempt_id` 是 `attempt-step9_63c_r11-2312daefa1364bfd83ff3948d101c765`。

```bash
$I --issue
```
输入 `--plan` 显示的令牌。写入前入口会证明待写清单与重新生成的计划逐字节一致（除 `issued_at_utc`），否则 `MANIFEST_DIFFERS_FROM_PLAN` 且什么都不写。预期：`"result": "ISSUED"`，`"state": "ISSUED_RECORDED"`。

```bash
$I --verify
$I --status
```

预期：`"ok": true`（V1–V5），`"state": "ISSUED_RECORDED"`。

| `--status` 状态 | 处理 |
|---|---|
| `ISSUED_UNRECORDED` | `$I --complete-record`，输入 `COMPLETE-R11-ISSUANCE-RECORD-<12 位>` |
| `ANOMALY_*` / `MANIFEST_READBACK_MISMATCH` / `POSTCONDITION_FAILED` | 不要重试、不要删除；保留现场，报告 |

## 8. 之后（本手册不包含）

preflight 与正式执行是另外的步骤，各自需要你的批准。签发之后 consumer 的预提交门会通过。

