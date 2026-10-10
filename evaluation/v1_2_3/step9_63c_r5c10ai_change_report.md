# Step 9.63c-r5c10ai 变更报告

**一句话**：按你的五项决定处理了 r5c10ah 的剩余问题，并生成最终待签署的激活批准记录（草案、核对清单、运行手册）。**没有任何真实激活**：真实仓库里没有 r11 指针、Freeze、授权或已签署的批准记录；没有执行 AR-14；真实账本仍是 3856 字节；我没有 commit、没有 push。`READY_FOR_R11_FREEZE_REVIEW = NO`——矩阵里所有非 PASS 项都只是“等待人工激活”（6 项）或 `ACCEPTED_EXCEPTION`（2 项：R15 的 AR-15、R16b 的 RC5/RC6），没有 FAIL。

## 1. 新值

| 文件 | SHA-256 | 状态 |
|---|---|---|
| builder | `99031a9156da87164c16b71eff9e2a9961428c52bbf7bc2590741e51e55f950e` | **已变**（原 `9cfaf75a…`）——唯一允许变化的文件 |
| consumer | `362eb4467fdadd29edc056ecf7b446f2cab99a2d3c407d350b4e91494c5b9528` | 未变 |
| 签发器 | `f41763f5c82e04360b3d9bcf694e6d05a6fcfa42ae8d71ada29be4ab204e32ab` | 未变 |
| resolver | `a0f5670d3834d5f91391b41a33fbac669d6162587bc620e9bd3acf202aa3c6a5` | 未变 |

完整性报告 C1–C13 全部通过（含：adapter、`authorization_lifecycle.py`、r7 签发器、r10 成员未变；账本 3856 字节未变；55 个历史钉成立）。

## 2. 五项决定的落实

1. **R16/R33**：`PROPOSED_ad_archival_replay_update.diff` 没有应用。`test_step9_63c_r5c10ad_v2_archival_replay` 整个模块按常设规则（FULL）归档退役；新模块 `test_step9_63c_r5c10ai_v2_archival_replay` 固定从提交 `201ef5c2d406b0eaf2ebf5ce12db912b3caf5762` 读取 V2 字节重放，并断言它存在、是提交对象、是当前 HEAD 的祖先。变异证明（6/6 被杀）：归档字节被篡改（两种）、提交不存在、提交被换成当前 HEAD、祖先关系没有被遍历、对象 ID 形状错误。
2. **退役令牌**：第一段是 r10 授权 ID 中 uuid 部分的前 12 位 `aff5c4b96bb7`；负向测试：用另一个 step9_6x 授权 ID 的前缀（`step9_63c_r4`、`step9_63a_r3`）构造的令牌被拒绝；上一步的字面量前缀 `auth-step9_6` 被拒绝。**第二段不是“批准记录文件的 SHA”，见 §3.1。**
3. **“14 个未变成员”**：历史文档没有改；`record.md` 追加了一条勘误（见该文件）。
4. **AR-15**：批准记录新增 `accepted_exceptions`，写入 `CONTENT_INTEGRITY_UNPROVEN` 及“签署即表示接受”的原文；readiness matrix 的 R15 是 `ACCEPTED_EXCEPTION`（引用批准记录），没有标 PASS。
5. **AR-14 之后的账本**：按“预期追加行模板 + 原前缀逐字节不变 + 恰好多一行”验证，核对清单第 6 节写出了预期追加行的规范字节。

## 3. 必须告诉你的两处设计取舍

