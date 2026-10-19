"""起動時の一括設定取得 (`Controller.updateConfigSettings`) の堅牢性テスト。

背景 (バックエンド再評価 2026-09-14 P-1):

`Controller.init()` の最終行が `updateConfigSettings()` を呼び、`init_mapping`
(= `/get/data/` 前方一致の全エンドポイント) を全て舐めてから
`/run/initialization_complete` を送る。UIのローディング画面はこの応答で解除
されるため、ここには 2 つの構造的な弱点があった:

1. `/get/data/available_releases` が含まれており、その実体は GitHub API への
   同期HTTPリクエスト (timeout (10, 60))。起動を最大70秒遅らせうる。
2. getter 呼び出しに try/except が無く、1 つでも例外を投げると `init()` が
   そこで死に、`/run/initialization_complete` が永久に送られず UI が
   ローディング画面のまま固まる。

本テストは両方の回帰を防ぐ。
"""

import unittest

from controller import Controller
from mainloop import init_mapping, mapping


class TestInitMappingExcludesNetworkEndpoints(unittest.TestCase):
    def test_available_releases_is_not_collected_at_startup(self) -> None:
        """GitHub API を叩くエンドポイントが起動時の一括取得に含まれないこと。

        UI 側は Updater.jsx のマウント時に自分で
        `/get/data/available_releases` を要求するため、ここから外しても
        取得経路は失われない。
        """
        self.assertIn("/get/data/available_releases", mapping)
        self.assertNotIn("/get/data/available_releases", init_mapping)

    def test_other_get_data_endpoints_are_still_collected(self) -> None:
        """除外は available_releases だけで、他は従来どおり集められること。"""
        get_data_keys = {k for k in mapping if k.startswith("/get/data/")}
        self.assertEqual(get_data_keys - set(init_mapping), {"/get/data/available_releases"})


class TestUpdateConfigSettingsIsolatesFailures(unittest.TestCase):
    def _makeController(self, init_mapping_override: dict) -> tuple:
        controller = Controller.__new__(Controller)
        controller.init_mapping = init_mapping_override
        controller.run_mapping = {"initialization_complete": "/run/initialization_complete"}
        sent = []
        controller.run = lambda status, endpoint, result: sent.append((status, endpoint, result))
        return controller, sent

    def test_a_raising_getter_does_not_abort_initialization(self) -> None:
        """1 つの getter が例外を投げても、残りを集めて完了通知まで到達すること。"""
        def ok(_data):
            return {"status": 200, "result": "fine"}

        def boom(_data):
            raise RuntimeError("getter exploded")

        controller, sent = self._makeController({
            "/get/data/good": {"status": True, "variable": ok},
            "/get/data/bad": {"status": True, "variable": boom},
            "/get/data/good2": {"status": True, "variable": ok},
        })

        controller.updateConfigSettings()

        self.assertEqual(len(sent), 1, "initialization_complete が送られていない")
        status, endpoint, settings = sent[0]
        self.assertEqual(status, 200)
        self.assertEqual(endpoint, "/run/initialization_complete")
        self.assertEqual(settings["/get/data/good"], "fine")
        self.assertEqual(settings["/get/data/good2"], "fine")
        self.assertIsNone(settings["/get/data/bad"], "失敗した項目は None で埋めること")

    def test_a_getter_returning_a_non_dict_is_also_isolated(self) -> None:
        """dict 以外を返す getter (=`.get` が無い) でも落ちないこと。"""
        controller, sent = self._makeController({
            "/get/data/weird": {"status": True, "variable": lambda _data: None},
        })

        controller.updateConfigSettings()

        self.assertEqual(len(sent), 1)
        self.assertIsNone(sent[0][2]["/get/data/weird"])


if __name__ == "__main__":
    unittest.main()
