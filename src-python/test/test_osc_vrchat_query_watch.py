"""VRChatのOSCQueryサービスをmDNSのイベント通知で検出する仕組み
(`_VrchatOscQueryFoundListener` / `OSCHandler.waitForVrchatOscQueryConnectionAsync`)
のテスト。

対象の欠陥: VRCTがVRChatより先に起動すると、起動時1回きりの
`setMuteSelfStatus()` (OSCQueryへの問い合わせ) が失敗し、
`model.mic_mute_status` が `None` のまま二度と更新されず、ミュート同期が
永久に機能しなかった。`getOSCParameterValue()` が使う `OSCQueryBrowser` は
zeroconfの`ServiceBrowser`を使っており本来は後から現れたサービスも検出できる
はずだが、VRCT側がそれを「その場限りの問い合わせ」としてしか使っておらず、
再試行の仕組みが無かった。

この監視は、mDNSで `_oscjson._tcp.local.` サービスが (VRCTの起動順序に
関わらず) 現れた瞬間にコールバックを呼ぶことで、呼び出し元
(controller.py の Init OSC Receive フェーズ) が `setMuteSelfStatus()` を
再試行できるようにする。

zeroconf自体はモックし、ネットワーク/mDNSには一切触れない。
"""

import unittest
from unittest.mock import MagicMock, patch

from models.osc.osc import OSCHandler, _VrchatOscQueryFoundListener


class TestVrchatOscQueryFoundListener(unittest.TestCase):
    def _make_host_info(self, name: str):
        host_info = MagicMock()
        host_info.name = name
        return host_info

    @patch("models.osc.osc.OSCQueryClient")
    def test_fires_when_service_type_and_name_match(self, mock_client_cls) -> None:
        mock_client_cls.return_value.get_host_info.return_value = self._make_host_info("VRChat-Client")
        on_found = MagicMock()
        listener = _VrchatOscQueryFoundListener("VRChat-Client", on_found)
        zc = MagicMock()
        zc.get_service_info.return_value = MagicMock()

        listener.add_service(zc, "_oscjson._tcp.local.", "some-service-name")

        on_found.assert_called_once()

    @patch("models.osc.osc.OSCQueryClient")
    def test_ignores_non_oscjson_service_type(self, mock_client_cls) -> None:
        mock_client_cls.return_value.get_host_info.return_value = self._make_host_info("VRChat-Client")
        on_found = MagicMock()
        listener = _VrchatOscQueryFoundListener("VRChat-Client", on_found)
        zc = MagicMock()

        listener.add_service(zc, "_osc._udp.local.", "some-service-name")

        on_found.assert_not_called()

    @patch("models.osc.osc.OSCQueryClient")
    def test_ignores_service_with_a_different_host_name(self, mock_client_cls) -> None:
        mock_client_cls.return_value.get_host_info.return_value = self._make_host_info("SomeOtherApp")
        on_found = MagicMock()
        listener = _VrchatOscQueryFoundListener("VRChat-Client", on_found)
        zc = MagicMock()
        zc.get_service_info.return_value = MagicMock()

        listener.add_service(zc, "_oscjson._tcp.local.", "some-service-name")

        on_found.assert_not_called()

    @patch("models.osc.osc.OSCQueryClient")
    def test_ignores_when_service_info_is_missing(self, mock_client_cls) -> None:
        on_found = MagicMock()
        listener = _VrchatOscQueryFoundListener("VRChat-Client", on_found)
        zc = MagicMock()
        zc.get_service_info.return_value = None

        listener.add_service(zc, "_oscjson._tcp.local.", "some-service-name")

        on_found.assert_not_called()
        mock_client_cls.assert_not_called()

    @patch("models.osc.osc.OSCQueryClient")
    def test_fires_only_once_even_if_called_multiple_times(self, mock_client_cls) -> None:
        mock_client_cls.return_value.get_host_info.return_value = self._make_host_info("VRChat-Client")
        on_found = MagicMock()
        listener = _VrchatOscQueryFoundListener("VRChat-Client", on_found)
        zc = MagicMock()
        zc.get_service_info.return_value = MagicMock()

        listener.add_service(zc, "_oscjson._tcp.local.", "some-service-name")
        listener.update_service(zc, "_oscjson._tcp.local.", "some-service-name")

        on_found.assert_called_once()

    @patch("models.osc.osc.OSCQueryClient")
    def test_exception_while_checking_is_swallowed_and_does_not_fire(self, mock_client_cls) -> None:
        mock_client_cls.side_effect = RuntimeError("boom")
        on_found = MagicMock()
        listener = _VrchatOscQueryFoundListener("VRChat-Client", on_found)
        zc = MagicMock()
        zc.get_service_info.return_value = MagicMock()

        listener.add_service(zc, "_oscjson._tcp.local.", "some-service-name")  # should not raise

        on_found.assert_not_called()


