# Step 9.63c-r5c10af 变更报告

状态：`PASS_FIVE_DECISIONS_APPLIED_GUARD_V3_CANDIDATE_NOT_APPROVED_DESIGN_DRAFTS_ONLY`

开始时快照与上一步结束时零漂移（2,458 个文件）。AR-10 钉住的两个 SHA 全程未变：resolver `a0f5670d3834d5f91391b41a33fbac669d6162587bc620e9bd3acf202aa3c6a5`，consumer `297558393e56c645fb02b4ec45d4af41486b504034bdd717237b7738a21f4879`。

全量回归（两次逐项一致）：**805 收集 / 774 通过 / 2 失败 / 29 错误 / 4 个导入阻断模块**。细节见 `step9_63c_r5c10af_regression_results.json`。

## 逐项决定

### 1. AR-7：新建 r5c10ae 版本化测试清单

- **新增**：`scripts/validate_step9_63c_r5c10ae_test_boundary.py`、`evaluation/v1_2_3/step9_63c_r5c10ae_test_boundary_manifest.json`（73 个模块，31 个允许运行，等于被钉住的允许列表）、`tests/test_step9_63c_r5c10ae_test_boundary_manifest.py`（11 个测试）。
- **版本钉死**：validator 用常量指定清单路径和版本号 `r5c10ae`，代码里没有任何目录发现类调用（测试用语法树检查），也没有"取最新"的逻辑。旧清单 r5c10ad 的 SHA（`acf0b429…`）写成常量并在每次审计时核对；清单中从旧版沿用的行，其决定字段（是否允许、理由、范围、来源、用途）一个都不能变。
- **复现性**：r5c10ae 清单可由当前源码逐字节重新生成。
- **变异验证**：5 个变异全部被检测到。第一轮有 1 个存活（沿用的决定字段检查），原因是我的篡改用例碰到的是被更底层检查先拦截的行，所以补了一个专门篡改"机械推导行"的用例。
- **覆盖变化**：无损失。r5c10ad 清单原样保留。

**需要你确认的推论：对 r5c10ad 旧测试的改动。** 新增测试模块使 r5c10ad 清单不再覆盖当前全部模块，它自己的两个测试因此必然失败。"保留 r5c10ad 清单"并没有说明这两个测试怎么办，我的做法是把它们限定在**该清单自己记录的 69 个模块**上（用指向真实源码的符号链接视图），而"覆盖当前全部模块"这条断言移到 r5c10ae 的测试里。证据：用同一套规则重新推导，这 69 行与 r5c10ad 清单**逐行完全一致**，说明旧清单没有过时。同时我加了两条防止空洞化的断言：旧清单字节被钉住；它记录的模块一个都不能从 `tests/` 里消失。这份改动单独成一个 diff（`step9_63c_r5c10af_ar7e_adtest.diff`），可单独否决或回退。

### 2. 退役 2 项 r5 UNCOVERED 测试

- 按 AR-2 流程：`test_multiple_active_authorizations` 与 `test_historical_pin_mismatch` 已从活动文件移出。原文件早已逐字节归档（`tests/retired/test_step9_63c_r5_mac_local_preflight.py.retired`，`6becc369…`，其中确有这两个方法），`RETIRED_INDEX.json` 追加了一条记录。
- 新建 `step9_63c_r5c10af_r5_coverage_mapping.json`（r5c10ad 版保留不动）：36 项中 **17 项退役已覆盖、19 项改写、0 项 UNCOVERED**；每个覆盖测试都用本次运行结果程序化核对过确实通过。
- 为了让"54/55 个 pin"这个旧属性有精确对应，在 consumer 门测试里**新增 2 个测试**：`test_historical_pin_count_54_rejected`（旧测试的直接对应）和 `test_inventory_pin_mismatch_rejected`（此前哈希篡改测试只覆盖补充 pin 那一侧，清单内 34 个 pin 那一侧没有覆盖）。
- **变异证明**：9 个变异全部被检测到：去掉"恰好 1 个"检查、去掉绑定 ID 检查、把 consumer 的独立重数换成 producer 的视图；去掉 pin 总检查、清单内哈希检查、补充 pin 哈希检查、账本前缀检查、数量检查，以及让 `execute_formal` 忽略门结果。
- **一处如实说明的差异**：旧的"多个活跃授权"测试还断言"此时不会去查历史 pin"（评估顺序）。新的门是独立评估每项检查并报告全部失败，顺序不是它的属性，所以这个细节没有对应物。

