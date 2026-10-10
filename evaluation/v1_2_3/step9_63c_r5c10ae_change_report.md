# Step 9.63c-r5c10ae — AR-17 / AR-10 / AR-11 变更报告

状态：`PASS_AR17_AR10_AR11_IMPLEMENTED_TWO_ITEMS_STOPPED_FOR_APPROVAL_R11_FREEZE_NOT_READY`

开始时快照与上一步结束时零漂移（2,434 个文件）。全量回归两次逐项一致：**776 collected / 741 passed / 4 failed / 31 errors / 4 import-blocked**。

## AR-17：consumer 预提交检查接线

缺口清单见 `step9_63c_r5c10ae_consumer_path_audit.md`（G1–G8）。修改文件：`scripts/run_step9_63_v3_formal_execution.py`，SHA 从 `cd0d0706…` 变为 `297558393e56c645fb02b4ec45d4af41486b504034bdd717237b7738a21f4879`。

| 缺口 | 修复 |
|---|---|
| G1 `validate_precommit()` 未接线 | 新增 `prepare_formal_gates()`（只读），在原有绑定检查和 preflight 证据检查之后，执行 `collect_r11_precommit_state()` 与 `validate_precommit(state, R11_PRECOMMIT_KEYS)`。`execute_formal()` 遇到任何失败都会直接 `raise`；冻结 adapter 只在全部通过后才导入，并调用 `adapter.run()`（第一个副作用）。 |
| “检查没有执行”也必须失败 | 每项检查单独执行；抛出异常时记入 `checks_not_executed` 并取值 False。`validate_precommit` 对缺失的键、非 `True` 的值，以及每个未执行的检查都报失败。 |
| G2 55 个历史 pin | 新增 `verify_historical_pins()`：34 个清单 pin + 20 个补充 pin + 账本 1161 字节前缀，合计 55。真实仓库验证结果 55/55。采用前缀语义（G8），没有复用 62b 的整文件哈希函数。 |
| G3 “恰好 1 个活跃授权” | consumer 独立调用 `lifecycle.active_authorizations(root)` 重新计数，要求结果恰为 `[authorization_id]`，不依赖 producer。 |
| G4 `main()` 写死值 | `precommit_failures` 和 `ready_for_controlled_execution` 改由真实检查结果决定；删除写死的 `atomic_commit_implemented: True`。未提供授权和 preflight 时，返回 `precommit_not_evaluated:…`（fail-closed）。 |
| G7 旧授权仍可执行 | 新增两项检查：非当前版本的 V3 授权必须全部不可执行。**后果：在 r10 授权退役（AR-14）之前，正式 r11 执行会被 fail-closed 阻断（R22）。** |
| 新发现 | 旧 r6 审计读取的 `formal_execution_commit_protocol` 字段在 lifecycle 合约中并不存在。原子提交和崩溃恢复两项检查改为读取 r11 freeze 钉住的原子提交合约 `step9_63a_r1_atomic_commit_contract.json`（先校验 SHA）。 |

`validate_precommit(state)` 的默认参数仍为原来的 24 个旧键，旧测试 23/23 通过，行为不变。

- **未修改**：adapter、`authorization_lifecycle.py`、账本、任何 r10 字节。G5 中的 r6 时代死代码 `audit_current_state()` 不在 r11 路径上，仅记录、未改（属于范围外）。
- **测试**：`tests/test_step9_63c_r5c10ae_consumer_precommit_gate.py`，28/28 通过。
  - 1 个正向对照（一致的 fixture 全部检查通过）。
  - 每个检查点都有负向测试：pin、账本前缀、清单缺失、第二个活跃授权、本授权已退役、旧授权仍可执行（含真实的 r10 授权）、agent 或冻结身份不符、adapter 不可用（检查未执行）、授权已消费、attempt 或命名空间已存在、命名空间绑定不符、用例或评估身份不符、formal entry 或 freeze 绑定不符、lifecycle 或原子提交合约被篡改、preflight 未验证、项目根不符。
  - 每个负向测试都断言临时根和仓库证据目录**没有任何写入**。
  - 另有 `prepare_formal_gates` 的端到端行为测试，以及 `execute_formal` 在 adapter 之前抛出异常的测试。
- **关于测试替身**：adapter 只能通过 `collect_r11_precommit_state` 的显式参数 `adapter_module` 替换；正式路径永远传 `None`，即真实 adapter。冻结函数 `active_authorizations()` 总是读取仓库账本，这一点已在测试中注明。

## AR-10：钉住 resolver 与 consumer 的 SHA

