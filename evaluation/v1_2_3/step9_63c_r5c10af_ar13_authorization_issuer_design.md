# AR-13 设计草案：r11 授权签发器（Authorization Issuer）

状态：`DRAFT_DESIGN_ONLY_NOT_IMPLEMENTED`

本文档只描述方案。本步没有创建授权、没有向账本追加任何事件、没有写可执行代码；文中的命令名、函数名、事件名都是**拟议名称**。

## 1. 目标与非目标

- **目标**：设计一个签发器，它只能为"已审定的 r11 Freeze 与身份指针"签发**恰好一份**一次性授权，并且签发过程可审计、可检测篡改。
- **非目标**：不执行、不消费授权；不替代 preflight；不处理 r10 授权的退役（AR-14）。

## 2. 已核实的事实

| 编号 | 事实 | 证据 |
|---|---|---|
| E1 | r7 签发器把"签发"实现为：在文件锁内重新验证 → 确认没有活跃授权 → 确认身份全局唯一 → 用 `O_EXCL` 写出**一个清单文件** → `fsync`。**账本里没有签发事件**，账本中只有 3 个退役事件。 | `scripts/issue_step9_63a_r3_authorization.py`、账本 |
| E2 | r7 签发器写死了 r7：`FREEZE_PATH`、`EXPECTED_R7_SHA256`、旧授权 `step9_62…`、`runner_freeze_revision: "r7"`、`FRESH_R7` 类型，并要求 r2 资格审计产物；它在**模块导入时**就导入冻结 adapter。清单模板取自一份被退役的旧清单。 | 同上 |
| E3 | 它是 r11 Freeze 的第 7 号成员，在 r11 清单里标注为"历史 r7 签发器，不可用于 r11"，字节必须等于 r10 的值（未变成员），因此**不能被修改成 r11 签发器**。 | builder `MEMBER_PATHS`；r5c10i 成员矩阵第 7 行 |
| E4 | 文件锁 `lifecycle_lock(LOCK_PATH)` 与事务提交、命名空间预留、退役共用。签发器持锁期间，这些操作不能交错。 | `authorization_lifecycle.py` |
| E5 | 账本读取方只有两处，且都按 `event_type` 过滤：退役查询、新授权身份唯一性检查。其他事件类型会被忽略，只要求每行是合法 JSON 对象。账本的 55-pin 校验只钉住前 1161 字节，追加不影响它。 | `_events`、`verify_historical_pins` |
| E6 | `active_authorizations()` 通过文件名模式 `step*authorization_manifest.json` 发现清单，且要求 `runner_freeze_revision` 等于当前指针的修订号；叫"V3"的条件是 `treatment == TREATMENT_V3`，或文件名含 `_v3_authorization_manifest`。 | 同上 |
| E7 | parent 校验器按键逐项比较，**不拒绝多余的键**；`consumed_at_utc` 必须为 `None`，状态字段必须是 `ISSUED_NOT_EXECUTED` / `ISSUED_NOT_CONSUMED`，消费计数必须为 0。 | `run_step9_35a_matched_treatment.py` |
| E8 | consumer 校验授权时需要这些字段：`authorization_id`、`attempt_id`、`evaluation_id`、`runner_freeze_{revision,path,sha256}`、`treatment_agent_sha256`、`frozen_evaluation_identity_sha256`（等于 Freeze 的 `bound_identities_sha256`）、`case_set_fingerprint_sha256`、`case_order_fingerprint_sha256`、`case_count`、`task_distribution`、`execution_namespace.namespace_id`（必须等于 `derive_namespace_id(...)`）、`issued_at_utc`，以及 13 个评估身份键。 | AR-17 的 consumer |
| E9 | 退役函数是冻结的，已存在：它要求清单处于 `ISSUED_NOT_EXECUTED`、未消费、无 attempt、无命名空间、无事务，并要求一份"不可重用判定"文件；它追加终态事件，**重复退役被拒绝**。 | `retire_unconsumed_authorization` |
| E10 | r10 授权 `auth-step9_63c_r5c6-…` 当前仍是 `ISSUED_EXECUTABLE`，即使不签发新授权，它在 r11 下也会被 consumer 的预提交检查拒绝（旧版本授权必须不可执行）。 | 只读 reducer |

