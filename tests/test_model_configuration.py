"""Configuration and embedding-adapter tests; never call model APIs."""

import importlib.util
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch, MagicMock


@unittest.skipUnless(importlib.util.find_spec("langchain_openai"), "Install project dependencies first")
class ModelConfigurationTests(unittest.TestCase):
    def test_deepseek_configuration_needs_no_legacy_keys(self):
        import model_config
        with patch.dict(os.environ, {
            "DEEPSEEK_API_KEY": "test-only", "DEEPSEEK_MODEL": "deepseek-flash",
            "DEEPSEEK_BASE_URL": "https://api.deepseek.com",
            "KIMI_API_KEY": "", "OPENAI_API_KEY": "",
        }), patch.object(model_config, "ChatOpenAI") as constructor:
            model_config.create_chat_model()
            kwargs = constructor.call_args.kwargs
            self.assertEqual(kwargs["model"], "deepseek-flash")
            self.assertEqual(kwargs["api_key"], "test-only")
            self.assertEqual(kwargs["base_url"], "https://api.deepseek.com")
            self.assertEqual(kwargs["extra_body"], {"thinking": {"type": "disabled"}})

    def test_missing_key_has_clear_error(self):
        from model_config import create_chat_model
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": ""}):
            with self.assertRaisesRegex(ValueError, "DEEPSEEK_API_KEY"):
                create_chat_model()

    def test_bge_query_instruction_is_not_added_to_documents(self):
        from local_embeddings import LocalBGEEmbeddings
        model = MagicMock()
        model.encode.return_value.tolist.return_value = [[0.1, 0.2]]
        with patch("local_embeddings._load_model", return_value=model):
            embedding = LocalBGEEmbeddings()
            self.assertEqual(embedding.embed_documents(["睡眠资料"]), [[0.1, 0.2]])
            self.assertEqual(model.encode.call_args.args[0], ["睡眠资料"])
            self.assertTrue(model.encode.call_args.kwargs["normalize_embeddings"])
            self.assertEqual(embedding.embed_query("失眠"), [0.1, 0.2])
            self.assertEqual(model.encode.call_args.args[0], ["为这个句子生成表示以用于检索相关文章：失眠"])
            model.encode.reset_mock()
            self.assertEqual(embedding.embed_documents([]), [])
            model.encode.assert_not_called()

    def test_index_requires_both_files_and_pdf_sidecars_are_ignored(self):
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-only"}):
            import rag_client
        with TemporaryDirectory() as tmp:
            folder = Path(tmp)
            with patch.object(rag_client, "INDEX_DIR", folder):
                (folder / "index.faiss").touch()
                self.assertFalse(rag_client.check_database_exists())
                (folder / "index.pkl").touch()
                self.assertTrue(rag_client.check_database_exists())
            (folder / "paper.pdf").touch()
            (folder / "._paper.pdf").touch()
            with patch.object(rag_client, "PyPDFLoader") as loader:
                loader.return_value.load.return_value = []
                rag_client.load_pdfs(tmp)
                loader.assert_called_once_with(str(folder / "paper.pdf"))


if __name__ == "__main__":
    unittest.main()
