# AR-12 设计草案：r11 正式身份指针的创建流程

状态：`DRAFT_DESIGN_ONLY_NOT_IMPLEMENTED`

本文档只描述方案。本步没有创建指针、Freeze、Registry 或授权，也没有写任何可执行代码；文中出现的命令名和函数名都是**拟议名称**，不对应现有文件。

## 1. 目标与非目标

- **目标**：给出一个可审计的流程，把 `evaluation/v1_2_3/step9_63c_r11_current_runner_identity.json` 创建出来，并保证过程幂等、不可覆盖、失败可恢复，且关键环节由人确认。
- **非目标**：本文不创建 r11 Freeze，不签发授权（见 AR-13），也不退役 r10 授权（AR-14）。指针只是 Freeze 之前的第一个不可逆产物。

## 2. 已核实的事实

| 编号 | 事实 | 证据 |
|---|---|---|
| E1 | 指针路径、Freeze 路径和修订号是 resolver 里的常量，不是输入：`step9_63c_r11_current_runner_identity.json`、`step9_63c_r11_runner_freeze.json`、`r11`。`load_identity_config` 只校验 4 个字段（`artifact_type`、`status`、`runner_freeze_revision`、`runner_freeze_path`），拒绝符号链接和非普通文件，返回指针的 SHA-256。多余字段被忽略。 | `scripts/v3_runner_identity.py` |
| E2 | **创建顺序是被代码强制的**：`assemble_candidate()` 先调用 `load_identity_config(root)`，把指针 SHA 写入 Freeze 的 `identity_config_sha256`；指针又是 Freeze 20 个成员中的第 13 个。所以指针必须先于 Freeze 存在且内容最终确定；Freeze 创建后，指针字节被钉住，再改动会使 Freeze 失效。 | `scripts/build_step9_63c_r11_runner_freeze.py` |
| E3 | 指针存在而 Freeze 不存在的期间，`resolve_current_freeze` 抛出"freeze missing"，所有 r11 消费者 fail-closed；但冻结 adapter 的导入时读取（`load_identity_config`）会成功。结果：目前 4 个导入阻断模块开始能导入，RC1 的 29 个运行时错误开始真正执行，**回归结果会变化**。 | resolver 与 adapter 第 25 行 |
| E4 | 现有先例：`persist_candidate` 用 `O_CREAT\|O_EXCL\|O_WRONLY`，写入后对文件和所在目录各做一次 `fsync`，并在写入前重新组装一次确认候选内容未变。 | builder |
| E5 | 本仓库所在的 exFAT 卷**不支持硬链接**（`os.link` 返回"Operation not supported"），`rename` 会**静默覆盖**已存在的目标，`O_EXCL` 生效，`flock` 可用。因此"先写临时文件再 link"这类无覆盖的原子发布做不到；`O_EXCL` 是唯一可用的"不覆盖"原语。（已在仓库之外的临时目录实测，探测目录已删除。） | 本步实测 |
| E6 | 命名空间预留、事务提交、退役和 r7 签发器共用同一把文件锁 `evaluation/v4_runs/.namespace-allocation.lock`（`lifecycle_lock`）。 | `scripts/authorization_lifecycle.py` |
| E7 | 当前状态：无 r11 指针、Freeze、Registry；r10 授权 `auth-step9_63c_r5c6-…` 仍是 `ISSUED_EXECUTABLE`；consumer 的预提交检查要求"非当前版本的授权全部不可执行"。 | 回归与只读 reducer |
| E8 | r10 指针除 4 个必需字段外，还带 `step`、`supersedes_for_new_authorization_only`、`execution_permission: false`。 | `step9_63c_r5c4_current_runner_identity.json` |
| E9 | AR-10 已在 builder 中钉住 resolver（`a0f5670d…`）与 consumer（`29755839…`）的 SHA；创建指针**不得**改动这两个文件。 | builder `CHANGED_SHA256` |

## 3. 要创建的对象（拟议规范字节）

沿用 r10 指针的字段结构，序列化规则与 `persist_candidate` 一致（键排序、缩进 2、末尾一个换行）：

```json
{
  "artifact_type": "V3_CURRENT_RUNNER_IDENTITY_POINTER",
  "execution_permission": false,
  "runner_freeze_path": "evaluation/v1_2_3/step9_63c_r11_runner_freeze.json",
  "runner_freeze_revision": "r11",
  "status": "FROZEN_IDENTITY_POINTER_NOT_AUTHORIZATION",
  "step": "9.63c-r11",
  "supersedes_for_new_authorization_only": "evaluation/v1_2_3/step9_63c_r5c5b_runner_freeze_r10.json"
}
```

