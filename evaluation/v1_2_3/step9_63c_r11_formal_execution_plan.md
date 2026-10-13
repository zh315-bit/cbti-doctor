# r11 正式执行计划（Step 9.63c-r11 formal execution）

**状态：只是计划，没有执行。** 编写本计划时没有调用 `execute_formal`，没有消费授权，没有创建命名空间、attempt 或事务。所有“期望输出”都在 HEAD `c944ed4` 上用只读方式实测过（guard v3 + 会话级硬防护下运行，guard 零事件，真实状态前后一致）。

| 项 | 值 |
|---|---|
| 授权 | `auth-step9_63c_r11-1a399434ec0e4494b0045734846b2042`，清单 SHA `33bd99b9f7fba0bde0fc6a40d0c6a3b570b9f59d1e4c0158c1d4b5e8d82f5ea1`，签发于 `2026-10-10T21:20:49Z` |
| attempt | `attempt-step9_63c_r11-2312daefa1364bfd83ff3948d101c765` |
| evaluation | `heldout-v4-step9_55a-treatment-v3-20260930-01`（40 个案例，四类各 10 个） |
| 命名空间 | `evaluation/v4_runs/heldout-v4-treatment-v3-run-9ec9c305cc4de01e6538`（现在不存在） |
| preflight | `preflight-step9_63c_r5-r11-b0b5945a808f4b57a74f3c34d2e293fe`，证据 SHA `042760d1833424665e9593309a7a4c3b32d071892fda4eabae209cb20add8cca` |
| Freeze / 指针 | `bafcec8d…57b3` / `4e077781…96fe` |

## 0. 最重要的三件事

1. **授权从事务日志的第一行起就作废，而不是从第一个案例起。** adapter 先在 `evaluation/v4_runs/.execution_transactions/<授权>.jsonl` 里连续写 `PREPARED → COMMITTING → COMMITTED`（毫秒级），`COMMITTED` 就是不可逆的消耗点；此后才预留命名空间、跑案例。哪怕只写了 `PREPARED`，reducer 也会判为 `INCONSISTENT_FAIL_CLOSED`，授权不能再执行。**之后发生的任何中断都会让授权作废，没有续跑。**
2. **单个案例的任何 API 错误都会终止整次运行。** Flask 应用以 `PROPAGATE_EXCEPTIONS=True` 运行，模型客户端 `timeout=120`、`max_retries=1`：一次请求失败会自动重试一次，第二次仍失败就抛出异常，整次 attempt 记为 `FAILED_AFTER_PARTIAL_EXECUTION`。**上一次 v3 尝试（Step 9.56，同一个 treatment agent `085d338e…`）就是在第 1 个案例因 `APIConnectionError` 作废的。**
3. **`--preflight-file` 必须写绝对路径。** consumer 内部用 `preflight_file.relative_to(ROOT)`，相对路径会抛 `ValueError`。这一步发生在任何写入之前，所以写错只会 fail-closed 退出、不消耗授权；但下面的命令一律用绝对路径。

## 1. 执行命令（由你本人在终端运行）

前提：第 3 节的检查清单全部符合。在 `/Volumes/Elements/cbti-doctor-main`、接上电源、合盖前确认不会睡眠：

