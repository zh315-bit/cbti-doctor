# 勘误附录：锁定基线 V4-PD-03 的 M4 标签（Step 9.63c-r11）

**性质：只做披露。** 本附录不修改、不替换、不重算任何已冻结的判定或报告，也不重新评审基线。受影响但保持原样的冻结文件及其 SHA-256 前缀：

| 文件 | SHA-256（前 16 位） |
|---|---|
| `step9_34a_baseline_metric_lock.json`（`no_readjudication: true`） | `63e33f8dd6610974` |
| `step9_30b_v4_human_adjudication.jsonl`（锁定基线评审记录） | `85d436955fe2b7ea` |
| `step9_63c_r11_blind_review_output/v3_adjudication.jsonl`（主评审） | `46d5e84d60b10444` |
| `step9_63c_r11_scoring_results.json` / `step9_63c_r11_scoring_report.md`（主结果） | `a3b9a7952dcc7ed5` / `8f695850c0208a54` |
| `step9_63c_r11_sensitivity_results.json` / `step9_63c_r11_sensitivity_report.md` | `977e0c6645166ec2` / `a5e5bdf8ea7a5f04` |
| `step9_63c_r11_scoring_preregistration_final.json` / `step9_63c_r11_reviewer_sensitivity_preregistration.json` | `ead55a09e7067d33` / `cc1e511b11e1b12e` |

## 1. 不一致之处

锁定基线（Codex 对 9.28 的早期评审）的 M4 = 1/4。分子 1 的唯一来源是 **V4-PD-03 的 `bedtime`：`acquired = true`**。该案例的 oracle 必要目标是 `bedtime`（追问事实：`work nights around 23:40; weekends vary`）。

9.28 的 trace 显示：

- PD-03 的 ASK 问的是“你上床后通常需要多久才能睡着？”，目标是 `sleep_onset_latency`，不是 `bedtime`；
- 用户（harness）的回复是“这项信息我目前不清楚。”，随后直接 `ANSWER`；
- harness 只在 ASK 的 `target` 与追问事实的键完全相同时才释放事实（`scripts/run_step8_9_v1_2_1.py:follow_up`），所以 `bedtime` 的追问事实**没有被释放**；
- 锁定基线对该案例的理由原文写的是“The necessary bedtime ASK is made and answered”，与上述 trace 不符。

其余三个评审格子对同一个标签都是 `false`：Claude 对 9.28（B）、Claude 对 v3（主评审）、Codex 对 v3（A）。CA-01、PD-01、PD-09 的 `acquired` 在四个格子里都是 `false`。

补充事实：两次运行（9.28 与 v3）共 21 次 ASK（9 次与 12 次），收到的回复全部是“这项信息我目前不清楚。”，即**两次运行里没有任何一个 oracle 追问事实被释放过**。早期锁定基线评审没有留下自报口径文本，无法知道该标签依据的是什么判断。

## 2. 影响

| 位置 | 原表述 | 按 trace 的读法 |
|---|---|---|
| 主结果（`step9_63c_r11_scoring_report.md`） | M4 由 **1/4 降到 0/4**，“不能更低”条件为 FAILED | **0/4 对 0/4**：两个版本都没有保留必要追问 |
| 敏感性报告 | M4：Claude 路径 +0 个百分点，Codex 路径 −25 个百分点，判“受评审者影响，不确定” | 两条路径都是 0 个百分点；Codex 路径的 −25 来自这一个标签 |
| README 的 M4 表格 | Codex × 9.28 = 1/4 | 同上，已加脚注指向本附录，数值未改 |

需要说明的是：主报告里“不具备描述性配对对比结论的资格”这一项，形式上依据的就是 M4 下降（M5 条件已满足）。本附录**不重新运行该资格检验，也不改写它的结果**；它只披露这条依据所依赖的标签与 trace 不一致。若按 trace 读，“不能更低”这一条件是平凡成立的（0/4 对 0/4），并不能说明任何一个版本保留了必要追问。

## 3. 声明

1. 按预注册的 `no_readjudication`，**锁定基线和主结果都不修改**；本附录不改变任何已冻结的判定、分数、指标或报告。
2. 主结论“**不能宣称 v3 相对基线整体优越**”保持不变。除 M4 外，它还有不依赖这个标签的依据：个性化决策与数据分析的任务均值在两条评审路径上方向都是下降；完成度、有效率、critical 在两条路径上方向不一致；评审者类型与基线不同、单一 AI 评审、V4 对 v3 并非未见数据等披露事项均仍然成立。
3. 本附录只提供一条核对线索，不是对基线评审质量的整体评价；除 PD-03 的 `bedtime` 之外，没有检查锁定基线的其他标签是否与 trace 一致。

## 4. 来源

事后探索分析 `step9_63c_r11_exploratory_analysis.md` 第 4 节（提交 `09cccab`）。核对所用数据：9.28 的 raw trace 与 case_results（`evaluation/v4_runs/heldout-v4-step9_28-20260925-01/…`，由 `step9_30a_v4_run_input_freeze.json` 钉住）、`benchmark_v4_cases.yaml`（`8b8c7209…`）、上表所列评审记录。
