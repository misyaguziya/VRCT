"""WebSocket サーバーのトークン認証と 0.0.0.0/:: バインド拒否に関する
テスト (ロードマップ項目 12)。

対象の欠陥:
  WebSocket は同一オリジンポリシーの対象外であるため、127.0.0.1 バインド
  だけでは「同じ PC 上で開いた任意の Web ページの JS が
  ws://127.0.0.1:PORT に直接接続して、マイク/スピーカーの文字起こしを
  リアルタイムに窃取する」ことを防げない。また WEBSOCKET_HOST に
  0.0.0.0/:: を設定すると、同一 LAN 上の全端末が到達可能になる。

  修正:
  1. WebSocketServer にトークン検証 (process_request フック) を追加し、
     ?token=... が一致しない接続を 403 で拒否する。トークンは
     config.WEBSOCKET_AUTH_TOKEN として初回起動時に 1 回だけ生成し、
     以降は config.json に永続化する (VRCT-TTS のような外部連携ツールは
     ユーザーが接続 URL を手動入力する方式のため、起動のたびにトークンが
     変わると毎回再設定が必要になってしまう)。OBS Browser Source が
     生成するページには自動的に埋め込まれる (ユーザーの手作業は不要)。
     VRCT-TTS 等、URL を手動入力する外部ツール向けには
     /get/data/websocket_auth_token を新設し、UI から
     `ws://{host}:{port}/?token={token}` をコピーできるようにする。
  2. WEBSOCKET_HOST に 0.0.0.0/:: を設定できないよう、Controller の
     入力検証と config.py のディスクリプタ両方で拒否する
     (setWebSocketHost だけだと config.json に既に保存されている
     0.0.0.0 を起動時に読み込むケースを防げないため)。

  origins=[None] は当初のレビュー提案に含まれていたが、VRCT の OBS
  Browser Source 自体がブラウザ (OBS 内蔵 Chromium) から Origin ヘッダー
  付きで接続するため、この方式だと OBS 連携自体を壊してしまうことが
  実装前の調査で判明した。よってトークン認証を主たる防御として採用し、
  origins チェックは見送っている。
"""

import unittest
from http import HTTPStatus
from unittest.mock import MagicMock, patch

from models.websocket.websocket_server import WebSocketServer
from models.obs.obs_browser_source_server import _build_overlay_html, ObsBrowserSourceServer
from utils import isWildcardBindAddress


class IsWildcardBindAddressTests(unittest.TestCase):
    def test_ipv4_wildcard_is_rejected(self) -> None:
        self.assertTrue(isWildcardBindAddress("0.0.0.0"))

    def test_ipv6_wildcard_is_rejected(self) -> None:
        self.assertTrue(isWildcardBindAddress("::"))

    def test_loopback_is_allowed(self) -> None:
        self.assertFalse(isWildcardBindAddress("127.0.0.1"))

    def test_lan_address_is_allowed(self) -> None:
        self.assertFalse(isWildcardBindAddress("192.168.1.10"))

    def test_invalid_string_is_not_flagged_as_wildcard(self) -> None:
        # isValidIpAddress 側の既存チェックが弾く前提なので、ここでは
        # False (=ワイルドカードではない) を返せば十分。
        self.assertFalse(isWildcardBindAddress("not-an-ip"))


class SetWebSocketHostRejectsWildcardTests(unittest.TestCase):
    def setUp(self) -> None:
        import config as config_module
        self._original_host = config_module.config.WEBSOCKET_HOST
        self.config = config_module.config

    def tearDown(self) -> None:
        self.config.WEBSOCKET_HOST = self._original_host

    @patch("controller.model")
    def test_rejects_0_0_0_0(self, mock_model) -> None:
        from controller import Controller
        mock_model.checkWebSocketServerAlive.return_value = False

        response = Controller.setWebSocketHost("0.0.0.0")

        self.assertEqual(response["status"], 400)
        self.assertNotEqual(self.config.WEBSOCKET_HOST, "0.0.0.0")

    @patch("controller.model")
    def test_rejects_ipv6_wildcard(self, mock_model) -> None:
        from controller import Controller
        mock_model.checkWebSocketServerAlive.return_value = False

        response = Controller.setWebSocketHost("::")

        self.assertEqual(response["status"], 400)
        self.assertNotEqual(self.config.WEBSOCKET_HOST, "::")

    @patch("controller.model")
    def test_accepts_a_normal_loopback_address(self, mock_model) -> None:
        from controller import Controller
        mock_model.checkWebSocketServerAlive.return_value = False

        response = Controller.setWebSocketHost("127.0.0.1")

        self.assertEqual(response["status"], 200)
        self.assertEqual(self.config.WEBSOCKET_HOST, "127.0.0.1")