```bash
cd /Volumes/Elements/cbti-doctor-main
unset PYTHONPATH CBTI_ALLOW_SYNTHETIC_ROOT CBTI_GUARD_ROOT CBTI_GUARD_LOG CBTI_SESSION_GUARD_INSTALLED
caffeinate -dims env PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/run_step9_63_v3_formal_execution.py \
  --execute-formal-v4 \
  --evaluation-id heldout-v4-step9_55a-treatment-v3-20260930-01 \
  --authorization-id auth-step9_63c_r11-1a399434ec0e4494b0045734846b2042 \
  --attempt-id attempt-step9_63c_r11-2312daefa1364bfd83ff3948d101c765 \
  --authorization-file /Volumes/Elements/cbti-doctor-main/evaluation/v1_2_3/step9_63c_r11_v3_authorization_manifest.json \
  --preflight-file /Volumes/Elements/cbti-doctor-main/evaluation/v1_2_3/step9_63c_r5_auth-step9_63c_r11-1a399434ec0e4494b0045734846b2042_preflight-step9_63c_r5-r11-b0b5945a808f4b57a74f3c34d2e293fe_mac_local_preclearance.json \
  --preflight-id preflight-step9_63c_r5-r11-b0b5945a808f4b57a74f3c34d2e293fe \
  --preflight-sha256 042760d1833424665e9593309a7a4c3b32d071892fda4eabae209cb20add8cca \
  --treatment-agent-sha256 085d338ed95bbef7370c41cf97ca0d6653ffdfd2f1c924eef4b7123dfdea4607 \
  --benchmark-sha256 8b8c72092fcd7544e69d5d2ecd13610c7bb4c14210fca330698b3e5ab3f01d7f \
  --harness-sha256 8bc271bebc1c5da5351d517e2bb4a0d1a99fda3de1b713a6197b12f81fad70c7 \
  --scoring-sha256 f742a8f8af7c8747818dadad81621c15d12d74f50538019913dfe18ab53bf59b \
  --metric-registry-sha256 de9f348cb1dff66410c03095abdaffcc256f53679718482870e4aa4d80c75056 \
  --one-shot-rules-sha256 1c7ed4ef47865b117bc943f3e0ad9a859f4f74cfb4e8001f723ac5532af140d0 \
  --matched-protocol-sha256 a71ba06090370b576fbba66bc4b005e519ddbabff3021a40c6546fc855f90265 \
  2>&1 | tee /tmp/r11_formal_console.log; echo "exit=${pipestatus[1]}"
```

说明：
- `caffeinate -dims` 在命令运行期间阻止显示器、空闲、磁盘和（接电源时的）系统睡眠；它会以原样的 `.venv/bin/python` 启动 consumer，`python_runtime_match` 不受影响。**合盖仍会睡眠**，运行期间不要合盖。
- `PYTHONDONTWRITEBYTECODE=1` 避免在仓库里写 `__pycache__`，让白名单核对保持干净。
- 不要加 `-I`（会忽略 `.env` 和项目导入）；不要设置 `PYTHONPATH`（guard v3）。
- `echo "exit=${pipestatus[1]}"` 是 zsh 写法（取 tee 前面那条命令的退出码）。
- **运行期间不打印进度**。成功时没有任何输出、`exit=0`；失败时打印 Python traceback、`exit=1`。看进度请在另一个终端标签运行（只读）：

```bash
grep -c CASE_COMPLETED evaluation/v4_runs/heldout-v4-treatment-v3-run-9ec9c305cc4de01e6538/heldout-v4-step9_55a-treatment-v3-20260930-01/attempts.jsonl
```

## 2. 防护方案

### 2.1 为什么 guard v3 和 session_safety 都不能用

| 防护 | 结论 | 原因 |
|---|---|---|
| guard v3 | **不能用** | 它拦截子进程和网络相关调用（preflight 时已实测拦下 `dscacheutil`），并拦截仓库内写入。在执行中被拦截 = 异常 = 授权作废。 |
| `tests/session_safety.py` | **不适用** | 它的保护对象正是 `evaluation/v4_runs/` 整棵树和锁文件；执行的第一个写入（打开 `.namespace-allocation.lock`）就会触发 `os._exit(86)`。如果发生在 `COMMITTED` 之后，授权作废且没有 `FAILED` 记录。改它的保护列表需要改测试设施代码，本计划不做。 |

所以执行期间**不加进程内防护**，安全性来自：consumer 自身的门禁（2.2）、执行前后的整仓快照与白名单比对（2.3）、以及事务日志的 fail-closed 设计。

### 2.2 consumer 自身的检查（全部在第一个写入之前，只读）

1. `prepare_formal_gates`：当前 Freeze、consumer 自身 SHA 与 Freeze 一致；授权与 preflight 绑定当前 runner；preflight 证据（路径、SHA、身份、连通性、晚于签发时间）；r11 producer 与调用记录的来源证明（`verify_registry_evidence`）；7 个冻结哈希参数齐全。
2. `collect_r11_precommit_state` 的 25 项预提交检查 + 签发事件交叉核对（见第 3 节 C5 的期望输出），任何一项失败或没执行都 fail-closed。
3. adapter `run()` 再验证一次冻结身份与授权；`begin_and_commit` 在锁内**再验证一次**，并检查命名空间、预留标记、attempt 账本、其他事务日志里都没有本授权/attempt/命名空间。
4. 父 runner 在认领 attempt、建目录、读案例前后又各验证一次；案例集合与顺序必须等于冻结指纹。
5. 每个案例开始前写 `CASE_STARTED`，重复的案例编号或案例 ID 会被拒绝（禁止重跑）。

