# Step 4.7 Answer Generation Grounding Report

日期：2026-09-19（America/New_York）  
测试数据：全部为人工构造的虚构输入和七天虚构日记。  
范围：只修改 Answer Generation；未修改 Decision Policy、Sufficiency Policy、Candidate Generation 或 Input Understanding。

## 结论

原 Step 4.5 的唯一剩余 failure 已修复。最终真实 Smoke 为 **5 PASS / 0 FAIL**；完整回归 **69 passed**；回答生成专项测试 **10 passed**。

建议正式重新验收 Step 4.5。按本阶段要求，工作在此停止，不进入 Step 5。

## 原失败原因

DATA_ANALYSIS 的 State 中只有 diary facts、没有 external evidence，但原 Answer Generator 只靠提示约束模型。真实模型自行加入了“睡眠效率低于 85%”这一医学参考阈值。该阈值既不是用户数据可直接得出的描述，也不在 current State 的 evidence 中，因此属于 Unsupported Quantitative Claim。

## Grounding 机制

`adaptive_agent/answer_generation.py` 现在按以下顺序工作：

```text
State goal + facts + answer_scope
→ 过滤与 goal 无关的 retrieved evidence
→ 代码从 facts 计算描述性 diary claims
→ 受限 prompt（数据结论 / 证据规则 / 禁止项）
→ 通用 Quantitative Claim Audit
→ DATA_ANALYSIS 保留确定性描述性计算
```

### 可从 facts 得出的内容

- 原始日记值：上床、起床、总睡眠、入睡潜伏期、夜醒、日期记录。
- 确定性计算：上床至起床的卧床时间、由 `total_sleep_time / time_in_bed` 得出的睡眠效率、日记条数。
- 这些输出由 `data_derived_claims()` 计算，而非要求 LLM 自己进行计算或解释临床意义。

本轮七天虚构日记允许的描述为：卧床 `480 分钟`、总睡眠 `360 分钟`、计算出的睡眠效率 `75%`、共 `7 天`记录。

### 必须有 evidence 的内容

百分比阈值、建议时长、治疗规则、clinical cutoff、具体量化医学结论以及任何“正常/异常/应当”的数字规则。只有与 current goal 相关并且 evidence 内确有相应量化内容时才可保留。

### 如何防止 unsupported quantitative claims

1. Prompt 明确将 User/Data-derived、Evidence-grounded 与 Unsupported Claims 分开。
2. `relevant_evidence()` 不把明显无关的检索文本传入模型。
3. `allowed_quantities()` 收集 facts、确定性计算和 relevant evidence 中允许出现的量化值。
4. `remove_unsupported_quantitative_claims()` 通用审计每个包含百分比、时长、天/周或次数的句子：未被允许的数量，或无 evidence 却带临床规则词的量化句，会被删除，并替换为“当前 State 没有支持相关量化规则的证据”的限制说明。
5. 对 DATA_ANALYSIS，即使模型的数字句被删除，代码计算出的描述性 claims 仍明确附加，确保“无 evidence”不会变成“什么都不能说”。
6. `remove_out_of_scope_claims()` 会遵守方向性 answer_scope：即使 evidence 含有具体睡眠限制规则，也不输出具体上床/卧床处方；限制提示使用中性措辞，不把“范围禁止”误写成“证据不存在”。
7. relevance filter 同时匹配中英文 goal/evidence 术语，避免英文 goal 误丢实际相关的 RAG 内容。

这不是针对 `85%` 的硬编码；任何同类、未被 facts/evidence 支撑的量化规则均走同一审计路径。

## 专项 Regression Tests

`tests/test_answer_generation_grounding.py`：**8 passed**。

- 空 evidence 时移除 unsupported threshold；
- evidence 含具体 threshold 时允许引用；
- diary facts 产生确定性描述性统计；
- 模型虚构的 diary numeric value 被移除；
- `answer_scope` 传入受限上下文；
- 无关 retrieved evidence 不传给模型；英文 goal 也能保留对应英文 evidence；
- 模型自身参数知识不能伪装为 retrieved evidence；
- 模型量化句被移除时，DATA_ANALYSIS 仍保留代码计算出的描述。

## 完整 Regression

```text
.venv/bin/python -m unittest discover -s tests -v
Ran 69 tests in 66.369s
OK
```

## 最终真实模型 Smoke

最终轨迹：`evaluation/runs/step4_5-answer-grounding-ultimate/http-traces.jsonl`。

| Case | 最终 Action Path | 结果 |
| --- | --- | --- |
| KNOWLEDGE_QA | `RETRIEVE → ANSWER` | PASS；英语 goal 仍保留相关刺激控制 evidence。 |
| PERSONALIZED_DECISION（信息不足） | `ASK(wake_time)` | PASS；不重复询问已知 latency。 |
| PERSONALIZED_DECISION（较充分） | `RETRIEVE → ANSWER` | PASS；回答未指定无依据的个性化新上床时间。 |
| CAUSE_ASSESSMENT | `RETRIEVE → ANSWER` | PASS；咖啡因只表述为可能关联，未输出无依据数值。 |
| DATA_ANALYSIS | `READ_DIARY → loaded → ANSWER` | PASS；包含 480 分钟、360 分钟、75%、7 天等数据派生描述；没有 85% 或其他无证据医学阈值。 |

没有发现新的 fabricated diary facts、repeated tool calls、Goal Drift 或 Policy failure。最终 Smoke 全部通过，但这仍是五个受控虚构案例的冒烟测试，不替代后续更大范围 benchmark。