## 3. 签发条件（必须引用 r11 Freeze 与身份指针）

签发器只在**全部**条件成立时才写入，任何一条失败即中止并不写任何东西。

| 编号 | 条件 | 方法 |
|---|---|---|
| I1 | 身份指针存在，字节等于 AR-12 的规范字节，SHA 等于批准记录；指针创建记录存在 | 复用 AR-12 的验证 |
| I2 | `resolve_current_freeze` 成功（指针 → Freeze → 20 个成员字节 → 聚合） | 冻结的 resolver |
| I3 | Freeze 的 SHA 等于**批准记录里你审定的值**，而不是仅与指针一致 | 防止"自洽的伪造" |
| I4 | 用 builder 以 Freeze 中记录的创建时间重新组装，结果与磁盘上的 Freeze 字节完全一致 | 检测被手工修改的 Freeze。**注意**：现有 `assemble_candidate` 在目标文件已存在时会直接拒绝（"r11 freeze target already exists"），所以这一条需要 builder 新增一个只读的"验证已落盘 Freeze"入口（见第 12 节） |
| I5 | 20 个成员中，3 个变更成员等于 builder 钉住的 SHA | AR-10 的常量 |
| I6 | 非当前版本的所有 V3 授权，经 reducer 判定均不可执行（r10 已退役，即 AR-14 已完成） | 复用 consumer 的 `_superseded_v3_authorizations` |
| I7 | **当前版本的活跃授权数为 0**（签发前）—— 见第 4 节 | `active_authorizations(root)` |
| I8 | 55 个历史 pin 通过 | 复用 `verify_historical_pins` |
| I9 | 新标识全局唯一：授权 ID、attempt ID、命名空间 ID 都不在任何清单、账本、事务、attempt 账本、命名空间目录里出现 | 复用 `assert_fresh_authorization_identity` 加 r7 的全局字节扫描 |
| I10 | 目标清单路径不存在（固定路径，见第 4 节） | `O_EXCL` |
| I11 | 取得 `lifecycle_lock` | 与事务提交互斥 |
| I12 | `issued_at_utc` 严格晚于 Freeze 的 `created_at_utc`，也晚于账本中最后一个事件的时间 | 防时钟回拨 |

**签发值的来源**：所有评估身份字段取自 Freeze 的 `bound_identities`，**不**从旧清单复制；`evaluation_id` 取自冻结 adapter 的常量。非身份字段（授权类型、边界、claim 范围、执行限制等）只来自**显式白名单**，白名单取自被钉住 SHA 的 r10 清单（`beac52d1…`）；生成后检查键集合等于"白名单加身份字段加签发字段"，多一个或少一个键都中止。

## 4. "恰好 1 个活跃授权"在签发侧如何保证

四层，互相独立：

1. **锁**：整个检查与写入在 `lifecycle_lock` 内完成，与事务提交、命名空间预留、退役互斥。
2. **签发前条件**：持锁后重新计算 `active_authorizations(root)` 必须是空列表，并且所有旧版本授权不可执行（I6、I7）。
3. **固定路径加 `O_EXCL`**：清单路径是固定的 `evaluation/v1_2_3/step9_63c_r11_v3_authorization_manifest.json`——**每个 Freeze 修订只允许一份授权**。这给出第二条与锁无关的"只有一次"保证；如果锁因任何原因失效，第二个签发者也会因 `FileExistsError` 失败。
4. **签发后断言**：写入后立即重新计算活跃授权，必须恰好等于 `[新授权 ID]`。不成立（理论上不应发生）时，签发器以非零退出，**不删除任何东西**；此时 consumer 的预提交检查会看到两个活跃授权并拒绝所有执行，等待人工走退役流程。