### 2.3 允许写入的路径白名单

| 路径（相对仓库根） | 操作 |
|---|---|
| `evaluation/v4_runs/.namespace-allocation.lock` | 已存在；以读写方式打开并加锁（内容不变） |
| `evaluation/v4_runs/.execution_transactions/auth-step9_63c_r11-1a399434ec0e4494b0045734846b2042.jsonl` | 新建，只追加：`PREPARED`、`COMMITTING`、`COMMITTED`、`ATTEMPT_CLAIMED`、40 × `CASE_STARTED`，共 44 行 |
| `evaluation/v4_runs/heldout-v4-treatment-v3-run-9ec9c305cc4de01e6538/` | 新建目录 |
| `…/.namespace_allocation.json` | 新建，命名空间预留标记 |
| `…/heldout-v4-step9_55a-treatment-v3-20260930-01/` | 新建目录 |
| `…/heldout-v4-step9_55a-treatment-v3-20260930-01/attempts.jsonl` | 新建，只追加，成功时 86 行 |
| `…/attempt-step9_63c_r11-2312daefa1364bfd83ff3948d101c765_raw_traces.jsonl` | 新建，40 行 |
| `…/attempt-step9_63c_r11-2312daefa1364bfd83ff3948d101c765_case_results.jsonl` | 新建，40 行 |
| 以上新文件的 `._*` AppleDouble 伴随文件 | 移动硬盘文件系统自动生成 |

**不会写**：授权生命周期账本（只有退役函数写它，执行路径不调用）、r11 授权清单（消费状态由 reducer 从事务日志推导，清单字节不变）、Freeze、指针、preflight 证据与调用记录、RAG 索引（`rag_lib/.rag_db/…` 已存在，只读加载）、本地 embedding 模型（`local_files_only=True`）。仓库外：DeepSeek API 网络流量；`/tmp/r11_formal_console.log`。

白名单核对工具：`evaluation/v1_2_3/step9_63c_r11_formal_tools/whitelist_check.py`（只读；快照只能写到仓库外）。它把整个仓库（除 `.git`、`.venv`）逐文件哈希，运行后列出所有新增、删除、变化的路径，并判断是否都在白名单内。已做负向自检：改账本、改 README、新增非白名单文件都会报 `ok: false`。

## 3. 运行前只读检查清单

全部在 `/Volumes/Elements/cbti-doctor-main` 下执行。任何一项不符 → **不要运行**，把输出发给我。

**C1 仓库与 HEAD**

计划和两个工具文件需要先提交（它们不是冻结成员，门禁不检查 HEAD，只检查成员字节）。提交后：

```bash
git status --porcelain
```

期望：空输出。

```bash
git diff --name-only c944ed4 HEAD
```

期望恰好三行：`evaluation/v1_2_3/step9_63c_r11_formal_execution_plan.md`、`evaluation/v1_2_3/step9_63c_r11_formal_tools/verify_after.py`、`evaluation/v1_2_3/step9_63c_r11_formal_tools/whitelist_check.py`。（若你选择不提交计划，则期望 `git rev-parse HEAD` = `c944ed4…`，`git status --porcelain` 只列出这三个未跟踪文件。）

**C2 执行路径成员字节**

```bash
shasum -a 256 scripts/run_step9_63_v3_formal_execution.py scripts/run_step9_53_v3_identity_adapter.py scripts/run_step9_35a_matched_treatment.py scripts/v3_execution_transaction.py scripts/v3_namespace_allocator.py scripts/authorization_lifecycle.py evaluation/v1_2_3/step9_63c_r11_runner_freeze.json evaluation/v1_2_3/step9_63c_r11_current_runner_identity.json evaluation/v1_2_3/step9_63c_r11_v3_authorization_manifest.json
```

期望（依次）：`362eb446…9528`、`3a4ec3e5…0da282`、`b79bc78a…776508`、`f0e74a49…690e91`、`3ee484e5…385bc5`、`f0d8b7e0…612744`、`bafcec8d…57b3`、`4e077781…96fe`、`33bd99b9…5ea1`。

**C3 真实激活状态**

