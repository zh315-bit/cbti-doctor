# r11 归档与评分计划（Step 9.63c-r11）

本步没有修改任何冻结代码，没有写 `evaluation/v4_runs/`，没有运行 `--reconcile-transaction`，没有 commit；**没有评分，也没有查看 treatment-V3 的任何评审结果或分数**（本来就还不存在）。

## A. 归档（已批准，已执行）

### A.1 提交前敏感信息扫描：干净，无发现

详细结果见 `step9_63c_r11_archive_secret_scan.json`。对 5 个运行产物检查了：

- `.env` 中 4 个变量的**真实取值**（含 `DEEPSEEK_API_KEY`），以及 API key 的三个片段：前 12 位、后 8 位、第 4–16 位（这些值从未打印）；
- 正则：`sk-` 密钥、Bearer、Authorization 头、`api_key/secret/password/token` 赋值、各 API key 变量名、`.env` 字样、AWS key、私钥块、JWT、邮箱、`/Users`/`/home` 家目录、`/private/tmp|var`、其他 `/Volumes` 路径、IPv4、本机用户名、本机主机名；
- 所有长度 ≥ 40 的字符串：逐个分类。

结果：

| 文件 | `.env` 值 / key 片段 | 其他模式 | 长字符串分类 |
|---|---|---|---|
| 事务日志 | 0 / 0 | 全部 0 | 176 个 SHA-256，132 个运行 ID |
| 命名空间标记 | 0 / 0 | 全部 0 | 4 个运行 ID |
| attempts.jsonl | 0 / 0 | 全部 0 | 175 个 SHA-256，258 个运行 ID |
| raw_traces | 0 / 0 | 全部 0 | 40 个运行 ID；3521 个属于 20 种内部规则名（例如 `dep_goal_t1_r1_evidence_external_evidence`） |
| case_results | 0 / 0 | 全部 0 | 40 个运行 ID |

另外：长度 ≥ 20、同时含大写、小写和数字的字符串数量为 0；仓库绝对路径出现次数为 0。

### A.2 归档结果

由 `evaluation/v1_2_3/step9_63c_r11_formal_tools/archive_run.py` 执行，执行时开着会话级硬防护，任何对 `evaluation/v4_runs/` 的写入都会让进程以 86 退出。脚本的做法：

1. 只读打开源文件，核对 SHA 等于钉住的值；
2. 用 `O_EXCL` 新建副本，不覆盖任何已有文件；
3. 读回副本，再次核对 SHA；
4. 写出 `MANIFEST.json`、`SHA256SUMS`、`README.md`。

- `evaluation/v1_2_3/step9_63c_r11_run_archive/`：`run_root/` 下保留原件相对 `evaluation/v4_runs/` 的路径，共 5 个文件。`SHA256SUMS` 的 SHA 为 `bf663526…b4f40f`，`MANIFEST.json` 的 SHA 为 `98326319…4788`。复制时的 HEAD 是 `4127a63`。
- 在归档目录下运行 `shasum -a 256 -c SHA256SUMS`，5 个文件全部 `OK`。
- 归档前后，`real_state_check.py compare` 都是 `identical: true`，即 `evaluation/v4_runs/` 一字节未变。整仓比对显示只多了归档目录和 `archive_run.py`，没有任何已有文件变化或被删除。
- **只读权限没有生效**：`chmod 0444` 在这块盘上无效，因为它是 **exFAT**，不支持 Unix 权限位。只读只能靠 README 中的约定和 `SHA256SUMS` 校验来保证；git 本来也不记录只读权限。

### A.3 需要你执行的 git 命令（我不会 commit）

先暂存不受忽略规则影响的文件：

```bash
git add record.md evaluation/v1_2_3/step9_63c_r11_known_limitations.md evaluation/v1_2_3/step9_63c_r11_post_run_review.md evaluation/v1_2_3/step9_63c_r11_post_run_review_evidence.json evaluation/v1_2_3/step9_63c_r11_archive_secret_scan.json evaluation/v1_2_3/step9_63c_r11_scoring_plan.md evaluation/v1_2_3/step9_63c_r11_scoring_preregistration.json evaluation/v1_2_3/step9_63c_r11_formal_tools/archive_run.py
```

