"""フロントエンドの SETTINGS_ARRAY とバックエンドの mainloop.mapping の整合。

UI 側の 1 エントリは `base_endpoint_name` と `logics_template_id` の組で
「どのエンドポイントを叩くか」を宣言しており、対応するエンドポイントが
`mainloop.mapping` に無いと、その設定項目は **実行時に初めて** 壊れる
(UI は出るが値が取れない / 保存されない)。片側だけ足した・綴りを間違えた・
別ブロックからコピペした、が原因で、どれも静的には誰も気付けない。

実際にこのテストで `OllamaURL` の宣言が見つかった (2025-11-14 に LMStudio
ブロックのコピペで入ったが、Ollama は接続時に URL を取らないため
バックエンドには対応するエンドポイントも config プロパティも無く、
この宣言以外から参照もされていなかった)。

本番コードは変更しない。検出器だけを足す。
"""

import re
import unittest
from pathlib import Path

from mainloop import mapping

_UI_CONFIG_SETTER = (
    Path(__file__).resolve().parents[2]
    / "src-ui" / "logics" / "configs" / "config_page_setter" / "ui_config_setter.js"
)


def _parseSettingsArray():
    """SETTINGS_ARRAY から (logics_template_id, base_endpoint_name) を取り出す。

    JS を実行せず正規表現で読む。各エントリは必ずこの2つのキーをこの順で
    持つ、という前提に依存しているので、その前提自体も下のテストで検証する。
    """
    source = _UI_CONFIG_SETTER.read_text(encoding="utf-8")
    tokens = re.findall(
        r'\b(logics_template_id|base_endpoint_name)\s*:\s*"([^"]+)"', source
    )
    return tokens


class TestSettingsArrayParsing(unittest.TestCase):
    def test_every_entry_declares_both_keys_in_order(self) -> None:
        """パース前提の検証。ここが崩れると下のテストが黙って素通りする。"""
        tokens = _parseSettingsArray()
        self.assertTrue(tokens, "SETTINGS_ARRAY を1件も読めていない")
        self.assertEqual(
            len(tokens) % 2, 0,
            "logics_template_id と base_endpoint_name が対になっていない",
        )
        keys = [key for key, _ in tokens]
        self.assertEqual(
            keys, ["logics_template_id", "base_endpoint_name"] * (len(tokens) // 2),
            "エントリ内のキーの並びが前提と違う。_parseSettingsArray を見直すこと",
        )


class TestUiEndpointContract(unittest.TestCase):
    """UI の宣言から導けるエンドポイントが mainloop.mapping に在ること。

    導出するのは実測で 100% 成立している規則だけに絞っている。特に
    `/set/data/<name>` は検査しない: `get_set` は「読み取り専用だが get は
    欲しい」項目にも流用されており (`selectable_*_list` 系 13 本、
    `websocket_auth_token`)、`/set/data/` を導出すると意図的な偽陽性が
    15 件出る。`websocket_auth_token` には JS 側にその旨のコメントもある。
    """

    def setUp(self) -> None:
        tokens = _parseSettingsArray()
        self.entries = [
            (tokens[i][1], tokens[i + 1][1]) for i in range(0, len(tokens), 2)
        ]

    def _assertEndpoints(self, templates, prefix) -> None:
        missing = [
            prefix + name
            for template, name in self.entries
            if template in templates and prefix + name not in mapping
        ]
        self.assertEqual(
            missing, [],
            f"UI が宣言しているのに mainloop.mapping に無いエンドポイント: {missing}",
        )

    def test_every_setting_has_a_get_endpoint(self) -> None:
        # weight_download_status だけは形が違い、値の取得ではなく
        # ダウンロードの起動 (/run/download_<name>) を指す。
        self._assertEndpoints(
            {"get_set", "get_set_delete", "toggle_enable_disable"}, "/get/data/"
        )

    def test_toggles_have_both_enable_and_disable_endpoints(self) -> None:
        """トグルは必ず両側が要る。片側だけ足す事故が起きやすい。"""
        self._assertEndpoints({"toggle_enable_disable"}, "/set/enable/")
        self._assertEndpoints({"toggle_enable_disable"}, "/set/disable/")

    def test_deletable_settings_have_a_delete_endpoint(self) -> None:
        self._assertEndpoints({"get_set_delete"}, "/delete/data/")

    def test_weight_download_settings_have_a_download_endpoint(self) -> None:
        self._assertEndpoints({"weight_download_status"}, "/run/download_")


if __name__ == "__main__":
    unittest.main()
