import asyncio
from typing import Any
from time import sleep
from threading import Thread
from pythonosc import udp_client, dispatcher, osc_server
from tinyoscquery.queryservice import OSCQueryService
from tinyoscquery.query import OSCQueryBrowser, OSCQueryClient
from tinyoscquery.utility  import get_open_udp_port, get_open_tcp_port
from tinyoscquery.shared.node import OSCAccess
from utils import errorLogging

class OSCHandler:
    def __init__(self, ip_address="127.0.0.1", port=9000) -> None:
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

    def setOscIpAddress(self, ip_address:str) -> None:
        self.osc_ip_address = ip_address
        self.udp_client = udp_client.SimpleUDPClient(self.osc_ip_address, self.osc_port)

    def setOscPort(self, port:int) -> None:
        self.osc_port = port
        self.udp_client = udp_client.SimpleUDPClient(self.osc_ip_address, self.osc_port)

    # send OSC message typing
    def sendTyping(self, flag:bool=False) -> None:
        self.udp_client.send_message(self.osc_parameter_chatbox_typing, [flag])

    # send OSC message
    def sendMessage(self, message:str="", notification:bool=True) -> None:
        if len(message) > 0:
            self.udp_client.send_message(self.osc_parameter_chatbox_input, [f"{message}", True, notification])

    def getOSCParameterValue(self, address:str) -> Any:
        value = None
        try:
            browser = OSCQueryBrowser()
            sleep(1)
            service = browser.find_service_by_name(self.osc_server_name)
            if service is not None:
                osc_query_client = OSCQueryClient(service)
                mute_self_node = osc_query_client.query_node(address)
                value = mute_self_node.value[0]
            browser.zc.close()
            browser.browser.cancel()

        except Exception:
            errorLogging()
        return value

    def getOSCParameterMuteSelf(self) -> bool:
        return self.getOSCParameterValue(self.osc_parameter_muteself)

    def receiveOscParameters(self, dict_filter_and_target:dict) -> None:
        self.osc_server_port = get_open_udp_port()
        self.http_port = get_open_tcp_port()
        osc_dispatcher = dispatcher.Dispatcher()
        for filter, target in dict_filter_and_target.items():
            osc_dispatcher.map(filter, target)
        self.osc_server = osc_server.ThreadingOSCUDPServer((self.osc_server_ip_address, self.osc_server_port), osc_dispatcher, asyncio.get_event_loop())
        Thread(target=self.oscServerServe, daemon=True).start()

        while True:
            try:
                self.osc_query_service = OSCQueryService(self.osc_query_service_name, self.http_port, self.osc_server_port)
                for filter, target in dict_filter_and_target.items():
                    self.osc_query_service.advertise_endpoint(filter, access=OSCAccess.READWRITE_VALUE)
                break
            except Exception:
                errorLogging()
                sleep(1)

    def oscServerServe(self) -> None:
        self.osc_server.serve_forever(2)

    def oscServerStop(self) -> None:
        if isinstance(self.osc_server, osc_server.ThreadingOSCUDPServer):
            self.osc_server.shutdown()
            self.osc_server = None
        if isinstance(self.osc_query_service, OSCQueryService):
            self.osc_query_service.http_server.shutdown()
            self.osc_query_service = None

if __name__ == "__main__":
    handler = OSCHandler()
    handler.receiveOscParameters({
        "/avatar/parameters/MuteSelf": print,
    })
    sleep(5)
    handler.sendTyping(True)
    sleep(1)
    handler.sendMessage(message="Hello World", notification=True)
    sleep(60)
    handler.oscServerStop()