`scripts/build_step9_63c_r11_runner_freeze.py`：

| 常量 | 文件 | SHA-256 |
|---|---|---|
| `RESOLVER_SHA256` | `scripts/v3_runner_identity.py` | `a0f5670d3834d5f91391b41a33fbac669d6162587bc620e9bd3acf202aa3c6a5` |
| `CONSUMER_SHA256` | `scripts/run_step9_63_v3_formal_execution.py` | `297558393e56c645fb02b4ec45d4af41486b504034bdd717237b7738a21f4879` |
| `SCANNER_SHA256`（原有） | `scripts/v3_execution_transaction.py` | `f0e74a49d152053b5455951c507edb8f7849a9e4708835711e5975a82e690e91` |

- 删除了“只要与 r10 不同就接受”的逻辑。现在三个 CHANGED 成员都必须精确等于 `CHANGED_SHA256` 中的值，并且 pin 表必须恰好覆盖 CHANGED 集合。
- 测试：`tests/test_step9_63c_r5c10ae_builder_pins.py` 中的 4 项（含“与 r10 不同但未经审定”的负向测试）。

## AR-11：内联 `verify_frozen_inputs`

- 把 `sha256_bytes`、`nonsecret_model_configuration_matches`、`verify_frozen_inputs` 三个函数从 r5c4 builder **逐字复制**过来（由程序提取，并验证文本一致），`build_candidate()` 不再 import r5c4。成员数仍为 20，r5c4 builder 不是成员。
- 等价性证明：
  - 静态：三个函数的源码与原函数完全相同。
  - 差分：14 个场景（1 个对照 + 13 个篡改）中，原函数与内联版本给出完全相同的结果（`None`，或相同的异常类型和消息）；对照场景在真实仓库上通过。
  - 差分测试使用了一个**仅限测试作用域**的 adapter 替身（`patch.dict(sys.modules)`，测试结束即恢复），原因是两个函数都在内部 import adapter。**这与 AR-17 的显式参数注入方式不同，请审查。**

builder SHA 从 `c2924475…` 变为 `eaa113dab72961846003958050027490f495945f995a3d77e92b7a323a3733bc`。builder 属于 REPLACED 成员，它的 SHA 会在正式建 freeze 时记入成员清单。

## 变异测试

29/29 KILLED，全部由行为测试的实际失败判定（AR-17 24 个、AR-10 2 个、AR-11 3 个）。见 `step9_63c_r5c10ae_mutation_results.json`。

基于源码检查的测试不计为变异检测证据，因为对 `exec` 生成的变异函数调用 `inspect.getsource()` 会读到文件中无关的行。我为此补充了 `prepare_formal_gates` 的行为测试。

## guard v2 与 v1 的差异（未改动，供审查）

只有 `guard/sitecustomize.py` 不同；其余 6 个 harness 文件逐字节相同。差异如下：

- 新增 `_ENTRY_EVENTS = {os.remove, os.rmdir, os.rename, os.replace, os.symlink, os.link, shutil.rmtree}`。
- 对这些“目录项级”操作，`_protected()` 只解析父目录的真实路径再拼上文件名（v1 会解析整条路径，所以把“删除临时目录中指向仓库的符号链接”误判为删除仓库文件）。
- 其余操作（`open` 写入、chmod、utime、chflags、复制或移动目标）仍解析到最终目标。

残余风险：对一个指向仓库目录的符号链接调用 `shutil.rmtree`，入口事件会被放行；此时依赖 Python 自身拒绝对符号链接执行 rmtree（3.12 会抛出 `OSError`），而且其下逐项删除的父目录都在仓库内，仍会被阻断。自测 21/21 通过。

## 停下报告、未执行的事项（按“超出范围先停下”规则）

1. **AR-7 清单漂移（2 个失败）**：本步新增了 2 个测试模块，r5c10ad 清单测试正确检测到清单与实际不符。修复需要重新生成或版本化 r5c10ad 清单，或修改 r5c10ad 的 validator。
2. **2 项 RC9（原 UNCOVERED）现在已有覆盖**：`test_multiple_active_authorizations` 对应新的 `test_second_active_authorization_rejected`；`test_historical_pin_mismatch` 对应新的 `test_historical_pin_mismatch_rejected` 和 `test_ledger_prefix_tamper_rejected`。按 AR-2 流程退役需要批准。

## 回滚

按 ar11 → ar10 → ar17 逆序执行 `git apply -R`。已在 scratch 副本上验证，4/4 个路径逐字节恢复到本步基线。