1. **令牌第二段用“批准记录内容哈希”，不用“批准记录文件 SHA”**。原因：你要求令牌写出完整具体值，而已签署文件的 SHA 取决于你填的批准人、时间、提交 SHA，现在不可能知道。内容哈希 = 把四个签名字段（`status`、`approver`、`signed_at_utc`、`signed_at_commit`）置空后的规范 JSON 的 SHA-256，所以草案和已签署记录的值相同。它还带来一个好处：签署时多改一个字节（除这四个字段外）就会被拒绝（`approval content differs from the prepared draft apart from the four signature fields`）。同样的第二段也用在 Freeze 令牌里。**例外**：签发入口的令牌 `ISSUE-R11-AUTH-<12 位>` 由已签署文件的字节派生，签发器不允许改，所以只能在签署后由 `--plan` 显示——它不能提前写全。
2. **内容哈希不包含 `repository_aggregate`**。整仓聚合哈希覆盖核对清单和运行手册，而它们引用令牌，令牌又来自内容哈希，包含它会循环。聚合哈希仍被单独核对（任何入口都会拒绝与仓库不符的值），所以没有损失。

## 4. 批准记录的“提交钉”

你要求批准记录钉住“签署时的提交 SHA”，并要求先 commit 再签署。草案**不可能**包含那个 SHA（它包含草案本身）。设计是：草案里 `signed_at_commit` 为 null，`commit_pin.required` 为 true；你 commit 之后把 `git rev-parse HEAD` 填进去（四个签名字段之一）。从此每个门禁入口（AR-14、指针、Freeze、签发）都核对 Git HEAD 仍等于它——所以签署之后到激活结束之间不能再 commit，运行手册里写了。

## 5. 变更清单（独立 diff，回滚已验证）

| 变更 | diff |
|---|---|
| builder（+68/−8） | `step9_63c_r5c10ai_builder.diff` |
| 新测试与夹具 | `step9_63c_r5c10ai_tests.diff` |
| 归档退役（r5c10ad 重放整模块；r5c10ah 的令牌测试 1 个、清单测试 2 个） | `step9_63c_r5c10ai_retirement.diff` |
| r5c10ai 清单、校验器、其测试 | `step9_63c_r5c10ai_manifest.diff` |

回滚验证：把“之后”的文件放进临时目录，按 `manifest → retirement → tests → builder` 逆序 `git apply -R`，builder、`RETIRED_INDEX.json`、r5c10ad 重放模块、两个 r5c10ah 测试文件与改前字节相同。

## 6. 验证

| 项 | 结果 |
|---|---|
| 新测试 | 36 个全部通过（最终形态与令牌 19、V2 归档重放 4、清单 13） |
| 变异 | 33 个，33 个被杀，无幸存者 |
| 演练（临时根，最终版本，只用门禁入口） | PASS：签署记录 → AR-14 → 指针 → Freeze → 签发 → consumer 门；恰好 1 个活动授权；批准记录字节全程不变。**46 个负向演练全部被拒绝，整树哈希证明没有写入**，包括新增的：令牌用另一个 step9_6x ID 前缀、旧字面量前缀、第二段用文件 SHA、各入口 HEAD 已移动、无签署提交、批准记录内容被改 |
| 全量回归（guard v3，两次） | 1074 项 = 1043 通过 / 2 失败 / 29 错误 / 4 导入阻断，两次逐项一致；**非身份类失败只剩 RC5、RC6**；RC1 仍是同一个 33 项集合；生产回归 0、未知 0 |
| 整仓哈希 | 两次回归前/中/后：0 新增、0 删除、0 内容变化、0 仅 mtime 变化；guard 日志 211 条放行的 `Popen`，0 条拦截 |

第一轮回归之后我又改了一处 builder（把聚合哈希排除出内容哈希，§3.2），所以回归、变异和演练都在最终 builder 上重新跑过，上面的数字是重跑后的。

## 7. 其他
- 草案的 `approval_id` 和三个签发 ID 沿用上一版（判定文件因此不变）；`created_at_utc` 与预测 Freeze 随 builder 变化而更新。
- 与上一步一样：`--approval` 参数仍保留（未指示改动）。
- 没有做：AR-14、指针、Freeze、授权、签署、preflight、正式执行、AR-16 的 commit/push。