class TestOscHandlerWaitForVrchatOscQueryConnection(unittest.TestCase):
    @patch("models.osc.osc.ServiceBrowser")
    @patch("models.osc.osc.Zeroconf")
    def test_creates_zeroconf_and_browser_for_the_right_service_type(self, mock_zeroconf_cls, mock_browser_cls) -> None:
        handler = OSCHandler(ip_address="127.0.0.1")
        on_found = MagicMock()

        handler.waitForVrchatOscQueryConnectionAsync(on_found)

        mock_zeroconf_cls.assert_called_once()
        args, _ = mock_browser_cls.call_args
        self.assertEqual(args[1], ["_oscjson._tcp.local."])

    @patch("models.osc.osc.ServiceBrowser")
    @patch("models.osc.osc.Zeroconf")
    def test_is_noop_when_osc_query_is_disabled(self, mock_zeroconf_cls, mock_browser_cls) -> None:
        handler = OSCHandler(ip_address="192.168.1.50")  # non-local -> OSCQuery disabled

        handler.waitForVrchatOscQueryConnectionAsync(MagicMock())

        mock_zeroconf_cls.assert_not_called()
        mock_browser_cls.assert_not_called()

    @patch("models.osc.osc.ServiceBrowser")
    @patch("models.osc.osc.Zeroconf")
    def test_is_noop_when_already_watching(self, mock_zeroconf_cls, mock_browser_cls) -> None:
        handler = OSCHandler(ip_address="127.0.0.1")

        handler.waitForVrchatOscQueryConnectionAsync(MagicMock())
        handler.waitForVrchatOscQueryConnectionAsync(MagicMock())

        mock_zeroconf_cls.assert_called_once()

    @patch("models.osc.osc.ServiceBrowser")
    @patch("models.osc.osc.Zeroconf")
    def test_stop_closes_zeroconf_and_resets_state(self, mock_zeroconf_cls, mock_browser_cls) -> None:
        mock_zc_instance = mock_zeroconf_cls.return_value
        handler = OSCHandler(ip_address="127.0.0.1")
        handler.waitForVrchatOscQueryConnectionAsync(MagicMock())

        handler.stopWaitingForVrchatOscQueryConnection()

        mock_zc_instance.close.assert_called_once()
        self.assertIsNone(handler._vrchat_watch_zc)
        self.assertIsNone(handler._vrchat_watch_browser)

    @patch("models.osc.osc.ServiceBrowser")
    @patch("models.osc.osc.Zeroconf")
    def test_stop_is_a_noop_when_not_watching(self, mock_zeroconf_cls, mock_browser_cls) -> None:
        handler = OSCHandler(ip_address="127.0.0.1")

        handler.stopWaitingForVrchatOscQueryConnection()  # should not raise

        mock_zeroconf_cls.return_value.close.assert_not_called()

    @patch("models.osc.osc.ServiceBrowser")
    @patch("models.osc.osc.Zeroconf")
    def test_osc_server_stop_also_stops_watching(self, mock_zeroconf_cls, mock_browser_cls) -> None:
        mock_zc_instance = mock_zeroconf_cls.return_value
        handler = OSCHandler(ip_address="127.0.0.1")
        handler.waitForVrchatOscQueryConnectionAsync(MagicMock())

        handler.oscServerStop()

        mock_zc_instance.close.assert_called_once()
        self.assertIsNone(handler._vrchat_watch_zc)


if __name__ == "__main__":
    unittest.main()