- 389 字节，SHA-256 **`4e077781faeecee57da02f37d1d3ad8cdc9dfa895d3eb72b1b4ab1f1d3f696fe`**。
- 这个值是在本步按上述格式计算出来的（未写入任何文件），请你逐字核对。如果你在决定点 D12-2 改变了格式，这个值必须重新计算并重新审定。
- 字节完全由 resolver 常量和 r10 Freeze 路径决定，**创建流程里没有任何自由输入**。这样"创建内容是否正确"就简化为"字节是否等于已审字节"。

## 4. 谁触发、输入哪些已审 SHA

**触发者**：只有你（人）在自己的终端里，用交互方式运行。不允许定时任务、CI 或 Agent 会话触发；Agent 只能运行只读的 `--plan` 和 `--status`。

**输入**：一份由你审定并签署的激活批准记录（拟议名称 `step9_63c_r11_activation_approval.json`），在创建时校验，内容如下：

| 钉住项 | 来源 |
|---|---|
| 拟创建指针的 SHA-256（第 3 节） | 本文 |
| resolver、consumer、scanner 的 SHA | builder 常量：`a0f5670d…`、`29755839…`、`f0e74a49…` |
| builder、r11 producer、（若 AR-13 采纳）r11 issuer 的 SHA | 审定当天的实际字节 |
| 14 个未变成员的 SHA | 等于 r10 manifest 中的值 |
| r10 Freeze manifest、r10 授权 manifest、账本前缀（1161 字节） | `d2424423…`、`beac52d1…`、`ca168f69…` |
| 最近一次受保护全量回归的结果文件 SHA、各类失败的数量 | 回归报告 |
| 全仓状态聚合哈希 | 快照工具计算：保证批准后没有任何文件变化 |
| AR-14 已完成的证据（账本中 r10 授权的退役事件 ID） | 账本 |

批准记录本身会被写入创建记录，并在以后被 AR-13 的签发器引用。

## 5. 前置条件（全部只读；任何一项失败即中止，不写任何东西）

1. 指针、Freeze、Registry、r11 授权都不存在，也不是符号链接。
2. 批准记录存在，哈希等于你给出的值；其中每个钉住项都等于当前实际字节。
3. 全仓状态聚合哈希等于批准记录中的值。
4. 账本中 r10 授权已有终态退役事件，并且 reducer 判定其不可执行（AR-14 已完成）。
5. 非当前版本的所有 V3 授权，经 reducer 判定均不可执行。
6. 55 个历史 pin 全部通过（复用 consumer 里的 `verify_historical_pins`）。
7. 没有任何事务日志、命名空间标记或 attempt 账本引用 r11 相关标识。
8. 已取得 `lifecycle_lock`（见第 6 节）。
9. 当前在 macOS、项目 `.venv`、项目根目录，且是交互终端（`isatty`）。

## 6. 创建步骤（幂等且原子）

| 步 | 动作 | 说明 |
|---|---|---|
| C0 | `--plan`（默认）：执行第 5 节全部检查，打印规范字节、SHA 和待创建路径；**不写** | 任何人都可运行 |
| C1 | 取 `lifecycle_lock` | 与事务提交、退役、签发互斥 |
| C2 | 在锁内**重新**执行第 5 节全部检查 | 防止检查与创建之间状态变化 |
| C3 | 人工确认：终端要求你输入 `CREATE-R11-POINTER-` 加规范 SHA 的前 12 位 | 见第 9 节 |
| C4 | `O_CREAT\|O_EXCL\|O_WRONLY\|O_NOFOLLOW` 创建目标路径，一次写入规范字节，`fsync` 文件，`fsync` 目录 | 这是唯一的写入点 |
| C5 | 立即重新读取，要求逐字节等于规范字节，且 SHA 等于批准记录 | 不符则进入 F4 |
| C6 | 以 `O_EXCL` 写创建记录（拟议名称 `step9_63c_r11_identity_pointer_creation_record.json`）：指针 SHA、批准记录 SHA、前置条件快照、时间、操作者确认标记、工具自身 SHA | 记录不能覆盖 |
| C7 | 释放锁，打印 SHA 与下一步提示 | 不自动继续到 Freeze |

