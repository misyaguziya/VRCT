# 初期化のため、config.jsonの削除
import os
import pprint
import time
import random
if os.path.exists("config.json"):
    os.remove("config.json")

from mainloop import main_instance

class Color:
	BLACK          = '\033[30m'#(文字)黒
	RED            = '\033[31m'#(文字)赤
	GREEN          = '\033[32m'#(文字)緑
	YELLOW         = '\033[33m'#(文字)黄
	BLUE           = '\033[34m'#(文字)青
	MAGENTA        = '\033[35m'#(文字)マゼンタ
	CYAN           = '\033[36m'#(文字)シアン
	WHITE          = '\033[37m'#(文字)白
	COLOR_DEFAULT  = '\033[39m'#文字色をデフォルトに戻す
	BOLD           = '\033[1m'#太字
	UNDERLINE      = '\033[4m'#下線
	INVISIBLE      = '\033[08m'#不可視
	REVERCE        = '\033[07m'#文字色と背景色を反転
	BG_BLACK       = '\033[40m'#(背景)黒
	BG_RED         = '\033[41m'#(背景)赤
	BG_GREEN       = '\033[42m'#(背景)緑
	BG_YELLOW      = '\033[43m'#(背景)黄
	BG_BLUE        = '\033[44m'#(背景)青
	BG_MAGENTA     = '\033[45m'#(背景)マゼンタ
	BG_CYAN        = '\033[46m'#(背景)シアン
	BG_WHITE       = '\033[47m'#(背景)白
	BG_DEFAULT     = '\033[49m'#背景色をデフォルトに戻す
	RESET          = '\033[0m'#全てリセット
 
