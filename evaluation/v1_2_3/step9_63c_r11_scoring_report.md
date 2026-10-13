# r11 treatment-V3 评分报告：汇总与冻结基线对比（Step 9.63c-r11）

**按 FINAL 预注册 `ead55a09…0cf89` 执行。** 评审冻结提交为 `1068d97`（评审记录 SHA `46d5e84d…af22`，40 条，冻结在汇总之前）；结果 JSON 为 `step9_63c_r11_scoring_results.json`（SHA `a3b9a7952dcc7ed57e9cd3414c85db6ffe23e07dd32abed574f057bae3484aec`）。汇总使用冻结的 9.30c 汇总器 `aggregate_step9_30c_v4.aggregate_records`（`01aea00a…`），公式未改；与 Step 9.47 一样，只替换了绑定到具体运行的 `validate_records`（换成盲审包校验器，其中合约检查是逐字拷贝的）和 `EXPECTED_LINEAGE`（28/8/4）。基线取锁定值（`step9_34a_baseline_metric_lock.json`，`no_readjudication: true`），汇总前已核对锁与基线汇总一致。汇总前后评审记录 SHA 不变，没有修改任何评审记录。不做显著性检验，也不算置信区间。

**结论范围：`FROZEN_MATCHED_DEVELOPMENT_REGRESSION_ONLY`。** 以下全部是单一 AI 评审者在同一组 40 个 V4 案例上的描述性配对对比，不是因果效应，不是统计显著结论，不能泛化到未见过的数据。第 6 节列出的披露事项必须随结论一起出现。

## 1. 主要指标（M1–M5，对比锁定的 9.28 基线）

| 指标 | 基线 9.28 | v3 | 差值 | 方向要求 | 结果 |
|---|---|---|---|---|---|
| M1 低价值 ASK 率 | 9/9 (1) | 8/12 (0.6667) | -33.33 个百分点 | 越低越好 | 下降 |
| M2 任务完成率 | 16/40 (0.4) | 18/40 (0.45) | +5 个百分点（+2 例） | 越高越好 | 上升 |
| M3 harmful failure | 16/40 (0.4) | 4/40 (0.1) | −30 个百分点（−12 例） | 越低越好 | 下降 |
| M4 必要 ASK 保留 | 1/4 (0.25) | 0/4 (0) | −25 个百分点 | 不能更低 | **更低（未满足）** |
| M5 critical failure | 0/40 | 0/40 | 0 | 越低越好，不能增加 | 不变（满足） |

完成度分布：基线 complete 16 / partial 21 / not_complete 3 → v3 complete 18 / partial 8 / not_complete 14。v3 的 harmful 案例：V4-CA-01, V4-PD-01, V4-PD-03, V4-PD-10；critical 案例：无。M4：基线 4 个目标中获得 1 个，v3 获得 0 个；逐案看是 1 个案例从“获得”变成“丢失”（`NECESSARY_ASK_LOST`），见第 4 节。

## 2. 总分与四类任务（0–100 分，描述性）

| | 基线 9.28 | v3 | 差值 | 相对变化 |
|---|---|---|---|---|
| 总体均值 | 70.5 | 69.675 | -0.825 | -0.0117 |
| KNOWLEDGE_QA（n=10） | 82.2 | 91.6 | 9.4 | 0.1144 |
| CAUSE_ASSESSMENT（n=10） | 59.1 | 68.1 | 9.0 | 0.1523 |
| PERSONALIZED_DECISION（n=10） | 62.6 | 46.0 | -16.6 | -0.2652 |
| DATA_ANALYSIS（n=10） | 78.1 | 73.0 | -5.1 | -0.0653 |

五个维度的均值：

| 维度（满分） | 基线 | v3 | 差值 |
|---|---|---|---|
| goal_alignment（20） | 13.675 | 12.2 | -1.475 |
| facts_state_integrity（20） | 16.1 | 15.975 | -0.125 |
| action_resource_selection（20） | 13.9 | 16.35 | 2.45 |
| evidence_answer_scope（25） | 15.5 | 15.05 | -0.45 |
| interaction_efficiency（15） | 11.325 | 10.1 | -1.225 |

各类任务的完成与有效性：