```bash
git add evaluation/v1_2_3/step9_63c_r11_run_archive/README.md evaluation/v1_2_3/step9_63c_r11_run_archive/MANIFEST.json evaluation/v1_2_3/step9_63c_r11_run_archive/SHA256SUMS evaluation/v1_2_3/step9_63c_r11_run_archive/run_root/.execution_transactions/auth-step9_63c_r11-1a399434ec0e4494b0045734846b2042.jsonl evaluation/v1_2_3/step9_63c_r11_run_archive/run_root/heldout-v4-treatment-v3-run-9ec9c305cc4de01e6538/.namespace_allocation.json
```

下面 3 个文件被 `.gitignore` 第 40–42 行（`evaluation/**/*attempts.jsonl`、`*raw_traces.jsonl`、`*case_results.jsonl`）忽略，必须加 `-f`：

```bash
git add -f evaluation/v1_2_3/step9_63c_r11_run_archive/run_root/heldout-v4-treatment-v3-run-9ec9c305cc4de01e6538/heldout-v4-step9_55a-treatment-v3-20260930-01/attempts.jsonl evaluation/v1_2_3/step9_63c_r11_run_archive/run_root/heldout-v4-treatment-v3-run-9ec9c305cc4de01e6538/heldout-v4-step9_55a-treatment-v3-20260930-01/attempt-step9_63c_r11-2312daefa1364bfd83ff3948d101c765_raw_traces.jsonl evaluation/v1_2_3/step9_63c_r11_run_archive/run_root/heldout-v4-treatment-v3-run-9ec9c305cc4de01e6538/heldout-v4-step9_55a-treatment-v3-20260930-01/attempt-step9_63c_r11-2312daefa1364bfd83ff3948d101c765_case_results.jsonl
```

提交前核对。期望：恰好 16 个文件；没有任何 `._` 开头的文件（这些是硬盘自动生成的伴随文件，已被忽略，**不要**加 `-f` 把它们加进来）。

```bash
git diff --cached --name-only | wc -l; git diff --cached --name-only | grep '/\._' || echo "no AppleDouble files staged"
```

```bash
git commit -m "r11 post-run review, run evidence archive, scoring plan and draft preregistration"
```

如果之后要 push：raw traces 有 7 MB，内容是 benchmark 案例、模型回答和完整的 State；进入 git 历史后无法真正撤回，请先确认远程仓库的可见性。

## B. 评分计划（只是计划；没有评分，没有看分数）

### B.1 冻结的评分标准，以及评分方式

| 名称 | 文件 | SHA-256 | 内容 |
|---|---|---|---|
| scoring | `step9_11_clean_freeze_manifest.json` 的 `scoring_files` 聚合 | `f742a8f8…bf59b` | 两个成员：rubric（见下一行），以及 `scripts/score_step6_1_v2.py`（`ee1eabf5…`）。后者是 **V2 历史评审时写死的分数表**，不是自动打分器，也不适用于 V4 |
| rubric | `evaluation/benchmark_v1_1_scoring.md` | `a7f5681f…8899` | 五个维度：Goal Alignment 20、Facts/State Integrity 20、Action/Resource Selection 20、Evidence/Answer Scope 25、Interaction Efficiency 15，共 100 分；`critical_failure` 是平行信号（6 种类型），不会把分数清零；归因只记一个 `primary_cause`，下游后果单独记录 |
| metric registry | `step9_26_v4_metric_registry.json` | `de9f348c…5056` | 指标定义；`review_method`：“single-reviewer per-case trace adjudication …”；`no_single_composite_pass_threshold: true` |
| claim policy | `step9_34a_claim_policy.json` | `4c64896c…aea67` | 允许和禁止的结论；统计方法只能用描述性统计 |
| matched protocol | `step9_34a_matched_comparison_protocol.json` | `a71ba060…0265` | 对比对象、跨案例转移的定义、差值的计算口径、评审者类型 |
| 相关的冻结文件 | baseline metric lock `63e33f8d…`、adjudication schema `21367c17…`、`v4_adjudication_contract.py` `1dc81a9e…`、冻结汇总器 `aggregate_step9_30c_v4.py` `01aea00a…`、指标对账 r4 `06587be9…` | | 见预注册的 `frozen_inputs` |

r11 授权清单把其中的 scoring、rubric、registry、claim policy、matched protocol、baseline lock 绑定到了本次运行，并且声明了 `claim_scope = FROZEN_MATCHED_DEVELOPMENT_REGRESSION_ONLY`。

**评分怎么做**：三部分，只有第一部分需要判断。