**一个 Freeze 修订只对应一份授权**的含义：授权被撤销或退役之后，要再次执行必须新建 Freeze 修订（r12）。这与本项目到目前为止的实践一致（r3 到 r10 每次签发都对应一个新修订）。

## 5. 与 r7 签发器的差异与不复用的理由

| 方面 | r7 签发器 | 拟议 r11 签发器 |
|---|---|---|
| 目标版本 | 写死 r7 的路径、SHA、类型 | 全部来自 resolver 与已审 Freeze |
| 身份值来源 | 复制旧清单后覆盖 | 只取 Freeze，旧清单仅提供白名单里的非身份键 |
| 导入方式 | 导入时就导入冻结 adapter（无身份即失败） | 函数内延迟导入，并只用冻结的纯函数 |
| 活跃授权检查 | 62b 的 `active_authorizations` | 冻结 reducer 加签发后断言 |
| 历史 pin | 自带一份拷贝（逻辑已在 consumer 里重复） | 直接复用 consumer 的 `verify_historical_pins`，不再有第二份 |
| 签发证据 | 只有清单文件 | 清单加账本签发事件（决定点 D13-3） |
| 人工确认 | 无（由调用方保证） | 默认只读 `--plan`；写入需要批准记录加键入确认标记 |
| 不复用的原因 | 它是 r11 的第 7 号"未变成员"，字节必须等于 r10 值，**改它就破坏 Freeze 的成员映射**；而且它的校验函数是 r7 专用的，参数化会改变其语义 | —— |

## 6. 账本事件格式（只追加）

**事件类型**：`AUTHORIZATION_ISSUED`（拟议）。现有代码按 `event_type` 过滤，因此该类型对 reducer、退役查询、唯一性检查**都是惰性的**（E5），不改变任何现有判定。

```text
{ "artifact_type": "AUTHORIZATION_LIFECYCLE_EVENT",
  "event_type": "AUTHORIZATION_ISSUED",
  "lifecycle_event_id": "issued-<uuid4hex>",
  "timestamp_utc": "...",
  "authorization_id": "...", "attempt_id": "...", "evaluation_id": "...", "namespace_id": "...",
  "authorization_manifest_path": "...", "authorization_manifest_sha256": "...",
  "runner_freeze_revision": "r11", "runner_freeze_path": "...", "runner_freeze_sha256": "...",
  "identity_pointer_sha256": "...", "approval_record_sha256": "...", "issuer_sha256": "...",
  "active_authorizations_before": [], "active_authorizations_after": ["<id>"],
  "authorization_consumed": false, "authorization_consumption_count": 0,
  "terminal": false }
```

- 序列化、追加和同步方式与退役事件完全一致：一行键排序的 JSON，`O_APPEND`，`fsync` 文件，`fsync` 目录。
- **写入顺序**：先写清单（`O_EXCL`），再追加事件，全程在同一把锁内。
- **崩溃恢复**：清单已存在但没有对应事件时，系统处于 `ISSUED_UNRECORDED`。`--status` 会报告；重新运行 `--complete-record`（拟议）在校验清单字节后补写事件，幂等。这个状态**不会**让授权不安全（清单本身就是 reducer 的依据），只是少了审计记录。
- **同一授权的第二个 `AUTHORIZATION_ISSUED` 事件被视为损坏**（检查器报错）。

## 7. 撤销与退役路径

| 授权所处阶段 | 路径 | 结果 |
|---|---|---|
| 已签发、未使用（无 attempt、无命名空间、无事务） | 使用**已冻结的退役函数**，需要不可重用判定文件和你的批准 | 追加终态退役事件；之后不可执行，不可重新签发（身份永久占用） |
| 事务已提交（授权已被烧毁），尚未开始用例 | 不可撤销；reducer 判为 `COMMITTED_BURNED_PRE_CASE_NON_REUSABLE` | 终态 |
| 已开始用例 | 不可撤销；`CONSUMED_NON_REUSABLE` | 终态 |
| 签发后发现签发器或 Freeze 有问题 | 先退役，然后新建 Freeze 修订 | 一个修订只对应一份授权 |

