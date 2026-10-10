# Step 9.63c-r5c10ai 剩余阻断清单

`READY_FOR_R11_FREEZE_REVIEW = NO`。就绪矩阵：29 PASS / 6 BLOCKED / 2 ACCEPTED_EXCEPTION / 0 FAIL。**所有非 PASS 项只有两类：等待人工激活，或已接受的例外（引用批准记录）。**

| 项 | 状态 | 类别 | 说明 |
|---|---|---|---|
| R01 正式 r11 指针 | BLOCKED | 等待人工激活 | 由 `--create-pointer` 在你的终端里创建 |
| R05 20 个成员齐全 | BLOCKED | 等待人工激活 | 缺的就是指针 |
| R13 r10 授权退役（AR-14） | BLOCKED | 等待人工激活 | `--retire-r10` 已就绪、已演练 |
| R16 回归里的 33 个 RC1 项 | BLOCKED | 等待人工激活 | 缺正式 r11 身份时 fail-closed；与上一步是同一个集合 |
| R22 非当前授权均不可执行 | BLOCKED | 等待人工激活 | AR-14 之后成立 |
| R30 已签署的批准记录 | BLOCKED | 等待人工激活 | 见下面“签署前的确切步骤” |
| R15 历史 Trace 原始内容完整性（AR-15） | ACCEPTED_EXCEPTION | 引用批准记录 | `accepted_exceptions[0]`；不是 PASS，只证明当前哈希未变，无法证明原始内容 |
| R16b 已知失败 RC5、RC6 | ACCEPTED_EXCEPTION | 引用批准记录 | 批准记录钉着回归结果文件，签署即接受；两者未修改，等价覆盖通过 |

## 签署前的确切步骤（你来做）

1. 逐条运行 `step9_63c_r5c10ai_activation_approval_checklist.md` 里的命令，输出与期望逐字相同。
2. `git add -A && git commit`，然后 `git status --short` 必须没有任何输出。
3. `cp` 草案为 `step9_63c_r11_activation_approval.json`，只改四个字段：`status`=`SIGNED`、`approver`、`signed_at_utc`、`signed_at_commit`（= `git rev-parse HEAD`）。
4. `$B --plan-retire` 必须 `ready: true`。之后签署之后到激活结束之间**不要再 commit**。

## 之后（本步均未执行）

| 事项 | 状态 |
|---|---|
| AR-14 → 指针 → Freeze → 签发 | 运行手册 `step9_63c_r5c10ai_activation_runbook.md`，你输入令牌 |
| preflight、正式执行 | 激活之后，各自需要批准 |
| AR-16 commit/push | 你来做（第 2 步）；本步所有改动尚未提交 |
| `--approval` 参数（D-E） | 仍保留；下一次 builder 修订再去掉 |
| AR-8/AR-9 | 维持不修改 |

## 观察

- 一旦指针创建，4 个导入阻断模块和 29 个运行时错误项会开始真正执行，结果目前是 `NOT_MEASURED`，不应预设为通过。
- 签发令牌无法提前写全（由已签署文件字节派生，签发器不允许改），签署后 `--plan` 会显示。
