# r11 正式执行：运行后复核与归档建议（Step 9.63c-r11 post-run review）

**本步只读分析、只写报告**：没有修改任何代码，没有写 `evaluation/v4_runs/`，没有运行 `--reconcile-transaction`，没有 commit。复核前后，整仓快照（`whitelist_check.py`）与受保护状态（`real_state_check.py`）都没有变化。原始数据见 `step9_63c_r11_post_run_review_evidence.json`。

**结论**

1. 你的判断成立：lifecycle reducer 对“正常跑完”的事务日志一定返回 `INCONSISTENT_FAIL_CLOSED`，`CONSUMED` 分支对任何合法日志都不可达。测试和演练都没发现，是因为它们从未让 reducer 读取一份越过 `COMMITTED` 的真实形状日志。
2. 本次运行有效。缺陷只出在事后读取状态的 reducer，执行路径没有用它。授权确实不能再执行。现有的评分、聚合脚本都不依赖 `CONSUMED`。
3. 已记为已知缺陷 KL-1，不在本步修复，修复必须进入下一个冻结修订版本。
4. 归档方案见第 4 节，**等你批准后再执行**。

## 1. 根因确认

### 1.1 逐行对照（`scripts/authorization_lifecycle.py`，冻结 SHA `f0d8b7e0…612744`，r11 第 9 号成员）

| 行 | 代码要点 | 对本次日志（44 行）的结果 |
|---|---|---|
| 205–206 | `events = read_events(journal)`；`state = current_state(events)` | `read_events` 校验通过；`current_state` 只看最后一个**状态事件**，得到 `"COMMITTED"` |
| 207–223 | 事务身份与签发清单一致 | 通过 |
| 224–227 | attempt 账本含 `AUTHORIZATION_CONSUMED`（`consumed=True`、`attempted=True`）；找到 1 个命名空间标记 | 通过 |
| 228 | `case_started = any(... == "CASE_STARTED")` | `True` |
| **229–231** | `burned = events and state == "COMMITTED" and events[-1].event_type == "COMMITTED" and events[-1].authorization_irreversibly_burned` | **`False`**：`events[-1]` 是第 40 个 `CASE_STARTED` |
| 233–236 | 退役冲突检查 | 不适用 |
| 237–251 | `if burned:` 分支，其中 241–246 在 `case_started and attempted` 时返回 `CONSUMED_STATE` | **被跳过** |
| **252–253** | `if events: raise RuntimeError("transaction exists without a valid irreversible committed burn")` | **触发**，在 270–273 行被转成 `INCONSISTENT_FAIL_CLOSED` |

**不可达性证明**：`v3_execution_transaction._validate_events` 规定 `ATTEMPT_CLAIMED` 和 `CASE_STARTED` 只能出现在 `COMMITTED` 之后。要进入 241–246 行返回 `CONSUMED`，必须同时满足“最后一个事件是 `COMMITTED`”（229–231 行）和“存在 `CASE_STARTED`”（228、242 行）。这两个条件对任何合法日志都矛盾，所以该分支不可达。

同理，`COMMITTED` 之后只要追加了 `ATTEMPT_CLAIMED`，哪怕还没开始任何案例，也会落到 253 行。冻结版 reducer 只在日志恰好止于 `COMMITTED` 时给出非 `INCONSISTENT` 的结果，即 `BURNED_PRE_CASE`。

### 1.2 实验（在临时目录的副本上，冻结代码未改）

把本次真实日志分别截到 N 行，连同真实的命名空间标记和 attempt 账本复制到临时根目录：

| 日志形状 | 冻结版 reducer | 修复草案（只把 229–231 行改为读取 `COMMITTED` 事件本身） |
|---|---|---|
| 3 行，止于 `COMMITTED` | `BURNED_PRE_CASE` | `BURNED_PRE_CASE` |
| 4 行，止于 `ATTEMPT_CLAIMED` | `INCONSISTENT`（无有效 burn） | `INCONSISTENT`（"committed pre-case evidence conflicts with attempt state"） |
| 5 行，第 1 个 `CASE_STARTED` | `INCONSISTENT` | **`CONSUMED_NON_REUSABLE`** |
| 44 行，本次完整日志 | `INCONSISTENT` | **`CONSUMED_NON_REUSABLE`** |

第二行说明，只改一行判定还不够：“已认领 attempt、尚未开始案例”这个合法的崩溃点仍然没有定义状态（见第 3 节修复草案）。

### 1.3 为什么以前没发现