**签发器不提供任何删除或修改清单的功能**。没有 `--force`，也没有 `--reissue`。

## 8. 威胁清单与对应防御

| 威胁 | 攻击路径 | 防御 | 残余风险 |
|---|---|---|---|
| **重放** | 重新提交旧授权清单，或复用旧授权的 ID/attempt | 新标识全局唯一性检查（I9）；固定路径加 `O_EXCL`；consumer 校验授权的 Freeze 修订与 SHA；退役、烧毁、消费状态在 reducer 里是终态；preflight 声明会记录清单 SHA | 低 |
| **并发签发** | 两个签发器同时运行 | `lifecycle_lock`；签发前重算活跃授权；固定路径 `O_EXCL`；签发后断言；consumer 在执行前独立重数 | 低。若文件锁失效，第二个签发者仍因路径已存在而失败 |
| **伪造指针/Freeze** | 手写一个自洽的 r11 指针和 Freeze | 指针字节无自由输入且与批准记录比对；Freeze 要与批准记录里的 SHA 一致，并能由 builder 以同样的时间戳逐字节重现（I3、I4）；3 个变更成员有精确 SHA 钉住；20 个成员字节逐一验证 | 你批准的 SHA 本身若被欺骗则无法防御（人为环节） |
| **旧授权复活** | 修改账本使 r10 授权不再"已退役"，或截断账本 | 账本前 1161 字节在 55-pin 中被钉住（截断会被检测）；r10 清单字节被钉住；退役事件重复被拒；r10 授权绑定的 r10 Freeze SHA 与当前不符，即使被复活，consumer 的 `runner_freeze_sha256` 检查也会拒绝 | 对账本**中间**行的改动只能靠追加式约定和人工审计 |
| **签发器被替换** | 用另一份脚本签发 | D13-1(a)：签发器作为 Freeze 成员；其 SHA 写入清单和账本事件；批准记录钉住它的 SHA | 若选 D13-1(b)，则只能事后核对 |
| **签发后篡改清单** | 修改清单中的字段 | preflight 产物记录 `AUTHORIZATION_MANIFEST_SHA256`，producer 在写入前再次校验，consumer 又与清单文件的实际 SHA 比对；账本事件（若采纳 D13-3）也记录该 SHA。（注意：Registry 的 claim **不**记录清单 SHA，它只记录授权/attempt/evaluation ID、Freeze SHA、基准 SHA 和用例指纹。） | 在 preflight 之前的窗口内，需要 `--verify` 与账本事件交叉核对 |
| **时钟操纵** | 回拨时间使 preflight"先于"签发 | I12：签发时间必须晚于 Freeze 和账本最后事件；consumer 的新鲜度检查要求 preflight 晚于签发 | 本机时钟被整体操纵无法防御 |
| **部分写入** | 签发中途崩溃 | 清单要么完整要么不存在（`O_EXCL`＋`fsync`＋读回）；残缺文件会被 reducer 视为 `INCONSISTENT`，fail-closed；`ISSUED_UNRECORDED` 可补记 | 残缺清单需要人工清理（同 AR-12 的 R-1，须你批准） |
| **输入被替换为他处的评估数据** | 把别的基准或用例身份写进清单 | 评估身份只取 Freeze 的 `bound_identities`，并用 `verify_frozen_inputs` 对磁盘文件再验证 | 低 |
| **误操作/自动化** | Agent 或脚本在无人在场时签发 | 默认只读；写入需要交互终端和键入确认标记；没有无人值守模式 | 低 |

## 9. 人工确认环节

