import asyncio
from typing import Any
from time import sleep
from threading import Thread
from pythonosc import udp_client, dispatcher, osc_server
from tinyoscquery.queryservice import OSCQueryService
from tinyoscquery.query import OSCQueryBrowser, OSCQueryClient
from tinyoscquery.utility  import get_open_udp_port, get_open_tcp_port
from tinyoscquery.shared.node import OSCAccess

try:
    from utils import errorLogging
except ImportError:
    def errorLogging():
        import traceback
        print("Error occurred:", traceback.format_exc())

class OSCHandler:
    def __init__(self, ip_address="127.0.0.1", port=9000) -> None:

        if ip_address in ["127.0.0.1", "localhost"]:
            self.is_osc_query_enabled = True
        else:
            self.is_osc_query_enabled = False

        self.osc_ip_address = ip_address
        self.osc_port = port
        self.osc_parameter_muteself = "/avatar/parameters/MuteSelf"
        self.osc_parameter_chatbox_typing = "/chatbox/typing"
        self.osc_parameter_chatbox_input = "/chatbox/input"
        self.udp_client = udp_client.SimpleUDPClient(self.osc_ip_address, self.osc_port)
        self.osc_server_name = "VRChat-Client"
        self.osc_server = None
        self.osc_query_service = None
        self.osc_query_service_name = "VRCT"
        self.osc_server_ip_address = ip_address
        self.http_port = None
        self.osc_server_port = None
        self.dict_filter_and_target = {}
        self.browser = None

    def getIsOscQueryEnabled(self) -> bool:
        return self.is_osc_query_enabled

    def setOscIpAddress(self, ip_address:str) -> None:
        if ip_address in ["127.0.0.1", "localhost"]:
            self.is_osc_query_enabled = True
        else:
            self.is_osc_query_enabled = False

        self.oscServerStop()
        self.osc_ip_address = ip_address
        self.udp_client = udp_client.SimpleUDPClient(self.osc_ip_address, self.osc_port)
        self.receiveOscParameters()

    def setOscPort(self, port:int) -> None:
        self.oscServerStop()
        self.osc_port = port
        self.udp_client = udp_client.SimpleUDPClient(self.osc_ip_address, self.osc_port)
        self.receiveOscParameters()

    # send OSC message typing
    def sendTyping(self, flag:bool=False) -> None:
        self.udp_client.send_message(self.osc_parameter_chatbox_typing, [flag])

    # send OSC message
    def sendMessage(self, message:str="", notification:bool=True) -> None:
        if len(message) > 0:
            self.udp_client.send_message(self.osc_parameter_chatbox_input, [f"{message}", True, notification])

    def getOSCParameterValue(self, address:str) -> Any:
        if not self.is_osc_query_enabled:
            # OSCQueryが無効な場合はNoneを返す
            return None

        value = None
        try:
            # browserインスタンスを再利用し、毎回の生成と破棄を避ける
            if self.browser is None:
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

    def getOSCParameterMuteSelf(self) -> bool:
        return self.getOSCParameterValue(self.osc_parameter_muteself)

    def setDictFilterAndTarget(self, dict_filter_and_target:dict) -> None:
        self.dict_filter_and_target = dict_filter_and_target

    def receiveOscParameters(self) -> None:
        if self.is_osc_query_enabled is False:
            # OSCQueryが無効な場合は何もしない
            return

        self.osc_server_port = get_open_udp_port()
        self.http_port = get_open_tcp_port()
        osc_dispatcher = dispatcher.Dispatcher()
        for filter, target in self.dict_filter_and_target.items():
            osc_dispatcher.map(filter, target)
        self.osc_server = osc_server.ThreadingOSCUDPServer((self.osc_server_ip_address, self.osc_server_port), osc_dispatcher)
        Thread(target=self.oscServerServe, daemon=True).start()

        def startOSCQueryService():
            while True:
                try:
                    self.osc_query_service = OSCQueryService(self.osc_query_service_name, self.http_port, self.osc_server_port)
                    for filter, target in self.dict_filter_and_target.items():
                        self.osc_query_service.advertise_endpoint(filter, access=OSCAccess.READWRITE_VALUE)
                    break
                except Exception:
                    errorLogging()
                    sleep(1)
        Thread(target=startOSCQueryService, daemon=True).start()

    def oscServerServe(self) -> None:
        # ポーリング間隔を長くして（2秒から10秒に）CPUの使用率を削減
        self.osc_server.serve_forever(10)

    def oscServerStop(self) -> None:
        if isinstance(self.osc_server, osc_server.ThreadingOSCUDPServer):
            self.osc_server.shutdown()
            self.osc_server = None
        if isinstance(self.osc_query_service, OSCQueryService):
            self.osc_query_service.http_server.shutdown()
            self.osc_query_service = None
        # browserがある場合はクリーンアップ
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