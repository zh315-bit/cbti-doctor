import json, subprocess, sys, os
from pathlib import Path
d = json.load(open(sys.argv[1])); outdir = Path(sys.argv[2])
env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
def run(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, env=env, cwd=Path.cwd(), executable="/bin/zsh")
    return (r.stdout + r.stderr).strip()
PY = ".venv/bin/python"
DRAFT = "evaluation/v1_2_3/step9_63c_r11_activation_approval.DRAFT.json"
L = []; w = L.append
def item(title, cmd, note=""):
    out = run(cmd)
    w(f"- **{title}**" + (f"（{note}）" if note else ""))
    w(f"  - 命令：`{cmd}`")
    w("  - 期望输出：\n    ```\n" + "\n".join("    " + x for x in out.splitlines()) + "\n    ```")
    return out
w("# r11 激活批准记录逐项核对清单（r5c10ai，最终版，供你逐字核对）\n")
w(f"对应文件：`{DRAFT}`（**未签署**：`status` = `DRAFT_NOT_SIGNED`，`approver` / `signed_at_utc` / `signed_at_commit` 为 null）。它取代 r5c10ah 的草案、核对清单和运行手册。\n")
w("**使用方法**：在仓库根目录 `/Volumes/Elements/cbti-doctor-main` 的终端里，逐条运行下面的命令，输出必须与“期望输出”逐字相同。“期望输出”是我在本步结束时的仓库上实际运行同一条命令得到的。**全部一致才 commit、才签。**\n")
w("两个无法在本清单里写死的值（循环依赖：整仓聚合哈希覆盖本清单文件，草案的 SHA 又包含该哈希）：整仓聚合哈希和草案文件自己的 SHA-256。对前者给出的是“重新计算的值必须等于草案里记录的值”的比较命令；两者的具体值写在我交给你的最终说明里。\n")
w("## 1. 仓库状态与归档提交\n")
item("归档提交 201ef5c 存在且是提交对象", "git cat-file -t 201ef5c2d406b0eaf2ebf5ce12db912b3caf5762")
item("归档提交是当前 HEAD 的祖先（退出码 0）", "git merge-base --is-ancestor 201ef5c2d406b0eaf2ebf5ce12db912b3caf5762 HEAD; echo $?")
w("- **commit 之后工作树必须干净**：`git status --short` → 期望输出：空（无任何输出）。现在它**不是**空的（本步的改动还没提交），这正是你要先 commit 的原因。")
w("- **签署时的提交**：`git rev-parse HEAD` → 就是你要填进批准记录 `signed_at_commit` 的 40 位十六进制；签署之后任何门禁入口都会核对 HEAD 仍等于它。\n")
w("## 2. 指针\n")
item("规范字节长度与 SHA-256", f"{PY} -c \"from scripts import build_step9_63c_r11_runner_freeze as b; import hashlib; x=b.canonical_pointer_bytes(); print(len(x), hashlib.sha256(x).hexdigest())\"", "你批准的 389 字节")
w("## 3. 命名文件\n")
for k, v in d["named_pins"].items(): item(f"{k}：`{v['path']}`", f"shasum -a 256 {v['path']}")
w("本步的预期：resolver、consumer、issuer、scanner、producer 都**未变**；**builder 是唯一变化的文件**。\n")
w("## 4. r11 的 20 个成员\n")
un = d["unchanged_members"]
for i, (path, sha) in enumerate(d["members"].items(), 1):
    if path.endswith("current_runner_identity.json"):
        item(f"#{i} 指针（尚不存在，钉的是规范字节）", f"{PY} -c \"from scripts import build_step9_63c_r11_runner_freeze as b; print(b.POINTER_SHA256)\"")
    else:
        item(f"#{i} `{path}`", f"shasum -a 256 {path}", "与 r10 逐字相同" if path in un else "新增/替换/已批准的变更")
