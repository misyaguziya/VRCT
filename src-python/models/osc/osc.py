"""OSC helpers and a thin OSCQuery-enabled server wrapper.

This module provides `OSCHandler`, a convenience wrapper used by the
application to send OSC messages and expose OSCQuery endpoints when the
target address is localhost. The implementation is defensive: missing
utilities are handled gracefully and logging helpers are used where
available.
"""

import time
from typing import Any, Callable, Dict, Optional
from time import sleep
from threading import Thread
from pythonosc import udp_client, dispatcher, osc_server
try:
    from tinyoscquery.queryservice import OSCQueryService
    from tinyoscquery.query import OSCQueryBrowser, OSCQueryClient
    from tinyoscquery.utility import get_open_udp_port, get_open_tcp_port
    from tinyoscquery.shared.node import OSCAccess
except Exception:
    # tinyoscquery is optional for non-local usage; functionality that
    # depends on it will be disabled if it's missing.
    OSCQueryService = None  # type: ignore
    OSCQueryBrowser = None  # type: ignore
    OSCQueryClient = None  # type: ignore
    def get_open_udp_port() -> int:  # type: ignore
        return 0

    def get_open_tcp_port() -> int:  # type: ignore
        return 0
    OSCAccess = None  # type: ignore

try:
    from utils import errorLogging
except Exception:
    def errorLogging() -> None:
        import traceback
        print("Error occurred:", traceback.format_exc())

