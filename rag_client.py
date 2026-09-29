import os
from functools import lru_cache
from typing import List
from pydantic import BaseModel, Field

from langchain_core.tools import tool
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from langchain.tools.retriever import create_retriever_tool

from local_embeddings import LocalBGEEmbeddings
from model_config import PROJECT_ROOT, create_chat_model

model = create_chat_model()
embeddings = LocalBGEEmbeddings()
# A new namespace prevents loading vectors produced by OpenAI embeddings.
INDEX_DIR = PROJECT_ROOT / "rag_lib" / ".rag_db" / "bge-small-zh-v1.5-ch400-v1"


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
        if os.path.isfile(full_path) and name.lower().endswith(".pdf") and not name.startswith("._"):
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
    splitter = RecursiveCharacterTextSplitter(chunk_size=400, chunk_overlap=80)
    chunked = splitter.split_documents(docs)
    return chunked


def build_vector_store(text_chunked):
    vector_store = FAISS.from_documents(text_chunked, embedding=embeddings)
    vector_store.save_local(str(INDEX_DIR))
    return vector_store


def get_conversational_chain(tools, user_input):
    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            """你是一个严谨的医学与睡眠健康助理。你需要根据用户的问题，调用pdf_extractor工具检索资料，并基于资料进行回答。尽量使用中文作答，并在事实陈述处用[文件名]标注引用的来源。如果资料不足，请明确说明资料不足，并严禁杜撰资料回答。""",
        ),
        ("placeholder", "{chat_history}"),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])

    tool = [tools]
    agent = create_tool_calling_agent(model, tool, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tool, verbose=False, max_iterations=4)

    response = agent_executor.invoke({"input": user_input})

    return response['output']


def check_database_exists():
    """检查FAISS数据库是否存在"""
    return (INDEX_DIR / "index.faiss").is_file() and (INDEX_DIR / "index.pkl").is_file()


@lru_cache(maxsize=1)
def get_vector_store():
    if not check_database_exists():
        docs = build_documents(load_pdfs(str(PROJECT_ROOT / "rag_lib" / "pdfs")))
        if not docs:
            raise ValueError("知识库中没有可用的 PDF 文本，无法构建索引")
        return build_vector_store(docs)
    # Only load the locally generated index from this application's directory.
    return FAISS.load_local(str(INDEX_DIR), embeddings, allow_dangerous_deserialization=True)


class RetrievalAugmentationGenerationSchema(BaseModel):
    user_input: str = Field(description="用户提出的问题")
    k: int = Field(description="检索的文档数量", default=5, ge=1, le=20)


@tool(args_schema=RetrievalAugmentationGenerationSchema)
def retrieval_augmentation_generation(user_input: str, k: int = 5):
    """
    这是一个与失眠认知行为疗法（CBT-I）医学知识相关的RAG知识库。基于用户提出的问题，从RAG数据库中检索相关文档，并使用这些文档生成答案。
    :param user_input: 用户提出的问题
    :param k: 检索的文档数量，默认为5
    :return: 基于检索到的文档生成的答案

    如果资料不足，请明确说明，不要杜撰答案。
    """
    vector_store = get_vector_store()
    retrieved = vector_store.as_retriever(search_kwargs={"k": k})
    retrieval_chain = create_retriever_tool(retrieved, "pdf_extractor", "This tool is to give answer to queries from the pdf")
    response = get_conversational_chain(retrieval_chain, user_input)

    return response


if __name__ == "__main__":
    user_input = "这些资料在讲什么？"
    response = retrieval_augmentation_generation(user_input)
    print(response)
