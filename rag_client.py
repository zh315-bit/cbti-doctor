import os
from dotenv import load_dotenv
from typing import List
from pydantic import BaseModel, Field

from langchain.chat_models import init_chat_model
from langchain_core.tools import tool
from langchain_openai import OpenAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain.agents import create_tool_calling_agent, create_openai_tools_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from langchain.tools.retriever import create_retriever_tool

load_dotenv(override=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
model = init_chat_model(model="gpt-3.5-turbo", model_provider="openai", openai_api_key=OPENAI_API_KEY)
embeddings = OpenAIEmbeddings(api_key=OPENAI_API_KEY)


def load_pdfs(pdf_file):
    """
    将 pdf_file 目录下的所有 .pdf 文件加载为 LangChain Documents 列表。

    参数:
        pdf_file: 文件夹路径（包含多个 PDF 文件）
    返回:
        List[Document]: 所有 PDF 的 Document 列表，供 build_documents 使用
    """
    docs: List[Document] = []

    if not os.path.isdir(pdf_file):
        raise ValueError(f"提供的路径不是文件夹: {pdf_file}")

    # 收集该目录下的所有 PDF 文件（不进入子文件夹）
    pdf_paths = []
    for name in os.listdir(pdf_file):
        full_path = os.path.join(pdf_file, name)
        if os.path.isfile(full_path) and name.lower().endswith(".pdf"):
            pdf_paths.append(full_path)

    # 逐个 PDF 加载并累加到 docs
    for path in pdf_paths:
        loader = PyPDFLoader(path)
        try:
            docs.extend(loader.load())
        except Exception as e:
            # 遇到无法解析的 PDF，跳过但继续处理其他文件
            print(f"跳过无法加载的PDF: {path}，错误: {e}")

    return docs


def build_documents(docs):
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunked = splitter.split_documents(docs)
    return chunked


def build_vector_store(text_chunked):
    vector_store = FAISS.from_documents(text_chunked, embedding=embeddings)
    vector_store.save_local("./rag_lib/.rag_db")


def get_conversational_chain(tools, user_input):
    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            """你是一个严谨的医学与睡眠健康助理。你需要根据用户的问题，调用retrieval_augmentation_generation工具检索资料，并基于资料进行回答。尽量使用中文作答，并在事实陈述处用[文件名]标注引用的来源。如果资料不足，请明确说明资料不足，并严禁杜撰资料回答。""",
        ),
        ("placeholder", "{chat_history}"),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])

    tool = [tools]
    agent = create_tool_calling_agent(model, tool, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tool, verbose=True)

    response = agent_executor.invoke({"input": user_input})

    return response['output']


def check_database_exists():
    """检查FAISS数据库是否存在"""
    return os.path.exists("./rag_lib/.rag_db") and os.path.exists("./rag_lib/.rag_db/index.faiss")


class RetrievalAugmentationGenerationSchema(BaseModel):
    user_input: str = Field(description="用户提出的问题")
    k: int = Field(description="检索的文档数量", default=5)


@tool(args_schema=RetrievalAugmentationGenerationSchema)
def retrieval_augmentation_generation(user_input: str, k: int = 5):
    """
    这是一个与失眠认知行为疗法（CBT-I）医学知识相关的RAG知识库。基于用户提出的问题，从RAG数据库中检索相关文档，并使用这些文档生成答案。
    :param user_input: 用户提出的问题
    :param k: 检索的文档数量，默认为5
    :return: 基于检索到的文档生成的答案

    注意，使用该工具时需要判断该工具返回的结果是否解决了用户的问题。如果没有给出具体的答案，那么需要重新调用search_tool上网查询。
    """
    if not check_database_exists():
        # 读取PDF内容
        pdf_file = "./rag_lib/pdfs"
        raw_text = load_pdfs(pdf_file)

        documents = build_documents(raw_text)  # 分割文本
        build_vector_store(documents)  # 创建向量数据库

    vector_store = FAISS.load_local("./rag_lib/.rag_db", embeddings, allow_dangerous_deserialization=True)
    retrieved = vector_store.as_retriever(search_kwargs={"k": k})
    retrieval_chain = create_retriever_tool(retrieved, "pdf_extractor", "This tool is to give answer to queries from the pdf")
    response = get_conversational_chain(retrieval_chain, user_input)

    return response


if __name__ == "__main__":
    user_input = "这些资料在讲什么？"
    response = retrieval_augmentation_generation(user_input)
    print(response)