1. **reducer 测试从未构造“完成”的形状。** `test_step9_63c_r5c5b_lifecycle_reducer`（现归档为 `tests/retired/…r5c5b_lifecycle_reducer.py.retired`）：
   - `test_08_consumption_is_terminal` 只写 attempt 账本、不写事务日志，走的是 258–263 行的**旧协议路径**，所以能得到 `CONSUMED`。
   - 辅助函数 `add_transaction` 虽然支持 `attempt_claimed=True`，但全仓库没有任何测试这样调用它。
   - `test_14_case_started_without_attempt_fails_closed` 断言 `INCONSISTENT` 能通过，但通过的原因恰好是这个缺陷（末事件不是 `COMMITTED`），而不是测试名所说的“缺少 attempt”。它掩盖了问题。
2. **crash 测试只检查事务模块。** `test_step9_63a_r1_production_integration` 的 `test_crash_after_attempt_projection_…` 和 `test_crash_after_case_projection_…` 确实写出了 `ATTEMPT_CLAIMED` 和 `CASE_STARTED`，但只断言 `v3_execution_transaction.reconcile()` 的分类（它正确地给出 `COMMITTED_EXECUTION_ALREADY_STARTED`），从不调用 lifecycle reducer。`test_lifecycle_rejects_committed_authorization` 只断言“不可执行 / 不等于 `ISSUED_EXECUTABLE`”，`INCONSISTENT` 也满足这个弱断言。
3. **演练从未走到 `CASE_STARTED`。** ag、ah、ai 三套端到端演练都止于 consumer 的只读预提交门（`prepare_formal_gates`），文件中 `execute_formal(`、`begin_and_commit`、`adapter.run`、`CASE_STARTED` 的出现次数都是 0。
4. **真实历史也从没出现过这种形状。** 仓库里唯一的旧事务日志 `auth-step9_63a_r3-…jsonl` 止于 `COMMITTED`（pre-case burn）。以前的完整运行（9.28、9.34a、9.43）以及在第 1 个案例失败的 9.56，都发生在事务协议之前，走的是旧路径。**本次是事务协议下第一次写出 `COMMITTED` 之后的事件。**
5. **变异测试无从检测。** 既然没有测试走到这个分支，把它删掉或改坏都不会被发现。

## 2. 影响评估

### 2.1 本次运行的结果是否有效：有效

- 执行路径没有使用 reducer。提交前的 `assert_executable_authorization` 只在 `transaction_id is None` 时调用（adapter 第 373–376 行、父 runner 第 291–292 行）。事务存在之后，运行时改用 `require_committed`，它直接找 `COMMITTED` 事件并核对 burn 标记，以及 `assert_not_retired`。所以这个缺陷只影响事后读取状态，没有改变执行过程。
- 完整性交叉核对全部通过：
  - `transaction_id` `txn-v3-e96bdfed431149098ea815dec817d6ab` 在事务日志、命名空间标记、attempt 账本中一致；
  - `CASE_STARTED` 的编号 1–40 与结果文件的案例顺序逐一对应，并符合授权的案例顺序指纹；
  - raw traces 与 case results 的案例 ID 相同，40 个各不重复；
  - attempt 账本没有失败事件，所有轮次 HTTP 200，40 个 `final_status` 都是 `ANSWER`，没有空回答；
  - 每条 attempt 事件里的 agent `085d338e…` 与 runner `3a4ec3e5…` 都等于冻结值；
  - 写入白名单比对 `ok: true`；账本、清单、Freeze、指针都未变。
- 所以本次运行可以作为**一次完整、恰好执行一次的 r11 treatment v3 运行**进入评分；只是它的生命周期“标签”目前被错误地读成 `INCONSISTENT`。

### 2.2 授权确实不可再执行：是

- reducer：`INCONSISTENT_FAIL_CLOSED`，`executable: false`。
- 重跑 consumer 的 `--audit-only`（只读），`precommit_failures` 为 `authorization_lifecycle_executable`、`exactly_one_active_authorization`、`active_authorization_is_bound_id`、`attempt_absent`、`namespace_absent`、`check_not_executed:active_authorizations`、`active_authorization_count`。
- 与 reducer 无关的独立阻断也成立：事务日志已存在，`assert_no_transaction` 会拒绝；命名空间和 attempt 账本已存在，碰撞检查会拒绝；`claim_attempt` 和 `append_case_started` 禁止重复。

### 2.3 依赖生命周期状态的组件