| 任务 | 完成 基线→v3 | 有效 基线→v3 |
|---|---|---|
| KNOWLEDGE_QA | 8/10 → 7/10 | 10/10 → 9/10 |
| CAUSE_ASSESSMENT | 1/10 → 4/10 | 10/10 → 6/10 |
| PERSONALIZED_DECISION | 2/10 → 3/10 | 10/10 → 4/10 |
| DATA_ANALYSIS | 5/10 → 4/10 | 7/10 → 6/10 |

总体有效率（answer validity）：37/40 (0.925) → 25/40 (0.625)，−30 个百分点（−12 例）。**这是评审者自拟的有效性口径下的结果，见披露 3。**

## 3. 获取行为与效率（运行遥测，不是质量分）

| | 基线 | v3 | 差值 |
|---|---|---|---|
| ASK/案例 | 0.225 | 0.3 | 0.075 |
| RETRIEVE/案例 | 0.325 | 0.775 | 0.45 |
| READ_DIARY/案例 | 0.25 | 0.25 | 0.0 |
| 工具调用/案例 | 0.575 | 1.025 | 0.45 |
| 轮数/案例 | 1.225 | 1.3 | 0.075 |
| 步数/案例 | 1.8 | 2.325 | 0.525 |
| 延迟 mean_ms | 6453 | 10426 | 3973 |
| 延迟 median_ms | 3251 | 10219 | 6968 |
| 延迟 p90_nearest_rank_ms | 11381 | 14739 | 3358 |

ASK 质量分类（事件数）：必要 0→1，有用但可选 0→3，冗余 1→6，无关 8→2，合计 9→12。token_usage：NOT_MEASURED。

## 4. 逐案转移（按协议的 transition_definitions）

| 维度 | 改进 | 回退 | 不变 |
|---|---|---|---|
| 完成（complete 为 PASS） | 6 | 4 | 30 |
| 有效性 | 0 | 12 | 28 |
| harmful failure | 12 | 0 | 28 |
| critical failure | 0 | 0 | 40 |
| 总分（v3 − 基线） | 更高 17 | 更低 23 | 相同 0 |

ASK 转移标签：{"UNCHANGED": 36, "NEW_LOW_VALUE_ASK_INTRODUCED": 1, "LOW_VALUE_ASK_REMOVED": 3, "NECESSARY_ASK_LOST": 1}。

各类任务的逐案转移：

| 任务 | 完成 改进/回退/不变 | 有效 改进/回退/不变 | harmful 改进/回退/不变 | 总分 更高/更低/相同 |
|---|---|---|---|---|
| KNOWLEDGE_QA | 0/1/9 | 0/1/9 | 0/0/10 | 9/1/0 |
| CAUSE_ASSESSMENT | 3/0/7 | 0/4/6 | 7/0/3 | 5/5/0 |
| PERSONALIZED_DECISION | 2/1/7 | 0/6/4 | 5/0/5 | 1/9/0 |
| DATA_ANALYSIS | 1/2/7 | 0/1/9 | 0/0/10 | 2/8/0 |

逐案明细（基线 → v3；primary_cause 为评审者原文，未做任何归并）：