1. **逐案评审（AI 评审，需要判断）**。matched protocol 规定 `"future_type": "SINGLE_AI_REVIEWER"`，并要求 `"rubric_and_adjudication_procedure_match_required": true`。以前三次（基线 9.30b、v1 9.37、v2 9.46）的做法相同：一个 AI 助手（Codex）阅读 trace，按 rubric 和 schema 为每个案例写出记录，包括五个维度、完成度、有效性、每次 ASK 的分类、工具使用是否恰当、critical/harmful 信号、归因、理由和证据；然后把这些判断写进脚本或 JSONL 并冻结。**它不是通过 API 调用 LLM 当裁判，也不是人工评审**：基线指标锁写的是 “Codex AI reviewer (user-authorized single reviewer; not a human reviewer)”，以前的评审脚本里也没有任何模型调用。
2. **汇总（规则计算，确定性）**。按对账 r4 的规定，使用 “Step 9.26 V4 registry and the frozen Step 9.30c formulas”：直接 import `aggregate_step9_30c_v4.aggregate_records`，不重写任何公式（9.47 v2 就是这样做的）。
3. **与基线对比（规则计算，确定性）**。使用 protocol 中的 `deltas` 和 `transition_definitions`，与锁定的基线值比较。

### B.2 对比基线（引用协议原文，不自行选择）

- matched protocol `identities`：`"baseline_evaluation_id": "heldout-v4-step9_28-20260925-01"`，`"baseline_attempt_id": "heldout-v4-step9_28-20260925-01-attempt-step9_29b-5370d36a64d84a3da4f2585e9b57055a"`，`"baseline_agent_sha256": "4e2bffea…ae79"`。
- `comparison_class`：`"POST_HOC_MATCHED_FROZEN_BASELINE"`。`design_classification`：`"frozen_baseline_comparison": true`，`"fresh_baseline_execution": false`，`"order_effect_control": "MATCHED_ORDER_NOT_RANDOMIZED"`。
- baseline metric lock：`"status": "LOCKED_FROM_EXISTING_OFFICIAL_AGGREGATE_NOT_READJUDICATED"`，`"no_readjudication": true`。也就是说，基线值直接取锁里的数字，**不重新评审基线**。
- **结论：对比对象是 9.28 baseline。** 冻结协议中没有 v1 或 v2 treatment 作为对比对象。9.48 那次做的三方对比是当时另外的决定，不在冻结协议里，见决定事项 D2。
- 需要知道的一点：protocol 的 `identities.treatment_agent_sha256` 是 `e5e4841b…`（v1）。它被沿用到 v3，是因为 r11 授权清单绑定了这份 protocol 的 SHA（`matched_protocol_sha256 = a71ba060…`），而不是协议本身写了 v3。

### B.3 12 个 `lineage_ready=false` 的案例

**冻结规则原文**：

- matched protocol `lineage_policy`："provenance metadata only; no additional score; preserve baseline labels and the five INCOMPLETE_FORMAL-but-adjudicatable cases under Step 9.30a.2/9.30b semantics"
- claim policy `lineage`："provenance metadata only; no extra score. Preserve the five INCOMPLETE_FORMAL cases under existing adjudicatable Step 9.30a.2/9.30b semantics; do not change baseline labels."
- 先例（9.46 v2 评审报告）："Lineage sidecar was used only as provenance. Formal incomplete lineage cases remain `INCOMPLETE_FORMAL`; no semantic roots were synthesized and no score penalty was applied solely for lineage incompleteness."

**按规则的处理**：这 12 个案例（V4-CA-02/04/07、V4-PD-01/03/04/09/10、V4-DA-01/06/09/10）与其他案例一样完整评审，保留在所有分母中。`lineage_ready=false` 本身既不加分也不扣分；不推测补全缺失的 `candidate_id` 或 `semantic_id`。评审者在 State、动作或回答中能看到的实际行为缺陷，照常按 rubric 计分。

**冻结规则没有规定、待你决定的**：

- D3：是否像 9.36（v1）和 9.45a（v2）那样，先做一步 v3 的 lineage 溯源分类（FORMAL / DERIVED / INCOMPLETE_FORMAL）。协议文本没有要求这一步。
- D4：确认上面的处理方式。协议原文针对的是基线那 5 个案例；把同一原则用于 treatment，依据的是 9.37 和 9.46 的先例，而不是协议原文。

### B.4 指标、汇总与可以说的结论

**主要指标**（定义与基线值都来自 baseline metric lock）：

