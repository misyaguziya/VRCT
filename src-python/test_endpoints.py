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
            "/set/enable/auto_mic_select",
            "/set/disable/auto_mic_select",
            "/set/enable/mic_automatic_threshold",
            "/set/disable/mic_automatic_threshold",
            "/set/enable/check_mic_threshold",
            "/set/disable/check_mic_threshold",
            "/set/enable/auto_speaker_select",
            "/set/disable/auto_speaker_select",
            "/set/enable/speaker_automatic_threshold",
            "/set/disable/speaker_automatic_threshold",
            "/set/enable/check_speaker_threshold",
            "/set/disable/check_speaker_threshold",
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
                    "data": {"id":"000001", "message":"test"},
                    "status": 200,
                },
                {
                    # 英語
                    "data": {"id":"000002", "message":"Hello World!"},
                    "status": 200,
                },
                {
                    # 日本語
                    "data": {"id":"000003", "message":"こんにちわ 世界！"},
                    "status": 200,
                },
                {
                    # 韓国語
                    "data": {"id":"000004", "message":"안녕하세요 세계!"},
                    "status": 200,
                },
                {
                    # 中国語 繁体字
                    "data": {"id":"000005", "message":"你好，世界！"},
                    "status": 200,
                },
            ],
            "/run/typing_message_box": [{"data": None, "status": 200, "result": True}],
            "/run/stop_typing_message_box": [{"data": None, "status": 200, "result": True}],
            "/run/send_text_overlay": [{"data": "test_overlay", "status": 200, "result": "test_overlay"}],
            "/run/swap_your_language_and_target_language": [{"data": None, "status": 200}],
            # !!!Cant be tested here!!!
            # "/run/update_software": [{"data": None, "status": 200, "result": True}],
            # "/run/update_cuda_software": [{"data": None, "status": 200, "result": True}],
            # "/run/download_ctranslate2_weight": [
            #     {"data": "small", "status": 200, "result": True},
            #     {"data": "large", "status": 400, "result": False},
            # ],
            # "/run/download_whisper_weight": [
            #     {"data": "tiny", "status": 200, "result": True},
            #     {"data": "base", "status": 200, "result": True},
            #     {"data": "small", "status": 200, "result": True},
            #     {"data": "medium", "status": 200, "result": True},
            #     {"data": "large-v1", "status": 200, "result": True},
            #     {"data": "large-v2", "status": 400, "result": True},
            #     {"data": "large-v3", "status": 400, "result": True},
            #     {"data": "large-v3-turbo-int8", "status": 400, "result": True},
            #     {"data": "large-v3-turbo", "status": 400, "result": True}
            # ],
            # "/run/open_filepath_logs": {"data": None, "status": 200, "result": True},
            # "/run/open_filepath_config_file": {"data": None, "status": 200, "result": True},
            # "/run/feed_watchdog": {"data": None, "status": 200, "result": True},
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

    # def test_endpoints_on_off_random(self):
    #     print("----ON/OFFでのランダムアクセスのテスト----")
    #     for i in range(1000):
    #         endpoint = random.choice(self.validity_endpoints)
    #         print(f"No.{i:04} Testing endpoint: {endpoint}", end="", flush=True)
    #         if endpoint.startswith("/set/enable/"):
    #             result, status = self.main.handleRequest(endpoint, None)
    #             expected_result = True
    #             if result == expected_result and status == 200:
    #                 self.config_dict[endpoint.split("/")[-1]] = result
    #                 print(f"\t -> {Color.GREEN}[PASS]{Color.RESET} Status: {status}, Result: {result}")
    #             else:
    #                 print(f"\t -> {Color.RED}[ERROR]{Color.RESET} Status: {status}, Result: {result}, Expected: {expected_result}")
    #                 pprint.pprint(self.config_dict)
    #                 break
    #         elif endpoint.startswith("/set/disable/"):
    #             result, status = self.main.handleRequest(endpoint, None)
    #             expected_result = False
    #             if result == expected_result and status == 200:
    #                 self.config_dict[endpoint.split("/")[-1]] = result
    #                 print(f"\t -> {Color.GREEN}[PASS]{Color.RESET} Status: {status}, Result: {result}")
    #             else:
    #                 print(f"\t -> {Color.RED}[ERROR]{Color.RESET} Status: {status}, Result: {result}, Expected: {expected_result}")
    #                 pprint.pprint(self.config_dict)
    #                 break

    #     # 最後にすべてOFFにして終了
    #     for endpoint in self.validity_endpoints:
    #         if endpoint.startswith("/set/disable/"):
    #             result, status = self.main.handleRequest(endpoint, None)
    #             time.sleep(0.2)
    #     print("----ON/OFFでのランダムアクセスのテスト終了----")

    # def test_endpoints_on_off_continuous(self):
    #     print("----ON/OFF連続テスト----")
    #     # endpoints = ["/set/enable/websocket_server", "/set/disable/websocket_server"]
    #     endpoints = [
    #         "/set/enable/translation",
    #         "/set/disable/translation",
    #         "/set/enable/transcription_send",
    #         "/set/disable/transcription_send",
    #         "/set/enable/transcription_receive",
    #         "/set/disable/transcription_receive",
    #     ]
    #     for i in range(1000):
    #         endpoint = random.choice(endpoints)
    #         print(f"No.{i:04} Testing endpoint: {endpoint}", end="", flush=True)
    #         if endpoint.startswith("/set/enable/"):
    #             result, status = self.main.handleRequest(endpoint, None)
    #             expected_result = True
    #             if result == expected_result and status == 200:
    #                 self.config_dict[endpoint.split("/")[-1]] = result
    #                 print(f"\t -> {Color.GREEN}[PASS]{Color.RESET} Status: {status}, Result: {result}")
    #             else:
    #                 print(f"\t -> {Color.RED}[ERROR]{Color.RESET} Status: {status}, Result: {result}, Expected: {expected_result}")
    #                 pprint.pprint(self.config_dict)
    #                 break
    #         elif endpoint.startswith("/set/disable/"):
    #             result, status = self.main.handleRequest(endpoint, None)
    #             expected_result = False
    #             if result == expected_result and status == 200:
    #                 self.config_dict[endpoint.split("/")[-1]] = result
    #                 print(f"\t -> {Color.GREEN}[PASS]{Color.RESET} Status: {status}, Result: {result}")
    #             else:
    #                 print(f"\t -> {Color.RED}[ERROR]{Color.RESET} Status: {status}, Result: {result}, Expected: {expected_result}")
    #                 pprint.pprint(self.config_dict)
    #                 break

    #     # 最後にすべてOFFにして終了
    #     for endpoint in self.validity_endpoints:
    #         if endpoint.startswith("/set/disable/"):
    #             result, status = self.main.handleRequest(endpoint, None)
    #     print("----ON/OFF連続テスト終了----")

    def test_set_data_endpoints_single(self):
        print("----データ設定系のエンドポイントのテスト----")
        for endpoint in self.set_data_endpoints:
            print(f"Testing endpoint: {endpoint}", end=" ", flush=True)
            match endpoint:
                case "/set/data/selected_tab_no":
                    data = random.choice(["1", "2", "3"])
                case "/set/data/selected_translation_engines":
                    translation_engines = self.config_dict.get("translation_engines", None)
                    data = {}
                    for i in ["1", "2", "3"]:
                        data[i] = random.choice(translation_engines)
                case "/set/data/selected_your_languages":
                    selectable_language_list = self.config_dict.get("selectable_language_list", None)
                    data = {}
                    for i in ["1", "2", "3"]:
                        data[i] = {}
                        data[i]["1"] = random.choice(selectable_language_list) | {"enable": True}
                case "/set/data/selected_target_languages":
                    selectable_language_list = self.config_dict.get("selectable_language_list", None)
                    data = {}
                    for i in ["1", "2", "3"]:
                        data[i] = {}
                        for j in ["1", "2", "3"]:
                            data[i][j] = random.choice(selectable_language_list) | {"enable": random.choice([True, False])}
                case "/set/data/selected_transcription_engine":
                    transcription_engines = self.config_dict.get("transcription_engines", None)
                    data = random.choice(transcription_engines)
                case "/set/data/transparency":
                    data = random.randint(0, 100)
                case "/set/data/ui_scaling":
                    data = random.randint(50, 200)
                case "/set/data/textbox_ui_scaling":
                    data = random.randint(50, 200)
                case "/set/data/message_box_ratio":
                    data = round(random.uniform(0.1, 0.9), 2)
                case "/set/data/send_message_button_type":
                    data = random.choice(["show", "hide", "show_and_disable_enter_key"])
                case "/set/data/font_family":
                    data = random.choice(["Arial", "Verdana", "Times New Roman"])
                case "/set/data/ui_language":
                    data = random.choice(["en", "ja", "ko", "zh-Hant", "zh-Hans"])
                case "/set/data/main_window_geometry":
                    data = {
                        "x_pos": random.randint(0, 1920),
                        "y_pos": random.randint(0, 1080),
                        "width": random.randint(800, 1920),
                        "height": random.randint(600, 1080)
                    }
                case "/set/data/selected_translation_compute_device":
                    data = random.choice(self.config_dict["translation_compute_device_list"])
                case "/set/data/selected_transcription_compute_device":
                    data = random.choice(self.config_dict["transcription_compute_device_list"])
                case "/set/data/ctranslate2_weight_type":
                    data = random.choice(list(self.config_dict["selectable_ctranslate2_weight_type_dict"].keys()))
                case "/set/data/deepl_auth_key":
                    data = None  # Set to None to avoid using a real key
                case "/set/data/selected_mic_host":
                    data = random.choice(self.config_dict["mic_host_list"])
                case "/set/data/selected_mic_device":
                    data = random.choice(self.config_dict["mic_device_list"])
                case "/set/data/mic_threshold":
                    data = random.randint(0, 100)
                case "/set/data/mic_record_timeout":
                    data = random.randint(1, 3)
                case "/set/data/mic_phrase_timeout":
                    data = random.randint(5, 10)
                case "/set/data/mic_max_phrases":
                    data = random.randint(1, 10)
                case "/set/data/hotkeys":
                    data = {
                        'toggle_vrct_visibility': None,
                        'toggle_translation': None,
                        'toggle_transcription_send': None,
                        'toggle_transcription_receive': None
                    }
                case "/set/data/plugins_status":
                    data = {plugin: random.choice([True, False]) for plugin in self.config_dict.get("plugins", [])}
                case "/set/data/mic_avg_logprob":
                    data = random.uniform(-5, 0)
                case "/set/data/mic_no_speech_prob":
                    data = random.uniform(0, 1)
                case "/set/data/mic_word_filter":
                    data = random.choice(
                        [
                            ["test_0_0", "test_0_1", "test_0_2", None],
                            ["test_1_0", "test_1_1", None],
                            ["test_2_0", None],
                            [None]
                        ]
                    )
                case "/set/data/selected_speaker_device":
                    data = random.choice(self.config_dict["speaker_device_list"])
                case "/set/data/speaker_threshold":
                    data = random.randint(0, 100)
                case "/set/data/speaker_record_timeout":
                    data = random.randint(1, 3)
                case "/set/data/speaker_phrase_timeout":
                    data = random.randint(5, 10)
                case "/set/data/speaker_max_phrases":
                    data = random.randint(1, 10)
                case "/set/data/speaker_avg_logprob":
                    data = random.uniform(-5, 0)
                case "/set/data/speaker_no_speech_prob":
                    data = random.uniform(0, 1)
                case "/set/data/whisper_weight_type":
                    data = random.choice([key for key, value in self.config_dict["selectable_whisper_weight_type_dict"].items() if value is True])
                case "/set/data/overlay_small_log_settings":
                    data = {
                        "x_pos": random.random(),
                        "y_pos": random.random(),
                        "z_pos": random.random(),
                        "x_rotation": random.random(),
                        "y_rotation": random.random(),
                        "z_rotation": random.random(),
                        "display_duration": random.randint(0, 100),
                        "fadeout_duration": random.randint(0, 100),
                        "opacity": random.random(),
                        "ui_scaling": random.random(),
                        "tracker": random.choice(["HMD", "LeftHand", "RightHand"]),
                    }
                case "/set/data/overlay_large_log_settings":
                    data = {
                        "x_pos": random.random(),
                        "y_pos": random.random(),
                        "z_pos": random.random(),
                        "x_rotation": random.random(),
                        "y_rotation": random.random(),
                        "z_rotation": random.random(),
                        "display_duration": random.randint(0, 100),
                        "fadeout_duration": random.randint(0, 100),
                        "opacity": random.random(),
                        "ui_scaling": random.random(),
                        "tracker": random.choice(["HMD", "LeftHand", "RightHand"]),
                    }
                case "/set/data/send_message_format_parts":
                    data = self.config_dict["send_message_format_parts"]
                case "/set/data/received_message_format_parts":
                    data = self.config_dict["received_message_format_parts"]
                case "/set/data/websocket_host":
                    data = "127.0.0.1"
                case "/set/data/websocket_port":
                    data = random.randint(1024, 65535)
                case "/set/data/osc_ip_address":
                    data = "127.0.0.1"
                case "/set/data/osc_port":
                    data = random.randint(1024, 65535)
                case _:
                    data = None

            if data is not None:
                print(f"data: {data}", end=" ", flush=True)
                result, status = self.main.handleRequest(endpoint, data)
                if status == 200:
                    self.config_dict[endpoint.split("/")[-1]] = result
                    print(f"\t -> {Color.GREEN}[PASS]{Color.RESET} Status: {status}, Result: {result}")
                else:
                    print(f"\t -> {Color.RED}[ERROR]{Color.RESET} Status: {status}, Result: {result}")
                    print(f" Current config_dict: {self.config_dict}")
                    break
            else:
                print(f"\t -> {Color.YELLOW}[SKIP]{Color.RESET} No data to set for this endpoint.")
        print("----データ設定系のエンドポイントのテスト終了----")

    def test_run_endpoints_single(self):
        print("----実行系のエンドポイントのテスト----")
        for endpoint, tests in self.run_endpoints.items():
            print(f"Testing endpoint: {endpoint}", end=" ", flush=True)
            match endpoint:
                case "/run/send_message_box":
                    for test in tests:
                        data = test["data"]
                        expected_status = test["status"]
                        result, status = self.main.handleRequest(endpoint, data)
                        if status == expected_status:
                            print(f"\t -> {Color.GREEN}[PASS]{Color.RESET} Status: {status}, Result: {result}")
                        else:
                            print(f"\t -> {Color.RED}[ERROR]{Color.RESET} Status: {status}, Result: {result}")
                            print(f" Current config_dict: {self.config_dict}")
                            break
                case "/run/typing_message_box" | "/run/stop_typing_message_box":
                    for test in tests:
                        data = test["data"]
                        expected_status = test["status"]
                        expected_result = test["result"]
                        result, status = self.main.handleRequest(endpoint, data)
                        if status == expected_status and result == expected_result:
                            print(f"\t -> {Color.GREEN}[PASS]{Color.RESET} Status: {status}, Result: {result}")
                        else:
                            print(f"\t -> {Color.RED}[ERROR]{Color.RESET} Status: {status}, Result: {result}, Expected: {expected_result}")
                            print(f" Current config_dict: {self.config_dict}")
                            break
                case "/run/send_text_overlay":
                    for test in tests:
                        data = test["data"]
                        expected_status = test["status"]
                        expected_result = test["result"]
                        result, status = self.main.handleRequest(endpoint, data)
                        if status == expected_status and result == expected_result:
                            print(f"\t -> {Color.GREEN}[PASS]{Color.RESET} Status: {status}, Result: {result}")
                        else:
                            print(f"\t -> {Color.RED}[ERROR]{Color.RESET} Status: {status}, Result: {result}, Expected: {expected_result}")
                            print(f" Current config_dict: {self.config_dict}")
                            break
                case "/run/swap_your_language_and_target_language":
                    for test in tests:
                        data = test["data"]
                        expected_status = test["status"]
                        result, status = self.main.handleRequest(endpoint, data)
                        if status == expected_status:
                            print(f"\t -> {Color.GREEN}[PASS]{Color.RESET} Status: {status}, Result: {result}")
                        else:
                            print(f"\t -> {Color.RED}[ERROR]{Color.RESET} Status: {status}, Result: {result}")
                            print(f" Current config_dict: {self.config_dict}")
                            break
        print("----実行系のエンドポイントのテスト終了----")

if __name__ == "__main__":
    try:
        test = TestMainloop()
        test.test_endpoints_on_off_single()
        test.test_set_data_endpoints_single()
        test.test_run_endpoints_single()
    except KeyboardInterrupt:
        print("Interrupted by user, shutting down...")
    except Exception as e:
        print(f"An error occurred: {e}")