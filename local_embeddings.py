"""Offline BGE adapter for LangChain; load weights only when retrieval is used."""

import os
from functools import lru_cache

from langchain_core.embeddings import Embeddings
from model_config import PROJECT_ROOT


@lru_cache(maxsize=1)
def _load_model():
    from sentence_transformers import SentenceTransformer

    model_path = PROJECT_ROOT / os.getenv("BGE_MODEL_PATH", "models/bge-small-zh-v1.5")
    if not (model_path / "model.safetensors").is_file():
        raise FileNotFoundError(f"本地 BGE 模型未准备好：{model_path}")
    return SentenceTransformer(str(model_path), device="cpu", local_files_only=True)


class LocalBGEEmbeddings(Embeddings):
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return _load_model().encode(
            texts, batch_size=32, normalize_embeddings=True, show_progress_bar=False,
        ).tolist()

    def embed_query(self, text: str) -> list[float]:
        # BGE v1.5 recommends the retrieval instruction for short queries only.
        return self.embed_documents(["为这个句子生成表示以用于检索相关文章：" + text])[0]
