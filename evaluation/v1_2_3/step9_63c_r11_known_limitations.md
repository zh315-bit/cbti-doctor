# r11 已知限制清单

适用范围：r11 Freeze `bafcec8d2ae0bad6c3cb43e89bd49171b85374957ec6ce173071fef5248357b3` 及其唯一授权 `auth-step9_63c_r11-1a399434ec0e4494b0045734846b2042`。本清单汇总此前散落在 `step9_63c_r5c10aj_r11_freeze_review_request.md` 第 5 节、`step9_63c_r5c10ak_r11_freeze_review_request.md` 第 4、7 节中的限制，并加入正式执行后的新发现。那两份历史文件不改。

**凡是需要修改冻结成员的项，都不能在 r11 内修复，必须进入下一个冻结修订版本。**

## A. 缺陷（需要在下一个修订版本修复）

| ID | 内容 | 影响 | 处理 |
|---|---|---|---|
| **KL-1** | `scripts/authorization_lifecycle.py`（r11 第 9 号成员，`f0d8b7e0…612744`）第 229–231 行用 `events[-1]` 判断 burn。只要 `COMMITTED` 之后正常追加了 `ATTEMPT_CLAIMED` 或 `CASE_STARTED`，reducer 就判 `INCONSISTENT_FAIL_CLOSED`；第 241–246 行的 `CONSUMED` 分支对任何合法日志都不可达；“已认领、未开始案例”的状态没有定义。 | 本次已完成的运行被读成 `INCONSISTENT`（应为 `CONSUMED_NON_REUSABLE`）。在 r11 指针下，`active_authorizations()` 抛异常而不是返回 `[]`。方向是 fail-closed，授权不会因此变得可再执行；执行过程与结果不受影响。 | **已知缺陷，不修复**。修复必须进入下一个冻结修订版本；修复建议草案与测试缺口见 `step9_63c_r11_post_run_review.md` 第 1、3 节。 |

## B. 记录与可观测性

| ID | 内容 | 处理 |
|---|---|---|
| KL-2 | 冻结案例路径把 `token_usage` 写死为 `NOT_MEASURED`，冻结记录器也不保存服务层传来的用量；本次运行没有 token 记录。 | 实际消耗只能查 DeepSeek 账单；如需记录，在下一个修订版本中修改记录器。 |
| KL-3 | consumer 的 `--preflight-file` 必须传绝对路径（内部 `relative_to(ROOT)`），相对路径会在预提交门 fail-closed（在任何写入之前）。 | 已在执行计划中规避；下一个修订版本可以先 `resolve()` 再比较。 |

## C. 防护范围

| ID | 内容 |
|---|---|
| KL-4 | guard v3 与会话级硬防护（`tests/session_safety.py`）都是防误操作护栏，不是安全边界：只覆盖安装了它们的 Python 进程，不覆盖 C 扩展、ctypes 或不安装它们的子进程。 |
| KL-5 | 正式执行期间不能使用任何进程内防护：guard v3 会拦截网络与子进程；session_safety 保护的正是 `evaluation/v4_runs/`。本次执行靠 consumer 门禁加事前、事后的整仓白名单比对来保证安全（结果 `ok: true`）。 |

## D. 流程与证据

| ID | 内容 |
|---|---|
| KL-6 | 签发令牌无法在签署前写全（由已签署文件字节派生），只能在签署后由 `--plan` 显示。 |
| KL-7 | AR-14 之后的账本按“模板 + 原前缀不变 + 恰好多一行”验证，而不是整文件 SHA（事件的 uuid 和时间戳在调用时生成）。 |
| KL-8 | builder 命令行仍保留 `--approval` 参数（下一次 builder 修订时去掉）。 |
| KL-9 | 历史文档里的“14 个未变成员”是当时的口径，现行口径是 13（`record.md` 有勘误）。 |
| KL-10 | `evaluation/v4_runs/` 被 `.gitignore` 忽略，本次运行产物目前只存在于本机移动硬盘上；归档方案见 `step9_63c_r11_post_run_review.md` 第 4 节，等待批准。 |

## E. 已接受的例外（不变）

| ID | 内容 |
|---|---|
| AR-15 | 历史 Trace 原始内容完整性 `CONTENT_INTEGRITY_UNPROVEN`（批准记录 `accepted_exceptions[0]`）。 |
| RC5 | `test_step9_43a…test_01a`，被 V2 runner freeze 钉住；等价覆盖是 r5c10ai V2 归档重放。 |
| RC6 | `test_step9_51a…test_current_manifest_passes_pinned_allowlist`。r5c10ak 后失败信息多了 3 条 `missing module file`（28/30a/30c 已归档）；是否接受，或按常设规则退役 51a 测试，**仍待你决定**。 |