| 组件 | 现在的表现 |
|---|---|
| `active_authorizations(ROOT)` | **抛出 `RuntimeError`**（"authorization lifecycle is inconsistent"），而不是返回 `[]`。凡是在当前 r11 指针下调用它的入口都会 fail-closed：consumer 门禁、r11 签发器的 `--plan`/`--issue`、`preflight_step9_63c_current_mac_local.validate_authorization_state`、`preflight_step9_63c_r5c7_mac_local`。r11 本来就是“每个 Freeze 只签发一份授权”，所以这不会阻止任何合法操作，但任何“统计活动授权”的检查都会报错而不是给出 0。 |
| builder `--status`、签发器 `--status` | 不受影响，仍是 `S2_FREEZE_PERSISTED` / `ISSUED_RECORDED`（已只读实测）。 |
| 下一个修订版本（r12） | `active_authorizations` 先按 `runner_freeze_revision` 过滤，再调用 reducer。指针移到 r12 后，r11 清单会被跳过，不会再报错。consumer 的 `_superseded_v3_authorizations` 会对 r11 调用 reducer：冻结版得到 `INCONSISTENT`（不可执行，能通过“旧授权已退役/不可执行”两项检查），修复版得到 `CONSUMED`。 |
| 评分与聚合 | **不依赖。** 读取 `case_results`/`raw_traces` 的脚本（`aggregate_step9_30c_v4`、`aggregate_step9_38_treatment`、`aggregate_step9_47_v2`、`complete_step9_37_treatment_adjudication`、`audit_step9_30a_v4_adjudication_integrity`、`v4_adjudication_contract` 等）都不调用 reducer 或检查授权状态（`lifecycle`/`CONSUMED`/`INCONSISTENT` 关键词计数为 0）。但它们都绑定以前那几次运行的路径与身份，**给 r11 评分需要新的单独步骤**；那一步应直接按事务日志、标记、attempt 账本和本报告的 SHA 绑定产物，不要以 reducer 的标签作为前提条件。 |
| 测试 | 读取真实 r11 状态的遗留测试已在 r5c10ak 隔离到临时镜像，CI 不受影响。 |

## 3. 已知缺陷 KL-1（不修复）与修复建议草案

**KL-1**：`reduce_authorization_lifecycle` 用 `events[-1]` 判断 burn，把“`COMMITTED` 之后正常追加了 `ATTEMPT_CLAIMED`/`CASE_STARTED`”的合法日志判为 `INCONSISTENT_FAIL_CLOSED`。`CONSUMED` 分支不可达，“已认领、未开始案例”的状态也没有定义。

- **影响**：读取侧标签错误，并且 `active_authorizations()` 在当前 r11 修订下抛异常；fail-closed 方向，不会让授权变得可再执行。
- **不在 r11 内修复的原因**：`scripts/authorization_lifecycle.py` 是 r11 Freeze 的第 9 号成员，改动它会改变 Freeze。**修复必须进入下一个冻结修订版本**，走完整的设计、测试、批准与激活流程。r11 的所有证据保持原样。

修复建议草案（只是文字，没有改代码）：

1. **burn 判定**：在日志中定位唯一的 `COMMITTED` 事件（sequence 3），检查**该事件**的 `commit_point is True` 与 `authorization_irreversibly_burned is True`，不再依赖 `events[-1]`。
2. **显式定义提交后的每一种合法形状**：

| 事务日志 | attempt 账本 | 派生状态（建议） |
|---|---|---|
| 止于 `COMMITTED` | 无 | `COMMITTED_BURNED_PRE_CASE_NON_REUSABLE`（现有） |
| + `ATTEMPT_CLAIMED`，无 `CASE_STARTED` | 无，或只有 `PREPARED`/`AUTHORIZATION_CONSUMED`/`FIRST_EVALUATION_ACCESS`/`CASE_SET_AND_ORDER_VERIFIED`/`FAILED_BEFORE_FIRST_CASE` | 新增，例如 `ATTEMPT_CLAIMED_BURNED_PRE_CASE_NON_REUSABLE` |
| + `ATTEMPT_CLAIMED` + ≥1 `CASE_STARTED` | 含 `AUTHORIZATION_CONSUMED` | `CONSUMED_NON_REUSABLE`，`evidence` 中区分 `COMPLETED` / `FAILED_AFTER_PARTIAL_EXECUTION` / 无终止事件（中断） |
| 其他组合（标记的事务 ID 不符、`CASE_STARTED` 编号与账本不符、退役冲突、身份漂移） | — | 仍为 `INCONSISTENT_FAIL_CLOSED` |

3. **测试**：
   - 在临时根上真实调用 `begin_and_commit → reserve_namespace → claim_attempt → append_case_started ×N`，加上 attempt 账本，对每个崩溃点断言 reducer 的状态和 `active_authorizations() == []`。
   - 把 `test_14` 改为构造“有 `CASE_STARTED`、无 `ATTEMPT_CLAIMED`”的形状，让它按测试名所说的原因失败。
   - 变异：把判定改回 `events[-1]` 必须让测试失败。
