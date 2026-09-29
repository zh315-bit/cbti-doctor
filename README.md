# CBTI Doctor

一个基于 `LangGraph + LangChain + Flask` 构建的 CBT-I（失眠认知行为疗法）对话助手项目。  
系统通过多阶段智能体流程，引导用户完成睡眠信息收集、问题总结、认知重构与综合干预，并结合本地 PDF 知识库进行 RAG 检索问答。

## 项目简介

本项目面向失眠相关场景，尝试将 CBT-I 的核心咨询流程结构化为可交互的智能体对话系统。  
后端使用 Flask 提供聊天接口，前端为一个轻量网页聊天页面；智能体主流程由 LangGraph 管理，不同治疗阶段由不同子图负责执行。

## 功能特性

- **信息收集阶段**：逐步询问用户的睡眠时间、夜间觉醒、睡前行为、日间习惯、压力事件与失眠相关想法
- **总结反馈阶段**：根据前面对话内容进行归因分析与认知标记
- **认知重构阶段**：识别负性思维，辅助完成替代性思维重建
- **综合干预阶段**：根据用户情况推荐刺激控制、睡眠限制、睡眠教育等 CBT-I 模块
- **RAG 检索**：从 `rag_lib/pdfs/` 中加载 CBT-I 相关 PDF，构建本地向量库并回答专业问题
- **网页交互**：前端通过 `/api/chat` 与后端通信，支持基础会话管理
- **CLI 模式**：可切换为命令行对话模式，便于调试

## 运行方式

### 0. 安装依赖与配置密钥

使用 Python 3.12，在项目根目录执行：

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-bge-lock.txt
```

当前配置为 DeepSeek V4.1 Flash + 本地 BGE，安装时使用包含本地推理依赖的 `requirements-bge-lock.txt`。`requirements.txt` 记录基础依赖范围，`requirements-lock.txt` 保留基础环境版本。项目使用 LangChain 0.3 系列接口，不要单独升级到 1.x。

若 `.env` 不存在，从 `.env.example` 复制一份，然后在本地编辑以下字段：

| 环境变量 | 用途 |
| --- | --- |
| `DEEPSEEK_API_KEY` | 主对话及 RAG 回答，唯一必需的 API 密钥 |
| `DEEPSEEK_MODEL` | 默认 `deepseek-flash`，对应 DeepSeek V4.1 Flash |
| `DEEPSEEK_BASE_URL` | 默认 `https://api.deepseek.com` |
| `BGE_MODEL_PATH` | 默认 `models/bge-small-zh-v1.5`，相对项目根目录 |
| `ENABLE_WEB_SEARCH` | 默认 `false`，无需 Tavily 密钥 |
| `TAVILY_API_KEY` | 仅显式启用网页搜索时需要 |

`.env` 已被 Git 忽略。不要将密钥写进代码或提交到仓库。虚拟环境不包含任何服务账号或额度，真实对话仍需有效密钥。

### 1. 启动后端 Flask 服务

在项目根目录执行：

```bash
.venv/bin/python main_flask.py
```

默认会启动在：`http://localhost:5001`。如需使用其他未占用端口，可在 `.env` 设置 `PORT=5002`，并同步修改 `public/index.html` 中的 `CBTI_API_PORT`。

### 2. 启动前端页面

前端文件位于 `public/` 目录，推荐使用一个简单静态服务器启动：

```bash
.venv/bin/python -m http.server 8000 --bind 127.0.0.1 --directory public
```

然后访问：`http://localhost:8000`

### 3. 启动命令行模式

如果希望使用终端交互模式，可设置环境变量后运行：

```bash
RUN_MODE=cli .venv/bin/python main_flask.py
```

## 注意事项

- 本项目主要用于学习、研究和原型验证，不应替代专业医生或心理治疗师的诊断与治疗建议。
- 首次运行时，会自动处理 `rag_lib/pdfs/` 中的 PDF 并生成向量数据库，可能会需要一些时间。
- 网页会话会保留当前阶段、完整消息和工具结果；会话结束后可点击“重置会话”重新开始。当前仍使用进程内存保存会话，重启服务会清空，不支持多进程共享。

## 离线回归测试

```bash
.venv/bin/python -m unittest discover -s tests -v
```

会话测试使用真实的应用工厂函数和模拟的 Flask、消息及图对象，覆盖阶段恢复、工具结果保留、会话隔离、重置、调用失败和会话结束处理。模型配置测试还验证 DeepSeek 配置、BGE 查询前缀及索引文件检查；全部测试不调用外部 API。它们不替代真实 Flask/LangGraph 集成测试。

## 已下载的本地 BGE 模型

`BAAI/bge-small-zh-v1.5` 存放在 `models/bge-small-zh-v1.5/`，该目录不提交到 Git。模型来源版本和权重校验值见目录中的 `download_source.json`。它生成 512 维中文向量，可在 CPU 上离线运行，无需 API 密钥。

本地推理额外依赖见 `requirements-bge.txt`，含 BGE 的完整环境版本见 `requirements-bge-lock.txt`（可用 `pip install -r requirements-bge-lock.txt` 复现）。验证命令：

```bash
.venv/bin/python scripts/check_bge.py
```

`rag_client.py` 已接入本地 BGE，文档与查询向量都在 CPU 本地生成。首次检索会自动构建专用索引 `rag_lib/.rag_db/bge-small-zh-v1.5-ch400-v1/`，不会复用旧 OpenAI 向量索引。回答生成仍调用 DeepSeek，相关检索片段会作为上下文发送给该服务。

主对话、总结工具和 RAG 回答共用 `model_config.py`。默认关闭思考模式，以兼容现有工具消息链；模型配置修改后需重启服务。