```bash
.venv/bin/python evaluation/v1_2_3/step9_63c_r11_formal_tools/verify_after.py
```

期望：`transaction_journal`、`attempt_ledger`、`raw_traces`、`case_results`、`namespace_marker` 都是 `"ABSENT"`，`namespace_dir_exists: false`；`lifecycle` = `ISSUED_EXECUTABLE` / `true`；`active_authorizations` 只有本授权；账本 `6743` 字节、`5` 行、SHA `aa7c21819a182c3b35aa32ab0c06995734185c9a89eb239bfd0ee44e4c392b31`；清单 SHA `33bd99b9…5ea1`。

```bash
B=".venv/bin/python -m scripts.build_step9_63c_r11_runner_freeze"; I=".venv/bin/python -m scripts.issue_step9_63c_r11_authorization"; $B --status | grep '"state"'; $I --status | grep '"state"'
```

期望：`"state": "S2_FREEZE_PERSISTED"` 与 `"state": "ISSUED_RECORDED"`。

**C4 preflight 证据完整**

```bash
shasum -a 256 evaluation/v1_2_3/step9_63c_r5_auth-step9_63c_r11-1a399434ec0e4494b0045734846b2042_preflight-step9_63c_r5-r11-b0b5945a808f4b57a74f3c34d2e293fe_mac_local_preclearance.json; wc -l evaluation/v1_2_3/step9_63c_r11_preflight_invocations.jsonl
```

期望：`042760d1833424665e9593309a7a4c3b32d071892fda4eabae209cb20add8cca`；`3`（初始化、认领、持久化）。调用记录的来源证明由 C5 里的 consumer 门禁完整核对（`verify_registry_evidence`）。

**C5 预提交门全部通过（只读，guard v3 下运行以证明不写入）**

```bash
CBTI_GUARD_ROOT=$PWD CBTI_GUARD_LOG=/tmp/r11_audit_guard.jsonl PYTHONPATH=$PWD/evaluation/v1_2_3/step9_63c_r5c10ak_test_harness/guard PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/run_step9_63_v3_formal_execution.py --audit-only --evaluation-id heldout-v4-step9_55a-treatment-v3-20260930-01 --authorization-id auth-step9_63c_r11-1a399434ec0e4494b0045734846b2042 --attempt-id attempt-step9_63c_r11-2312daefa1364bfd83ff3948d101c765 --authorization-file /Volumes/Elements/cbti-doctor-main/evaluation/v1_2_3/step9_63c_r11_v3_authorization_manifest.json --preflight-file /Volumes/Elements/cbti-doctor-main/evaluation/v1_2_3/step9_63c_r5_auth-step9_63c_r11-1a399434ec0e4494b0045734846b2042_preflight-step9_63c_r5-r11-b0b5945a808f4b57a74f3c34d2e293fe_mac_local_preclearance.json --preflight-id preflight-step9_63c_r5-r11-b0b5945a808f4b57a74f3c34d2e293fe --preflight-sha256 042760d1833424665e9593309a7a4c3b32d071892fda4eabae209cb20add8cca --treatment-agent-sha256 085d338ed95bbef7370c41cf97ca0d6653ffdfd2f1c924eef4b7123dfdea4607 --benchmark-sha256 8b8c72092fcd7544e69d5d2ecd13610c7bb4c14210fca330698b3e5ab3f01d7f --harness-sha256 8bc271bebc1c5da5351d517e2bb4a0d1a99fda3de1b713a6197b12f81fad70c7 --scoring-sha256 f742a8f8af7c8747818dadad81621c15d12d74f50538019913dfe18ab53bf59b --metric-registry-sha256 de9f348cb1dff66410c03095abdaffcc256f53679718482870e4aa4d80c75056 --one-shot-rules-sha256 1c7ed4ef47865b117bc943f3e0ad9a859f4f74cfb4e8001f723ac5532af140d0 --matched-protocol-sha256 a71ba06090370b576fbba66bc4b005e519ddbabff3021a40c6546fc855f90265 | grep -E '"precommit_failures"|"ready_for_controlled_execution"|"checks_not_executed"'; ls /tmp/r11_audit_guard.jsonl 2>&1
```

