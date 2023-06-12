from pythonosc import osc_message_builder
from pythonosc import udp_client

# send OSC message typing
def send_typing(flag=False, ip_address="127.0.0.1", port=9000):
    typing = osc_message_builder.OscMessageBuilder(address="/chatbox/typing")
    typing.add_arg(flag)
    b_typing = typing.build()
    client = udp_client.SimpleUDPClient(ip_address, port)
    client.send(b_typing)

# send OSC message
def send_message(message=None, ip_address="127.0.0.1", port=9000):
    if message != None:
        msg = osc_message_builder.OscMessageBuilder(address="/chatbox/input")
        msg.add_arg(f"{message}")
        msg.add_arg(True)
        msg.add_arg(True)
        b_msg = msg.build()
        client = udp_client.SimpleUDPClient(ip_address, port)
        client.send(b_msg)