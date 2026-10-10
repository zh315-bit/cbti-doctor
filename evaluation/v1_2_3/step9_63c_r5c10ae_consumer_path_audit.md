# Step 9.63c-r5c10ae — r11 formal consumer 执行路径只读审计

审计对象：`scripts/run_step9_63_v3_formal_execution.py`（修复前 SHA-256 `cd0d0706f76329a23cc26aad18e3c51997a2e2cfd1467aff7c1baf0c55a5ead6`）。
该文件是 r10 清单中的路径（r10 冻结 SHA `ce836355…`），在 r5c10j 中经批准改为 r11 CHANGED 成员。r10 字节早已不在工作树中，r10 manifest 不受影响。本步按 AR-17 的明确授权修改它。

## 执行路径（修复前）

`main --execute-formal-v4` → `execute_formal()`：

1. 导入冻结 adapter 和 parent 的 `supplied_hash_keys`（需要正式身份）。
2. `resolve_current_freeze(ROOT)`：r11 指针、freeze、20 个成员字节、aggregate。
3. 校验 freeze 的 revision、status 和 `formal_entry_runner_sha256`。
4. 检查参数是否齐全，读取授权和 preflight JSON。
5. 15 项字段绑定：revision、freeze SHA、ID、preflight 状态、`*_ready`。
6. `validate_preflight_evidence()`：路径/SHA 钉住、身份与安全字段、连通性、时效；r11 时追加 producer/freeze/registry 来源校验。
7. 检查哈希参数是否齐全。
8. **`adapter.run()`：第一个副作用点。** 进入后依次执行 `validate_frozen_v3_identity` 和 `parent.validate_authorization`（含 `assert_executable_authorization`），然后才执行 `begin_and_commit`（写 journal）、`reserve_namespace`，最后调用 `parent.run`。

## 缺口清单

| # | 缺口 | 证据 | 严重性 |
|---|---|---|---|
| G1 | `validate_precommit()` 未接入 `execute_formal()` | 全文只有定义，执行路径上没有调用；测试只覆盖这个纯函数本身 | 高：24 项预提交条件在正式执行中不生效 |
| G2 | 55 个历史 pin 在 r11 路径上没有检查点 | consumer、adapter、parent 均无此检查；只有 r7 签发器（`historical_pins_match`）和 r10 时代的 62b preflight 有。今天 55/55 匹配（34 个清单 pin + 20 个补充 pin + 账本 1161 字节前缀） | 高 |
| G3 | “恰好 1 个活跃授权”只在 producer 检查 | 只在 `preflight_step9_63c_current_mac_local.validate_authorization_state` 中检查；consumer、adapter、parent 均无（parent 只检查本授权是否可执行） | 高：consumer 依赖 producer 的历史结论 |
| G4 | `main()` 审计输出含写死值 | `"precommit_failures": []`、`"atomic_commit_implemented": True`、`"ready_for_controlled_execution": False` 都是字面量 | 中：审计结果并非来自真实检查 |
| G5 | `audit_current_state()` 是 r6 时代的死代码，含写死值 | 钉死 r6 freeze 和 step9_62 授权 ID；`"parent_validator_pass": True`、`"fresh_connectivity_pass": False`、`"formal_v4_case_executed": 0` 是字面量；会加载密封的 benchmark 用例；`main()` 不调用它 | 低：不在 r11 路径上。仅记录，不修改（属于范围外清理） |
| G6 | `audit_current_runner_non_consuming()` 含三个 `"NOT_ASSESSED_BY_RUNNER_IDENTITY_AUDIT"` 字符串，以及 `ready_for_formal_execution: False` | 如实声明“未评估”，不构成通过声明 | 低：保留，并在 `main()` 中改由真实的预提交结果驱动 |
| G7 | 旧授权仍可执行时，没有任何检查阻断新执行 | `validate_precommit` 中有 `old_authorization_retired` 键，但从未被赋值；今天 r10 授权 `auth-step9_63c_r5c6-…` 经 reducer 判定仍为 `ISSUED_EXECUTABLE` | 中：接入后，在 AR-14 完成前正式执行会被 fail-closed 阻断（符合预期） |
| G8 | 62b `historical_hashes()` 把只追加账本的整个文件 SHA 当作 pin | 账本当前 SHA 为 `aaa2e989…`，与 pin `ca168f69…` 不同；该函数今天必然失败 | 信息：r11 检查必须采用 r7 签发器的前缀语义，不能复用这个函数 |

## 不需要触及冻结成员

- 所有新检查都只**读取**以下模块：`authorization_lifecycle.active_authorizations` / `reduce_authorization_lifecycle`、`append_only_ledger.prefix_matches`、62b 的 `SUPPLEMENTAL_HISTORICAL_PINS` 常量、adapter 的 `current_v3_agent_identity` / `_authoritative_authorization_bindings`、`v3_namespace_allocator.derive_namespace_id`。
- 不修改 adapter、`authorization_lifecycle.py`、账本或任何 r10 字节。
- 检查放在 `adapter.run()` 之前，即任何副作用之前。
