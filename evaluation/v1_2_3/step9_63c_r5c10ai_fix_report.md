# Step 9.63c-r5c10ai-fix：只修正激活核对清单

**原因**：清单第 8、9 节的 3 条“期望输出”是在 builder 最后一次修改之前、对仓库里**旧的**草案运行同一批命令时生成的，所以记录了 `KeyError: 'content_sha256'`、`KeyError: 'accepted_exceptions'` 和旧内容哈希 `37ea0d4a…`。

**做法**：没有改任何代码（builder、consumer、签发器、resolver 及其他脚本和测试均未动）。在当前最终仓库上用同一个生成器重新生成清单（和运行手册，内容不变）；新增两个工具文件：`step9_63c_r5c10ai_mutation_tools/generate_checklist_and_runbook.py`（生成器）和 `selfcheck_checklist.py`（自检）。

**自检**：生成之后自动重跑清单里的全部 44 条命令，与记录的“期望输出”逐字比对，并要求期望输出里不得出现 Traceback / Error；结果 **44/44 一致**。以后任何人都可以随时运行 `.venv/bin/python evaluation/v1_2_3/step9_63c_r5c10ai_mutation_tools/selfcheck_checklist.py`（只读）。

**草案**：清单文件变了，整仓聚合哈希随之变化，所以重新生成了草案的 `repository_aggregate`；除它之外草案的每个字段不变，`content_sha256` 与三个令牌不变（内容哈希不包含聚合哈希），具体值见最终说明。
