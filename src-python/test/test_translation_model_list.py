"""setModel が、直前に取得したモデル一覧を使い回して、ネットワークの2回目の取得を省くこと。

起動時は「getModelList() で一覧を取る → 選んだモデルを setModel() で確かめる」と続けて呼ぶ。
setModel が毎回一覧を取り直していたので、API キーを設定したエンジンごとに、起動が
ネットワーク1往復ぶん (Gemini で約1.5秒) 遅れていた。
"""

import importlib
import unittest
from unittest.mock import patch

from models.translation.translation_model_list import RecentModelList


class _FakeClient(RecentModelList):
    def __init__(self, models):
        self.model = None
        self.models = models
        self.fetches = 0

    def getModelList(self):
        self.fetches += 1
        return self._remember(list(self.models))


class RecentModelListTests(unittest.TestCase):
    def test_set_model_reuses_the_list_just_fetched(self) -> None:
        client = _FakeClient(["a", "b"])
        client.getModelList()

        self.assertTrue(client.setModel("b"))

        self.assertEqual(client.fetches, 1)
        self.assertEqual(client.model, "b")

    def test_set_model_without_a_recent_list_fetches_one(self) -> None:
        client = _FakeClient(["a", "b"])

        self.assertTrue(client.setModel("a"))

        self.assertEqual(client.fetches, 1)

    def test_set_model_rejects_a_model_not_in_the_list(self) -> None:
        client = _FakeClient(["a"])
        client.getModelList()

        self.assertFalse(client.setModel("x"))

        self.assertIsNone(client.model)

    def test_old_list_is_fetched_again(self) -> None:
        # UI の「更新」などあとから呼ぶときは、一覧が古くなっているので取り直す
        client = _FakeClient(["a"])
        with patch("models.translation.translation_model_list.time.monotonic", return_value=100.0):
            client.getModelList()
        with patch("models.translation.translation_model_list.time.monotonic", return_value=100.0 + 31.0):
            client.setModel("a")

        self.assertEqual(client.fetches, 2)

    def test_empty_list_is_not_remembered(self) -> None:
        # 取得に失敗した ([]) 結果を覚えると、setModel が取り直せずに失敗し続ける
        client = _FakeClient([])
        client.getModelList()
        client.models = ["a"]

        self.assertTrue(client.setModel("a"))

        self.assertEqual(client.fetches, 2)


# (モジュール, クラス, 一覧を取る関数の名前, 属性)
_CLIENTS = [
    ("translation_gemini", "GeminiClient", {"api_key": "k"}),
    ("translation_openai", "OpenAIClient", {"api_key": "k", "base_url": None}),
    ("translation_groq", "GroqClient", {"api_key": "k"}),
    ("translation_openrouter", "OpenRouterClient", {"api_key": "k", "base_url": "https://example.invalid"}),
    ("translation_plamo", "PlamoClient", {"api_key": "k"}),
    ("translation_lmstudio", "LMStudioClient", {"base_url": "http://127.0.0.1:1234/v1"}),
    ("translation_ollama", "OllamaClient", {"base_url": "http://127.0.0.1:11434"}),
    ("translation_openai_compatible", "OpenAICompatibleClient", {"api_key": "k", "base_url": "https://example.invalid"}),
]


class ClientStartupFlowTests(unittest.TestCase):
    def test_every_client_fetches_the_model_list_once_for_list_then_set(self) -> None:
        for module_name, class_name, attrs in _CLIENTS:
            with self.subTest(client=class_name):
                module = importlib.import_module(f"models.translation.{module_name}")
                client_class = getattr(module, class_name)
                client = client_class.__new__(client_class)
                client.model = None
                for key, value in attrs.items():
                    setattr(client, key, value)

                fetch_name = "_get_available_text_models"
                fetch_target = module if hasattr(module, fetch_name) else importlib.import_module("models.translation.translation_openai_compatible")
                with patch.object(fetch_target, fetch_name, return_value=["m1", "m2"]) as fetch, \
                        patch.object(client_class, "authenticationCheck", return_value=True, create=True):
                    models = client.getModelList()
                    selected = models[0]
                    self.assertTrue(client.setModel(selected))

                self.assertEqual(fetch.call_count, 1, f"{class_name}: setModel fetched the list again")
                self.assertEqual(client.model, "m1")


if __name__ == "__main__":
    unittest.main()