期望：`"checks_not_executed": []`、`"precommit_failures": []`、`"ready_for_controlled_execution": true`；guard 日志**不存在**（零事件）。若看到 `FAIL_CLOSED_AUDIT_ERROR` / `FAILURE_TYPE = ValueError`，多半是路径写成了相对路径。

**C6 网络与凭据（不发 HTTP、不带密钥）**

```bash
.venv/bin/python -c "import sys,json; sys.path.insert(0,'.'); from scripts.preflight_step9_63b_mac_local import connectivity; d=connectivity(); print({k:v for k,v in d.items() if k!='DNS_ADDRESSES'})"
```

期望：五个 `*_DNS_STATUS`、`TCP_CONNECTION`、`TLS_CONNECTION` 全为 `PASS`，`TLS_CERTIFICATE_VERIFIED: True`。

**C7 运行环境**

```bash
pmset -g batt | head -2; df -h /Volumes/Elements | tail -1
```

期望：`AC Power`；可用空间远大于 1 GB（运行产物约 10 MB 量级）。另外：关闭会自动弹出外置盘的工具；运行期间不要对 `/Volumes/Elements` 做 Time Machine 备份、Spotlight 重建或拷贝大文件；用稳定的网络（有线或稳定 Wi-Fi，不要切换 VPN）。

**C8 运行前快照（写到仓库外）**

```bash
.venv/bin/python evaluation/v1_2_3/step9_63c_r11_formal_tools/whitelist_check.py snapshot /tmp/r11_pre_tree.json
```

```bash
.venv/bin/python evaluation/v1_2_3/step9_63c_r5c10ak_tools/real_state_check.py snapshot /tmp/r11_pre_state.json
```

期望：第一条打印 `{"entries": 3xxx, ...}`（在外置盘上约 30 秒）；第二条退出码 0。

## 4. 预估

### 4.1 耗时：大约 10 分钟，按 30 分钟预留

依据：同一 benchmark 的历史完整运行（`evaluation/v4_runs/*/attempts.jsonl` 的时间戳）：

| 运行 | 40 个案例总时长 | 单案例中位数 | 单案例最长 |
|---|---|---|---|
| 9.28 baseline | 5.5 分钟 | 3.3 秒 | 45 秒 |
| 9.34a treatment v1 | 8.1 分钟 | 10.6 秒 | 42.5 秒 |
| 9.43 treatment v2 | 6.6 分钟 | 6.5 秒 | 42.2 秒 |

r11 的 treatment agent（v3，`085d338e…`）以前从未完整跑过（9.56 在第 1 个案例失败），所以按 v1/v2 的 6–8 分钟加上执行前门禁（多次全量哈希，外置盘上约 1–2 分钟）与模型/索引加载，**预计 8–12 分钟**。单次请求最长可达 120 秒超时 × 2 次，遇到慢响应时会明显变长，**请预留 30 分钟**，期间不要动这台机器。

### 4.2 API 调用次数：约 150–250 次（数量级 10²）

依据：历史 treatment 运行每次约 52–53 个用户轮次（13 个案例会追问一轮）、31 次 RAG 工具调用、10 次读日记（本地，无 API）。代码里调用模型的位置只有三处：

| 调用点 | 每次 | 估计次数 |
|---|---|---|
| 输入理解 `input_understanding`（结构化输出） | 每个用户轮次 1 次 | ~53 |
| 回答生成 `answer_generation` | 每次生成回答/追问 1 次 | ~40–53 |
| RAG `AgentExecutor`（工具调用 agent，`max_iterations=4`） | 每次检索至少 2 次（决定检索 + 最终作答），最多 4 次以上 | ~62–124 |

合计约 155–230 次；`max_retries=1` 的重试一般不会发生，最坏情况翻倍。embedding 用本地 BGE 模型，不调 API。

### 4.3 token：约 3–5 × 10⁵（数量级 10⁵，上限不超过 10⁶）

历史运行没有记录 token（`token_usage` 全是 `NOT_MEASURED`），以下按提示词大小估算：

| 调用点 | 输入 | 输出 | 小计 |
|---|---|---|---|
| 输入理解 ~53 次 | 系统提示 ~650 字 + 函数 schema + 上下文 ≈ 1–2k | ~100–200 | ~60–110k |
| 回答生成 ~50 次 | 系统提示 ~400 字 + 受限上下文（证据、RAG 结果、溯源）≈ 2–3k | ~200–400（历史回答平均 275 字） | ~110–170k |
| RAG ~31 × 2–3 次 | 第一次 ~0.5k；第二次带 5 段 × 400 字检索结果 ≈ 2–3k | ~300–600 | ~100–150k |

