import os
import yaml
from dotenv import load_dotenv
from typing import Annotated, Sequence, Optional
from typing_extensions import TypedDict
from rag_client import retrieval_augmentation_generation
from langchain_tavily import TavilySearch

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage, ToolMessage
from langchain_openai import ChatOpenAI

# Flask 集成
import uuid
from flask import Flask, request, jsonify
from flask_cors import CORS


# ================== 工具定义 ==================
# 网络搜索工具
search_tool = TavilySearch(max_results=5, search_depth="advanced", topic="general")

def negative_thinking_record_tool(model: ChatOpenAI):
    @tool
    def negative_thinking_record(conversation: str) -> str:
        """
        用markdown表格总结用户在谈话中展现出的负性思维
        :param conversation: 必要参数，字符串类型，谈话记录
        :return: 字符串类型，负性思维总结表格
        """

        sys_prompt = (
            "你是一名专业的CBT-I治疗师。请分析下面的对话，识别并归纳用户的负性思维，"
            "并生成一个Markdown表格，严格包含以下列且使用这些列名：\n"
            "1) 事件；2) 负性思维内容；3) 情绪反应；4) 思维扭曲类型；5) 替代性思维。\n"
            "生成要求：\n"
            "- 事件：从对话中提炼具体情境，用一段话总结。\n"
            "- 负性思维内容：尽量贴近原话或准确转述。\n"
            "- 情绪反应：结合上下文判断（如焦虑、沮丧、愤怒、内疚等），必要时可注明强度（如“轻度/中度/重度”）。\n"
            "- 思维扭曲类型：从常见类别中选择，使用中文并以顿号分隔多项，如“灾难化、非黑即白、过度概括、心理过滤、贴标签、应该化、读心术、预言错误、放大/缩小、个人化”。\n"
            "- 替代性思维：给出具体、平衡、可执行的替代观点，避免空泛。\n"
            "- 如果信息不足仍需输出至少一行，并在“事件”或“负性思维内容”中说明。\n"
            "- 只输出表格，不要任何解释或额外文本。"
        )

        messages = [
            SystemMessage(content=sys_prompt),
            HumanMessage(content=f"请基于以下对话记录进行分析并直接输出表格：\n{conversation}"),
        ]

        response = model.invoke(messages)
        content = response.content if isinstance(response, AIMessage) else str(response)

        if ("|" not in content) or ("事件" not in content) or ("负性思维内容" not in content):
            content = (
                "| 事件 | 负性思维内容 | 情绪反应 | 思维扭曲类型 | 替代性思维 |\n"
                "| --- | --- | --- | --- | --- |\n"
                "| 信息不足 | 无法从当前对话准确提取 | 焦虑（估计） | 未识别 | 从更多角度评估并给予现实、具体的替代观点 |"
            )

        return content

    return negative_thinking_record


def dialogue_summary_tool(model: ChatOpenAI):
    @tool
    def dialogue_summary(conversation: str) -> str:
        """
        把本阶段中的对话进行总结，提取其中重要信息，降低token占用，并为后续对话提供依据
        :param conversation: 必要参数，字符串类型，谈话记录
        :return: 字符串类型，谈话记录总结
        """

        sys_prompt = (
            "我会给你一段CBTI治疗师与用户之间的谈话记录。"
            "请你根据这段谈话记录，提取其中重要的信息，比如用户的上床时间、入睡时间、起床时间、夜间觉醒次数、睡眠质量评分，以及睡眠习惯、日间行为、压力事件和失眠时的思维等信息。"
            "另外在信息收集过程中，一些和用户个人相关的想法都需要记录下来。"
            "最后总结成一段文本，为后续的对话提供依据。"
        )

        messages = [
            SystemMessage(content=sys_prompt),
            HumanMessage(content=f"请基于以下对话记录进行总结：\n{conversation}"),
        ]

        response = model.invoke(messages)
        content = response.content if isinstance(response, AIMessage) else str(response)

        return content

    return dialogue_summary


# ================== 核心封装层 ==================
# 定义状态类型
class AgentState(TypedDict):
    """Agent的状态定义"""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    enter_stage: str  # 进入下一个阶段的标志