w(f"\n与 r10 逐字相同的成员共 **{len(un)}** 个（统一口径 13）。\n")
w("## 5. 历史钉与账本（AR-14 的起点）\n")
h = d["historical"]
item("r10 Freeze 清单", f"shasum -a 256 {h['r10_freeze_manifest']['path']}")
item("r10 授权清单", f"shasum -a 256 {h['r10_authorization_manifest']['path']}")
lp = h["lifecycle_ledger_prefix"]; pre = d["ar14"]["pre_retirement_ledger"]
item("账本冻结前缀（前 1161 字节）", f"head -c {lp['length']} {lp['path']} | shasum -a 256")
item("**退役前账本**字节数（写入前必须逐字相等）", f"wc -c < {pre['path']}")
item("**退役前账本** SHA-256", f"shasum -a 256 {pre['path']}")
w("## 6. AR-14\n"); a = d["ar14"]; det = a["determination"]
item("待退役的 r10 授权 ID", f"python3 -c \"import json;print(json.load(open('{h['r10_authorization_manifest']['path']}'))['authorization_id'])\"")
item("不可重用判定文件（已在仓库中）", f"shasum -a 256 {det['path']}")
item("判定文件引用的 approval_id 等于草案的 approval_id", f"python3 -c \"import json;print(json.load(open('{det['path']}'))['approval_id']); print(json.load(open('{DRAFT}'))['approval_id'])\"", "两行相同")
item("预期追加事件模板的 SHA-256", f"python3 -c \"import json,hashlib;d=json.load(open('{DRAFT}'));print(hashlib.sha256(json.dumps(d['ar14']['expected_retirement_event_template'],sort_keys=True,ensure_ascii=False).encode()).hexdigest())\"")
w("\n**AR-14 之后的预期账本**：不能钉成整个文件的 SHA（事件里的 `lifecycle_event_id` 与 `timestamp_utc` 由冻结函数在调用时生成）。按你的决定 5，验证方式是：模板 + 原前缀逐字节不变 + 恰好多一行。预期追加行的规范字节（`sort_keys`、`ensure_ascii=False`、单个换行结尾；两个生成字段是变量，两个路径字段在生产根下是绝对路径）：\n")
t = dict(a["expected_retirement_event_template"]); t["reuse_determination"] = "/Volumes/Elements/cbti-doctor-main/" + t["reuse_determination"]; t["lifecycle_contract_path"] = "/Volumes/Elements/cbti-doctor-main/" + t["lifecycle_contract_path"]
t["lifecycle_event_id"] = "retire-<32 位十六进制>"; t["timestamp_utc"] = "<ISO 时间，晚于账本里所有已有事件>"
w("```json\n" + json.dumps(t, sort_keys=True, ensure_ascii=False) + "\n```\n")
w("## 7. 回归、聚合、预测的 Freeze\n"); r = d["regression"]; f = d["freeze"]
item("回归结果文件 SHA-256", f"shasum -a 256 {r['result_path']}")
w(f"- **整仓聚合哈希**（稳定口径，排除各门禁步骤的产物与批准记录）：\n  - 命令（重新计算）：`{PY} -c \"from scripts import build_step9_63c_r11_runner_freeze as b; a=b.stable_aggregate(b.ROOT); print(a['sha256'], a['files'])\"`\n  - 命令（草案中的值）：`python3 -c \"import json;a=json.load(open('{DRAFT}'))['repository_aggregate'];print(a['sha256'], a['files'])\"`\n  - 期望：两条命令的输出**逐字相同**（具体值见最终说明）。\n")
item("预测的 Freeze（`created_at_utc`、SHA-256、长度）", f"{PY} -c \"from scripts import build_step9_63c_r11_runner_freeze as b; import json; print(json.dumps(b.predict_freeze(b.ROOT, '{f['created_at_utc']}'), sort_keys=True))\"")
w("## 8. 签发身份、内容哈希、令牌\n"); iss = d["issuance"]
item("namespace_id 可由另外三个 ID 独立推出", f"{PY} -c \"from scripts.v3_namespace_allocator import derive_namespace_id as g; print(g('{iss['evaluation_id']}','{iss['authorization_id']}','{iss['attempt_id']}'))\"")
w(f"  - 草案里记录的身份：authorization `{iss['authorization_id']}`；attempt `{iss['attempt_id']}`；evaluation `{iss['evaluation_id']}`。\n")
item("批准记录内容哈希（签名字段置空后的 SHA-256）", f"{PY} -c \"import json; from scripts import build_step9_63c_r11_runner_freeze as b; d=json.load(open('{DRAFT}')); print(b.approval_content_sha256(d)); print(d['content_sha256'])\"", "两行相同；签署只改四个签名字段，所以签署前后这个值不变，令牌因此现在就能写全")
tk = d["tokens"]
w("\n**三个写入入口的令牌（完整具体值，签署前后不变）：**\n")
w("| 入口 | 令牌 |\n|---|---|")
w(f"| `--retire-r10`（AR-14） | `{tk['retire_r10']['value']}` |")
w(f"| `--create-pointer` | `{tk['create_pointer']['value']}` |")
w(f"| `--create-freeze` | `{tk['create_freeze']['value']}` |")
w("\n（签发入口 `issue_step9_63c_r11_authorization --issue` 的令牌 `ISSUE-R11-AUTH-<12 位>` 由已签署文件的字节派生，签发器不允许改，所以要等签署后由 `--plan` 显示；它不能提前写全。）\n")
item("退役令牌的构成可复算", f"{PY} -c \"import json; from scripts import build_step9_63c_r11_runner_freeze as b; d=json.load(open('{DRAFT}')); print(b.retire_token(d['content_sha256'])); print(b.freeze_token(d['freeze']['predicted_sha256'], d['content_sha256'])); print(b.POINTER_TOKEN)\"")
w("\n## 9. 已接受的例外（AR-15）\n")
item("批准记录里的 accepted_exceptions", f"python3 -c \"import json;e=json.load(open('{DRAFT}'))['accepted_exceptions'];print(e[0]['id']);print(e[0]['state']);print(e[0]['text'])\"", "签署即表示接受")
w("\n## 10. 签署前自问\n")
for t_ in ("上面每条命令的输出都与期望逐字相同。", "我接受 AR-15 的例外说明。", "我接受回归结果文件里的已知失败（RC5、RC6）和 33 个等待 r11 身份的 RC1 项。",
           "我接受“AR-14 之后账本”的验证方式（模板 + 原前缀不变 + 恰好多一行）。", "我已 commit，`git status --short` 为空，且这个 commit 包含草案、判定文件、清单和运行手册。"):
    w(f"- [ ] {t_}")