合计约 2.7–4.3 × 10⁵ token，按 3–5 × 10⁵ 理解。具体费用取决于 `.env` 里 `DEEPSEEK_MODEL` 对应的定价，本计划不估金额。

## 5. 中断风险与处理

先分清两个阶段：

- **阶段 A（门禁，约 1–2 分钟，没有写入）**：任何中断都无害，授权仍是 `ISSUED_EXECUTABLE`。重跑第 3 节检查清单（重新快照）后可以再次执行。
- **阶段 B（从事务日志第一行起）**：授权已作废，**不能续跑、不能重跑**；已写的部分结果保留为只追加证据。

| 情形 | 会发生什么 | 授权 |
|---|---|---|
| **Mac 睡眠** | 进程被挂起。醒来后正在进行的 HTTPS 连接通常已断：客户端报连接错误并重试一次；网络恢复得快可能继续跑完，否则这个案例抛出 `APIConnectionError`，attempt 记 `FAILED_AFTER_PARTIAL_EXECUTION`。`caffeinate -dims` + 接电源 + 不合盖可以避免。 | 阶段 B 中**很可能作废** |
| **移动硬盘断开** | 仓库、虚拟环境、模型都在 `/Volumes/Elements` 上。下一次读写（日志 fsync、懒加载模块）抛 `OSError`；runner 试图写 `FAILED` 记录但盘不在，写不进去。最后一行可能被截断。 | 阶段 B 中**作废**；还可能留下截断行 |
| **断网** | 正在进行的请求连接失败，客户端约 0.5–1 秒后重试一次；断网超过几秒就第二次失败，抛 `APIConnectionError`，attempt 失败（与 9.56 相同）。 | 阶段 B 中**作废** |
| **API 限流（429）或服务端错误（5xx、408、409）** | 客户端按 `Retry-After` 或约 0.5–8 秒退避后重试**一次**；再次失败抛 `RateLimitError` / `APIStatusError` → attempt 失败。400 类错误（如上下文超长、内容策略）不重试，直接失败。 | 阶段 B 中**作废** |
| **单次请求卡住** | 120 秒超时 → 重试一次 → 再超时就抛 `APITimeoutError` → attempt 失败。卡住期间命令没有任何输出，这是正常现象，**不要按 Ctrl-C**。 | 阶段 B 中**作废** |
| **Ctrl-C** | `KeyboardInterrupt` 是 `BaseException`：阶段 A 直接退出、什么都没写；阶段 B 中若 attempt 账本已建立，runner 会写一条 `FAILED_BEFORE_FIRST_CASE` / `FAILED_AFTER_PARTIAL_EXECUTION` 再退出；若恰好在 `PREPARED`/`COMMITTING` 之间（毫秒级窗口），事务停在中间状态。 | 阶段 B 中**作废** |
| **断电 / 强制关机 / 内核崩溃** | 没有 `FAILED` 记录，日志停在最后一次 fsync 的位置。 | 阶段 B 中**作废** |

**哪些情况会让授权作废**：阶段 B 中的上述任何一种。只有在阶段 A（事务日志出现之前）发生的中断不会。判断方法：`evaluation/v4_runs/.execution_transactions/auth-step9_63c_r11-1a399434ec0e4494b0045734846b2042.jsonl` 是否存在。存在 = 已作废。

**出现中断时你应该做的（保留现场）：**

1. **不要重跑**执行命令。若在阶段 B，它会被门禁拒绝；若在阶段 A，也先把情况交给我再决定。
2. **不要运行 `--reconcile-transaction`**。它看起来像恢复命令，但它会**写**事务日志（追加 `ABORTED_UNCONSUMED` 或补写 `COMMITTED`），必须先由你我决定。
3. 不要删除、移动、编辑 `evaluation/v4_runs/` 下的任何东西；不要 `git clean`、`git stash`、`git checkout`。
4. 移动硬盘断开时：重新插上，让 macOS 正常挂载；**不要**运行“磁盘工具 → 急救”或 `fsck` 修复（会改文件系统），先做下面的只读检查。
5. 保存终端输出（`/tmp/r11_formal_console.log` 已自动保存）。
6. 运行两条只读命令，把输出和终端输出一起发给我：