class InformationGatheringAgent:
    """第一阶段 - 信息收集智能体"""

    def __init__(self, model: Optional[ChatOpenAI] = None, config=None, main_tools=None) -> None:
        # YAML配置
        self.config = config
        # 模型配置
        self.model = model

        # 工具配置
        dialogue_summary = dialogue_summary_tool(self.model)
        self.tools = [dialogue_summary]

        # 加入通用工具
        if main_tools:
            self.tools.extend(main_tools)

        self.tool_node = ToolNode(tools=self.tools)
        self.model = self.model.bind_tools(self.tools)

        # 构建图
        self.workflow = StateGraph(AgentState)
        # 设置节点
        self.workflow.add_node("chat", self._chat_node)
        self.workflow.add_node("tools", self.tool_node)
        # 设置入口点与边
        self.workflow.set_entry_point("chat")
        self.workflow.add_edge("tools", "chat")
        self.workflow.add_edge("chat", END)
        # 设置条件分支
        self.workflow.add_conditional_edges(
            "chat",
            tools_condition,
            {"tools": "tools", END: END}
        )

        # 编译图结构
        self.subgraph_information_gathering = self.workflow.compile()

        # 定义默认提示词
        system_prompt = """
        你是一名严谨的CBT-I（失眠认知行为疗法）治疗师，现在处于信息收集阶段。
        你的任务是通过结构化对话收集用户的基础睡眠数据、睡眠习惯、睡前行为、压力事件和失眠时的思维等信息。

        1. 基础睡眠数据：上床时间、入睡时间（不要问多久入睡，直接问时间点）、起床时间、夜间觉醒次数、睡眠质量评分（0-10分）
        2. 睡眠习惯：睡前都会做什么活动？使用电子设备吗？
        3. 日间行为：白天的运动、咖啡因摄入、午睡情况
        4. 压力事件：最近是否有让您感到压力的事情？
        5. 思维：失眠时脑海中会出现什么想法？

        请保持专业且共情的态度，每次只问一个问题，不要让用户一次性提供多项数据。
        如果用户出现不配合回答（如拒绝回答，或拒绝你提出的建议，不想改变现状等情况），或者用户不知道怎么回答时，就直接跳过当前问题，并且不要再询问相关的问题。

        【工具说明】
        1. dialogue_summary：把本阶段中的对话进行总结，提取其中重要信息，降低token占用，并为后续对话提供依据
        2. retrieval_augmentation_generation：这是一个与失眠认知行为疗法（CBT-I）医学知识相关的RAG知识库。如果用户提出的问题与CBT-I相关，从RAG数据库中检索相关文档，并使用这些文档生成答案。

        【重要规则】
        当你认为已经收集到足够信息，准备进入总结阶段时，**请严格按以下两步执行**：
        1. 先调用 dialogue_summary 工具，把当前全部对话历史传给它进行总结。
        2. 在工具返回总结结果后，再对用户说：“好的，已了解您的情况，接下来我们进入总结反馈阶段”。
        3. 注意只需要使用工具进行总结，你不要自己做总结。

        **永远不要在没有调用工具的情况下直接说“接下来我们进入总结反馈阶段”**
        """

        if config and config.get("prompt_file"):
            try:
                with open(config["prompt_file"], "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        system_prompt = content
                    else:
                        print(f"外部提示词文件为空，使用默认提示词")
            except Exception as e:
                print(f"读取提示词文件失败（{e}），使用默认提示词")

        self.system_message: Sequence[BaseMessage] = [SystemMessage(content=system_prompt)]

    def _chat_node(self, state: AgentState) -> AgentState:
        """处理用户消息并生成回复"""
        messages = state["messages"]
        # 注入阶段系统指令
        if not any(isinstance(m, SystemMessage) and m.content == self.system_message[0].content for m in messages):
            messages = list(self.system_message) + list(messages)
        response = self.model.invoke(messages)

        # 判断是否进入下一阶段
        enter_stage = state["enter_stage"]

        next_trigger = self.config.get("next_trigger", "进入总结反馈阶段") if self.config else "进入总结反馈阶段"
        next_stage = self.config.get("next_stage", "summary_feedback") if self.config else "summary_feedback"
        if isinstance(response, AIMessage) and (next_trigger in response.content):
            enter_stage = next_stage

        return {"messages": [response], "enter_stage": enter_stage}


class SummaryFeedbackAgent:
    """第二阶段 - 总结反馈智能体"""

    def __init__(self, model: Optional[ChatOpenAI] = None, config=None, main_tools=None) -> None:
        # YAML配置
        self.config = config
        # 模型配置
        self.model = model

        # 工具配置
        self.tools = []

        # 加入通用工具
        if main_tools:
            self.tools.extend(main_tools)

        self.tool_node = ToolNode(tools=self.tools)
        self.model = self.model.bind_tools(self.tools)

        # 构建图
        self.workflow = StateGraph(AgentState)
        # 设置节点
        self.workflow.add_node("chat", self._chat_node)
        self.workflow.add_node("tools", self.tool_node)
        # 设置入口点与边
        self.workflow.set_entry_point("chat")
        self.workflow.add_edge("tools", "chat")
        self.workflow.add_edge("chat", END)
        # 设置条件分支
        self.workflow.add_conditional_edges(
            "chat",
            tools_condition,
            {"tools": "tools", END: END}
        )

        # 编译图结构
        self.subgraph_summary_feedback = self.workflow.compile()

        # 定义默认提示词
        system_prompt = """
        你是一名严谨的CBT-I（失眠认知行为疗法）治疗师，现在处于总结反馈阶段。
        
        基于前面收集的信息，请进行以下分析：
        
        1. 三维度归因分析：
            - 生理因素：睡眠节律、身体状况等
            - 心理因素：压力、焦虑、负性思维等
            - 行为因素：睡前行为、睡眠习惯等
        
        2. 认知标记：识别并明确指出具体的认知扭曲类型，如：
            - 灾难化思维（catastrophizing）
            - 非黑即白思维（all-or-nothing thinking）
            - 过度概括（overgeneralization）
            - 心理过滤（mental filtering）
        
        【工具说明】
        1. retrieval_augmentation_generation：
            - 这是一个与失眠认知行为疗法（CBT-I）医学知识相关的RAG知识库。如果用户提出的问题与CBT-I相关，从RAG数据库中检索相关文档，并使用这些文档生成答案。
        
        你需要增强与用户的互动性，把结论一条条地告诉用户，询问用户是否对总结有异议，绝对不能一次性把内容全部说出来。
        完成这一阶段任务后，请说"接下来我们进入认知重构阶段"。
        """

        if config and config.get("prompt_file"):
            try:
                with open(config["prompt_file"], "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        system_prompt = content
                    else:
                        print(f"外部提示词文件为空，使用默认提示词")
            except Exception as e:
                print(f"读取提示词文件失败（{e}），使用默认提示词")

        self.system_message: Sequence[BaseMessage] = [SystemMessage(content=system_prompt)]

    def _chat_node(self, state: AgentState) -> AgentState:
        """处理用户消息并生成回复"""
        messages = state["messages"]
        # 注入阶段系统指令
        if not any(isinstance(m, SystemMessage) and m.content == self.system_message[0].content for m in messages):
            messages = list(self.system_message) + list(messages)
        response = self.model.invoke(messages)

        # 判断是否进入下一阶段
        enter_stage = state["enter_stage"]

        next_trigger = self.config.get("next_trigger", "进入认知重构阶段") if self.config else "进入认知重构阶段"
        next_stage = self.config.get("next_stage", "cognitive_restructuring") if self.config else "cognitive_restructuring"
        if isinstance(response, AIMessage) and (next_trigger in response.content):
            enter_stage = next_stage

        return {"messages": [response], "enter_stage": enter_stage}


class CognitiveRestructuringAgent:
    """第三阶段 - 认知重构智能体"""

    def __init__(self, model: Optional[ChatOpenAI] = None, config=None, main_tools=None) -> None:
        # YAML配置
        self.config = config
        # 模型配置
        self.model = model

        # 工具配置
        negative_thinking_record = negative_thinking_record_tool(self.model)
        self.tools = [negative_thinking_record]

        # 加入通用工具
        if main_tools:
            self.tools.extend(main_tools)

        self.tool_node = ToolNode(tools=self.tools)
        self.model = self.model.bind_tools(self.tools)

        # 构建图
        self.workflow = StateGraph(AgentState)
        # 设置节点
        self.workflow.add_node("chat", self._chat_node)
        self.workflow.add_node("tools", self.tool_node)
        # 设置入口点与边
        self.workflow.set_entry_point("chat")
        self.workflow.add_edge("tools", "chat")
        self.workflow.add_edge("chat", END)
        # 设置条件分支
        self.workflow.add_conditional_edges(
            "chat",
            tools_condition,
            {"tools": "tools", END: END}
        )

        # 编译图结构
        self.subgraph_cognitive_restructuring = self.workflow.compile()

        # 定义默认提示词
        system_prompt = """
        你是一名严谨的CBT-I（失眠认知行为疗法）治疗师，现在处于认知重构阶段。
        
        你的任务是运用专业的认知重构技术，帮助用户识别并改变与睡眠相关的负性思维模式。请灵活运用以下三种核心技术：
        
        1. 连续谱技术：
            - 运用量化评估方法，帮助用户重新评估灾难化思维的合理性
            - 引导用户在0-100的量表上评估各种睡眠相关担忧的真实程度
            - 通过量化分析，帮助用户认识到极端思维的不合理性
            - 循序渐进地进行，避免一次性提出过多量表
        
        2. 行为实验设计：
            - 与用户协作设计小规模、可执行的行为实验
            - 帮助用户通过实际行动验证或反驳其睡眠相关的负性假设
            - 确保实验设计科学合理，具有可操作性和安全性
            - 鼓励用户主动参与实验设计过程
        
        3. 替代性思维：
            - 引导用户探索更加平衡、现实和建设性的思维方式
            - 帮助用户从多个角度重新审视睡眠问题
            - 培养用户的认知灵活性，发现思维的多样性
            - 协助用户建立更加适应性的睡眠认知模式
        
        请按照用户的具体情况和需要，灵活运用这些技术。保持专业、耐心和共情的态度，根据用户的反应调整干预策略。如果用户表现出抗拒或困惑，请适时调整方法或跳过当前技术。
        
        【工具说明】
        1. negative_thinking_record：
            - 用于从之前的对话记录中总结出负性思维
            - 输入：用户的对话记录
            - 输出：用户的负性思维总结
        2. retrieval_augmentation_generation：
            - 这是一个与失眠认知行为疗法（CBT-I）医学知识相关的RAG知识库。如果用户提出的问题与CBT-I相关，从RAG数据库中检索相关文档，并使用这些文档生成答案。
        
        在本阶段中，用户可能提出需要从之前的对话记录中总结出负性思维，你需要调用negative_thinking_record工具，然后把得到的负性思维用Markdown格式展示出来。
        总结完负性思维后，延续之前的话题进行对话。
        当认知重构工作基本完成时，请说"接下来我们进行综合干预阶段"。
        """

        if config and config.get("prompt_file"):
            try:
                with open(config["prompt_file"], "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        system_prompt = content
                    else:
                        print(f"外部提示词文件为空，使用默认提示词")
            except Exception as e:
                print(f"读取提示词文件失败（{e}），使用默认提示词")

        self.system_message: Sequence[BaseMessage] = [SystemMessage(content=system_prompt)]

    def _chat_node(self, state: AgentState) -> AgentState:
        """处理用户消息并生成回复"""
        messages = state["messages"]
        # 注入阶段系统指令
        if not any(isinstance(m, SystemMessage) and m.content == self.system_message[0].content for m in messages):
            messages = list(self.system_message) + list(messages)
        response = self.model.invoke(messages)

        # 判断是否进入下一阶段
        enter_stage = state["enter_stage"]

        next_trigger = self.config.get("next_trigger", "进行综合干预阶段") if self.config else "进行综合干预阶段"
        next_stage = self.config.get("next_stage", "comprehensive_intervention") if self.config else "comprehensive_intervention"
        if isinstance(response, AIMessage) and (next_trigger in response.content):
            enter_stage = next_stage

        return {"messages": [response], "enter_stage": enter_stage}


class ComprehensiveInterventionAgent:
    """第四阶段 - 综合干预智能体"""

    def __init__(self, model: Optional[ChatOpenAI] = None, config=None, main_tools=None) -> None:
        # YAML配置
        self.config = config
        # 模型配置
        self.model = model

        # 工具配置
        self.tools = []

        # 加入通用工具
        if main_tools:
            self.tools.extend(main_tools)

        self.tool_node = ToolNode(tools=self.tools)
        self.model = self.model.bind_tools(self.tools)

        # 构建图
        self.workflow = StateGraph(AgentState)
        # 设置节点
        self.workflow.add_node("chat", self._chat_node)
        self.workflow.add_node("tools", self.tool_node)
        # 设置入口点与边
        self.workflow.set_entry_point("chat")
        self.workflow.add_edge("tools", "chat")
        self.workflow.add_edge("chat", END)
        # 设置条件分支
        self.workflow.add_conditional_edges(
            "chat",
            tools_condition,
            {"tools": "tools", END: END}
        )

        # 编译图结构
        self.subgraph_comprehensive_intervention = self.workflow.compile()

        # 定义默认提示词
        system_prompt = """
        你是一名严谨的CBT-I（失眠认知行为疗法）治疗师，现在处于综合干预阶段。
        
        基于前面的分析和认知重构，请为用户推荐适合的CBTI模块并详细教导使用方法：
        
        1. 刺激控制技术：
            - 只在困倦时才上床
            - 床只用于睡觉和性生活
            - 如果20分钟内无法入睡，起床做安静活动
            - 固定起床时间，无论睡眠质量如何
            - 避免白天午睡
        
        2. 睡眠限制技术：
            - 根据睡眠日记计算睡眠效率
            - 限制在床时间等于实际睡眠时间
            - 逐步调整睡眠窗口
            - 监控睡眠效率改善情况
        
        3. 睡眠教育：
            - 正常睡眠的生理机制
            - 睡眠需求的个体差异
            - 年龄对睡眠的影响
            - 睡眠卫生知识
        
        请根据用户的实际情况，推荐一个或多个最适合的模块，并且提出证据解释为什么推荐这个模块，然后讲述如何在日常生活中应用推荐的模块。
        如果推荐了多个模块，必须分别解释每个模块的作用和使用方法。当一个模块解释完后，询问用户是否已了解该模块。如果用户已了解，则继续解释下一个模块。如果用户未了解，则必须先解释清楚该模块，然后再继续。
        解释完毕后，询问用户是否还有问题。如果没有问题，则结束对话。
        
        【工具说明】
        1. retrieval_augmentation_generation：
            - 这是一个与失眠认知行为疗法（CBT-I）医学知识相关的RAG知识库。如果用户提出的问题与CBT-I相关，从RAG数据库中检索相关文档，并使用这些文档生成答案。
        
        【结束语】
        我们可以在下一次会谈时一起回顾你的记录，看看你是否有新的感受和进展。记住，睡眠问题是可以逐渐改善的，而你已经迈出了非常重要的一步。如果你有任何疑问或需要帮助，请随时联系我。祝你晚安！
        """

        if config and config.get("prompt_file"):
            try:
                with open(config["prompt_file"], "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        system_prompt = content
                    else:
                        print(f"外部提示词文件为空，使用默认提示词")
            except Exception as e:
                print(f"读取提示词文件失败（{e}），使用默认提示词")

        self.system_message: Sequence[BaseMessage] = [SystemMessage(content=system_prompt)]

    def _chat_node(self, state: AgentState) -> AgentState:
        """处理用户消息并生成回复"""
        messages = state["messages"]
        # 注入阶段系统指令
        if not any(isinstance(m, SystemMessage) and m.content == self.system_message[0].content for m in messages):
            messages = list(self.system_message) + list(messages)
        response = self.model.invoke(messages)

        # 判断是否进入下一阶段
        enter_stage = state["enter_stage"]

        next_trigger = self.config.get("next_trigger", "晚安") if self.config else "晚安"
        next_stage = self.config.get("next_stage", "end_process") if self.config else "end_process"
        if isinstance(response, AIMessage) and (next_trigger in response.content):
            enter_stage = next_stage

        return {"messages": [response], "enter_stage": enter_stage}


class CognitiveTherapyAgent:
    """主智能体 - 认知疗法智能体"""

    def __init__(self, config_path="configs/stages.yaml") -> None:
        # 加载环境变量
        load_dotenv()

        # 加载YAML配置
        with open(config_path, "r", encoding="utf-8") as f:
            self.stage_configs = yaml.safe_load(f)

        # 主图配置
        main_config = self.stage_configs["main-graph"]

        # 模型配置
        api_key = os.getenv("KIMI_API_KEY")
        if not api_key:
            raise ValueError("请配置 .env 或传入 api_key")
        self.model = ChatOpenAI(
            model="moonshot-v1-32k",
            api_key=api_key,
            base_url="https://api.moonshot.cn/v1"
        )

        # 配置通用工具
        self.main_tools = [retrieval_augmentation_generation, search_tool]

        # 实例化子图
        self.sub_agents = {}
        for stage_name, config in self.stage_configs["subgraph"].items():
            class_name = globals()[config["class_name"]]
            self.sub_agents[stage_name] = class_name(model=self.model, config=config, main_tools=self.main_tools)

        # 构建图
        self.workflow = StateGraph(AgentState)
        # 设置节点
        self.workflow.add_node("route", self._route_node)
        self.workflow.add_node("subgraph_information_gathering", self.sub_agents["information_gathering"].subgraph_information_gathering)
        self.workflow.add_node("subgraph_summary_feedback", self.sub_agents["summary_feedback"].subgraph_summary_feedback)
        self.workflow.add_node("subgraph_cognitive_restructuring", self.sub_agents["cognitive_restructuring"].subgraph_cognitive_restructuring)
        self.workflow.add_node("subgraph_comprehensive_intervention", self.sub_agents["comprehensive_intervention"].subgraph_comprehensive_intervention)
        # 设置入口点与条件边
        self.workflow.set_entry_point("route")
        self.workflow.add_conditional_edges(
            "route",
            self.choose_route,
            {
                "subgraph_information_gathering": "subgraph_information_gathering",
                "subgraph_summary_feedback": "subgraph_summary_feedback",
                "subgraph_cognitive_restructuring": "subgraph_cognitive_restructuring",
                "subgraph_comprehensive_intervention": "subgraph_comprehensive_intervention",
                "end_process": END,
            },
        )
        # 子图结束后直接返回父图 END（避免单次内多次调用）
        self.workflow.add_edge("subgraph_information_gathering", END)
        self.workflow.add_edge("subgraph_summary_feedback", END)
        self.workflow.add_edge("subgraph_cognitive_restructuring", END)
        self.workflow.add_edge("subgraph_comprehensive_intervention", END)

        self.main_graph = self.workflow.compile()

        # 定义默认提示词
        system_prompt = """
        你是一个有着丰富经验的CBT-I（失眠认知行为疗法）治疗师。你要指导用户进行认知疗法，注意以下几点：
        1. 认知疗法是一种基于认知行为理论（Cognitive Behavioral Therapy, CBT）的治疗方法，用于帮助患者识别和改变负面思维模式。
        2. 治疗师要与患者建立信任关系，理解患者的情感和需求。
        3. 治疗师要根据患者的情况，提供有针对性的建议和指导。
        4. 治疗师在互动过程中不能一次性提出多个问题，必须一个问题一个问题地引导患者。
        
        当用户主动提问与CBTI或失眠相关的问题时，你需要调用retrieval_augmentation_generation工具，从RAG知识库中查找相关信息并回答。
        完成回答后，继续之前的话题或提问。
        """

        if main_config and main_config.get("prompt_file"):
            try:
                with open(main_config["prompt_file"], "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        system_prompt = content
                    else:
                        print(f"外部提示词文件为空，使用默认提示词")
            except Exception as e:
                print(f"读取提示词文件失败（{e}），使用默认提示词")

        self.message_history: list[BaseMessage] = [SystemMessage(content=system_prompt)]

    def _route_node(self, state: AgentState) -> AgentState:
        """路由节点"""
        if not state.get("enter_stage"):
            return {"enter_stage": "information_gathering"}
        return {}

    def choose_route(self, state: AgentState) -> str:
        """根据状态选择路由到信息收集或总结反馈子图"""
        if state.get("enter_stage") == "information_gathering":
            return "subgraph_information_gathering"
        elif state.get("enter_stage") == "summary_feedback":
            return "subgraph_summary_feedback"
        elif state.get("enter_stage") == "cognitive_restructuring":
            return "subgraph_cognitive_restructuring"
        elif state.get("enter_stage") == "comprehensive_intervention":
            return "subgraph_comprehensive_intervention"
        else:
            return "end_process"

    def _compress_history_node(self, state: AgentState) -> dict:
        """
        取消add_messages，手动实现历史记录追加时可启用.
        当阶段切换时压缩历史：
        - 如果 is_summarize_dialogue 为 True：
            - 保留所有 SystemMessage 和 ToolMessage
            - 删除所有 HumanMessage 和 AIMessage（普通对话）
            - 将 is_summarize_dialogue 重置为 False
        - 否则不做处理
        """
        print(f"is_summarize_dialogue: {state.get('is_summarize_dialogue')}")
        if state.get("is_summarize_dialogue"):
            messages = state["messages"]

            # 保留 SystemMessage 和 ToolMessage，过滤掉 Human 和 AI 的普通对话
            kept_messages = [
                msg for msg in messages
                if isinstance(msg, (SystemMessage, ToolMessage))
            ]
            return {"messages": kept_messages, "enter_stage": state.get("enter_stage"), "is_summarize_dialogue": False}


# Flask 应用工厂，提供 /api/chat 等接口供前端调用

def create_app():
    app = Flask(__name__)
    CORS(app, supports_credentials=True)

    server_agent = CognitiveTherapyAgent()

    sessions: dict[str, list[BaseMessage]] = {}

    # 读取阶段提示词，供阶段切换时注入系统消息
    try:
        with open(server_agent.stage_configs["subgraph"]["information_gathering"]["prompt_file"], "r", encoding="utf-8") as f:
            information_gathering_prompt = f.read().strip() or ""
    except Exception as e:
        print(f"信息收集阶段提示词文件读取失败（{e}），使用默认提示词")
        information_gathering_prompt = ""
    try:
        with open(server_agent.stage_configs["subgraph"]["summary_feedback"]["prompt_file"], "r", encoding="utf-8") as f:
            summary_feedback_prompt = f.read().strip() or ""
    except Exception as e:
        print(f"总结反馈阶段提示词文件读取失败（{e}），使用默认提示词")
        summary_feedback_prompt = ""
    try:
        with open(server_agent.stage_configs["subgraph"]["cognitive_restructuring"]["prompt_file"], "r", encoding="utf-8") as f:
            cognitive_restructuring_prompt = f.read().strip() or ""
    except Exception as e:
        print(f"认知重构阶段提示词文件读取失败（{e}），使用默认提示词")
        cognitive_restructuring_prompt = ""
    try:
        with open(server_agent.stage_configs["subgraph"]["comprehensive_intervention"]["prompt_file"], "r", encoding="utf-8") as f:
            comprehensive_intervention_prompt = f.read().strip() or ""
    except Exception as e:
        print(f"综合干预阶段提示词文件读取失败（{e}），使用默认提示词")
        comprehensive_intervention_prompt = ""

    @app.route("/api/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok"}), 200

    @app.route("/api/chat", methods=["POST"])
    def chat():
        data = request.get_json(force=True) or {}
        message = (data.get("message") or "").strip()
        session_id = data.get("session_id")
        if not message:
            return jsonify({"error": "message is required"}), 400

        if not session_id:
            session_id = str(uuid.uuid4())
        history = sessions.get(session_id)
        if history is None:
            history = list(server_agent.message_history)

        history.append(HumanMessage(content=message))
        prior_len = len(history)
        result = server_agent.main_graph.invoke({"messages": history})
        # 收集本轮调用的工具名称
        tools_used: list[str] = []
        try:
            for msg in result["messages"][prior_len:]:
                if isinstance(msg, ToolMessage):
                    name = getattr(msg, "name", None)
                    if name:
                        tools_used.append(name)
        except Exception:
            pass
        # 去重保持顺序
        seen = set()
        tools_used = [t for t in tools_used if not (t in seen or seen.add(t))]

        ai_text = result["messages"][-1].content
        history.append(AIMessage(content=ai_text))

        if "进入总结反馈阶段" in ai_text and summary_feedback_prompt:
            history.append(SystemMessage(content=summary_feedback_prompt))
        if "进入认知重构阶段" in ai_text and cognitive_restructuring_prompt:
            history.append(SystemMessage(content=cognitive_restructuring_prompt))
        if "进行综合干预阶段" in ai_text and comprehensive_intervention_prompt:
            history.append(SystemMessage(content=comprehensive_intervention_prompt))

        sessions[session_id] = history

        return jsonify({"session_id": session_id, "assistant": ai_text, "tools_used": tools_used}), 200

    @app.route("/api/reset", methods=["POST"])
    def reset():
        data = request.get_json(force=True) or {}
        session_id = data.get("session_id")
        if not session_id:
            return jsonify({"error": "session_id is required"}), 400
        sessions.pop(session_id, None)
        return jsonify({"ok": True}), 200

    return app


cognitive_therapy_agent = CognitiveTherapyAgent().main_graph


def view_history(message: list[BaseMessage]) -> None:
    """查看指定线程的消息历史（模块级函数）"""

    def role_of(m: BaseMessage) -> str:
        if isinstance(m, SystemMessage):
            return "系统"
        if isinstance(m, HumanMessage):
            return "用户"
        if isinstance(m, AIMessage):
            return "助手"
        if isinstance(m, ToolMessage):
            return "工具"
        return type(m).__name__

    print(f"历史条数: {len(message)}")
    for i, m in enumerate(message, 1):
        print(f"[{i}] {role_of(m)}: {m.content}")


if __name__ == "__main__":
    # 通过环境变量控制运行模式：默认启动 Flask，为需要终端交互时设置 RUN_MODE=cli
    mode = os.getenv("RUN_MODE", "flask")
    if mode == "flask":
        app = create_app()
        # 对外提供 5000 端口，便于本地前端（http://localhost:8000）跨域调用
        app.run(host="0.0.0.0", port=5000)
    else:
        # 保留原有命令行交互模式
        agent = CognitiveTherapyAgent()

        message_history = list(agent.message_history)
        try:
            with open(agent.stage_configs["subgraph"]["information_gathering"]["prompt_file"], "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    information_gathering_prompt = content
                else:
                    print(f"信息收集阶段提示词文件为空，使用默认提示词")

            with open(agent.stage_configs["subgraph"]["summary_feedback"]["prompt_file"], "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    summary_feedback_prompt = content
                else:
                    print(f"总结反馈阶段提示词文件为空，使用默认提示词")

            with open(agent.stage_configs["subgraph"]["cognitive_restructuring"]["prompt_file"], "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    cognitive_restructuring_prompt = content
                else:
                    print(f"认知重构阶段提示词文件为空，使用默认提示词")

            with open(agent.stage_configs["subgraph"]["comprehensive_intervention"]["prompt_file"], "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    comprehensive_intervention_prompt = content
                else:
                    print(f"综合干预阶段提示词文件为空，使用默认提示词")
        except Exception as e:
            print(f"读取提示词文件失败（{e}），使用默认提示词")

        while True:
            user_input = input("用户: ")

            if not user_input:
                continue
            if user_input.lower() in ("history", "h"):
                view_history(message_history)
                continue
            if user_input.lower() == "exit":
                break

            message_history.append(HumanMessage(content=user_input))
            response = agent.main_graph.invoke({"messages": message_history})
            message_history.append(AIMessage(content=response["messages"][-1].content))

            if "进入总结反馈阶段" in response["messages"][-1].content:
                message_history.append(SystemMessage(content=summary_feedback_prompt))
            if "进入认知重构阶段" in response["messages"][-1].content:
                message_history.append(SystemMessage(content=cognitive_restructuring_prompt))
            if "进行综合干预阶段" in response["messages"][-1].content:
                message_history.append(SystemMessage(content=comprehensive_intervention_prompt))
            print("助手:", response["messages"][-1].content)
