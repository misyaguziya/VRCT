"""setModel が、直前に取得したモデル一覧を使い回して、ネットワークの2回目の取得を省くこと。

起動時は「getModelList() で一覧を取る → 選んだモデルを setModel() で確かめる」と続けて呼ぶ。
setModel が毎回一覧を取り直していたので、API キーを設定したエンジンごとに、起動が
ネットワーク1往復ぶん (Gemini で約1.5秒) 遅れていた。
"""

import importlib
import unittest
from types import SimpleNamespace
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


class AuthModelsTests(unittest.TestCase):
    """認証 (setAuthKey) で取得した一覧を、直後の最初の getModelList だけが使う。"""

    def test_auth_list_is_used_once_by_the_next_get_model_list(self) -> None:
        client = _FakeClient(["fetched"])
        client._rememberFromAuth(lambda: ["from-auth"])

        self.assertEqual(client._takeAuthModels(), ["from-auth"])
        self.assertIsNone(client._takeAuthModels())

    def test_old_auth_list_is_not_used(self) -> None:
        client = _FakeClient([])
        with patch("models.translation.translation_model_list.time.monotonic", return_value=100.0):
            client._rememberFromAuth(lambda: ["from-auth"])
        with patch("models.translation.translation_model_list.time.monotonic", return_value=100.0 + 31.0):
            self.assertIsNone(client._takeAuthModels())

    def test_unbuildable_or_empty_list_is_ignored(self) -> None:
        client = _FakeClient([])

        def broken():
            raise AttributeError("unexpected response")

        client._rememberFromAuth(broken)
        self.assertIsNone(client._takeAuthModels())
        client._rememberFromAuth(lambda: [])
        self.assertIsNone(client._takeAuthModels())


def _openai_style(*ids):
    return SimpleNamespace(data=[SimpleNamespace(id=i, root="") for i in ids])


def _gemini_style(*names):
    return [SimpleNamespace(name=f"models/{n}", supported_actions=["generateContent"]) for n in names]


# (モジュール, クラス, 属性, 認証で受け取る応答, 期待する一覧)
_AUTH_CLIENTS = [
    ("translation_openai", "OpenAIClient", {"base_url": None}, _openai_style("gpt-b", "gpt-a", "whisper-1"), ["gpt-a", "gpt-b"]),
    ("translation_groq", "GroqClient", {}, _openai_style("llama-b", "llama-a"), ["llama-a", "llama-b"]),
    ("translation_plamo", "PlamoClient", {}, _openai_style("plamo-b", "plamo-a"), ["plamo-a", "plamo-b"]),
    ("translation_gemini", "GeminiClient", {}, _gemini_style("gemini-b", "gemini-a"), ["gemini-a", "gemini-b"]),
    ("translation_openai_compatible", "OpenAICompatibleClient", {"base_url": "https://example.invalid"},
     _openai_style("llama-b", "llama-a"), ["llama-a", "llama-b"]),
]


def _bare_client(module, class_name, attrs):
    client_class = getattr(module, class_name)
    client = client_class.__new__(client_class)
    client.api_key = None
    client.model = None
    for key, value in attrs.items():
        setattr(client, key, value)
    return client


class ClientAuthFlowTests(unittest.TestCase):
    def test_auth_then_list_then_set_model_fetches_once(self) -> None:
        # 起動時の流れ。以前は認証と一覧取得で同じ API を2回呼び、setModel でさらに1回呼んでいた
        for module_name, class_name, attrs, response, expected in _AUTH_CLIENTS:
            with self.subTest(client=class_name):
                module = importlib.import_module(f"models.translation.{module_name}")
                client = _bare_client(module, class_name, attrs)

                with patch.object(module, "_fetch_models", return_value=response) as fetch:
                    self.assertTrue(client.setAuthKey("key"))
                    models = client.getModelList()
                    self.assertTrue(client.setModel(models[0]))

                self.assertEqual(fetch.call_count, 1, f"{class_name}: fetched the list more than once")
                self.assertEqual(models, expected)
                self.assertEqual(client.api_key, "key")
                self.assertEqual(client.model, expected[0])

    def test_refresh_after_auth_fetches_again(self) -> None:
        # UI の更新ボタン (認証のあとの2回目の getModelList) は、取り直す
        for module_name, class_name, attrs, response, expected in _AUTH_CLIENTS:
            with self.subTest(client=class_name):
                module = importlib.import_module(f"models.translation.{module_name}")
                client = _bare_client(module, class_name, attrs)

                with patch.object(module, "_fetch_models", return_value=response) as fetch:
                    client.setAuthKey("key")
                    client.getModelList()
                    client.getModelList()

                self.assertEqual(fetch.call_count, 2, class_name)

    def test_invalid_key_is_rejected_and_not_stored(self) -> None:
        for module_name, class_name, attrs, _response, _expected in _AUTH_CLIENTS:
            with self.subTest(client=class_name):
                module = importlib.import_module(f"models.translation.{module_name}")
                client = _bare_client(module, class_name, attrs)

                with patch.object(module, "_fetch_models", side_effect=RuntimeError("401")):
                    self.assertFalse(client.setAuthKey("bad"))

                self.assertIsNone(client.api_key)

    def test_unparseable_response_keeps_auth_ok_and_lists_again(self) -> None:
        # 一覧を作れない応答でも、認証が通ったことは変えない (キーを無効扱いにしない)
        for module_name, class_name, attrs, _response, expected in _AUTH_CLIENTS:
            with self.subTest(client=class_name):
                module = importlib.import_module(f"models.translation.{module_name}")
                client = _bare_client(module, class_name, attrs)
                good = next(r for m, c, a, r, e in _AUTH_CLIENTS if c == class_name)

                with patch.object(module, "_fetch_models", side_effect=[object(), good]) as fetch:
                    self.assertTrue(client.setAuthKey("key"))
                    self.assertEqual(client.getModelList(), expected)

                self.assertEqual(fetch.call_count, 2, class_name)


if __name__ == "__main__":
    unittest.main()