(outdir / "step9_63c_r5c10ai_activation_approval_checklist.md").write_text("\n".join(L) + "\n")

# ---------------- runbook
R = []; x = R.append
head = d["commit_pin"]["head_when_prepared"]
x("# r11 激活运行手册（Step 9.63c-r5c10ai，最终版）\n")
x("**状态：草案。本步没有执行其中任何一步。** 它取代 r5c10ah 的运行手册。\n")
x("**每一步只调用对应的门禁入口：`--plan`（只读）→ 人工核对 → 写入入口 → `--verify`（只读）。** 唯一的手工编辑是第 3 步给批准记录签名的四个字段。\n")
x("通用约定：\n")
x("- 写入入口只能在**交互终端**里运行（管道、脚本、CI、代理调用都被拒绝，退出码 2）；令牌由你**亲手输入**。\n- 工作目录 `/Volumes/Elements/cbti-doctor-main`；解释器 `.venv/bin/python`；**不要**设置 `CBTI_ALLOW_SYNTHETIC_ROOT`。\n- 签署之后到激活结束之间**不要再 commit**：每个入口都会核对 Git HEAD 仍等于批准记录里的 `signed_at_commit`。\n- **停止点规则**：任何一步的输出与“预期”不符、或出现 `REFUSED` / `POSTCONDITION_FAILED` / `ANOMALY_*`，立刻停下，不重试、不手工修补，把输出原样交给我。账本只追加，已写入的字节不能撤销。\n")
x("```bash\nB=\".venv/bin/python -m scripts.build_step9_63c_r11_runner_freeze\"\nI=\".venv/bin/python -m scripts.issue_step9_63c_r11_authorization\"\n```\n")
x("## 0. 前置检查（两项，缺一不可）\n")
x("1. 逐项完成 `step9_63c_r5c10ai_activation_approval_checklist.md`（每条命令输出都与期望相同）。\n2. **commit**，使工作树干净：\n")
x("```bash\ngit add -A\ngit commit -m \"Final r11 activation package (r5c10ai)\"\ngit status --short\n```\n")
x("预期：`git status --short` **没有任何输出**。**停止点**：有任何输出（未跟踪或已修改的文件）→ 停，不要签署。\n")
x(f"（准备草案时 HEAD 是 `{head}`；commit 之后 HEAD 会变成新的 SHA，那个新 SHA 就是 `signed_at_commit`。）\n")
x("## 1. 起点检查（只读）\n")
x("```bash\n$B --status\n$I --status\nwc -c evaluation/v1_2_3/authorization_lifecycle_events.jsonl\nshasum -a 256 evaluation/v1_2_3/authorization_lifecycle_events.jsonl\n```\n")
x(f"预期：`\"state\": \"S0_NOT_ACTIVATED\"`；`\"state\": \"NOT_ISSUED\"`；`{pre['size']}` 字节；SHA-256 `{pre['sha256']}`。**停止点**：任何不同。\n")
x("## 2. （可选）独立重新生成草案\n")
x(f"```bash\n$B --print-approval-draft --created-at \"{f['created_at_utc']}\" --regression-result {r['result_path']} | grep -A2 '\"repository_aggregate\"'\n```\n")
x("`sha256` 必须等于草案里的（`approval_id` 和签发 ID 会不同，聚合哈希必须相同）。\n")
x("## 3. 签署（唯一的手工编辑）\n")
x("```bash\ncp evaluation/v1_2_3/step9_63c_r11_activation_approval.DRAFT.json evaluation/v1_2_3/step9_63c_r11_activation_approval.json\ngit rev-parse HEAD\n```\n")
x("编辑新文件 `step9_63c_r11_activation_approval.json`，**只改这四个字段**，其余任何字节都不要动：\n")
x("| 字段 | 填写 |\n|---|---|\n| `status` | `SIGNED` |\n| `approver` | 你的名字 |\n| `signed_at_utc` | 当前 UTC 时间，ISO 格式（如 `2026-10-11T09:30:00+00:00`） |\n| `signed_at_commit` | 上面 `git rev-parse HEAD` 输出的 40 位十六进制 |\n")
x("（`content_sha256` 会核对“除这四个字段外与草案一致”，所以填错别的字段、或多一个空格都会被拒绝。）\n")
x("立刻用只读入口确认签署有效：\n```bash\n$B --plan-retire\n```\n")
x(f"预期：退出码 0，`\"ready\": true`，`RT1`–`RT7` 全部 `\"ok\": true`，`\"confirmation_token\": \"{tk['retire_r10']['value']}\"`，并显示将要追加的事件模板。\n")
x("**停止点**：`ready` 为 false。常见原因：`RT1`=四个字段以外被改动，或 HEAD 不等于 `signed_at_commit`（签署后又 commit 了）；`RT3`=账本不是退役前那份；`RT5`=判定文件被改动。\n")
x("## 4. AR-14：退役 r10 授权（不可逆，向真实账本追加一行）\n")
x("写入前人工核对 `--plan-retire` 显示的模板：`authorization_id` = `auth-step9_63c_r5c6-aff5c4b96bb74278a14d3fd08bf8a84e`；`authorization_manifest_sha256` = `beac52d1…1241`；`reuse_determination_sha256` = 核对清单第 6 节的判定文件 SHA；`authorization_consumed` false、`authorization_consumption_count` 0、`cases_started` 0；`terminal` true。\n")
x("```bash\n$B --retire-r10\n```\n")
x(f"终端提示 `Type exactly ... to proceed:`，**你自己输入** `{tk['retire_r10']['value']}` 并回车。预期末尾：`\"result\": \"RETIRED\"`，`\"state\": \"RETIRED_AS_APPROVED\"`，退出码 0。\n")
x("```bash\n$B --verify-retire\nwc -c evaluation/v1_2_3/authorization_lifecycle_events.jsonl\n```\n")
x("预期：`\"ok\": true`，V1–V5 全部 true；账本比第 1 步的字节数大，且**恰好多一行**。\n")
x("**停止点**：令牌被拒 → 没有写入，可重来；`refused by the frozen function` → 账本未变，停并报告；`POSTCONDITION_FAILED` → **不要再运行** `--retire-r10`，运行 `--verify-retire` 并把输出交给我；重复运行 `--retire-r10` 会被 `RT3/RT4` 拒绝。\n")
x("## 5. 创建身份指针\n")
x("```bash\n$B --plan\n```\n")
x(f"预期：`\"ready\": true`（`PP4` 即 AR-14 已完成），`\"canonical_size\": 389`，`\"canonical_sha256\": \"4e077781faeecee57da02f37d1d3ad8cdc9dfa895d3eb72b1b4ab1f1d3f696fe\"`，`\"confirmation_token\": \"{tk['create_pointer']['value']}\"`。\n")
x(f"```bash\n$B --create-pointer\n```\n输入 `{tk['create_pointer']['value']}`。预期：`\"result\": \"CREATED\"`，`\"state\": \"S1_POINTER_ONLY\"`。\n")
x("```bash\n$B --verify\nshasum -a 256 evaluation/v1_2_3/step9_63c_r11_current_runner_identity.json\n```\n")
x("预期：`\"ok\": true`；SHA `4e077781…f696fe`。**停止点**：`PP4` 失败=AR-14 没完成；`POINTER_READBACK_MISMATCH`；中断后重跑只补记录（`RECORD_COMPLETED`）。\n")
x("## 6. 创建 r11 Freeze\n")
x("```bash\n$B --plan-freeze\n```\n")
x(f"预期：`\"ready\": true`，`FZ1`–`FZ7` 全部 true（`FZ5`=现在组装出的 Freeze 等于批准的预测），`\"confirmation_token\": \"{tk['create_freeze']['value']}\"`。核对令牌第一段 `{f['predicted_sha256'][:12]}` 就是预测 Freeze SHA `{f['predicted_sha256']}` 的前 12 位。\n")
x(f"```bash\n$B --create-freeze\n```\n输入 `{tk['create_freeze']['value']}`。预期：`\"freeze_sha256\"` = `{f['predicted_sha256']}`，`\"state\": \"S2_FREEZE_PERSISTED\"`。\n")
x("```bash\n$B --verify-freeze\n$B --status\n```\n")
x("预期：`\"ok\": true`、`\"reason\": \"ok\"`；`\"state\": \"S2_FREEZE_PERSISTED\"`。**停止点**：`FZ5` 失败=成员字节在签署后变化，没有写入；`FREEZE_SHA_MISMATCH`=文件已落盘但 SHA 不等于预测——**不要签发**、不要删除，运行 `--verify-freeze` 与 `--status` 并报告。\n")
x("## 7. 签发 r11 授权\n")
x("```bash\n$I --plan\n```\n")
x(f"预期：`\"ready\": true`，`I0`–`I13`、`IX1` 全部 true；显示令牌 `ISSUE-R11-AUTH-<12 位>`（由已签署文件字节派生，只能现在读出）和清单预览。清单里的 `authorization_id` 必须是 `{iss['authorization_id']}`，`attempt_id` 是 `{iss['attempt_id']}`。\n")
x("```bash\n$I --issue\n```\n输入 `--plan` 显示的令牌。写入前入口会证明待写清单与重新生成的计划逐字节一致（除 `issued_at_utc`），否则 `MANIFEST_DIFFERS_FROM_PLAN` 且什么都不写。预期：`\"result\": \"ISSUED\"`，`\"state\": \"ISSUED_RECORDED\"`。\n")
x("```bash\n$I --verify\n$I --status\n```\n")
x("预期：`\"ok\": true`（V1–V5），`\"state\": \"ISSUED_RECORDED\"`。\n")
x("| `--status` 状态 | 处理 |\n|---|---|\n| `ISSUED_UNRECORDED` | `$I --complete-record`，输入 `COMPLETE-R11-ISSUANCE-RECORD-<12 位>` |\n| `ANOMALY_*` / `MANIFEST_READBACK_MISMATCH` / `POSTCONDITION_FAILED` | 不要重试、不要删除；保留现场，报告 |\n")
x("## 8. 之后（本手册不包含）\n")
x("preflight 与正式执行是另外的步骤，各自需要你的批准。签发之后 consumer 的预提交门会通过。\n")
(outdir / "step9_63c_r5c10ai_activation_runbook.md").write_text("\n".join(R) + "\n")
print("docs ok", len(L), len(R))