4. **演练**：端到端演练应在临时根上用替身案例执行器跑完 `adapter.run`，直到 `COMPLETED`，然后断言 reducer 和 consumer 审计的结果。只演练到预提交门是本次缺陷漏网的直接原因。
5. **回读本次运行**：新修订激活后，用新 reducer 对 r11 的证据只读复核一次，预期为 `CONSUMED_NON_REUSABLE`（本报告 1.2 已在副本上验证），并把结果写进新修订的审查材料。

## 4. 归档方案（等你批准）

### 4.1 要归档的文件（源路径 → SHA-256）

| 源（`evaluation/v4_runs/` 下） | 字节 | SHA-256 |
|---|---|---|
| `.execution_transactions/auth-step9_63c_r11-1a399434ec0e4494b0045734846b2042.jsonl` | 36421 | `63dd783f4f24beedf2bc68a47e282d04a8efb8968a0c7d959703411792b52108` |
| `heldout-v4-treatment-v3-run-9ec9c305cc4de01e6538/.namespace_allocation.json` | 449 | `21fad903a54e323c97721ca4a9f3956026bd1431498d3696aa8cb1615f5980e3` |
| `…/heldout-v4-step9_55a-treatment-v3-20260930-01/attempts.jsonl` | 57189 | `4326a64094b626db45cb13f31b1ec8a716f683153639a7a4e93fd50fc9bfda36` |
| `…/attempt-step9_63c_r11-2312daefa1364bfd83ff3948d101c765_raw_traces.jsonl` | 7034829 | `abd307e0e64730448856c595f134d437a2130bf8ef160a680126cd0067b2a2f5` |
| `…/attempt-step9_63c_r11-2312daefa1364bfd83ff3948d101c765_case_results.jsonl` | 59322 | `6672f3ef21a20a68776925267896ed4362832aaabc5a16c06546a6b778ef0ba8` |

合计约 7.2 MB。preflight 证据与调用记录已在仓库里（`c944ed4`）。可选：你本机的 `/tmp/r11_formal_console.log`。

### 4.2 目标布局

```
evaluation/v1_2_3/step9_63c_r11_run_archive/
  README.md              说明：只读证据副本、来源、何时复制、不得修改；原件仍在 evaluation/v4_runs/
  MANIFEST.json          每个文件：源路径、归档路径、字节数、SHA-256、源文件 mtime、复制时间、复制时所在 HEAD
  SHA256SUMS             与 `shasum -a 256 -c` 兼容
  run_root/.execution_transactions/auth-step9_63c_r11-….jsonl
  run_root/heldout-v4-treatment-v3-run-9ec9c305cc4de01e6538/.namespace_allocation.json
  run_root/heldout-v4-treatment-v3-run-9ec9c305cc4de01e6538/heldout-v4-step9_55a-treatment-v3-20260930-01/{attempts.jsonl, …_raw_traces.jsonl, …_case_results.jsonl}
```

目录名用 `run_root/` 而不是 `v4_runs/`。所有扫描 attempt 账本和命名空间标记的代码都以 `evaluation/v4_runs` 为根（已核对），归档副本不会被误认作新的 attempt 或命名空间。

### 4.3 步骤（批准后执行；对 `evaluation/v4_runs/` 只读）

1. 运行前：`whitelist_check.py snapshot` 与 `real_state_check.py snapshot`（写到 `/tmp`）。
2. 读源文件，确认 SHA 等于 4.1 的表 → 复制（`O_EXCL`，不覆盖）→ 读回目标文件，确认 SHA 相同 → 生成 `MANIFEST.json`、`SHA256SUMS`、`README.md` → 把归档文件权限设为只读（`0444`，git 不记录这个权限，只防本机误改）。
3. 运行后：`real_state_check.py compare` 必须 `identical: true`（`evaluation/v4_runs/` 一字节都不变）；`whitelist_check.py compare` 应只显示新增的归档目录。
4. 跑一次全量回归（r5c10ak harness），确认新增目录不影响任何测试或清单。

### 4.4 需要你决定的两点

1. **`.gitignore` 会挡住其中 3 个文件。** 规则 `evaluation/**/*attempts.jsonl`、`*raw_traces.jsonl`、`*case_results.jsonl`（第 40–42 行）同样匹配归档目录。可选做法：
   - (a) **推荐**：提交时对这 3 个文件 `git add -f`。不改忽略规则；文件被跟踪后，后续修改也会显示在 `git status` 里。
   - (b) 在 `.gitignore` 里加一条针对归档目录的反向规则（`!evaluation/v1_2_3/step9_63c_r11_run_archive/**`）。规则长期显式存在，但要改仓库配置。
   - (c) 给文件加后缀（如 `.archived`）。不推荐，会破坏与原文件名的对应关系。