**幂等**：重复运行时，若指针已存在，工具只做比较：字节等于规范字节则报告 `ALREADY_CREATED`，退出码 0，不写；字节不同则拒绝，退出码非 0，**绝不自动删除或修复**。

## 7. 防止重复创建与覆盖

- `O_EXCL` 是主防线（E5：这个盘上 `rename` 会覆盖，所以不使用 rename 发布）。
- `lifecycle_lock` 保证同一时刻只有一个创建者。
- 没有 `--force`、`--overwrite` 之类的选项，代码路径里不存在删除或替换指针的函数。
- 创建记录同样用 `O_EXCL`，指针与记录一一对应；只有指针没有记录，或只有记录没有指针，都被 `--status` 判为需要人工介入。

## 8. 失败与回滚

| 编号 | 失败点 | 结果 | 处理 |
|---|---|---|---|
| F1 | C0–C3 任一步失败或你不确认 | 无任何写入 | 修复前置条件后重来 |
| F2 | C4 之前崩溃 | 无指针 | 同 F1 |
| F3 | C4 写入中途崩溃或 `fsync` 失败 | 最终路径上可能有**残缺指针**。resolver 会因 JSON 无效而拒绝，系统 fail-closed | 恢复流程 R-1（见下） |
| F4 | C5 验证不一致 | 同 F3 | R-1 |
| F5 | 指针已创建、C6 失败 | 有指针、无创建记录 | `--status` 报告"缺记录"；重跑即可补写记录（前提：字节等于规范字节） |
| F6 | 指针已创建，但 Freeze 步骤失败 | 指针保持，系统停在"仅指针"状态，仍 fail-closed | builder 的 Freeze 创建本身是幂等的（目标不存在时可重试） |
| F7 | Freeze 已创建之后发现问题 | 指针已被 Freeze 钉住 | **不可回滚**。只能前进：新建修订（r12）及其指针；r11 产物原样保留为历史证据 |

**R-1（残缺指针的恢复）**：由你批准；工具不会自己删除，只打印要执行的确切命令；删除前必须证明 (a) Freeze 不存在，(b) 没有授权、Registry 或创建记录引用它。删除动作与原因写入 `record.md`。这是流程里**唯一**允许的删除。

## 9. 需要人工确认的环节

| 编号 | 环节 | 确认内容 |
|---|---|---|
| H1 | 批准记录签署 | 你核对第 4 节每一项钉住值 |
| H2 | 终端输入确认标记（C3） | 你亲自键入，防止误触和自动化 |
| H3 | 创建后验证签收（第 10 节） | 你核对打印出来的 SHA 与批准记录一致 |
| H4 | 进入 Freeze 步骤 | 单独批准，不随指针一起授权 |
| H5 | R-1 恢复（仅在 F3/F4 时） | 单独批准 |

## 10. 创建后由谁、用什么方式验证

由一个**独立的只读验证命令**完成（拟议 `--verify`），由你在自己的终端运行，Agent 另行出具报告供交叉核对：

1. 指针是普通文件、非符号链接，字节等于规范字节，SHA 等于批准记录。
2. 创建记录存在、SHA 一致，并引用同一份批准记录。
3. 用 resolver 解析：此时应得到"Freeze 缺失"这一**预期**的失败，而不是"指针无效"。这证明指针被接受，且 Freeze 缺失时仍 fail-closed。
4. 重新计算全仓快照：除指针和创建记录外，**没有任何文件变化**；r10 manifest、r10 成员、账本前缀、Trace、resolver/consumer 的 SHA 保持不变。
5. 运行受保护全量回归，并对照预先登记的预期表（第 12 节）。

## 11. 与其他步骤的顺序

`AR-14 退役 r10 授权` → **`AR-12 创建指针`** → `builder 创建 Freeze`（单独批准）→ 验证 → `AR-13 签发 r11 授权` → preflight → 正式执行。

**已核实的约束**：退役函数只检查判定文件中的 `old_authorization_id` 和 `old_authorization_reuse_status`，不检查"当前 Freeze"字段（其中 `current_runner_equality_required` 在 r8 判定里是 `false`）。因此 AR-14 完全可以在 r11 Freeze 不存在时执行；判定文件里的 r11 字段应引用批准记录，而不是尚不存在的 Freeze SHA。

## 12. 对回归的影响（须预先登记预期）

