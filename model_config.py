"""Shared DeepSeek configuration for the CLI, web agent and RAG answers."""

import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")


def create_chat_model() -> ChatOpenAI:
    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        raise ValueError("请在项目 .env 中配置 DEEPSEEK_API_KEY")
    return ChatOpenAI(
        model=os.getenv("DEEPSEEK_MODEL", "deepseek-flash"),
        api_key=api_key,
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        # Use non-thinking tool calls with the existing LangChain message format.
        extra_body={"thinking": {"type": "disabled"}},
        timeout=120,
        max_retries=1,
    )
