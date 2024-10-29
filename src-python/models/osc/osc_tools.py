from time import sleep
from pythonosc import osc_message_builder, udp_client, dispatcher, osc_server
from tinyoscquery.queryservice import OSCQueryService
from tinyoscquery.query import OSCQueryBrowser, OSCQueryClient
from tinyoscquery.utility  import get_open_udp_port, get_open_tcp_port
from psutil import process_iter

# send OSC message typing
def sendTyping(flag=False, ip_address="127.0.0.1", port=9000):
    typing = osc_message_builder.OscMessageBuilder(address="/chatbox/typing")
    typing.add_arg(flag)
    b_typing = typing.build()
    client = udp_client.SimpleUDPClient(ip_address, port)
    client.send(b_typing)

# send OSC message
def sendMessage(message=None, ip_address="127.0.0.1", port=9000):
    if message is not None:
        msg = osc_message_builder.OscMessageBuilder(address="/chatbox/input")
        msg.add_arg(f"{message}")
        msg.add_arg(True)
        msg.add_arg(True)
        b_msg = msg.build()
        client = udp_client.SimpleUDPClient(ip_address, port)
        client.send(b_msg)

def sendTestAction(ip_address="127.0.0.1", port=9000):
    client = udp_client.SimpleUDPClient(ip_address, port)
    client.send_message("/input/Vertical", 1)
    sleep(0.01)
    client.send_message("/input/Vertical", False)

# send Input Voice
def sendInputVoice(flag=False, ip_address="127.0.0.1", port=9000):
    input_voice = osc_message_builder.OscMessageBuilder(address="/input/Voice")
    input_voice.add_arg(flag)
    b_input_voice = input_voice.build()
    client = udp_client.SimpleUDPClient(ip_address, port)
    client.send(b_input_voice)

def sendChangeVoice(ip_address="127.0.0.1", port=9000):
    sendInputVoice(flag=0, ip_address=ip_address, port=port)
    sleep(0.05)
    sendInputVoice(flag=1, ip_address=ip_address, port=port)
    sleep(0.05)
    sendInputVoice(flag=0, ip_address=ip_address, port=port)
    sleep(0.05)

def getOSCParameterValue(address, server_name="VRChat-Client"):
    value = None
    try:
        browser = OSCQueryBrowser()
        sleep(1)
        service = browser.find_service_by_name(server_name)
        if service is not None:
            oscq = OSCQueryClient(service)
            mute_self_node = oscq.query_node(address)
            value = mute_self_node.value[0]
        browser.zc.close()
        browser.browser.cancel()

    except Exception:
        pass
    return value

def checkVRChatRunning() -> bool:
    _proc_name = "VRChat.exe"
    return _proc_name in (p.name() for p in process_iter())

def receiveOscParameters(dict_filter_and_target, ip_address="127.0.0.1", title="VRCT"):
    while True:
        if not checkVRChatRunning():
            sleep(1)
        else:
            try:
                osc_port = get_open_udp_port()
                http_port = get_open_tcp_port()
                osc_dispatcher = dispatcher.Dispatcher()
                for filter, target in dict_filter_and_target.items():
                    osc_dispatcher.map(filter, target)
                osc_udp_server = osc_server.ThreadingOSCUDPServer((ip_address, osc_port), osc_dispatcher)

                osc_client = OSCQueryService(title, http_port, osc_port)
                for filter, target in dict_filter_and_target.items():
                    osc_client.advertise_endpoint(filter)

                osc_udp_server.serve_forever()
            except Exception:
                pass

if __name__ == "__main__":
    osc_parameter_prefix = "/avatar/parameters/"
    osc_avatar_change_path = "/avatar/change"
    param_MuteSelf = "MuteSelf"
    param_Voice = "Voice"

    def print_handler_all(address, *args):
        print(f"all {address}: {args}")

    def print_handler_muteself(address, *args):
        print(f"muteself {address}: {args}")

    def print_handler_voice(address, *args):
        print(f"voice {address}: {args}")

    dict_filter_and_target = {
        # osc_parameter_prefix + "*": print_handler_all,
        osc_parameter_prefix + param_MuteSelf: print_handler_muteself,
        osc_parameter_prefix + param_Voice: print_handler_voice,
    }

    receiveOscParameters(dict_filter_and_target)