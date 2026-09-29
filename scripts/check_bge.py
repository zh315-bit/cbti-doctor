"""Verify the downloaded BGE model locally, without API keys or network access."""

import os
from pathlib import Path

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"

import numpy as np
from sentence_transformers import SentenceTransformer


def main():
    model_path = Path(__file__).resolve().parents[1] / "models" / "bge-small-zh-v1.5"
    model = SentenceTransformer(str(model_path), device="cpu", local_files_only=True)
    texts = ["晚上躺在床上很久也睡不着。", "入睡困难是常见的睡眠问题。", "今天的天气晴朗。"]
    vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    assert vectors.shape == (3, 512), vectors.shape
    assert np.isfinite(vectors).all()
    assert np.allclose(np.linalg.norm(vectors, axis=1), 1.0, atol=1e-5)
    print(f"PASS: CPU offline inference; shape={vectors.shape}; normalized finite vectors.")
    print(f"Model: {model_path}")


if __name__ == "__main__":
    main()