class OSCHandler:
    """Thin wrapper managing OSC send/receive and optional OSCQuery advertising.

    Args:
        ip_address: OSC server client target / bind address
        port: UDP port to send to
    """

    def __init__(self, ip_address: str = "127.0.0.1", port: int = 9000) -> None:

        self.is_osc_query_enabled: bool = ip_address in ["127.0.0.1", "localhost"]

        self.osc_ip_address: str = ip_address
        self.osc_port: int = port
        self.osc_parameter_muteself: str = "/avatar/parameters/MuteSelf"
        self.osc_parameter_chatbox_typing: str = "/chatbox/typing"
        self.osc_parameter_chatbox_input: str = "/chatbox/input"
        self.udp_client = udp_client.SimpleUDPClient(self.osc_ip_address, self.osc_port)
        self.osc_server_name: str = "VRChat-Client"
        self.osc_server = None
        self.osc_query_service = None
        self.osc_query_service_name: str = "VRCT"
        self.osc_server_ip_address: str = ip_address
        self.http_port: Optional[int] = None
        self.osc_server_port: Optional[int] = None
        self.dict_filter_and_target: Dict[str, Callable] = {}
        self.browser = None

    def getIsOscQueryEnabled(self) -> bool:
        """Return whether OSCQuery support is enabled (local addresses only)."""
        return self.is_osc_query_enabled

    def setOscIpAddress(self, ip_address: str) -> None:
        """Change the OSC target IP address and reinitialize services."""
        self.is_osc_query_enabled = ip_address in ["127.0.0.1", "localhost"]

        self.oscServerStop()
        self.osc_ip_address = ip_address
        self.udp_client = udp_client.SimpleUDPClient(self.osc_ip_address, self.osc_port)
        self.receiveOscParameters()

    def setOscPort(self, port: int) -> None:
        """Change the OSC UDP port used for sending and reinitialize services."""
        self.oscServerStop()
        self.osc_port = port
        self.udp_client = udp_client.SimpleUDPClient(self.osc_ip_address, self.osc_port)
        self.receiveOscParameters()

    # send OSC message typing
    def sendTyping(self, flag: bool = False) -> None:
        """Send /chatbox/typing with a boolean flag."""
        self.udp_client.send_message(self.osc_parameter_chatbox_typing, [flag])

    # send OSC message
    def sendMessage(self, message: str = "", notification: bool = True) -> None:
        """Send /chatbox/input if message is non-empty.

        The second argument historically was a boolean flag for clearing; we keep
        compatibility by sending [message, True, notification].
        """
        if len(message) > 0:
            self.udp_client.send_message(self.osc_parameter_chatbox_input, [f"{message}", True, notification])

    def getOSCParameterValue(self, address: str) -> Any:
        if not self.is_osc_query_enabled:
            # OSCQueryが無効な場合はNoneを返す
            return None
        value: Any = None
        try:
            # browserインスタンスを再利用し、毎回の生成と破棄を避ける
            if self.browser is None:
                # OSCQueryBrowser may not be available; guard
                if OSCQueryBrowser is None:
                    return None
                self.browser = OSCQueryBrowser()
                sleep(1)  # 初回のみスリープ

            service = self.browser.find_service_by_name(self.osc_server_name)
            if service is not None:
                osc_query_client = OSCQueryClient(service)
                mute_self_node = osc_query_client.query_node(address)
                value = mute_self_node.value[0]
        except Exception:
            errorLogging()
            # エラー発生時にbrowserをリセットして次回再初期化
            if self.browser is not None:
                try:
                    if hasattr(self.browser, 'zc') and self.browser.zc is not None:
                        self.browser.zc.close()
                    if hasattr(self.browser, 'browser') and self.browser.browser is not None:
                        self.browser.browser.cancel()
                except Exception:
                    pass
                self.browser = None
        return value

    def getOSCParameterMuteSelf(self) -> Optional[bool]:
        """Return the value of the MuteSelf parameter when available, else None."""
        return self.getOSCParameterValue(self.osc_parameter_muteself)

    def setDictFilterAndTarget(self, dict_filter_and_target: Dict[str, Callable]) -> None:
        """Set the mapping from OSC address filters to handler callables."""
        self.dict_filter_and_target = dict_filter_and_target

    def receiveOscParameters(self) -> None:
        """Start a local OSC server and advertise OSCQuery endpoints when supported.

        If `tinyoscquery` is not available or OSCQuery is disabled, this is a
        no-op.
        """
        if not self.is_osc_query_enabled or OSCQueryService is None:
            # OSCQuery が無効またはライブラリが無い場合は何もしない
            return

        self.osc_server_port = get_open_udp_port()
        self.http_port = get_open_tcp_port()
        osc_dispatcher = dispatcher.Dispatcher()
        for filter, target in self.dict_filter_and_target.items():
            osc_dispatcher.map(filter, target)
        self.osc_server = osc_server.ThreadingOSCUDPServer((self.osc_server_ip_address, self.osc_server_port), osc_dispatcher)
        Thread(target=self.oscServerServe, daemon=True).start()

        while True:
            try:
                # osc_server_name + UTC timestamp でユニークなサービス名を生成
                service_name = f"{self.osc_query_service_name}:{int(time.time())}"
                self.osc_query_service = OSCQueryService(service_name, self.http_port, self.osc_server_port)
                for filter, target in self.dict_filter_and_target.items():
                    # OSCAccess may be None when tinyoscquery is not present; guard
                    if OSCAccess is not None:
                        self.osc_query_service.advertise_endpoint(filter, access=OSCAccess.READWRITE_VALUE)
                break
            except Exception:
                errorLogging()
                sleep(1)

    def oscServerServe(self) -> None:
        """Run the OSC server loop with a longer poll interval to reduce CPU."""
        # ポーリング間隔を長くして（2秒から10秒に）CPUの使用率を削減
        if self.osc_server is not None:
            self.osc_server.serve_forever(10)

    def oscServerStop(self) -> None:
        """Stop and clean up any running OSC server and OSCQuery service."""
        if isinstance(self.osc_server, osc_server.ThreadingOSCUDPServer):
            try:
                self.osc_server.shutdown()
            except Exception:
                pass
            self.osc_server = None
        if OSCQueryService is not None and isinstance(self.osc_query_service, OSCQueryService):
            try:
                self.osc_query_service.http_server.shutdown()
            except Exception:
                pass
            self.osc_query_service = None
        # browser がある場合はクリーンアップ
        if self.browser is not None:
            try:
                if hasattr(self.browser, 'zc') and self.browser.zc is not None:
                    self.browser.zc.close()
                if hasattr(self.browser, 'browser') and self.browser.browser is not None:
                    self.browser.browser.cancel()
            except Exception:
                pass
            self.browser = None

if __name__ == "__main__":
    handler = OSCHandler()
    handler.setDictFilterAndTarget({
        "/avatar/parameters/MuteSelf": lambda address, *args: print(f"Received {address} with args {args}"),
        "/chatbox/typing": lambda address, *args: print(f"Received {address} with args {args}"),
        "/chatbox/input": lambda address, *args: print(f"Received {address} with args {args}"),
    })
    handler.receiveOscParameters()
    sleep(5)
    handler.sendTyping(True)
    sleep(1)
    handler.sendMessage(message="Hello World 1", notification=True)
    sleep(10)

    print("IP address changed to 192.168.193.2")
    handler.setOscIpAddress("192.168.193.2")
    sleep(5)
    handler.sendMessage(message="Hello World 2", notification=True)

    print("IP address changed to 127.0.0.1")
    handler.setOscIpAddress("127.0.0.1")
    sleep(5)
    handler.sendMessage(message="Hello World 3", notification=True)
    sleep(10)
    handler.oscServerStop()