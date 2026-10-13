# 给评审者会话的开场提示词（Step 9.63c-r11 盲审）

## 1. 准备（你在自己的终端里做）

把盲审包复制到**仓库之外**的独立目录。评审会话只在那里工作，以往评测的文件不在它的工作目录里。

```bash
mkdir -p ~/r11_blind_review && rsync -a --exclude '._*' /Volumes/Elements/cbti-doctor-main/evaluation/v1_2_3/step9_63c_r11_blind_review_packet/ ~/r11_blind_review/
```

```bash
cd ~/r11_blind_review && shasum -a 256 SHA256SUMS && shasum -a 256 -c SHA256SUMS
```

期望：第一行是 `5d95134989289aa6db49b0926f40b40ce0f2b9cc503dd57eb5f5ba7a3f6a668b  SHA256SUMS`，随后 9 行全部 `OK`。

然后**以 `~/r11_blind_review` 为工作目录**开启评审会话：

- **首选 Codex**（与基线评审者同一类型）：在 `~/r11_blind_review` 下启动 Codex，记下它显示的模型和版本。
- 如果 Codex 不可用：在 Claude 中**新开一个会话**，工作目录选 `~/r11_blind_review`。这种情况下，结论里要披露“评审者类型与基线不同”（预注册 D1）。

把下面第 2 节的提示词原样粘贴进去，并把 `<评审者身份>` 换成实际的身份字符串，例如 `Codex AI reviewer (model: <名称>, version: <版本>)` 或 `Claude (<model id>), fresh session`。

## 2. 提示词（原样粘贴）

```text
你是 CBTI-Doctor r11 treatment-V3 运行的唯一评审者（single AI reviewer）。你的身份字符串是：<评审者身份>。每条记录的 review_provenance.reviewer 都必须写这个字符串，一字不改。

当前目录是一个盲审包。规则如下，必须全部遵守：

1. 先运行 `shasum -a 256 SHA256SUMS`，确认输出为 5d95134989289aa6db49b0926f40b40ce0f2b9cc503dd57eb5f5ba7a3f6a668b。不一致就立刻停止并报告，不要评审。
2. 完整阅读 README_REVIEWER.md，它是本次评审的正式规则（预注册的一部分）。规则冲突时，以 README_REVIEWER.md 为准。
3. 只读取当前目录内的文件。只能写 output/ 目录。不要访问当前目录以外的任何文件或目录，不要读 git 历史，不要联网，不要运行任何模型、Agent 或 RAG，也不要试图寻找本包以外的任何结果或评审。
4. 不要修改当前目录中的任何已有文件。
5. 按 review_template.jsonl 的顺序，一次一个案例：阅读该案例在 cases/benchmark_v4_cases.yaml、v3_run/raw_traces.jsonl、v3_run/case_results.jsonl 中的内容，按 rubric/benchmark_v1_1_scoring.md 和 README_REVIEWER.md 写出完整的评审记录（只填写 reviewer_judgments、review_provenance.reviewer、review_provenance.reviewed_at，其余字段从模板原样复制）。
6. 每条记录先用 `python3 validate_review.py check-next output/v3_adjudication.jsonl < 记录文件` 校验，显示 OK 后再作为一行追加到 output/v3_adjudication.jsonl，然后运行 `python3 validate_review.py check-file output/v3_adjudication.jsonl`。
7. 记录一经写入，内容不得修改。只允许修正 schema 格式错误，并且每处修正都要向 output/format_corrections.jsonl 追加一行，写明修改前后的值（见 README_REVIEWER.md 第 5 节）。
8. 不要计算任何汇总：不要算平均分、比率或合计，不要运行任何汇总器或对比脚本。
9. 写完第 40 条后立即停止。报告：output/v3_adjudication.jsonl 的行数、最后一次 check-file 的输出、output/format_corrections.jsonl 是否存在及其行数、你使用的身份字符串，以及你认为需要披露的问题。

现在从第 1 步开始。
```

## 3. 评审结束后（你来做，然后交给我）

```bash
mkdir /Volumes/Elements/cbti-doctor-main/evaluation/v1_2_3/step9_63c_r11_blind_review_output && cp ~/r11_blind_review/output/* /Volumes/Elements/cbti-doctor-main/evaluation/v1_2_3/step9_63c_r11_blind_review_output/
```

下一步（另行进行）会做这些事：校验 40 条记录和格式修正日志；核对盲审包未被修改；写入评审冻结文件（记录 SHA）。按预注册，**只有在冻结之后才运行汇总器**；看到汇总结果之后，任何评审记录都不得修改。