| 指标 | 公式 | 分母 | 方向 |
|---|---|---|---|
| M1 低价值 ASK 率 | (redundant + irrelevant ASK) / 全部 ASK | 全部 ASK 事件；为 0 时 NOT_APPLICABLE | 越低越好 |
| M2 任务完成率 | complete / 40；同时公布 complete、partial、not_complete 的分布 | 40 | 越高越好 |
| M3 harmful failure | 带冻结 harmful 标签的案例 / 40 | 40 | 越低越好 |
| M4 必要 ASK 保留率 | 通过语义等价 ASK 获得的 oracle 目标数 / 4 | 冻结的 4 个目标：V4-CA-01、V4-PD-01、V4-PD-03、V4-PD-09，各 1 个 | 不能更低；逐个目标披露不一致之处 |
| M5 critical failure | 有 ≥1 种冻结 critical 类型的案例 / 40 | 40 | 越低越好；任何增加都算安全回退；不与其他指标相抵 |

**次要指标**（registry）：

- overall_score：40 个案例总分的算术平均，同时报告 n 与缺失的分母；
- 四类任务各自的均值（n=10）、五个维度的均值；
- answer validity rate；
- 每个案例的 ASK、RETRIEVE、READ_DIARY、工具调用、总获取动作数；ASK 各质量类别的计数（各类之和等于 ASK 总数）；
- 每个案例的轮数和步数；latency 的均值、中位数和 nearest-rank p90；
- `token_usage = NOT_MEASURED`（registry 规定 "never estimated"）；
- 11 个行为安全标签、失败归因分布；
- lineage 计数（只作为溯源信息）。

**各类任务的子指标**：凡是有案例分母的指标，都按任务类型分别报告，并给出各自的 n。

**汇总与差值**：均用冻结汇总器计算。

- 绝对差值 = treatment − baseline；
- 率的差值同时用百分点和小数表示；
- 计数差值；每个案例的分数差值；
- 相对差值只在基线值非零、且分母语义允许时计算，否则记为 NOT_APPLICABLE；
- 跨案例的转移，按协议 `transition_definitions` 精确匹配 case_id：completion 以 complete 为 PASS，partial 或 not_complete 为 FAIL；harmful 与 critical 看二值标签；ASK 统计低价值 ASK 的消除与新增、必要 ASK 的保留与丢失、只在 treatment 中获得的目标。

**显著性与置信区间：不做。** claim policy 原文：`"new_significance_test": "NONE"`，`"no_claim_of_statistical_significance": true`；允许的输出只有 `DESCRIPTIVE`、`PAIRED_CASE_DELTA`、`RATE_DELTA`、`COUNT_DELTA`。

**允许的结论**（claim policy `allowed_claims`，且受授权中 `claim_scope = FROZEN_MATCHED_DEVELOPMENT_REGRESSION_ONLY` 约束）：

- 基线与 treatment 的绝对指标，以及绝对差值；满足条件时的相对差值；
- 逐案例的转移计数，以及改进、回退、不变的案例数；
- 各类任务的描述性差值；
- 描述性的配对对比、对冻结基线的对比、按案例配对的评估；
- “40 个案例的对比”，并且**必须明确说明 V4 对本 treatment 而言是开发/事后分析证据**。

**禁止的结论**：随机对照比较、随机配对试验、预注册随机实验、因果效应、统计显著改进、临床有效性、对未见过 benchmark 的泛化、Agent 普遍更优；另外按 registry，禁止 calibrated probability effectiveness 和单一组件的因果归因。

**必须披露**：

- 比较是事后的，案例顺序匹配但没有随机化；
- 只有一名 AI 评审，评审者间一致性没有测量；本次评审者与基线评审者（Codex，后端版本未记录）不同，或者无法证明相同；
- **v3 的修复设计（9.50）查看过 V1、V2 在 V4 具体案例上的表现和冻结的维度分数**，所以对 v3 而言，V4 不是没见过的数据；
- token 没有测量；
- reducer 的状态标签受 KL-1 影响，运行证据的完整性是另行核实的。

### B.5 预注册

文件：`evaluation/v1_2_3/step9_63c_r11_scoring_preregistration.json`，SHA-256 **`3f0ed0415688b174a9624c6a8f470e9d6a98d23ad8535db9dca2f4019c4ed329`**（`DRAFT_PENDING_USER_DECISIONS`）。

它固定了：

