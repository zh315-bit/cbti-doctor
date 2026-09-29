# Step 9.23 State → Answer Contract

本契约只约束回答生成，不改变 Agent 的行动选择。`build_answer_context(state)` 是唯一投影入口：传入当前 `goal`、`task_type`、`answer_scope`；从已验证的 State 输出 `user_facts`、`diary_facts`、`relevant_facts`、`relevant_evidence`、`known_missing`、`unavailable_resources`、`semantic_status` 和来源元数据。用户原话、`raw_value` 与未验证工具载荷不进入回答上下文，不能绕过 State 再提取事实。

`user_facts` 仅标记 `source_type=user_explicit` 的字段，保留字段值、轮次和确定性等安全元数据；其他已在 State 的事实仍可出现在兼容字段 `relevant_facts`，但不冒充“用户明确说过”。日记事实仅在 `projection_status=valid` 时进入；无效/不可用日记只进入资源状态，不进入事实。`claim_provenance` 将用户、确定性派生和证据声明与来源关联。`answer_context_audit` 随 State snapshot 留存证据纳入/排除理由和语义状态。

最终一致性检查在现有量化声明与 answer_scope 检查之后执行，只删除能识别为与 State 冲突的事实句，不作医学决策。对无法确定的自然语言隐含声明，仍依赖受限 prompt 与人工审计；不能声称任意生成文本都获得形式化证明。