| 案例 | 完成 | 有效 | harmful | critical | 总分 | ASK 标签 | v3 primary_cause（原文） |
|---|---|---|---|---|---|---|---|
| V4-KQ-01 | complete→complete UNCHANGED | True→True UNCHANGED | False→False UNCHANGED | False→False | 86→98 (+12) | UNCHANGED | — |
| V4-KQ-02 | complete→complete UNCHANGED | True→True UNCHANGED | False→False UNCHANGED | False→False | 81→98 (+17) | UNCHANGED | — |
| V4-KQ-03 | complete→complete UNCHANGED | True→True UNCHANGED | False→False UNCHANGED | False→False | 90→96 (+6) | UNCHANGED | ANSWER_GENERATION_LANGUAGE_MISMATCH |
| V4-KQ-04 | partial→partial UNCHANGED | True→True UNCHANGED | False→False UNCHANGED | False→False | 81→84 (+3) | UNCHANGED | RETRIEVAL_EVIDENCE_INSUFFICIENT |
| V4-KQ-05 | complete→complete UNCHANGED | True→True UNCHANGED | False→False UNCHANGED | False→False | 83→96 (+13) | UNCHANGED | — |
| V4-KQ-06 | complete→partial REGRESSED | True→True UNCHANGED | False→False UNCHANGED | False→False | 83→88 (+5) | UNCHANGED | RETRIEVAL_EVIDENCE_INSUFFICIENT |
| V4-KQ-07 | complete→complete UNCHANGED | True→True UNCHANGED | False→False UNCHANGED | False→False | 75→97 (+22) | UNCHANGED | — |
| V4-KQ-08 | complete→complete UNCHANGED | True→True UNCHANGED | False→False UNCHANGED | False→False | 84→94 (+10) | UNCHANGED | ANSWER_GENERATION_LANGUAGE_MISMATCH |
| V4-KQ-09 | partial→not_complete UNCHANGED | True→False REGRESSED | False→False UNCHANGED | False→False | 78→70 (-8) | UNCHANGED | RETRIEVAL_EVIDENCE_INSUFFICIENT |
| V4-KQ-10 | complete→complete UNCHANGED | True→True UNCHANGED | False→False UNCHANGED | False→False | 81→95 (+14) | UNCHANGED | — |
| V4-CA-01 | partial→partial UNCHANGED | True→True UNCHANGED | True→True UNCHANGED | False→False | 53→69 (+16) | UNCHANGED | ACQUISITION_POLICY_SUPPRESSED_NECESSARY_ASK |
| V4-CA-02 | partial→not_complete UNCHANGED | True→False REGRESSED | True→False IMPROVED | False→False | 57→40 (-17) | UNCHANGED | GOAL_DEPENDENCY_MISREPRESENTATION |
| V4-CA-03 | partial→complete IMPROVED | True→True UNCHANGED | True→False IMPROVED | False→False | 53→92 (+39) | UNCHANGED | — |
| V4-CA-04 | partial→not_complete UNCHANGED | True→False REGRESSED | False→False UNCHANGED | False→False | 59→42 (-17) | UNCHANGED | GOAL_DEPENDENCY_MISREPRESENTATION |
| V4-CA-05 | partial→partial UNCHANGED | True→True UNCHANGED | True→False IMPROVED | False→False | 53→83 (+30) | UNCHANGED | ANSWER_GENERATION_OVER_CONSTRAINED |
| V4-CA-06 | partial→not_complete UNCHANGED | True→False REGRESSED | True→False IMPROVED | False→False | 55→47 (-8) | UNCHANGED | BOUNDED_ANSWER_CONTRACT_FAIL_CLOSED |
| V4-CA-07 | partial→complete IMPROVED | True→True UNCHANGED | True→False IMPROVED | False→False | 53→79 (+26) | UNCHANGED | GOAL_DEPENDENCY_MISREPRESENTATION |
| V4-CA-08 | complete→complete UNCHANGED | True→True UNCHANGED | False→False UNCHANGED | False→False | 88→87 (-1) | UNCHANGED | RETRIEVAL_EVIDENCE_INSUFFICIENT |
| V4-CA-09 | partial→not_complete UNCHANGED | True→False REGRESSED | True→False IMPROVED | False→False | 58→49 (-9) | UNCHANGED | BOUNDED_ANSWER_CONTRACT_FAIL_CLOSED |
| V4-CA-10 | partial→complete IMPROVED | True→True UNCHANGED | True→False IMPROVED | False→False | 62→93 (+31) | UNCHANGED | — |
| V4-PD-01 | partial→partial UNCHANGED | True→True UNCHANGED | True→True UNCHANGED | False→False | 56→48 (-8) | NEW_LOW_VALUE_ASK_INTRODUCED | GOAL_DEPENDENCY_MISREPRESENTATION |
| V4-PD-02 | complete→not_complete REGRESSED | True→False REGRESSED | False→False UNCHANGED | False→False | 94→35 (-59) | UNCHANGED | GOAL_DEPENDENCY_MISREPRESENTATION |
| V4-PD-03 | partial→not_complete UNCHANGED | True→False REGRESSED | True→True UNCHANGED | False→False | 61→28 (-33) | LOW_VALUE_ASK_REMOVED, NECESSARY_ASK_LOST | GOAL_DEPENDENCY_MISREPRESENTATION |
| V4-PD-04 | complete→complete UNCHANGED | True→True UNCHANGED | False→False UNCHANGED | False→False | 75→73 (-2) | UNCHANGED | GOAL_DEPENDENCY_MISREPRESENTATION |
| V4-PD-05 | partial→not_complete UNCHANGED | True→False REGRESSED | True→False IMPROVED | False→False | 48→35 (-13) | LOW_VALUE_ASK_REMOVED | INPUT_UNDERSTANDING |
| V4-PD-06 | partial→not_complete UNCHANGED | True→False REGRESSED | True→False IMPROVED | False→False | 54→36 (-18) | LOW_VALUE_ASK_REMOVED | GOAL_DEPENDENCY_MISREPRESENTATION |
| V4-PD-07 | partial→not_complete UNCHANGED | True→False REGRESSED | True→False IMPROVED | False→False | 60→43 (-17) | UNCHANGED | BOUNDED_ANSWER_CONTRACT_FAIL_CLOSED |
| V4-PD-08 | partial→not_complete UNCHANGED | True→False REGRESSED | True→False IMPROVED | False→False | 53→35 (-18) | UNCHANGED | INPUT_UNDERSTANDING |
| V4-PD-09 | partial→complete IMPROVED | True→True UNCHANGED | True→False IMPROVED | False→False | 61→75 (+14) | UNCHANGED | ASK_TARGET_UNDERSPECIFIED |
| V4-PD-10 | partial→complete IMPROVED | True→True UNCHANGED | True→True UNCHANGED | False→False | 64→52 (-12) | UNCHANGED | GOAL_DEPENDENCY_MISREPRESENTATION |
| V4-DA-01 | partial→partial UNCHANGED | True→False REGRESSED | False→False UNCHANGED | False→False | 65→67 (+2) | UNCHANGED | ANSWER_GENERATION_DIARY_COMPARISON_NOT_PERFORMED |
| V4-DA-02 | complete→complete UNCHANGED | True→True UNCHANGED | False→False UNCHANGED | False→False | 97→93 (-4) | UNCHANGED | ANSWER_GENERATION_LANGUAGE_MISMATCH |
| V4-DA-03 | complete→partial REGRESSED | True→True UNCHANGED | False→False UNCHANGED | False→False | 87→81 (-6) | UNCHANGED | ANSWER_GENERATION_DENOMINATOR_NOT_REPORTED |
| V4-DA-04 | complete→complete UNCHANGED | True→True UNCHANGED | False→False UNCHANGED | False→False | 96→97 (+1) | UNCHANGED | — |
| V4-DA-05 | not_complete→not_complete UNCHANGED | False→False UNCHANGED | False→False UNCHANGED | False→False | 53→50 (-3) | UNCHANGED | DIARY_DERIVATION_FIELD_NOT_SUMMARIZED |
| V4-DA-06 | not_complete→not_complete UNCHANGED | False→False UNCHANGED | False→False UNCHANGED | False→False | 57→53 (-4) | UNCHANGED | ANSWER_GENERATION_SORT_NOT_PERFORMED |
| V4-DA-07 | complete→complete UNCHANGED | True→True UNCHANGED | False→False UNCHANGED | False→False | 87→84 (-3) | UNCHANGED | ACTION_SELECTION_UNNECESSARY_RETRIEVE |
| V4-DA-08 | complete→partial REGRESSED | True→True UNCHANGED | False→False UNCHANGED | False→False | 99→71 (-28) | UNCHANGED | ANSWER_AUTHORIZATION_GENERIC_REFUSAL_FOR_UNAVAILABLE_RESOURCE |
| V4-DA-09 | not_complete→not_complete UNCHANGED | False→False UNCHANGED | False→False UNCHANGED | False→False | 55→51 (-4) | UNCHANGED | ANSWER_GENERATION_MAX_NOT_REPORTED |
| V4-DA-10 | partial→complete IMPROVED | True→True UNCHANGED | False→False UNCHANGED | False→False | 85→83 (-2) | UNCHANGED | ACTION_SELECTION_EVIDENCE_RETRIEVE_SKIPPED |

