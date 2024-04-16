from time import sleep
from threading import Thread
from pythonosc import osc_message_builder
from pythonosc import udp_client
from pythonosc import dispatcher
from pythonosc import osc_server
from tinyoscquery.queryservice import OSCQueryService
from tinyoscquery.utility  import get_open_udp_port, get_open_tcp_port

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


def receiveOscParameters(dict_filter_and_target, ip_address="127.0.0.1", title="VRCT"):
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