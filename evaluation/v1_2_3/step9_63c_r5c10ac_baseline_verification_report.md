# Step 9.63c-r5c10ac — 基线独立验证报告（Baseline Verification Report）

状态：`PASS_BASELINE_REPRODUCED_628_OF_650`

## 1. 验证对象与方法

- 前任报告：`step9_63c_r5c10ab_test_infrastructure_report.md` 与 `step9_63c_r5c10ab_test_results_matrix.json`。
- 环境：项目 `.venv/bin/python`（Python 3.12.14），原生 `unittest`，未安装 pytest，无依赖变更。
- 仓库漂移检查：上一步结束时的快照（2,355 个文件）与本步开始时的快照比较，结果为 0 新增、0 删除、0 内容变化、0 mtime 变化。
- 保护框架完整性：`step9_63c_r5c10ab_test_harness/` 的 `guard/sitecustomize.py`（`1376cf08…`）、`run_module.py`（`d53ab6ea…`）、`run_all.sh`（`7ee6800c…`）与上一步记录一致。
- Guard 自测（本步新写）：18/18 通过。
  - 15 条阻断路径均生效：仓库写入、`os.open O_CREAT`、`mkdir`（含 `dir_fd`）、`remove`、`rename`、`replace`、复制或移动进仓库、`utime`、外部 DNS、外部连接、`git` 子进程、`os.system`、子 Python 进程写仓库。
  - 3 条允许路径正常：仓库到临时目录的复制、临时目录读写与删除、仓库读取。

## 2. 复现结果

命令：`evaluation/v1_2_3/step9_63c_r5c10ab_test_harness/run_all.sh <scratch 输出目录>`，退出码 0，66 个模块进程全部退出码 0。

| 指标 | 前任报告 | 本步实测 |
|---|---:|---:|
| Collected | 650 | 650 |
| Passed | 628 | 628 |
| Failed | 4 | 4 |
| Errors | 18 | 18 |
| Import-blocked modules | 8 | 8 |
| Guard 阻断事件 | 0 | 0（仅 2 个被允许的 `python -c` 子进程） |
| 运行后仓库快照变化 | 0 | 0 |

22 个非通过项的 test ID 与结果，与前任矩阵逐项一致。

**结论：628/650 已独立复现。**

## 3. 与前任报告的差异（新发现）

1. **CI 环境与本地不一致。**
   - Git 只跟踪 38/66 个测试模块和 47/70 个脚本。8 个导入阻断模块全部未被跟踪，GitHub CI 根本看不到它们。
   - 因此“CI loader 崩溃”只会在本地工作树上发生，不会出现在 GitHub 上。
2. **已提交的 HEAD 版本仍会写历史 Trace。**
   - 对干净的 `git archive HEAD` 导出运行 CI 原脚本，结果为 277 tests、2 errors。
   - 这 2 个 error 都是 HEAD 中的 v1_2 mechanism 测试尝试写固定历史 Trace 路径，被 guard 阻断。r5c10o 的隔离修复只存在于未提交的工作树。
3. **工作树上 CI 脚本直接中止。**
   - 修复前：未捕获的 `RuntimeError`，运行 0 个测试，不生成任何报告。
4. **导入阻断掩盖了过期契约。**
   - 8 个导入阻断模块中，有 4 个阻断纯属模块级 import 位置所致。81/140 个方法在静态分析中不使用身份相关模块。
   - 解除阻断后暴露出原本被掩盖的过期契约（RC8、RC9，详见根因矩阵）。
5. **HEAD 中保存有 V2 归档父 runner 字节。**
   - Git HEAD 中 `scripts/run_step9_35a_matched_treatment.py` 的 blob SHA-256 为 `920486b1…`，与 V2 runner 的 `LEGACY_RUNNER_SHA256` 完全一致。
   - 工作树中的 r10 冻结版本为 `b79bc78a…`，是有意演进后的版本。