### 3. AR-11 测试替身

- 旧写法的 `patch.dict(sys.modules, …)` 已换成显式的上下文管理器 `scoped_adapter_stub`：安装替身，**总是**还原进入前的状态，并断言 `sys.modules` 条目和 `scripts` 包属性都恢复。
- **与你的文字不完全一致的地方**：项目里没有安装 pytest，用不了 `monkeypatch.setitem`，所以用语义等价的显式 `setitem`/还原代替。另外，当前仓库里真实 adapter 因缺少 r11 指针而**根本无法导入**，所以"恢复为真实模块"在这里表现为"恢复为进入前的状态（不存在）"；r11 存在后同一断言会比较到真实模块对象。新增测试覆盖正常退出和主体抛异常两种情形。
- r11 builder 接口未修改。

### 4. guard v2：补充负向测试（不批准 v2）

- 新建 119 个场景的目录，覆盖你要求的 a–d 四类（以及 `e` 子进程类和 `f` 已知限制类）。每个场景在独立子进程里、在一棵**临时的假仓库**上运行（真实仓库从不作为目标），并且先**不带 guard 跑一遍**以证明场景确有破坏效果。
- **结果**（详见 `step9_63c_r5c10af_guard_negative_results.json`）：

| guard | PASS | 绕过/误报 | 已记录的不可阻断项 |
|---|---:|---:|---:|
| v1（历史证据） | 84 | 30 绕过 + 4 误报 | 1 |
| v2（未批准） | 87 | **31 绕过** | 1 |
| v3 候选 | **118** | **0** | 1（`ctypes` 直接调用 libc） |

- **v2 失守的 11 类**：已存在的硬链接（6）；符号链接之后的 `..`（2）；尾随斜杠穿透符号链接删除仓库目录（1，这是 **v2 相对 v1 新引入的回退**）；对描述符的 `chmod`/`utime`（3）；`mkfifo`/`mknod`（3，根本不触发审计事件）；`sqlite3.connect`（1）；`os.open(..., dir_fd=)`（2，审计事件里没有 `dir_fd`）；根目录的大小写别名（1）；**重命名/删除/改权限仓库的上级目录**（3，一次调用就能搬走或锁死整个仓库）；子进程逃逸（9：`-I`、`-S`、`-E`、合并写法、清空环境、修改环境、`exec`、`posix_spawn`）。
- **你要求的四类里 v2 的表现**：a 类（硬链接）失守；b 类（rename/replace 任一端）全部拦住；c 类（符号链接）在"`..`"和"尾随斜杠"上失守，普通的"删链接允许、经链接写入阻断"是对的；d 类（写入入口）在描述符、`mkfifo`、`sqlite`、`dir_fd`、大小写别名上失守。
- **v3 候选**：在新目录 `step9_63c_r5c10af_test_harness/guard/` 中，是 v2 的加固版，**v1 和 v2 文件一字未动**（SHA 在测试里钉住）。变异检验 22/23 被检测到，剩下 1 个（`shutil.move` 目标检查）是**冗余的纵深防御**：它的行为已被 rename 规则或复制规则覆盖，我在结果里如实标注，没有当作被杀掉。
- **在真实回归里的表现**：v3 与 v2 对其余 793 项的结果逐项一致；guard 阻断 0 次，没有误报。
- **harness 的一个必要改动**：v3 正确地拒绝启动环境被改掉的 Python 子进程，因此"测试 guard 的测试"不能在受保护进程里实时跑场景。`run_all.sh` 新增一个前置步骤：先在 guard 之外跑场景目录，测试模块再校验结果与当前 guard/场景文件的 SHA 绑定；既无结果又处于受保护状态时直接失败，**不 skip**。
- **v3 尚未获批**。回归之所以用 v3 跑，是因为它是 v2 的超集；我另用 v2 的 harness 做了一次对照运行以证明结果不依赖于哪个 guard。