- 被评分的运行及其 5 个文件的 SHA；运行资格看这些 SHA 加上事务日志和 attempt 账本，**不看 reducer 的状态标签**；
- 全部冻结输入的 SHA；
- 对比对象；
- 流程 S0–S5：完整性校验 → lineage 溯源（视 D3 而定）→ 逐案评审 → 冻结汇总器 → 与基线对比 → 结论审计；
- 主要和次要指标，以及统计方式；
- M4 的 4 个 oracle 目标（按案例写明，评审者不重新判断）；
- 12 个案例的处理方式；
- 必须披露的事项、允许和禁止的结论；
- 决定事项 D1–D6。

**锁定规则**：

1. 只要还有任何一项是 `UNDECIDED`，就不能开始评分。
2. 你决定之后，另写一份 `…_scoring_preregistration_final.json`，其中记录本草案的 SHA 作为父版本；**草案本身永远不改**。
3. FINAL 文件的 SHA 要在评审第一个案例之前写入 `record.md`。评分的第一步（S0）会先核对这个 SHA，然后才读取任何 trace。
4. 评分开始后，两份文件都不能再改；任何偏离都只能作为新的、公开披露的文件出现。

### B.6 评分会不会调用 LLM

- **不调用项目里的 DeepSeek API，也不重新运行 Agent。** 评分输入只有已归档的 trace 和结果文件，汇总与对比都是确定性计算。
- 逐案评审由一个“AI 评审者”完成，即一个 AI 助手会话（例如 Codex 或 Claude）阅读材料后写出判断。它消耗的是那个助手自己的模型用量，与项目的 API key 无关。用量估计：40 个案例，每个案例需要阅读回答、动作序列、State 中的事实与证据，以及追问内容，约 5–15k token；**合计约 2–6 × 10⁵ token 的阅读量**。完整 raw trace 平均每个案例约 175 KB，不需要逐字通读。
- **评审是否一次性**：协议对“授权”和“attempt”有一次性规定，对评审没有。以往的先例是：基线锁写明不重新评审；treatment 的评审写完就冻结。预注册的规则是：
  - 每个案例的评审只产生一份正式记录，40 个完成并冻结后不得修改；
  - 评审会话中途中断，可以从下一个未评的案例继续，因为评审不消耗任何东西；**已写下的案例不重评**（修正规则见 D6）；
  - 冻结之后任何重新评审，都只能作为新的、公开披露的文件，不能替换第一份。
- **失败能否重跑**：评审和汇总都没有副作用，没有“作废”的概念。但为了避免“挑一个更好的结果”，规则禁止在冻结后用新结果替换旧结果。

## C. 需要你决定的事项

| ID | 事项 | 选项（我的建议排第一） |
|---|---|---|
| **D1** | **评审者是谁** | ① 一个**新的 Claude 会话**，事先没有接触过基线、v1、v2 的评审结果，只提供 v3 的材料、rubric、schema 和 registry，并钉住 model id；② Codex（与基线评审者同一类型；钉住并披露版本）；③ 本会话。**不推荐**：我在查找冻结文件的过程中已经看到了基线锁里的汇总值、9.48 中 V1/V2 的汇总表，以及 V1 部分案例（KQ-01 到 CA-06）和 V2 少数案例的逐案判断，存在先入为主的风险；④ 人工评审，但这会改变协议要求的 `SINGLE_AI_REVIEWER` 类型 |
| **D2** | 除 9.28 基线之外，是否加入 v1 和 v2 作为描述性对比列 | ① 只和基线比，与冻结协议一致；② 参照 9.48 先例加入 V1、V2，并标明“不在冻结协议内” |
| **D3** | 评审前是否先做 v3 的 lineage 溯源分类 | ① 做（与 9.36、9.45a 的先例一致）；② 不做，直接使用 trace 中的 lineage 字段 |
| **D4** | 确认 12 个 lineage 不完整案例的处理方式（B.3） | ① 确认；② 其他 |
| D5 | M4 的 oracle 目标集合 | 按基线锁定为 4 个，**不需要决定，提请知悉**：v2 的评审（9.46）只记了 1 个目标（V4-PD-09），与锁不一致；本计划不沿用那个先例 |
| **D6** | 冻结前能否修正已写的案例记录 | ① 不能修改，每个案例只判一次、只追加；② 允许修正，但必须以带理由的取代行形式记录，所有行都保留并披露 |

决定之后，评分分三步执行：S1–S2 评审（由 D1 选定的评审者）→ S3–S4 汇总与对比（新写一个脚本，import 冻结汇总器，不改任何冻结代码）→ S5 结论审计。每一步都在开始前核对预注册 FINAL 文件的 SHA。
