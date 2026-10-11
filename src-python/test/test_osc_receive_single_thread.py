"""OSC 受信はパケットごとにスレッドを起こさず、1本の受信スレッドで順に処理する。

ThreadingOSCUDPServer だった頃は、VRChat が送り続けるアバターのパラメータだけで
スレッドを起こし続け (実測、起動からスレッド約32万本)、CPU を約0.1コア使っていた。
"""

import threading
import time
import unittest
from unittest.mock import MagicMock, patch

from pythonosc import udp_client

from models.osc import osc as osc_module
from models.osc.osc import OSCHandler


class OscReceiveSingleThreadTest(unittest.TestCase):
    def test_every_packet_is_handled_on_the_one_receive_thread(self):
        handler = OSCHandler.__new__(OSCHandler)
        handler.is_osc_query_enabled = True
        handler.osc_server_ip_address = "127.0.0.1"
        handler.osc_query_service_name = "VRCT-test"
        handler.osc_query_service = None
        handler.browser = None
        seen = []
        handler.dict_filter_and_target = {"/avatar/parameters/MuteSelf": lambda address, value: seen.append(threading.get_ident())}
        with patch.object(osc_module, "OSCQueryService", MagicMock()):
            handler.receiveOscParameters()
        try:
            client = udp_client.SimpleUDPClient("127.0.0.1", handler.osc_server_port)
            for value in (True, False, True, False, True):
                client.send_message("/avatar/parameters/MuteSelf", value)
                client.send_message("/avatar/parameters/Unregistered", 1.0)
            deadline = time.monotonic() + 5
            while len(seen) < 5 and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertEqual(len(seen), 5)
            self.assertEqual(len(set(seen)), 1)  # always the same thread, none started per packet
            self.assertNotEqual(seen[0], threading.get_ident())
        finally:
            handler.osc_server.shutdown()
            handler.osc_server.server_close()


if __name__ == "__main__":
    unittest.main()