class ConfigDescriptorRejectsWildcardTests(unittest.TestCase):
    """setWebSocketHost() を経由しない経路 (config.json のロード相当) でも
    0.0.0.0/:: が弾かれることを確認する。"""

    def setUp(self) -> None:
        import config as config_module
        self.config = config_module.config
        self._original_host = self.config.WEBSOCKET_HOST

    def tearDown(self) -> None:
        self.config.WEBSOCKET_HOST = self._original_host

    def test_direct_assignment_of_wildcard_is_ignored(self) -> None:
        self.config.WEBSOCKET_HOST = "127.0.0.1"
        self.config.WEBSOCKET_HOST = "0.0.0.0"  # load_config() の setattr() 相当
        self.assertEqual(self.config.WEBSOCKET_HOST, "127.0.0.1", "0.0.0.0 が素通りしている")

    def test_direct_assignment_of_valid_host_is_accepted(self) -> None:
        self.config.WEBSOCKET_HOST = "192.168.1.5"
        self.assertEqual(self.config.WEBSOCKET_HOST, "192.168.1.5")


class WebSocketAuthTokenPersistenceTests(unittest.TestCase):
    """トークンが起動のたびに変わらず、config.json 経由で永続化されることを
    確認する (VRCT-TTS のような URL 手動入力型の外部連携ツールが、
    VRCT を再起動するたびに再設定を強いられないようにするため)。"""

    def setUp(self) -> None:
        import config as config_module
        self.config = config_module.config
        self._original_token = self.config.WEBSOCKET_AUTH_TOKEN

    def tearDown(self) -> None:
        self.config.WEBSOCKET_AUTH_TOKEN = self._original_token

    def test_token_is_a_non_empty_string_by_default(self) -> None:
        self.assertIsInstance(self._original_token, str)
        self.assertGreater(len(self._original_token), 0)

    def test_persisted_value_survives_a_simulated_reload(self) -> None:
        # load_config() の setattr() 相当: config.json に既に保存されている
        # 値があれば、それがそのまま使われ続ける (起動のたびに変わらない)。
        self.config.WEBSOCKET_AUTH_TOKEN = "persisted-token-value"
        self.assertEqual(self.config.WEBSOCKET_AUTH_TOKEN, "persisted-token-value")

    @patch("controller.model")
    def test_getter_endpoint_returns_the_persisted_token(self, _mock_model) -> None:
        from controller import Controller
        self.config.WEBSOCKET_AUTH_TOKEN = "abc-xyz-123"
        response = Controller.getWebSocketAuthToken()
        self.assertEqual(response, {"status": 200, "result": "abc-xyz-123"})


class WebSocketServerTokenAuthTests(unittest.IsolatedAsyncioTestCase):
    async def test_missing_token_is_rejected(self) -> None:
        server = WebSocketServer(token="secret123")
        result = await server._process_request("/", {})
        self.assertIsNotNone(result)
        status, _headers, _body = result
        self.assertEqual(status, HTTPStatus.FORBIDDEN)

    async def test_wrong_token_is_rejected(self) -> None:
        server = WebSocketServer(token="secret123")
        result = await server._process_request("/?token=wrong", {})
        self.assertIsNotNone(result)
        status, _headers, _body = result
        self.assertEqual(status, HTTPStatus.FORBIDDEN)

    async def test_correct_token_is_accepted(self) -> None:
        server = WebSocketServer(token="secret123")
        result = await server._process_request("/?token=secret123", {})
        self.assertIsNone(result, "正しいトークンなのにハンドシェイクが拒否された")

    async def test_no_token_configured_skips_verification(self) -> None:
        # token=None (デフォルト) の場合は検証しない (後方互換・テスト用)。
        server = WebSocketServer(token=None)
        result = await server._process_request("/", {})
        self.assertIsNone(result)


class ObsBrowserSourceEmbedsTokenTests(unittest.TestCase):
    def test_html_embeds_the_supplied_token(self) -> None:
        html = _build_overlay_html(ws_token="abc123XYZ")
        self.assertIn('wsToken: "abc123XYZ"', html)
        self.assertIn("token=${encodeURIComponent(SETTINGS.wsToken)}", html)

    def test_html_with_empty_token_omits_query_string_at_runtime(self) -> None:
        html = _build_overlay_html(ws_token="")
        self.assertIn('wsToken: ""', html)

    def test_obs_server_passes_its_token_through_to_the_page(self) -> None:
        server = ObsBrowserSourceServer(host="127.0.0.1", port=0, ws_token="tok-xyz")
        self.assertEqual(server.ws_token, "tok-xyz")


if __name__ == "__main__":
    unittest.main()
