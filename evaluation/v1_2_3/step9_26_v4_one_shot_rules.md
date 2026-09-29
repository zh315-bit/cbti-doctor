# Step 9.26 — V4 One-Shot Rules（冻结草案）

1. V4 case file 在未来构建阶段生成并 seal；本准备阶段不创建或查看任何 case。seal manifest 固定 repository-relative path、byte SHA-256、case count、schema version、UTC creation time、task distribution。
2. “First access”定义为评价方/runner 第一次为正式评估读取 sealed case bytes；数据集作者的构建、校验和静态 leakage audit 不算正式 evaluation access。runner 必须先 append-only 写 `FIRST_EVALUATION_ACCESS`（UTC timestamp、evaluator、evaluation/authorization/attempt IDs、dataset hash），再读取 case 内容。
3. 正式运行开始前显式验证 Agent candidate freeze、Harness/runner、Scoring、Metric Registry、Rules、V4 manifest 与实际 case bytes；任一不匹配或缺失则 fail closed，不刷新冻结值。
4. 使用全新的 evaluation ID、authorization ID、attempt ID，并由授权 manifest 绑定全部身份、V4 path/hash 与成功的 local preflight artifact。一个授权至多启动一个 attempt；无授权、身份不符、先前 attempt 状态含糊时拒绝。
5. append-only attempt lifecycle 至少为 PREPARED → STARTED → COMPLETED / FAILED_BEFORE_FIRST_CASE / FAILED_AFTER_PARTIAL_EXECUTION。STARTED 必须持久化在第一个真实 Agent Loop/case 之前；逐例 trace、score、异常与中断状态及时写入，不覆盖或删除历史。
6. 不选 case、不重排以寻优、不针对 case ID 分支、不手工替换模型输出、不做自动 retry。执行期间不得修改 Agent、Prompt、Tools、RAG、fixtures、dataset、Scoring、Metrics 或 Harness semantics。
7. 完成后重新核对所有 hashes。首次有效完整运行成为 immutable `PRIMARY_HELDOUT_RESULT`。任何模型/API、Harness、Environment、Agent、Scoring failure 均按证据分类；非 Agent 基础设施中断也不能自行重跑，需保留 attempt 并等待新的人类审查/授权。任何后续恢复运行都是独立且披露的 evaluation，不覆盖原 attempt。
8. V2 仅作为历史 development/regression 结果；V3 为 consumed historical set。不得把 V2/V3 与 V4 宣称为 matched/paird comparison，也不重新运行/重评分 V3。
9. 任何缺失的 token、latency 分量、tool timing 写 `NOT_MEASURED`，不得估算。报告分开呈现质量、获取效率、安全；不使用单一通过阈值，也不声称临床效力、普遍优越或已校准信息价值。

当前 V4 runner 尚未准备，当前无 V4 数据集、无 evaluation/authorization/attempt ID、无授权、无 first-access event。本文件只冻结后续规则，不是执行许可。

### 我的理解


### 仍然不理解的问题

