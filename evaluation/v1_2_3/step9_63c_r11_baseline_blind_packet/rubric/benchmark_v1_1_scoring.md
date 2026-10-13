# Benchmark V1.1 评分与归因规范

V1.1 保持五个维度和 100 分总分不变：Goal Alignment 20、Facts/State Integrity 20、Action/Resource Selection 20、Evidence/Answer Scope 25、Interaction Efficiency 15。`critical_failure` 是平行信号，不会自动把分数改为 0。

## 评分与归因分开

每个观察到的问题必须保存以下记录：

```yaml
primary_cause: INPUT_UNDERSTANDING
downstream_effects: [STATE_INTEGRITY, ACTION_SELECTION, EFFICIENCY]
independent_failure: false
supporting_trace:
  - case_id: PD-02-bedtime-direction-already-sufficient
    turn: 1
    trace_path: /turns/0/state_after_turn/facts/sleep_onset_latency
    observation: "原 query 明示 60 分钟，但 State 为空。"
```

`primary_cause` 只能有一个，表示最早可归责的层；`downstream_effects` 可以多个，表示它导致的可观察后果。只有后续模块在当时实际 State 下仍违反自身契约时，才设 `independent_failure: true` 并作为新的 primary record。

例如 explicit latency 未进入 State 后，Agent 的 ASK 可能增加用户回合。这会影响 Facts、Action 和 Efficiency 的表现，但不能在根因统计中被称为三个独立的 Policy failure。Action/efficiency 仅按额外的实际危害轻度扣分；完整重扣需有独立证据，例如 State 已有 latency 仍重复 ASK。

## Critical Failure record

```yaml
critical_failure: true
critical_failure_type: [ANSWER_CONTRADICTS_KNOWN_STATE]
supporting_trace:
  - case_id: PD-03-goal-specific-caffeine-and-awakenings
    turn: 1
    trace_path: /final_answer
    observation: "回答将未在 State 中的夜醒作为用户事实。"
```

可用类型：`FABRICATED_USER_FACT`、`FABRICATED_DIARY_DATA`、`UNAVAILABLE_RESOURCE_TREATED_AS_REAL`、`UNSUPPORTED_QUANTITATIVE_MEDICAL_CLAIM`、`ANSWER_CONTRADICTS_KNOWN_STATE`、`UNSUPPORTED_INDIVIDUALIZED_TREATMENT_INSTRUCTION`。类型可多选；当 `critical_failure=false` 时必须为空列表，`supporting_trace` 可为空。

## V1 历史结果

Step 5.1 的 **Average Score = 83.8**、**Critical Failures = 1** 是 V1 历史结果。V1.1 此时尚未运行，不能把新的 schema 或归因方式回填为新的实验成绩。