```bash
.venv/bin/python evaluation/v1_2_3/step9_63c_r11_formal_tools/verify_after.py
```

```bash
.venv/bin/python evaluation/v1_2_3/step9_63c_r11_formal_tools/whitelist_check.py compare /tmp/r11_pre_tree.json
```

## 6. 完成后的只读验证

**V1 终端**：没有 traceback，`exit=0`。

**V2 运行报告**：

```bash
.venv/bin/python evaluation/v1_2_3/step9_63c_r11_formal_tools/verify_after.py
```

期望：
- `transaction_journal`：`lines: 44`，前四个 `PREPARED, COMMITTING, COMMITTED, ATTEMPT_CLAIMED`，`case_started: 40`，`classification: COMMITTED_EXECUTION_ALREADY_STARTED`（这是纯分类函数，不写入）。
- `namespace_dir_exists: true`；`namespace_marker` 的 `authorization_id`、`attempt_id`、`transaction_id` 与本次一致。
- `attempt_ledger`：`lines: 86`，以 `PREPARED, AUTHORIZATION_CONSUMED, FIRST_EVALUATION_ACCESS, CASE_SET_AND_ORDER_VERIFIED, STARTED` 开头，`last_status: ["COMPLETED"]`，`cases_started: 40`，`cases_completed: 40`，无 `failure`。
- `raw_traces`、`case_results`：各 `lines: 40`。
- `lifecycle`：`CONSUMED_NON_REUSABLE` / `false`；`active_authorizations: []`。
- 账本仍是 `6743` 字节、`5` 行、`aa7c2181…`；清单仍是 `33bd99b9…`。

**V3 白名单**：

```bash
.venv/bin/python evaluation/v1_2_3/step9_63c_r11_formal_tools/whitelist_check.py compare /tmp/r11_pre_tree.json
```

期望：`"ok": true`；`removed`、`added_not_whitelisted`、`changed_not_whitelisted` 都为空；`whitelisted_paths_present` 列出第 2.3 节的 7 个路径。

**V4 受保护文件**：

```bash
.venv/bin/python evaluation/v1_2_3/step9_63c_r5c10ak_tools/real_state_check.py compare /tmp/r11_pre_state.json
```

期望：退出码 1、`identical: false`（因为 `v4_runs_tree` 必然变化）。它打印的是当前值，请逐项核对：`ledger` 为 `6743` 字节、`5` 行、`aa7c2181…`、`equals_activation_commit_blob: true`；`r11_manifest` 为 `33bd99b9…`；`freeze` 为 `bafcec8d…`；`pointer` 为 `4e077781…`。只有 `v4_runs_tree` 的哈希和条目数不同。

**V5 不可重用**：重跑第 3 节 C5 的 `--audit-only` 命令。期望：`ready_for_controlled_execution: false`，`precommit_failures` 至少包含 `authorization_lifecycle_executable`、`exactly_one_active_authorization`、`attempt_absent`、`namespace_absent`；或者在更早的检查处直接 `FAIL_CLOSED_AUDIT_ERROR`。两种结果都说明授权不能再次执行（此结果是推断，执行后才能实测）。

**V6 git**：`git status --porcelain` 仍为空（`evaluation/v4_runs/` 被 `.gitignore` 忽略，运行产物不会进 git；如需归档，另行决定）。

**会产生的结果文件**（都在 `evaluation/v4_runs/` 下，被 gitignore）：

| 文件 | 内容 |
|---|---|
| `.execution_transactions/auth-step9_63c_r11-1a399434….jsonl` | 事务日志，44 行 |
| `heldout-v4-treatment-v3-run-9ec9c305cc4de01e6538/.namespace_allocation.json` | 命名空间预留标记 |
| `…/heldout-v4-step9_55a-treatment-v3-20260930-01/attempts.jsonl` | attempt 账本，86 行 |
| `…/attempt-step9_63c_r11-2312daef…_raw_traces.jsonl` | 40 个案例的完整原始 trace |
| `…/attempt-step9_63c_r11-2312daef…_case_results.jsonl` | 40 个案例的结果，`score_status: PENDING_FROZEN_RUBRIC_REVIEW` |

评分（按冻结 rubric）不在本次执行内，是之后的单独步骤。
