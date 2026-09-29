# Step 9.23 Evidence Projection

原先固定 `_GOAL_TERMS` 造成目标未含少数词面关键词时，已检索证据被静默丢弃。现在 `project_evidence(state)` 按顺序检查载荷有效性、来源状态、重复、显式 answer_scope 排除；对于同一 goal 的 `RETRIEVE`，使用 State 中的 action query、goal ID 和 RAG 来源血缘确认检索归属；无该血缘时使用通用 Unicode 字词重叠作为保守回退。它不包含 Benchmark case ID 或任务固定关键词表。

每项证据写入审计记录：`included`、`exclusion_reason`、source、dependency ID。排除理由为 `invalid`、`unavailable`、`duplicate`、`outside answer_scope` 或 `irrelevant`。被排除内容留在 State 审计中，但不发送给模型；被纳入内容进入 `relevant_evidence` 和 `claim_provenance`。同目标检索归属不是检索质量的独立语义保证：RAG 若返回主题错误但带同目标元数据，仍需后续检索质量审计。本修复不改变 RETRIEVE 的调用或 RAG 排序。
