# Step 9.63c-r5c10ac — 修复变更报告（Repair Change Report）

本步完成两个修复批次。两者都只修改非冻结文件，不改变生产语义、身份或授权机制，也没有 skip、xfail、删除测试或修改断言。

## R1：CI 测试加载器（Test Infrastructure Defect）

**根因**
- `unittest.TestLoader.loadTestsFromName` 只把 `ImportError` 转为 `_FailedTest`。
- 冻结适配器在导入时抛出 `RuntimeError`，这会中止整个 CI 加载循环，结果是 0 测试、无报告。

**修改**：`.github/workflows/tests.yml`（Git 跟踪，非冻结）。
- 每个模块的加载包在 `try/except Exception` 中。
- 异常转为一个名为 `import_<module>` 的失败测试，失败时抛出 `ImportError`，消息中包含原始异常类型与内容。
- 排除集合、模块列表、运行器和退出码语义均不变：失败仍会让 CI 退出非零。

**SHA-256**：`3d064509a930b414c19007ccaebdac9c553b1bddbedfe7d8f08a37de0eda7b57` → `b98554b427239b0a4644f9bd57fbf97182162781b183bc172d5adc27d04fb4df`。
差异：`step9_63c_r5c10ac_r1_ci_loader.diff`（+11/−2）。

**验收**
- YAML 解析通过，内嵌脚本 AST 通过。
- 工作树：
  - 修复前：中止，0 tests。
  - 修复后：`Ran 576, failures=4, errors=25`，含 8 个具名的 `import_test_*` 项。
  - 这些数字与 harness 结果减去 CI 的 `artifact_bound` 排除项后逐一吻合。
- 干净 HEAD 导出：修复前后均为 `Ran 277, errors=2`，**test-id 集合完全相同**，覆盖范围没有变化。

## R2：4 个模块的导入延迟（Test Infrastructure Defect：收集方式导致的阻断）

**根因**
- 以下 4 个测试模块在模块级导入身份相关模块（`adapter` 或 `transport`）：
  - `test_step9_63a_r1_production_integration`
  - `test_step9_63a_r2_retirement_eligibility`
  - `test_step9_63c_r5_mac_local_preflight`
  - `test_step9_63c_r5b_preflight_lifecycle`
- 结果是 95 个方法全部无法收集，其中 81 个在静态分析中根本不使用这些模块。

**修改**
- 用确定性的 AST 变换（`defer_import.py`）删除 1 条顶层 import，并把**同一条语句**插入每个直接使用该名称的函数体首行。
- 共删除 4 行、新增 12 行，所有新增行都是原 import 语句的复制。
- 静态检查：42 处名称引用全部有包含它的函数作用域内 import 覆盖，没有残留的顶层 import。
- 修改后的文件与预先在 scratch 中试运行的副本逐字节一致。

**为何不用 `importlib.util.LazyLoader`**：导入失败时，它会把**执行了一半的 adapter 模块**留在 `sys.modules` 中（第 1–24 行已执行，身份未校验）。同一进程中后续的导入会无错误地拿到这个模块，属于 fail-open 风险。函数内 import 在每次失败时都会重新抛错。

| 文件（均为 Git 未跟踪） | 修改前 SHA-256 | 修改后 SHA-256 |
|---|---|---|
| tests/test_step9_63a_r1_production_integration.py | `b5a15e30ccfc9900e86ea81e66de572d46e51744e509e12dfb4040598fae1c15` | `784d4ac88835c312b2af6af134a61b7917063d0ea7963029b13af8067eaf5e12` |
| tests/test_step9_63a_r2_retirement_eligibility.py | `cca6f6d850f99398f4a47e53f89129e98dfb46716bad2d6353a3b7ec1eedf1a6` | `9717646517b97b72c7d22995fb9173fe2f473dc10a385d39a9fdb579e39a5b14` |
| tests/test_step9_63c_r5_mac_local_preflight.py | `3823e68eae92900f23b7fdd9c5f36e667c3bd1d80e5c065c4ac9f1f59104f564` | `6becc369b9eb92347bfd9de064bf35277da15743d9b331efb453b3548e2b78d3` |
| tests/test_step9_63c_r5b_preflight_lifecycle.py | `e5bed6c164bb858eebc70c277c794a1e89442d6d0e38a168fd015cbafc3cbc47` | `2d95a200d286e20ac35fa04f3665abff626ea5846270ca7a36164e0bb371f6c5` |

差异：`step9_63c_r5c10ac_r2_import_deferral.diff`。

**验收（受保护完整回归，两次逐项一致）**
- 新增 95 个收集项，其中 31 个真实通过。
- 16 个方法确实需要身份，仍以 `current runner identity pointer is missing or unsafe` 失败关闭。
- 另有 48 个此前被掩盖的过期契约或 fixture 缺陷显现（RC8、RC9）。
- Guard 阻断 0 次；仓库快照只显示预期文件变化。

**对剩余 4 个导入阻断模块未做修改**：`53_v3_identity_adapter`、`55a_namespace_lifecycle`、`59a_auth_identity_binding`、`63a_r3_authorization_issuance` 中，0 个方法独立于身份模块（每个方法或 fixture 都使用它）。延迟导入只会把阻断改名为运行时错误，不增加任何真实覆盖。

## 已评估但未实施（需审批）

- RC8 重复键 fixture：两个修正变体都在 scratch 中实测过，结果均为 13 pass / 5 RC1 / 1 RC7。选择哪个值属于语义决定。
- RC3–RC7、RC9：修复需要修改断言、期望消息或历史清单，或需要变更冻结成员。

## 回滚

- R1：`patch -R -p1 < evaluation/v1_2_3/step9_63c_r5c10ac_r1_ci_loader.diff`。
- R2：`patch -R -p1 < evaluation/v1_2_3/step9_63c_r5c10ac_r2_import_deferral.diff`。
- 修改前的副本也保存在会话 scratchpad 的 `backup/` 目录中。
- 注意：R2 的 4 个文件未被 Git 跟踪，不能用 `git checkout` 回滚。
