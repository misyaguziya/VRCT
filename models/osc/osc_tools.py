from time import sleep
from typing import List
from pythonosc import osc_message_builder
from pythonosc import udp_client
from pythonosc import dispatcher
from pythonosc import osc_server

# send OSC message typing
def sendTyping(flag=False, ip_address="127.0.0.1", port=9000):
    typing = osc_message_builder.OscMessageBuilder(address="/chatbox/typing")
    typing.add_arg(flag)
    b_typing = typing.build()
    client = udp_client.SimpleUDPClient(ip_address, port)
    client.send(b_typing)

# send OSC message
def sendMessage(message=None, ip_address="127.0.0.1", port=9000):
    if message != None:
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

def receiveOscParameters(target, filter="/*", ip_address="127.0.0.1", port=9001):
    _dispatcher = dispatcher.Dispatcher()
    _dispatcher.map(filter, target)
    server = osc_server.ThreadingOSCUDPServer((ip_address, port), _dispatcher)
    server.serve_forever()