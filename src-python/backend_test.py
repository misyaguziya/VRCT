# 初期化のため、config.jsonの削除
import os
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
                self.config_dict[endpoint.split("/")[-1]], _ = self.main.handleRequest(endpoint, None)
            elif endpoint.startswith("/set/disable/"):
                self.config_dict[endpoint.split("/")[-1]], _ = self.main.handleRequest(endpoint, None)
        print(self.config_dict, flush=True)

        self.validity_endpoints = []
        for endpoint in self.main.mapping.keys():
            if endpoint.startswith("/set/enable/") or endpoint.startswith("/set/disable/"):
                self.validity_endpoints.append(endpoint)

        self.set_data_endpoints = []
        for endpoint in self.main.mapping.keys():
            if endpoint.startswith("/set/data/"):
                self.set_data_endpoints.append(endpoint)

        self.delete_data_endpoints = []
        for endpoint in self.main.mapping.keys():
            if endpoint.startswith("/delete/data/"):
                self.delete_data_endpoints.append(endpoint)

        self.run_endpoints = []
        for endpoint in self.main.mapping.keys():
            if endpoint.startswith("/run/"):
                self.run_endpoints.append(endpoint)

        self.test_results = {}

    def record_test_result(self, endpoint, status, result, expected_status):
        """
        テスト結果を記録する
        :param endpoint: テスト対象のエンドポイント
        :param status: 実際のステータスコード
        :param result: 実際の結果
        :param expected_status: 期待されるステータスコード
        """
        self.test_results[endpoint] = {
            "status": status,
            "result": result,
            "expected_status": expected_status,
            "success": status in expected_status
        }

    def test_endpoints_on_off_single(self, endpoint):
        success = False
        expected_status = [200]
        if endpoint.startswith("/set/enable/"):
            match endpoint:
                case "/set/enable/websocket_server":
                    expected_status = [200, 400]
                case _:
                    pass

            result, status = self.main.handleRequest(endpoint, None)
            if status in expected_status:
                if status == 200:
                    self.config_dict[endpoint.split("/")[-1]] = result
                print(f"-> {Color.GREEN}[PASS]{Color.RESET} endpoint:{endpoint} Status: {status}, Result: {result}")
                success = True
            else:
                print(f"-> {Color.RED}[ERROR]{Color.RESET} endpoint:{endpoint} Status: {status}, Result: {result}")
                print(f"Current config_dict: {self.config_dict}")
        elif endpoint.startswith("/set/disable/"):
            result, status = self.main.handleRequest(endpoint, None)
            if status in expected_status:
                if status == 200:
                    self.config_dict[endpoint.split("/")[-1]] = result
                print(f"-> {Color.GREEN}[PASS]{Color.RESET} endpoint:{endpoint} Status: {status}, Result: {result}")
                success = True
            else:
                print(f"-> {Color.RED}[ERROR]{Color.RESET} endpoint:{endpoint} Status: {status}, Result: {result}")
                print(f"Current config_dict: {self.config_dict}")
        self.record_test_result(endpoint, status, result, expected_status)
        return success

    def test_endpoints_on_off_all(self):
        print("----ON/OFF系のエンドポイントのテスト----")
        for endpoint in self.validity_endpoints:
            print(f"Testing endpoint: {endpoint}", flush=True)
            self.test_endpoints_on_off_single(endpoint)
        print("----ON/OFF系のエンドポイントのテスト終了----")

    def test_endpoints_on_off_random(self):
        print("----ON/OFFでのランダムアクセスのテスト----")
        for i in range(1000):
            endpoint = random.choice(self.validity_endpoints)
            print(f"No.{i:04} Testing endpoint: {endpoint}", flush=True)
            if self.test_endpoints_on_off_single(endpoint) is False:
                break

        # 最後にすべてOFFにして終了
        for endpoint in self.validity_endpoints:
            if endpoint.startswith("/set/disable/"):
                result, status = self.main.handleRequest(endpoint, None)
                time.sleep(0.2)
        print("----ON/OFFでのランダムアクセスのテスト終了----")

    def test_endpoints_on_off_continuous(self):
        print("----ON/OFF連続テスト----")
        endpoints = ["/set/enable/websocket_server", "/set/disable/websocket_server"]
        # endpoints = [
        #     "/set/enable/translation",
        #     "/set/disable/translation",
        #     "/set/enable/transcription_send",
        #     "/set/disable/transcription_send",
        #     "/set/enable/transcription_receive",
        #     "/set/disable/transcription_receive",
        # ]
        for i in range(1000):
            endpoint = random.choice(endpoints)
            print(f"No.{i:04} Testing endpoint: {endpoint}", flush=True)
            if self.test_endpoints_on_off_single(endpoint) is False:
                break

        # 最後にすべてOFFにして終了
        for endpoint in self.validity_endpoints:
            if endpoint.startswith("/set/disable/"):
                result, status = self.main.handleRequest(endpoint, None)
        print("----ON/OFF連続テスト終了----")

    def test_set_data_endpoints_single(self, endpoint):
        success = False
        expected_status = [200]
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
                data = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
                expected_status = [400]
            case "/set/data/selected_mic_host":
                data = random.choice(self.config_dict["mic_host_list"])
            case "/set/data/selected_mic_device":
                data = random.choice(self.config_dict["mic_device_list"])
            case "/set/data/mic_threshold":
                data = random.randint(-1000, 3000)
                if 0 <= data <= 2000:
                    pass
                else:
                    expected_status = [400]
            case "/set/data/mic_record_timeout":
                data = random.randint(-1, 10)
                if 0 <= data <= self.config_dict["mic_phrase_timeout"]:
                    pass
                else:
                    expected_status = [400]
            case "/set/data/mic_phrase_timeout":
                data = random.randint(-1, 10)
                if self.config_dict["mic_record_timeout"] <= data:
                    pass
                else:
                    expected_status = [400]
            case "/set/data/mic_max_phrases":
                data = random.randint(-1, 10)
                if 0 <= data:
                    pass
                else:
                    expected_status = [400]
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
                data = random.randint(-1000, 5000)
                if 0 <= data <= 4000:
                    pass
                else:
                    expected_status = [400]
            case "/set/data/speaker_record_timeout":
                data = random.randint(-1, 10)
                if 0 <= data <= self.config_dict["speaker_phrase_timeout"]:
                    pass
                else:
                    expected_status = [400]
            case "/set/data/speaker_phrase_timeout":
                data = random.randint(-1, 10)
                if self.config_dict["speaker_record_timeout"] <= data:
                    pass
                else:
                    expected_status = [400]
            case "/set/data/speaker_max_phrases":
                data = random.randint(-1, 10)
                if 0 <= data:
                    pass
                else:
                    expected_status = [400]
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
                data = random.choice(["127.0.0.1", "aaaaadwafasdsd", "0210.1564.845.0"])
                if data == "127.0.0.1":
                    expected_status = [200, 400]
                else:
                    expected_status = [400]
            case "/set/data/websocket_port":
                data = random.randint(1024, 65535)
                expected_status = [200, 400]
            case "/set/data/osc_ip_address":
                data = random.choice(["127.0.0.1", "aaaaadwafasdsd", "0210.1564.845.0"])
                if data == "127.0.0.1":
                    pass
                else:
                    expected_status = [400]
            case "/set/data/osc_port":
                data = random.randint(1024, 65535)
            case "/set/data/selected_translation_compute_type":
                data = random.choice(self.config_dict["selected_translation_compute_device"]["compute_types"])
            case "/set/data/selected_transcription_compute_type":
                data = random.choice(self.config_dict["selected_transcription_compute_device"]["compute_types"])
            case _:
                data = None
                expected_status = [404]

        if expected_status == [401]:
            print(f"-> {Color.YELLOW}[SKIP]{Color.RESET} No test available for this endpoint: {endpoint}.")
            self.record_test_result(endpoint, None, None, expected_status)  # テスト結果を記録
            success=True
            return success
        elif expected_status == [404]:
            print(f"-> {Color.RED}[ERROR]{Color.RESET} Unknown endpoint: {endpoint}.")
            self.record_test_result(endpoint, None, None, expected_status)  # テスト結果を記録
            return False

        if data is not None:
            print(f"data: {data}", end=" ", flush=True)
            result, status = self.main.handleRequest(endpoint, data)
            if status in expected_status:
                if status == 200:
                    self.config_dict[endpoint.split("/")[-1]] = result
                print(f"-> {Color.GREEN}[PASS]{Color.RESET} endpoint:{endpoint} Status: {status}, Result: {result}")
                success = True
            else:
                print(f"-> {Color.RED}[ERROR]{Color.RESET} endpoint:{endpoint} Status: {status}, Result: {result}")
                print(f" Current config_dict: {self.config_dict}")
        else:
            print(f"-> {Color.YELLOW}[SKIP]{Color.RESET} No data to set for this endpoint: {endpoint}.")
            success = True
        self.record_test_result(endpoint, status, result if data is not None else None, expected_status)  # テスト結果を記録
        return success

    def test_set_data_endpoints_all(self):
        print("----データ設定系のエンドポイントのテスト----")
        for endpoint in self.set_data_endpoints:
            print(f"Testing endpoint: {endpoint}", end=" ", flush=True)
            self.test_set_data_endpoints_single(endpoint)
        print("----データ設定系のエンドポイントのテスト終了----")

    def test_run_endpoints_single(self, endpoint):
        success = False
        expected_status = [200]
        match endpoint:
            case "/run/send_message_box":
                data_list = [
                    {
                        "data": {"id":"000001", "message":"test"},
                        "status": [200],
                    },
                    {
                        # 英語
                        "data": {"id":"000002", "message":"Hello World!"},
                        "status": [200],
                    },
                    {
                        # 日本語
                        "data": {"id":"000003", "message":"こんにちわ 世界！"},
                        "status": [200],
                    },
                    {
                        # 韓国語
                        "data": {"id":"000004", "message":"안녕하세요 세계!"},
                        "status": [200],
                    },
                    {
                        # 中国語 繁体字
                        "data": {"id":"000005", "message":"你好，世界！"},
                        "status": [200],
                    },
                ]
                choice_data = random.choice(data_list)
                data, expected_status = choice_data["data"], choice_data["status"]
            case "/run/typing_message_box":
                data = None
            case "/run/stop_typing_message_box":
                data = None
            case "/run/send_text_overlay":
                data = "test_overlay"
            case "/run/swap_your_language_and_target_language":
                data = None
            case "/run/update_software":
                data = None
                expected_status = [401] # !!!Cant be tested here!!!
            case "/run/update_cuda_software":
                data = None
                expected_status = [401] # !!!Cant be tested here!!!
            case "/run/download_ctranslate2_weight":
                data_list = random.choice(["small", "large"])
                data = random.choice(data_list)
                expected_status = [401] # !!!Cant be tested here!!!
            case "/run/download_whisper_weight":
                data_list = [
                    "tiny", "base", "small", "medium",
                    "large-v1", "large-v2", "large-v3",
                    "large-v3-turbo-int8", "large-v3-turbo"
                ]
                data = random.choice(data_list)
                expected_status = [401] # !!!Cant be tested here!!!
            case "/run/open_filepath_logs":
                data = None
                expected_status = [401] # !!!Cant be tested here!!!
            case "/run/open_filepath_config_file":
                data = None
                expected_status = [401] # !!!Cant be tested here!!!
            case "/run/feed_watchdog":
                data = None
                expected_status = [401] # !!!Cant be tested here!!!
            case _:
                data = None
                expected_status = [404]
                success = True

        if expected_status == [401]:
            print(f"-> {Color.YELLOW}[SKIP]{Color.RESET} No test available for this endpoint: {endpoint}.")
            self.record_test_result(endpoint, None, None, expected_status)  # テスト結果を記録
            success=True
            return success
        elif expected_status == [404]:
            print(f"-> {Color.RED}[ERROR]{Color.RESET} Unknown endpoint: {endpoint}.")
            self.record_test_result(endpoint, None, None, expected_status)  # テスト結果を記録
            return False

        result, status = self.main.handleRequest(endpoint, data)
        if status in expected_status:
            print(f"-> {Color.GREEN}[PASS]{Color.RESET} endpoint:{endpoint} Status: {status}, Result: {result}")
            success = True
        else:
            print(f"-> {Color.RED}[ERROR]{Color.RESET} endpoint:{endpoint} Status: {status}, Result: {result}")
            print(f"Current config_dict: {self.config_dict}")
        self.record_test_result(endpoint, status, result, expected_status)  # テスト結果を記録
        return success

    def test_run_endpoints_all(self):
        print("----実行系のエンドポイントのテスト----")
        for endpoint in self.run_endpoints:
            print(f"Testing endpoint: {endpoint}", end=" ", flush=True)
            self.test_run_endpoints_single(endpoint)
        print("----実行系のエンドポイントのテスト終了----")

    def test_endpoints_all_random(self):
        print("----すべてのエンドポイントのランダムアクセスのテスト----")
        endpoint_types = [
            "validity",
            "set_data",
            "run",
            "delete",
        ]

        for i in range(10000):
            endpoints_type = random.choice(endpoint_types)
            match endpoints_type:
                case "validity":
                    endpoint = random.choice(self.validity_endpoints)
                    print(f"No.{i:04} Testing endpoint: {endpoint}", flush=True)
                    if self.test_endpoints_on_off_single(endpoint) is False:
                        break
                case "set_data":
                    endpoint = random.choice(self.set_data_endpoints)
                    print(f"No.{i:04} Testing endpoint: {endpoint}", flush=True)
                    if self.test_set_data_endpoints_single(endpoint) is False:
                        break
                case "run":
                    endpoint = random.choice(self.run_endpoints)
                    print(f"No.{i:04} Testing endpoint: {endpoint}", flush=True)
                    if self.test_run_endpoints_single(endpoint) is False:
                        break
                case "delete":
                    endpoint = random.choice(self.delete_data_endpoints)
                    print(f"No.{i:04} Testing endpoint: {endpoint}", flush=True)
                    if self.test_delete_data_endpoints_single(endpoint) is False:
                        break

        # 最後にすべてOFFにして終了
        for endpoint in self.validity_endpoints:
            if endpoint.startswith("/set/disable/"):
                _, _ = self.main.handleRequest(endpoint, None)
        print("----すべてのエンドポイントのランダムアクセスのテスト終了----")

    def test_endpoints_specific_random(self):
        print("----特定のエンドポイントのランダムアクセスのテスト----")

        self.validity_specific_endpoints = [
            "/set/enable/websocket_server",
            "/set/disable/websocket_server",
        ]

        self.set_data_specific_endpoints = [
            "/set/data/ctranslate2_weight_type",
            "/set/data/websocket_host",
            "/set/data/websocket_port",
            "/set/data/osc_ip_address",
            "/set/data/osc_port",
        ]

        self.run_specific_endpoints = []
        self.delete_data_endpoints = []

        endpoint_types = [
            "validity",
            "set_data",
            # "run",
            # "delete",
        ]

        for i in range(1000):
            endpoints_type = random.choice(endpoint_types)
            match endpoints_type:
                case "validity":
                    endpoint = random.choice(self.validity_specific_endpoints)
                    print(f"No.{i:04} Testing endpoint: {endpoint}", flush=True)
                    if self.test_endpoints_on_off_single(endpoint) is False:
                        break
                case "set_data":
                    endpoint = random.choice(self.set_data_specific_endpoints)
                    print(f"No.{i:04} Testing endpoint: {endpoint}", flush=True)
                    if self.test_set_data_endpoints_single(endpoint) is False:
                        break
                case "run":
                    endpoint = random.choice(self.run_specific_endpoints)
                    print(f"No.{i:04} Testing endpoint: {endpoint}", flush=True)
                    if self.test_run_endpoints_single(endpoint) is False:
                        break
                case "delete":
                    endpoint = random.choice(self.delete_data_endpoints)
                    print(f"No.{i:04} Testing endpoint: {endpoint}", flush=True)
                    if self.test_delete_data_endpoints_single(endpoint) is False:
                        break

        # 最後にすべてOFFにして終了
        for endpoint in self.validity_endpoints:
            if endpoint.startswith("/set/disable/"):
                _, _ = self.main.handleRequest(endpoint, None)
        print("----特定のエンドポイントのランダムアクセスのテスト終了----")

    def test_delete_data_endpoints_single(self, endpoint):
        success = False
        expected_status = [200]
        match endpoint:
            case "/delete/data/deepl_auth_key":
                data = None
            case _:
                data = None
                expected_status = [404]
                success = True

        if expected_status == [404]:
            print(f"-> {Color.RED}[ERROR]{Color.RESET} Unknown endpoint: {endpoint}.")
            self.record_test_result(endpoint, None, None, expected_status)  # テスト結果を記録
            return False

        result, status = self.main.handleRequest(endpoint, data)
        if status in expected_status:
            print(f"-> {Color.GREEN}[PASS]{Color.RESET} endpoint:{endpoint} Status: {status}, Result: {result}")
            success = True
        else:
            print(f"-> {Color.RED}[ERROR]{Color.RESET} endpoint:{endpoint} Status: {status}, Result: {result}")
            print(f"Current config_dict: {self.config_dict}")
        self.record_test_result(endpoint, status, result, expected_status)  # テスト結果を記録
        return success

    def test_delete_data_endpoints_all(self):
        print("----データ削除系のエンドポイントのテスト----")
        for endpoint in self.delete_data_endpoints:
            print(f"Testing endpoint: {endpoint}", flush=True)
            self.test_delete_data_endpoints_single(endpoint)
        print("----データ削除系のエンドポイントのテスト終了----")

    def generate_summary(self):
        """
        テスト結果のサマリーを生成して表示する
        """
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result["success"])
        untested_tests = sum(1 for result in self.test_results.values() if result["expected_status"] == [401])
        invalid_tests = sum(1 for result in self.test_results.values() if result["expected_status"] == [404])
        failed_tests = total_tests - passed_tests - untested_tests - invalid_tests

        print("\n---- テスト結果のサマリー ----")
        print(f"総テスト数: {total_tests}")
        print(f"成功したテスト数: {passed_tests}")
        print(f"失敗したテスト数: {failed_tests}")
        print(f"テストをしなかったテスト数: {untested_tests}")
        print(f"無効なテスト数: {invalid_tests}\n")

        if untested_tests > 0:
            print("テストをしなかったテストの詳細:")
            for endpoint, result in self.test_results.items():
                if result["expected_status"] == [401]:
                    print(f"- エンドポイント: {endpoint}")
                    print(f"  ステータス: {result['status']}")
                    print(f"  結果: {result['result']}\n")
        if invalid_tests > 0:
            print("無効なテストの詳細:")
            for endpoint, result in self.test_results.items():
                if result["expected_status"] == [404]:
                    print(f"- エンドポイント: {endpoint}")
                    print(f"  ステータス: {result['status']}")
                    print(f"  結果: {result['result']}\n")
        if failed_tests > 0:
            print("失敗したテストの詳細:")
            for endpoint, result in self.test_results.items():
                if result["success"] != [200]:
                    print(f"- エンドポイント: {endpoint}")
                    print(f"  ステータス: {result['status']} (期待されるステータス: {result['expected_status']})")
                    print(f"  結果: {result['result']}\n")
        print("---- サマリー終了 ----\n")

if __name__ == "__main__":
    import traceback
    try:
        test = TestMainloop()
        # test.test_endpoints_on_off_all()
        # test.test_set_data_endpoints_all()
        # test.test_run_endpoints_all()
        # test.test_delete_data_endpoints_all()
        test.test_endpoints_all_random()
        # test.test_endpoints_on_off_continuous()
        # test.test_endpoints_on_off_random()
        # test.test_endpoints_specific_random()
        test.generate_summary()
    except KeyboardInterrupt:
        print("Interrupted by user, shutting down...")
    except Exception as e:
        traceback.print_exc()
        print(f"An error occurred: {e}")