class TestMainloop():
    def __init__(self):
        self.main = main_instance
        self.main.startReceiver()
        self.main.startHandler()

        def stop_main():
            pass
        self.main.controller.setWatchdogCallback(stop_main)
        self.main.controller.init()

        # mappingのすべてのstatusをTrueにする
        for key in self.main.mapping.keys():
            self.main.mapping[key]["status"] = True

        self.config_dict = {}
        for endpoint in self.main.mapping.keys():
            if endpoint.startswith("/get/data/"):
                self.config_dict[endpoint.split("/")[-1]] = self.main.handleRequest(endpoint, None)[0]
            elif endpoint.startswith("/set/disable/"):
                self.config_dict[endpoint.split("/")[-1]] = self.main.handleRequest(endpoint, None)[0]
        print(self.config_dict)

        self.validity_endpoints = [
            "/set/enable/translation",
            "/set/disable/translation",
            "/set/enable/transcription_send",
            "/set/disable/transcription_send",
            "/set/enable/transcription_receive",
            "/set/disable/transcription_receive",
            "/set/enable/foreground",
            "/set/disable/foreground",
            "/set/enable/main_window_sidebar_compact_mode",
            "/set/disable/main_window_sidebar_compact_mode",
            "/set/enable/show_resend_button",
            "/set/disable/show_resend_button",
            "/set/enable/convert_message_to_romaji",
            "/set/disable/convert_message_to_romaji",
            "/set/enable/convert_message_to_hiragana",
            "/set/disable/convert_message_to_hiragana",
            # "/set/enable/auto_mic_select",
            # "/set/disable/auto_mic_select",
            "/set/enable/mic_automatic_threshold",
            "/set/disable/mic_automatic_threshold",
            # "/set/enable/check_mic_threshold",
            # "/set/disable/check_mic_threshold",
            # "/set/enable/auto_speaker_select",
            # "/set/disable/auto_speaker_select",
            "/set/enable/speaker_automatic_threshold",
            "/set/disable/speaker_automatic_threshold",
            # "/set/enable/check_speaker_threshold",
            # "/set/disable/check_speaker_threshold",
            "/set/enable/overlay_small_log",
            "/set/disable/overlay_small_log",
            "/set/enable/overlay_large_log",
            "/set/disable/overlay_large_log",
            "/set/enable/overlay_show_only_translated_messages",
            "/set/disable/overlay_show_only_translated_messages",
            "/set/enable/auto_clear_message_box",
            "/set/disable/auto_clear_message_box",
            "/set/enable/send_only_translated_messages",
            "/set/disable/send_only_translated_messages",
            "/set/enable/logger_feature",
            "/set/disable/logger_feature",
            "/set/enable/vrc_mic_mute_sync",
            "/set/disable/vrc_mic_mute_sync",
            "/set/enable/send_message_to_vrc",
            "/set/disable/send_message_to_vrc",
            "/set/enable/send_received_message_to_vrc",
            "/set/disable/send_received_message_to_vrc",
            "/set/enable/websocket_server",
            "/set/disable/websocket_server",
            "/set/enable/notification_vrc_sfx",
            "/set/disable/notification_vrc_sfx",
        ]

        self.set_data_endpoints = [
            "/set/data/selected_tab_no",
            "/set/data/selected_translation_engines",
            "/set/data/selected_your_languages",
            "/set/data/selected_target_languages"
            "/set/data/selected_transcription_engine",
            "/set/data/transparency",
            "/set/data/ui_scaling",
            "/set/data/textbox_ui_scaling",
            "/set/data/message_box_ratio",
            "/set/data/send_message_button_type",
            "/set/data/font_family",
            "/set/data/ui_language",
            "/set/data/main_window_geometry",
            "/set/data/selected_translation_compute_device",
            "/set/data/selected_transcription_compute_device",
            "/set/data/ctranslate2_weight_type",
            "/set/data/deepl_auth_key",
            "/set/data/selected_mic_host",
            "/set/data/selected_mic_device",
            "/set/data/mic_threshold",
            "/set/data/mic_record_timeout",
            "/set/data/mic_phrase_timeout",
            "/set/data/mic_max_phrases",
            "/set/data/hotkeys",
            "/set/data/plugins_status",
            "/set/data/mic_avg_logprob",
            "/set/data/mic_no_speech_prob",
            "/set/data/mic_word_filter",
            "/set/data/selected_speaker_device",
            "/set/data/speaker_threshold",
            "/set/data/speaker_record_timeout",
            "/set/data/speaker_phrase_timeout",
            "/set/data/speaker_max_phrases",
            "/set/data/speaker_avg_logprob",
            "/set/data/speaker_no_speech_prob",
            "/set/data/whisper_weight_type",
            "/set/data/overlay_small_log_settings",
            "/set/data/overlay_large_log_settings",
            "/set/data/send_message_format_parts",
            "/set/data/received_message_format_parts",
            "/set/data/websocket_host",
            "/set/data/websocket_port",
            "/set/data/osc_ip_address",
            "/set/data/osc_port",
        ]

        self.delete_data_endpoints = [
            "/delete/data/deepl_auth_key",
        ]

        self.run_endpoints = {
            "/run/send_message_box": [
                {
                    "data": {"id":"123456", "message":"test"},
                    "status": 200,
                    "result": {
                        'id': '123456',
                        'original': {
                            'message': 'test',
                            'transliteration': []
                            },
                        'translations': []
                    }
                }
            ],
            "/run/typing_message_box": [{"data": None, "status": 200, "result": True}],
            "/run/stop_typing_message_box": [{"data": None, "status": 200, "result": True}],
            "/run/send_text_overlay": [{"data": "test_overlay", "status": 200, "result": "test_overlay"}],
            "/run/swap_your_language_and_target_language": [{"data": None, "status": 200, "result": True}],
            # !!!Cant be tested here!!!
            # "/run/update_software": [{"data": None, "status": 200, "result": True}],
            # "/run/update_cuda_software": [{"data": None, "status": 200, "result": True}],
            "/run/download_ctranslate2_weight": [
                {"data": "small", "status": 200, "result": True},
                {"data": "large", "status": 400, "result": False},
            ],
            "/run/download_whisper_weight": [
                {"data": "tiny", "status": 200, "result": True},
                {"data": "base", "status": 200, "result": True},
                {"data": "small", "status": 200, "result": True},
                {"data": "medium", "status": 200, "result": True},
                {"data": "large-v1", "status": 200, "result": True},
                {"data": "large-v2", "status": 400, "result": False},
                {"data": "large-v3", "status": 400, "result": False},
                {"data": "large-v3-turbo-int8", "status": 400, "result": False},
                {"data": "large-v3-turbo", "status": 400, "result": False}
            ],
            "/run/open_filepath_logs": {"data": None, "status": 200, "result": True},
            "/run/open_filepath_config_file": {"data": None, "status": 200, "result": True},
            "/run/feed_watchdog": {"data": None, "status": 200, "result": True},
        }

    def test_endpoints_on_off_single(self):
        print("----ON/OFF系のエンドポイントのテスト----")
        for endpoint in self.validity_endpoints:
            print(f"Testing endpoint: {endpoint}", end="", flush=True)
            if endpoint.startswith("/set/enable/"):
                result, status = self.main.handleRequest(endpoint, None)
                if result is True and status == 200:
                    self.config_dict[endpoint.split("/")[-1]] = result
                    print(f"\t -> {Color.GREEN}[PASS]{Color.RESET} Status: {status}, Result: {result}")
                else:
                    print(f"\t -> {Color.RED}[ERROR]{Color.RESET} Status: {status}, Result: {result}")
                    print(f"Current config_dict: {self.config_dict}")
                    break
            elif endpoint.startswith("/set/disable/"):
                result, status = self.main.handleRequest(endpoint, None)
                if result is False and status == 200:
                    self.config_dict[endpoint.split("/")[-1]] = result
                    print(f"\t -> {Color.GREEN}[PASS]{Color.RESET} Status: {status}, Result: {result}")
                else:
                    print(f"\t -> {Color.RED}[ERROR]{Color.RESET} Status: {status}, Result: {result}")
                    print(f"Current config_dict: {self.config_dict}")
                    break
        print("----ON/OFF系のエンドポイントのテスト終了----")

    def test_endpoints_on_off_random(self):
        print("----ON/OFFでのランダムアクセスのテスト----")
        for i in range(1000):
            endpoint = random.choice(self.validity_endpoints)
            print(f"No.{i:04} Testing endpoint: {endpoint}", end="", flush=True)
            if endpoint.startswith("/set/enable/"):
                result, status = self.main.handleRequest(endpoint, None)
                expected_result = True
                if result == expected_result and status == 200:
                    self.config_dict[endpoint.split("/")[-1]] = result
                    print(f"\t -> {Color.GREEN}[PASS]{Color.RESET} Status: {status}, Result: {result}")
                else:
                    print(f"\t -> {Color.RED}[ERROR]{Color.RESET} Status: {status}, Result: {result}, Expected: {expected_result}")
                    pprint.pprint(self.config_dict)
                    break
            elif endpoint.startswith("/set/disable/"):
                result, status = self.main.handleRequest(endpoint, None)
                expected_result = False
                if result == expected_result and status == 200:
                    self.config_dict[endpoint.split("/")[-1]] = result
                    print(f"\t -> {Color.GREEN}[PASS]{Color.RESET} Status: {status}, Result: {result}")
                else:
                    print(f"\t -> {Color.RED}[ERROR]{Color.RESET} Status: {status}, Result: {result}, Expected: {expected_result}")
                    pprint.pprint(self.config_dict)
                    break
        print("----ON/OFFでのランダムアクセスのテスト終了----")

    def test_endpoints_continuous(self):
        print("----連続テスト----")
        # endpoints = ["/set/enable/websocket_server", "/set/disable/websocket_server"]
        endpoints = ["/set/enable/transcription_receive", "/set/disable/transcription_receive"]
        for i in range(1000):
            endpoint = random.choice(endpoints)
            print(f"No.{i:04} Testing endpoint: {endpoint}", end="", flush=True)
            if endpoint.startswith("/set/enable/"):
                result, status = self.main.handleRequest(endpoint, None)
                expected_result = True
                if result == expected_result and status == 200:
                    self.config_dict[endpoint.split("/")[-1]] = result
                    print(f"\t -> {Color.GREEN}[PASS]{Color.RESET} Status: {status}, Result: {result}")
                else:
                    print(f"\t -> {Color.RED}[ERROR]{Color.RESET} Status: {status}, Result: {result}, Expected: {expected_result}")
                    pprint.pprint(self.config_dict)
                    break
            elif endpoint.startswith("/set/disable/"):
                result, status = self.main.handleRequest(endpoint, None)
                expected_result = False
                if result == expected_result and status == 200:
                    self.config_dict[endpoint.split("/")[-1]] = result
                    print(f"\t -> {Color.GREEN}[PASS]{Color.RESET} Status: {status}, Result: {result}")
                else:
                    print(f"\t -> {Color.RED}[ERROR]{Color.RESET} Status: {status}, Result: {result}, Expected: {expected_result}")
                    pprint.pprint(self.config_dict)
                    break
        print("----連続テスト終了----")

if __name__ == "__main__":
    test = TestMainloop()
    test.test_endpoints_continuous()