| 编号 | 环节 | 内容 |
|---|---|---|
| H1 | 批准记录 | 你核对 Freeze SHA、签发器 SHA、指针 SHA 与第 3 节每一条 |
| H2 | `--plan` | 打印将写入的完整清单和 SHA，不写任何东西，你检查 |
| H3 | 键入确认标记 | `ISSUE-R11-AUTH-` 加清单 SHA 前 12 位 |
| H4 | 签发后 `--verify` | 清单、账本事件、活跃授权数（恰为 1）、状态（`ISSUED_EXECUTABLE`、消费计数 0）逐项核对 |
| H5 | 之后的 preflight 与正式执行 | 各自单独批准 |

## 10. 时序

`AR-14 退役 r10` → `AR-12 指针` → `Freeze 创建`（单独批准）→ **`AR-13 签发`** → `preflight` → `执行预提交门` → 正式执行。

AR-13 的第一个写入发生在 AR-14 和 AR-12 之后，所以签发器的前置条件 I6（旧授权不可执行）与 I1（指针存在）自然成立。

## 11. 需要你审批的决定点

| 编号 | 决定 | 选项与建议 |
|---|---|---|
| D13-1 | 签发器放在哪里 | (a)**建议**：替换 Freeze 的第 7 号成员（原 r7 签发器），使签发器受冻结覆盖；需要修改 builder 的成员清单、映射和相关测试，成员数仍为 20；(b) 作为不受冻结覆盖的操作脚本，仅靠 SHA 记录事后核对 |
| D13-2 | 每个 Freeze 修订只允许一份授权 | 建议采纳（固定路径加 `O_EXCL`）。若你想允许同一修订下按序号重新签发，需要引入序号并重新评估"恰好 1 个活跃授权"的论证 |
| D13-3 | 是否在账本里追加 `AUTHORIZATION_ISSUED` 事件 | (a)**建议**：追加，对现有代码惰性（E5），提供篡改检测和审计；(b) 仅清单，与 r7 一致，更简单但没有签发记录 |
| D13-4 | 事件追加之后 consumer 是否也交叉核对 | 建议先不改 consumer（它已钉住 SHA，改动会触发 AR-10 的重新审定）；先由 `--verify` 和人工清单核对承担 |
| D13-5 | 清单模板的白名单来源 | 建议取自被钉住 SHA 的 r10 清单，并随批准记录一起审定键集合 |
| D13-6 | 授权 ID 前缀 | 建议 `auth-step9_63c_r11-<uuid4hex>` |
| D13-7 | 序列与时序 | 确认 `AR-14 → AR-12 → Freeze → AR-13`，以及 AR-14 的判定文件引用批准记录 |

## 12. 将修改或新增的文件

**修改**
- `scripts/build_step9_63c_r11_runner_freeze.py`（D13-1(a)：`MEMBER_PATHS` 第 7 项与 `REPLACED` 映射改为 r11 签发器，并在 `assemble_candidate` 中记录签发器 SHA；另外新增只读的"验证已落盘 Freeze"入口以支持 I4；builder SHA 变化）
- `record.md`、readiness matrix 的后续版本

**新增**
- `scripts/issue_step9_63c_r11_authorization.py`（替换原 r7 签发器在 Freeze 里的位置；r7 签发器文件本身保留，不修改）
- `tests/test_step9_63c_r5c10ag_authorization_issuer.py`（仅使用临时根，覆盖第 3、4、6、7、8 节的每条，附变异验证）
- 测试清单的新版本（与 AR-12 的新增测试一起升级）
- `evaluation/v1_2_3/step9_63c_r11_activation_approval.json`（你签署，AR-12 与 AR-13 共用）
- 签发时才产生：`evaluation/v1_2_3/step9_63c_r11_v3_authorization_manifest.json`，以及账本末尾追加的一行 `AUTHORIZATION_ISSUED`

**不会修改**：resolver、consumer、adapter、`authorization_lifecycle.py`、r7 签发器、r10 的任何成员和历史清单；账本只追加，不改动已有字节。