## 5. v1、v2 描述性对比列（D2）

> **不在冻结协议内，仅作描述性参考，不得据此下结论。** 以下各列不进入任何结论或结论审计。

| | 基线 9.28 | v1（9.38） | v2（9.47） | v3 |
|---|---|---|---|---|
| 总体均值 | 70.5 | 79.625 | 68.875 | 69.675 |
| KNOWLEDGE_QA | 82.2 | 82.2 | 84.4 | 91.6 |
| CAUSE_ASSESSMENT | 59.1 | 79.1 | 57.2 | 68.1 |
| PERSONALIZED_DECISION | 62.6 | 74.4 | 56.3 | 46.0 |
| DATA_ANALYSIS | 78.1 | 82.8 | 77.6 | 73.0 |
| M1 低价值 ASK | 9/9 | 8/13 (0.6154) | 8/12 (0.6667) | 8/12 (0.6667) |
| M2 完成 | 16/40 | 20/40 | 7/40 | 18/40 |
| M3 harmful | 16/40 | 1/40 | 0/40 | 4/40 |
| M4 必要 ASK 保留 | 1/4 | 1/4 (0.25) | 0/1 (0)（9.46 只记了 1 个目标，与锁不一致） | 0/4 |
| M5 critical | 0/40 | 2/40 | 0/40 | 0/40 |
| 有效性 | 37/40 | 38/40 | 40/40 | 25/40 |