### 5. AR-14：未执行

只记录了顺序：**AR-12/AR-13 设计审定 → AR-14 → 激活（指针、Freeze）→ AR-13 签发**。已核实一个会影响 AR-14 的事实：退役函数只检查判定文件中的 `old_authorization_id` 和 `old_authorization_reuse_status`，不看"当前 Freeze"字段，因此 AR-14 可以在 r11 Freeze 不存在时执行。

### 6. 设计草案（只有文档）

- `step9_63c_r5c10af_ar12_identity_pointer_design.md`
- `step9_63c_r5c10af_ar13_authorization_issuer_design.md`

为了写这两份草案，我核对了代码，修正了自己最初的两处错误：Registry 的 claim **不**记录授权清单 SHA（记录它的是 preflight 产物）；`assemble_candidate` 在 Freeze 已存在时会拒绝，所以"重新组装并与磁盘比对"需要 builder 新增只读入口。这两条已写入草案。另外实测发现本仓库所在的 exFAT 不支持硬链接且 `rename` 会静默覆盖，所以无覆盖的原子创建只能依赖 `O_EXCL`。

## 覆盖是否有净损失

**没有。** 退役的两个测试各有对应：多个活跃授权 ← 1 个直接对应测试；55 个 pin ← 4 个测试（含新增的 2 个）；两者合计 9 个变异证明。AR-7 的两个 r5c10ad 测试被限定在其记录的范围内，同时 r5c10ae 测试接管了"覆盖当前清单"。RC6 的等价覆盖（上一步因清单漂移而暂时失效）现在恢复且通过。没有使用 skip、xfail，也没有放宽断言。

## 本步的非预期决定（需要你确认或否决）

| 编号 | 决定 | 如何单独回退 |
|---|---|---|
| X-1 | 对 r5c10ad 旧测试的限定改动（见 1） | `git apply -R step9_63c_r5c10af_ar7e_adtest.diff` |
| X-2 | AR-11 用显式还原上下文代替不可用的 `monkeypatch.setitem`（见 3） | `git apply -R step9_63c_r5c10af_ar11t.diff` |
| X-3 | 生成 v3 候选 guard 并让回归使用它（未批准 v2，本步用的是超集） | 删除 `step9_63c_r5c10af_test_harness/`；`ar4g` |
| X-4 | consumer 门测试新增 2 个测试，以便旧属性有精确对应 | `ar2r` |

## 回滚

五份独立 diff：`step9_63c_r5c10af_ar7e.diff`、`ar7e_adtest.diff`、`ar2r.diff`、`ar11t.diff`、`ar4g.diff`。在临时副本上按反序 `git apply -R`，**17 个路径全部逐字节恢复**到步骤开始时的状态（包括"被创建的文件应当消失"）。macOS 自带的 BSD `patch` 不能在回退模式下重建文件，所以验证用的是 `git apply -R`。

## 新增/修改文件

**修改**：`tests/test_step9_63c_r5c10ad_test_boundary_manifest.py`、`tests/test_step9_63c_r5c10ae_builder_pins.py`、`tests/test_step9_63c_r5c10ae_consumer_precommit_gate.py`、`tests/test_step9_63c_r5_mac_local_preflight.py`、`tests/retired/RETIRED_INDEX.json`、`record.md`。

**新增**：`scripts/validate_step9_63c_r5c10ae_test_boundary.py`、r5c10ae 清单及其测试、`tests/test_step9_63c_r5c10af_guard_negative.py`、`step9_63c_r5c10af_test_harness/`（v3 候选 guard、场景目录、运行脚本）、`step9_63c_r5c10af_mutation_tools/`、各类报告与 JSON、五份 diff、两份设计草案。

**未触及**：r10/r11 冻结成员、adapter、`authorization_lifecycle.py`、账本、历史 Trace、历史清单、9.51a 清单、r5c10ad 清单、v1 与 v2 的 guard。
