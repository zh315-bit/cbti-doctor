# Step 9.63c-r5c10ak 变更报告：激活后测试修复

**一句话**：危险测试已全部隔离，全量回归两次逐项一致、只剩 RC5、RC6；新增一道不依赖 guard 的会话级硬防护；真实激活状态（账本、r11 授权清单、Freeze、指针、`evaluation/v4_runs/` 目录树）在本步开始前、每次回归之间和结束后**完全不变**。没有修改任何冻结成员或生产代码，没有运行任何写入入口、preflight 或 execute_formal，没有 commit、没有 push。

## 1. 危险测试审计（`step9_63c_r5c10ak_dangerous_test_audit.json`）

方法：在 guard v3 下逐模块运行全部测试，并加一个只记录不拦截的审计钩子，记下每个测试对真实根下 `evaluation/v4_runs/`、账本、r11 授权清单的每一次访问（读和写）；被拦截的写入来自 guard 日志。

| 类别 | 数量 | 处置 |
|---|---|---|
| **试图写真实根**（创建 `evaluation/v4_runs`、以写模式打开 `.namespace-allocation.lock`） | **1 个测试**（`test_step9_63a_r1_production_integration…test_real_parent_rejects_prepared_before_agent_boundary`），2 次尝试，均被 guard 拦截 | 所在模块整体归档，原样在临时镜像根上运行；该测试在镜像里通过 |
| 通过生产代码的默认路径**读取真实激活状态**（账本、r11 清单、运行根、事务日志） | 11 个模块：55a、58a、59a、63a_r1、63a_r2、63c_r3、r5c5b、63_v3、28、30a、30c，再加 ae gate 模块直接读真实账本与历史钉 | 12 个模块全部按常设规则归档（原字节在 `tests/retired/`），由 `test_step9_63c_r5c10ak_isolated_*` 包装模块把**原文件原样**放到临时镜像根上运行 |
| 已经在临时根上、只把真实文件当**复制源**读取 | r5c10ag/ah/ai 套件、ai V2 归档重放 | 保留；共享夹具按你的决定只取账本被钉住的 3856 字节前缀，并排除 r11 清单 |

临时镜像（`tests/legacy_isolation.py`）：`scripts/`、`tests/`、`evaluation/` 下的 Python 文件、`evaluation/v4_runs/` 整树、账本、所有授权清单、r11 产物和全部被钉住的成员/历史钉文件都是**复制**；其余只读符号链接。镜像里的子进程同样安装会话级硬防护，保护的是**真实**仓库。

## 2. 会话级硬防护（不依赖 guard）

`tests/session_safety.py`：在测试进程里安装审计钩子，任何对真实激活状态的**写入类**访问（以写/追加/创建/截断方式打开，mkdir、rename/replace 两端、remove、rmdir、truncate、rmtree、link/symlink、chmod、utime、copyfile/move 落到其上，以及删除或移动其祖先目录）立刻 `os._exit(86)`，整个测试会话失败、不会写一半。路径用 realpath 解析（相对路径、符号链接别名都算），删除/改名类按“目录项本身”解析（不会把临时目录里指向真实文件的符号链接误判为真实文件），`dir_fd` 相对路径按该目录解析。读不受限。

安装位置：`tests/test_000_session_guard.py`（排序第一，unittest 发现和 CI 加载器都会最先导入它）、CI 加载器（显式安装）、r5c10ak 测试 harness（每个模块进程最先安装）。

- 负向测试 8 个（含 25 种写入场景，全部在子进程中、针对临时假仓库执行，失败的防护也碰不到真实状态）。
- 变异验证：24 个变异体，19 个被杀；5 个幸存者都是等价变异（例如 `open()` 的审计事件同时带有计算后的 flags，所以“追加模式字符”检查被 flags 检查覆盖）。
- **本步中它确实拦住过一次**：第一版对 `shutil.rmtree` 用 `dir_fd` 删除临时目录时做了误判，在一次变异运行中停止了会话；真实状态核对未变。随后加了 `dir_fd` 解析和对应的正反测试，变异验证覆盖这一点。

## 3. 按你的决定处理的测试（`step9_63c_r5c10ak_coverage_mapping.json`）

| 项 | 处置 |
|---|---|
| `PROPOSED_fixture_update.diff` | 已应用 |
| 2 个“真实仓库无 r11 指针”断言 | 归档退役；该属性现在对**每个**测试由会话级硬防护与真实状态核对强制 |
| 3 个 r5 预检测试 | 归档退役；其中“探测前后状态变化”在 r11 producer 上**没有任何测试**，因此新增 `test_step9_63c_r5c10ak_r11_producer_recheck.py`（5 个测试；去掉 producer 的复核会让其中 4 个失败） |
| 2 个 ae gate 测试 | 归档退役，映射到 ae 的“可执行的被取代授权被拒绝”“未执行的检查算失败”等测试 |
| 13 个遗留测试 | **5 个改写**（55a×4、58a×1：属性是 adapter 自己的检查，其他地方没有覆盖；测试**函数对象原样复用**，期望错误文本一个字没改，只是让 reducer 的默认路径指向带合成授权清单和空账本的临时根）；**8 个退役**（59a×5、63a_r1×1、63a_r2×2：属性已被覆盖） |
| r5c10ai 清单的 2 个库存测试 | 常设规则，被 r5c10ak 清单取代 |