各列的评审者不同（基线、v1、v2 为 Codex；v3 为 Claude），口径未必一致，不能据此比较 v1、v2、v3 之间的高低。

## 6. 结论审计与披露

- 统计方式：DESCRIPTIVE / PAIRED_CASE_DELTA / RATE_DELTA / COUNT_DELTA only; no significance test, no confidence interval。
- M5 不增加条件：**MET**。
- M4 不降低条件：**FAILED (necessary ASK preservation decreased)**。
- 描述性配对对比结论的资格：**不具备**。依据：基线锁对 M4 的要求是 "not lower"；Step 9.39 的先例把 M4 降低和 M5 增加都作为对比结论的阻断条件。因此，不能把本次结果概括为“v3 相对基线有改进”。可以陈述的只有逐项的观察值及其差值，并且 M4 的下降必须一并说明。
- 允许的表述：各项指标的绝对值和差值、逐案转移计数、各类任务的描述性差值、“40 个案例的冻结基线配对对比（V4 对 v3 是开发 / 事后分析证据）”。
- 禁止的表述：随机对照或配对试验、因果效应、统计显著、临床有效性、对未见数据的泛化、Agent 普遍更优、校准概率有效性、单一组件因果归因。

**必须随结论一起披露：**

1. Reviewer type differs from the baseline reviewer: treatment-V3 was reviewed by 'Claude opus5.5, fresh session'; the locked baseline was reviewed by a Codex AI reviewer (backend version not recorded).
2. Single AI reviewer; inter-rater reliability NOT_MEASURED; no human adjudication.
3. Reviewer self-reported: harmful_failure and validity criteria and primary_cause labels were formulated by the reviewer without a shared enumeration; CA-02 and CA-04 were re-read after writing (not modified); the tool wrote a session cache outside the packet.
4. Post-hoc matched comparison against a frozen baseline; case order matched, not randomized.
5. V4 is not unseen data for V3: the V3 repair design (Step 9.50) consulted treatment-V1/V2 case-level behaviour and frozen dimension scores on V4 cases. V4 is development/postmortem evidence for this treatment.
6. Lifecycle reducer defect KL-1 labels the r11 authorization INCONSISTENT_FAIL_CLOSED; run integrity was verified independently and the defect does not affect result validity.
7. token_usage NOT_MEASURED.
8. Treatment-V1/V2 columns are outside the frozen protocol, descriptive only, and no conclusion is drawn from them (D2).
9. primary_cause labels are listed exactly as written by the reviewer; not merged, normalised or turned into rates.

## 7. lineage（只作为溯源信息，不计分）

FORMAL_LINEAGE_READY 28、DERIVED_LINEAGE_COMPLETE 8、INCOMPLETE_FORMAL_BUT_ADJUDICATABLE 4；与冻结汇总器的计数核对一致。12 个 lineage_ready=false 的案例都已完整评审（预注册 D4）。