2. **这与此前“运行产物不进 git”的做法相反。** CI 注释写明历史运行产物是有意不进 git 的。归档后 7 MB 的 raw traces（benchmark 案例、模型回答、完整 State）会进入 git 历史，push 后无法真正撤回。**push 前请确认远程仓库的可见性，以及内容是否适合公开**；如果只想留本机证据，可以把归档改为仓库外的只读副本，仓库内只提交 `MANIFEST.json` 和 `SHA256SUMS`。

## 5. 运行摘要（不评分、不和基线比较）

### 5.1 时间线（UTC）

| 事件 | 时间 |
|---|---|
| 事务 `PREPARED`（授权作废点） | 02:36:42.10 |
| attempt 账本 `PREPARED` | 02:36:42.62 |
| 第 1 个案例开始（之前约 84 秒用于加载 agent、模型与 RAG 索引） | 02:38:06.28 |
| 最后一个案例完成 / `COMPLETED` | 02:45:07.25 |
| attempt 总时长 | 504.6 秒（8.4 分钟） |

### 5.2 每类任务

| 任务类型 | 案例 | ANSWER | 轮次 | agent 步数 | ASK（有 ASK 的案例） | RETRIEVE | READ_DIARY | 单案例耗时 秒（最短 / 中位数 / 最长 / 合计） |
|---|---|---|---|---|---|---|---|---|
| KNOWLEDGE_QA | 10 | 10 | 10 | 20 | 0（0） | 10 | 0 | 10.2 / 12.7 / 47.2 / 162.5 |
| CAUSE_ASSESSMENT | 10 | 10 | 13 | 23 | 3（3） | 10 | 0 | 8.2 / 10.3 / 18.5 / 110.1 |
| PERSONALIZED_DECISION | 10 | 10 | 19 | 29 | 9（5） | 10 | 0 | 5.3 / 11.8 / 14.9 / 113.4 |
| DATA_ANALYSIS | 10 | 10 | 10 | 21 | 0（0） | 1 | 10 | 1.6 / 3.2 / 7.5 / 34.8 |
| **合计** | **40** | **40** | **52** | **93** | **12（8）** | **31** | **10** | 1.6 / 10.3 / 47.2 / 420.8 |

单案例耗时分布（全部 40 个）：P25 7.5 秒，中位数 10.3 秒，P75 12.5 秒，最长 47.2 秒。最慢的 5 个：V4-KQ-01（47.2，第一个案例，含 RAG 首次调用的冷启动）、V4-CA-07（18.5）、V4-KQ-02（15.6）、V4-KQ-05（15.1）、V4-KQ-08（15.0）。

### 5.3 token_usage

**没有记录**：40 个 `case_results` 和 40 条 raw traces 的 `token_usage` 都是 `NOT_MEASURED`，与以前的运行相同。冻结的案例路径（`run_step9_28_v4_heldout.py` 第 215、220 行）把它写死为常量 `NOT_MEASURED`。服务层虽然把回答生成的用量（`last_token_usage`）传给了记录器（`adaptive_agent/service.py` 第 43–44 行），但冻结的 `_CaptureRecorder` 没有保存它（raw traces 里 `prompt_tokens` 出现 0 次）；输入理解和 RAG 两类调用的用量本来就没有采集。如果要报告实际 token 消耗，只能查 DeepSeek 控制台的账单。

### 5.4 留给评分步骤的观察（不做判断）

12 个案例的 `lineage_ready` 为 false：

- 8 个案例（V4-CA-02/04/07、V4-PD-01/03/04/09/10）都在追问后的轮次缺少 `candidate_id`（`act_goal_t1_r*_*`）；
- 4 个 DATA_ANALYSIS 案例（V4-DA-01/06/09/10）缺少根溯源 `semantic_id`。

以前 v1、v2 的完整运行都是 13/40。这属于 trace 溯源完整性，不影响执行是否有效，是否计入评分由冻结 rubric 决定。

## 6. 复核时运行过的命令（全部只读）

- `verify_after.py`；builder 与签发器的 `--status`、consumer 的 `--audit-only`（在 guard v3 下运行，零事件）。
- reducer 实验与运行摘要：会话级硬防护开启，只在临时目录写副本。
- 运行前后各做一次快照比对：`whitelist_check.py compare` 为 `ok`，`real_state_check.py compare` 为 `identical`。