- 仅有指针时：4 个导入阻断模块可导入，29 个运行时错误项开始执行。预期它们以"Freeze 缺失"这类 fail-closed 的方式失败，或暴露此前被导入错误掩盖的 r10 时代假设。
- Freeze 创建后：这些测试第一次对真实的 r11 身份运行。**目前无法预测**其中多少会通过，预期会有新的契约冲突需要逐项归类（这部分结果目前是 `NOT_MEASURED`）。
- 建议在"仅指针"和"指针加 Freeze"两个状态各跑一次受保护回归，并在运行前写下预期表；与预期不一致的项目先分类再决定，不得为了变绿而改测试。

## 13. 本流程特有的威胁

| 威胁 | 防御 |
|---|---|
| 伪造或篡改指针 | 规范字节无自由输入；创建后与批准记录的 SHA 比对；Freeze 之后由 Freeze 钉住 |
| 创建时被他人覆盖或竞争创建 | `O_EXCL` 加文件锁；没有任何覆盖路径 |
| 误用 r10 指针作为回退 | resolver 只接受 r11 常量；已有测试覆盖 |
| 批准后文件被改动 | 全仓聚合哈希在 C2 重验 |
| 自动化或 Agent 误触发 | 必须交互终端加人工键入确认标记 |
| 创建工具本身被替换 | 方案 P1：工具放进 builder（Freeze 成员）；其 SHA 写入创建记录 |

## 14. 需要你审批的决定点

| 编号 | 决定 | 选项与建议 |
|---|---|---|
| D12-1 | 创建逻辑放在哪里 | (a)**建议**：放进 r11 builder，作为 Freeze 成员受冻结覆盖，builder 的 SHA 变化（它没有被钉住自身）；(b) 独立的操作脚本，不受冻结覆盖，只靠创建记录里的 SHA 事后核对 |
| D12-2 | 规范字节格式 | 建议沿用 r10 的字段加键排序、缩进 2；若你要精简字段，需重算 SHA |
| D12-3 | 原子性策略 | (a)**建议**：`O_EXCL` 加 `fsync` 加读回验证（唯一在 exFAT 上可行的无覆盖方案，接受 F3 的残缺窗口，靠 R-1 恢复）；(b) 把指针发布到 APFS 再复制到仓库（引入新的失败面，不建议） |
| D12-4 | 是否接受"仅指针"这一中间状态 | 建议接受，但要求与 Freeze 创建在同一次受监督会话中完成，并提供 `--status` |
| D12-5 | 批准记录由谁起草、何时签署 | 建议由 Agent 起草，你逐项核对后签署；签署前不得有任何写操作 |
| D12-6 | R-1 恢复策略 | 建议：仅人工批准的删除，且只在证明 Freeze 与引用都不存在时 |
| D12-7 | 回归预期表的验收口径 | 建议：与预期不一致的项目先分类，由你决定是否可接受后才继续 |
| D12-8 | 顺序 | 确认 `AR-14 → AR-12 → Freeze → AR-13`，以及 AR-14 的判定文件引用批准记录而不是 Freeze SHA |

## 15. 将修改或新增的文件

**修改**
- `scripts/build_step9_63c_r11_runner_freeze.py`（D12-1(a)：新增指针规范字节、创建、验证、状态函数和命令行入口；AR-13 还需要同一个文件新增"验证已落盘 Freeze"的只读入口，两项改动应合并为一次 builder 修订并一次性重新审定；r11 REPLACED 成员，SHA 随之改变）
- `evaluation/v1_2_3/step9_63c_r5c10af_r11_freeze_readiness_matrix.json` 的后续版本（记录状态）
- `record.md`

**新增**
- `tests/test_step9_63c_r5c10ag_identity_pointer_creation.py`（仅使用临时根，覆盖第 5–8 节的每一条，并附变异验证）
- 测试清单的新版本（新增测试模块会使 r5c10ae 清单过期，需要 r5c10ag 版本及其 validator）
- `evaluation/v1_2_3/step9_63c_r11_activation_approval.json`（你签署）
- 激活时才产生：`evaluation/v1_2_3/step9_63c_r11_current_runner_identity.json`、`evaluation/v1_2_3/step9_63c_r11_identity_pointer_creation_record.json`

**不会修改**：resolver、consumer、adapter、`authorization_lifecycle.py`、账本、r10 的任何成员和历史清单。