变异证明：16 个变异体（每个被退役或改写的属性一个），16 个被杀。

## 4. GitHub CI（`step9_63c_r5c10ak_ci_test_set.json`）

CI 加载器现在在导入任何测试模块之前安装会话级硬防护；artifact-bound 排除列表把 28/30a/30c 换成了它们的包装模块。CI 运行 82 个模块，**其中没有任何一个原先读写真实激活状态的遗留模块**（都已归档）；它们在 CI 中可见的 9 个包装模块在检出副本的临时镜像上运行。本地按 CI 的方式（同一段加载器、`python -` 从标准输入、工作流 env）完整跑了一遍：1049 个测试，13 个失败，0 错误，会话级硬防护停止 0 次：

- 1 个是 RC6（51a）：真实 CI 里激活前就失败（RC5 所在的 43a 在 CI 中被排除）。
- 12 个是 af guard 负向模块：它检测到自己运行在 guard 下、又没有 `CBTI_GUARD_NEGATIVE_RESULTS` 时会主动失败，要求走 af harness。这是因为本步硬性要求全程开启 guard，我在本地 CI 运行里也加了 guard v3；真实 CI 没有 guard，不会触发。harness 回归里这 12 个全部通过。为遵守“全程开启 guard”，我**没有**在关掉 guard 的情况下复跑来证明这一点。

所以真实 CI 的预期结果和激活前一样：只有 RC6 失败。

激活后追踪审计（隔离后重跑一遍）：23 个模块共 2359 次访问真实激活状态，全部是读取（镜像复制源、目录扫描、只读打开），以写模式打开 **0** 次；guard 253 个事件、0 拦截；91 个模块退出码全部为 0。

## 5. 验收

| 项 | 结果 |
|---|---|
| 全量回归两次（guard v3 + 会话级硬防护） | 逐项一致：1131 个测试，1129 通过，失败只剩 RC5、RC6；导入阻断 0；guard 拦截 0；会话级硬防护停止 0；生产回归 0；未知 0 |
| 真实状态不变 | 开始前、两次回归之间、结束后：账本（5 行，与 ef37534 中的字节一致）、r11 清单 `33bd99b9…`、Freeze `bafcec8d…`、指针 `4e077781…`、`evaluation/v4_runs/` 目录树哈希，全部相同（`step9_63c_r5c10ak_real_state_proof.json`） |
| 整仓快照 | 两次回归期间 0 变化 |
| readiness matrix | R16、R39、R40 为 PASS；唯一 BLOCKED 是 R41（preflight 与正式执行）；R15、R16b 为已接受的例外 |

## 6. 改动清单（未提交）

- 新增：`tests/session_safety.py`、`tests/test_000_session_guard.py`、`tests/legacy_isolation.py`、12 个 `tests/test_step9_63c_r5c10ak_isolated_*.py`、`tests/test_step9_63c_r5c10ak_legacy_rewrites.py`、`tests/test_step9_63c_r5c10ak_r11_producer_recheck.py`、`tests/test_step9_63c_r5c10ak_test_boundary_manifest.py`、`scripts/validate_step9_63c_r5c10ak_test_boundary.py`、`evaluation/v1_2_3/step9_63c_r5c10ak_test_boundary_manifest.json`、`evaluation/v1_2_3/step9_63c_r5c10ak_test_harness/`、`evaluation/v1_2_3/step9_63c_r5c10ak_tools/`、16 个 `tests/retired/*` 归档。
- 修改：`tests/r11_activation_fixtures.py`（夹具提案）、`.github/workflows/tests.yml`（安装硬防护、更新排除列表）、`tests/retired/RETIRED_INDEX.json`、4 个测试文件里删除被退役的方法（ag 演练、ah 门禁演练、r5 预检、ai 清单）。
- 删除（已归档）：12 个遗留测试模块。
- `scripts/validate_step9_63c_r5c10ak_test_boundary.py` 是测试清单校验器（测试设施），不是激活相关的生产代码；所有 20 个冻结成员与生产脚本字节未变。

## 7. 需要你知道的

0. **RC6 的失败内容变多了（需要你决定）**：51a 测试仍是同一个已接受的失败，但失败原因在原来的“inventory 不一致”之外多了 3 条 `missing module file`（28/30a/30c）。原因：这 3 个模块被归档到 `tests/retired/`，而历史 51a 清单 `step9_51a_safe_test_manifest.json` 仍登记着它们。我没有改历史清单、测试或期望文本。可选：(a) 接受为 RC6 的扩展；(b) 把 51a 测试按常设规则退役，由 r5c10ak 清单取代。

1. CI 工作流文件改了（安装硬防护、更新排除列表）。这是测试设施，但会在你下次 push 时生效。
2. 会话级硬防护和 guard 一样只看得到本进程（不覆盖 C 扩展、ctypes 和不安装它的子进程）；镜像里的子进程会自己安装。它是防误操作护栏，不是安全边界。
3. 被包装的 12 个遗留模块现在每次运行都要建一个临时镜像（约 0.3–8 秒/模块），总回归时间略增。
