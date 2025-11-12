"""
フロントエンドを模擬したテストクライアント
stdin/stdoutを介してバックエンドと通信し、エンドポイントをテストします。

使用方法:
1. バックエンドを起動: python mainloop.py
2. 別のターミナルでこのスクリプトを実行: python test_client.py
3. エンドポイントとデータを指定してテストを実行
"""
import os
import subprocess
import json
import base64
import sys
import time
import threading
from typing import Optional, Dict, Any

if os.path.exists("config.json"):
    os.remove("config.json")

class Color:
    GREEN = '\033[32m'
    RED = '\033[31m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    CYAN = '\033[36m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

class TestClient:
    def __init__(self):
        """バックエンドプロセスを起動してstdin/stdout通信を確立"""
        print(f"{Color.CYAN}バックエンドプロセスを起動中...{Color.RESET}")
        self.process = subprocess.Popen(
            [sys.executable, 'mainloop.py'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            cwd='.'
        )
        self._watchdog_stop_event = threading.Event()
        self._watchdog_thread: Optional[threading.Thread] = None
        
        # 初期化完了を待つ
        print(f"{Color.CYAN}バックエンドの初期化を待機中...{Color.RESET}")
        self._wait_for_initialization()
        print(f"{Color.GREEN}バックエンド起動完了{Color.RESET}\n")
        
        # 初期化完了後 watchdog 開始
        self._start_watchdog()

    def _wait_for_initialization(self, timeout: Optional[float] = None):
        """バックエンド初期化完了 (/run/initialization_complete) を待機する。

        旧仕様: 60秒で TimeoutError を発生させていた。
        新仕様:
          - timeout が None の場合は無期限待機。
          - 'VRCT_INIT_TIMEOUT' 環境変数が設定されていれば soft timeout 値として使用。
          - soft timeout 経過時は ERROR ではなく WARN を表示し継続待機。
          - 進捗: 30秒ごとに経過時間と最後に受信した endpoint を表示。
          - バックエンドプロセスが終了した場合のみ例外を投げる。
        """
        import os
        env_timeout = os.getenv("VRCT_INIT_TIMEOUT")
        if timeout is None:
            try:
                timeout = float(env_timeout) if env_timeout else None
            except ValueError:
                timeout = None

        start_time = time.time()
        last_progress_endpoint = None
        last_progress_time_log = 0.0

        while True:
            # プロセス終了検知
            if self.process.poll() is not None:
                raise RuntimeError("Backend process terminated during initialization")

            # soft timeout 警告表示
            if timeout is not None and (time.time() - start_time) > timeout:
                # 一度だけ警告を出し timeout を解除（以降は継続待機）
                print(f"{Color.YELLOW}[WARN]{Color.RESET} 初期化が {timeout:.1f} 秒を超過しました。ダウンロード等で長時間かかっています。引き続き待機します。環境変数 VRCT_INIT_TIMEOUT を調整できます。")
                timeout = None  # 解除

            # 30秒ごとの進捗ログ
            now = time.time()
            if now - last_progress_time_log >= 30:
                elapsed = now - start_time
                ep_info = last_progress_endpoint or "(受信なし)"
                print(f"{Color.CYAN}[進捗]{Color.RESET} 初期化経過 {elapsed:.1f} 秒 / 最終 endpoint: {ep_info}")
                last_progress_time_log = now

            line = self.process.stdout.readline()
            if not line:
                # 何も来ていないがプロセスは動作中 -> 継続
                continue

            stripped = line.strip()
            if not stripped:
                continue

            # JSON解析試行
            try:
                response = json.loads(stripped)
                endpoint = response.get("endpoint", "")
                status = response.get("status", 0)
                last_progress_endpoint = endpoint or last_progress_endpoint
                if status == 348:
                    # 348 はログ扱い: 全フィールド展開
                    print(f"{Color.CYAN}  [初期化ログ]{Color.RESET} Status: {status} endpoint:{endpoint or '(none)'}")
                    expanded = json.dumps(response, ensure_ascii=False, indent=2)
                    for line in expanded.split('\n'):
                        print(f"    {line}")
                else:
                    print(f"{Color.CYAN}  [初期化中]{Color.RESET} {endpoint} (Status: {status})")
                if endpoint == "/run/initialization_complete" and status == 200:
                    total_elapsed = time.time() - start_time
                    print(f"{Color.GREEN}  [初期化完了]{Color.RESET} 経過 {total_elapsed:.1f} 秒")
                    return
            except json.JSONDecodeError:
                # ログ行として扱う
                print(f"{Color.CYAN}  [Backend]{Color.RESET} {stripped}")
                continue

    def send_request(self, endpoint: str, data: Optional[Any] = None, timeout: float = 30.0, silent: bool = False) -> Dict[str, Any]:
        """
        エンドポイントにリクエストを送信し、レスポンスを取得
        対応するエンドポイントの応答が返ってくるまで処理を待機します
        
        Args:
            endpoint: テストするエンドポイント (例: "/get/data/version")
            data: 送信するデータ (None, dict, str, int, float, bool, list等)
            timeout: タイムアウト時間(秒)
        
        Returns:
            レスポンスの辞書 {"status": int, "endpoint": str, "result": Any}
        """
        try:
            # プロセスが生きているかチェック
            if self.process.poll() is not None:
                print(f"{Color.RED}[ERROR]{Color.RESET} バックエンドプロセスが終了しています")
                return {"status": 500, "endpoint": endpoint, "result": "Backend process is not running"}
            
            # リクエストの構築
            request = {"endpoint": endpoint}
            
            if data is not None:
                # データをJSON文字列に変換してBase64エンコード
                json_data = json.dumps(data, ensure_ascii=False)
                encoded_data = base64.b64encode(json_data.encode('utf-8')).decode('utf-8')
                request["data"] = encoded_data
            
            # リクエストを送信
            request_json = json.dumps(request, ensure_ascii=False)
            if not silent:
                print(f"{Color.BLUE}[送信]{Color.RESET} {endpoint}")
                if data is not None:
                    print(f"  データ: {data}")
                print("  応答待機中...", flush=True)
            
            try:
                self.process.stdin.write(request_json + '\n')
                self.process.stdin.flush()
            except (OSError, BrokenPipeError) as e:
                print(f"{Color.RED}[ERROR]{Color.RESET} バックエンドプロセスとの通信に失敗: {e}")
                # stderrの内容を確認
                stderr_output = self.process.stderr.read()
                if stderr_output:
                    print(f"{Color.RED}[Backend Error]{Color.RESET}")
                    print(stderr_output)
                return {"status": 500, "endpoint": endpoint, "result": f"Communication error: {e}"}
            
            # 対応するエンドポイントのレスポンスを受信するまで待機
            start_time = time.time()
            while True:
                # タイムアウトチェック
                if time.time() - start_time > timeout:
                    print(f"{Color.RED}[TIMEOUT]{Color.RESET} レスポンスがタイムアウトしました ({timeout}秒)")
                    return {"status": 504, "endpoint": endpoint, "result": f"Timeout after {timeout} seconds"}
                
                # レスポンスを受信
                response_line = self.process.stdout.readline()
                
                if not response_line:
                    # プロセスが終了した可能性
                    if self.process.poll() is not None:
                        return {"status": 500, "endpoint": endpoint, "result": "Backend process terminated"}
                    continue
                
                # JSONとしてパース
                try:
                    response = json.loads(response_line.strip())
                except json.JSONDecodeError:
                    # ログ出力など、JSONでない行を表示
                    print(f"{Color.CYAN}[Backend出力]{Color.RESET} {response_line.strip()}")
                    continue
                
                # レスポンスのエンドポイントが一致するかチェック
                response_endpoint = response.get("endpoint", "")
                if response_endpoint == endpoint:
                    # 対応するレスポンスを受信
                    status = response.get("status", 500)
                    result = response.get("result", None)
                    
                    # ステータスに応じて色分けして表示
                    if not silent:
                        if status == 200:
                            print(f"{Color.GREEN}[受信]{Color.RESET} Status: {status}")
                        elif status == 400:
                            print(f"{Color.YELLOW}[受信]{Color.RESET} Status: {status}")
                        elif status == 348:
                            # 348 = ログ扱い: 中身を全展開
                            print(f"{Color.CYAN}[LOG]{Color.RESET} Status: {status} (endpoint={response_endpoint})")
                        else:
                            print(f"{Color.RED}[受信]{Color.RESET} Status: {status}")
                    
                    # 結果を整形して表示
                    if not silent:
                        # 348 の場合はログとしてフルコンテンツ優先表示
                        if status == 348:
                            print("  ログエントリ全体:")
                            full_str = json.dumps(response, ensure_ascii=False, indent=2)
                            for line in full_str.split('\n'):
                                print(f"    {line}")
                            print()
                        else:
                            print(f"  エンドポイント: {response_endpoint}")
                            print("  結果:")
                            if isinstance(result, (dict, list)):
                                # dict/listの場合はインデント付きで表示
                                result_str = json.dumps(result, ensure_ascii=False, indent=2)
                                for line in result_str.split('\n'):
                                    print(f"    {line}")
                            else:
                                print(f"    {result}")
                            
                            # レスポンス全体も表示
                            print("  完全なレスポンス:")
                            response_str = json.dumps(response, ensure_ascii=False, indent=2)
                            for line in response_str.split('\n'):
                                print(f"    {line}")
                            print()
                    
                    return response
                else:
                    # 別のエンドポイントのレスポンス、またはログメッセージ
                    if not silent:
                        if response_endpoint:
                            print(f"{Color.YELLOW}[他のエンドポイントの応答]{Color.RESET} {response_endpoint}")
                        else:
                            # endpointキーがない場合はログメッセージ
                            print(f"{Color.CYAN}[Backendログ]{Color.RESET}")
                        print(f"  {json.dumps(response, ensure_ascii=False)}")
                    continue
            
        except json.JSONDecodeError as e:
            print(f"{Color.RED}[ERROR]{Color.RESET} JSONデコードエラー: {e}")
            return {"status": 500, "endpoint": endpoint, "result": f"JSON decode error: {e}"}
        except (BrokenPipeError, OSError) as e:
            print(f"{Color.RED}[ERROR]{Color.RESET} プロセス通信エラー: {e}")
            # プロセスの状態を確認
            if self.process.poll() is not None:
                print(f"{Color.RED}[ERROR]{Color.RESET} バックエンドプロセスが終了しています")
                # stderrの内容を表示
                try:
                    stderr_output = self.process.stderr.read()
                    if stderr_output:
                        print(f"{Color.RED}[Backend Error Output]{Color.RESET}")
                        print(stderr_output)
                except Exception:
                    pass
            return {"status": 500, "endpoint": endpoint, "result": f"Process communication error: {e}"}
        except Exception as e:
            print(f"{Color.RED}[ERROR]{Color.RESET} 予期しないエラー: {e}")
            import traceback
            traceback.print_exc()
            return {"status": 500, "endpoint": endpoint, "result": f"Error: {e}"}

    def _start_watchdog(self):
        """watchdog スレッドを開始 (30秒間隔で /run/feed_watchdog 送信)"""
        def _watchdog_loop():
            print(f"{Color.CYAN}[Watchdog]{Color.RESET} 開始 (30秒間隔)")
            while not self._watchdog_stop_event.is_set():
                if self._watchdog_stop_event.wait(timeout=30):
                    break
                if self.process.poll() is None:
                    try:
                        request = {"endpoint": "/run/feed_watchdog"}
                        request_json = json.dumps(request, ensure_ascii=False)
                        self.process.stdin.write(request_json + '\n')
                        self.process.stdin.flush()
                        # レスポンスは受信しない（バックグラウンド送信）
                    except Exception as e:
                        print(f"{Color.YELLOW}[Watchdog]{Color.RESET} 送信エラー: {e}")
                        break
            print(f"{Color.CYAN}[Watchdog]{Color.RESET} 終了")
        
        self._watchdog_thread = threading.Thread(target=_watchdog_loop, daemon=True)
        self._watchdog_thread.start()

    def cleanup(self):
        """バックエンドプロセスを終了"""
        print(f"\n{Color.CYAN}バックエンドプロセスを終了中...{Color.RESET}")
        # watchdog 停止
        if self._watchdog_thread and self._watchdog_thread.is_alive():
            self._watchdog_stop_event.set()
            self._watchdog_thread.join(timeout=2)
        # プロセス終了
        self.process.terminate()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
        print(f"{Color.GREEN}終了完了{Color.RESET}")

def run_example_tests(client: TestClient):
    """サンプルテストの実行"""
    print(f"{Color.BOLD}=== サンプルテスト開始 ==={Color.RESET}\n")
    
    # 1. バージョン情報の取得
    print(f"{Color.BOLD}Test 1: バージョン情報の取得{Color.RESET}")
    client.send_request("/get/data/version")
    
    # 2. 透明度の設定
    print(f"{Color.BOLD}Test 2: 透明度の設定{Color.RESET}")
    client.send_request("/set/data/transparency", 75)
    
    # 3. UI言語の設定
    print(f"{Color.BOLD}Test 3: UI言語の設定{Color.RESET}")
    client.send_request("/set/data/ui_language", "ja")
    
    # 4. 翻訳機能の有効化
    print(f"{Color.BOLD}Test 4: 翻訳機能の有効化{Color.RESET}")
    client.send_request("/set/enable/translation")
    
    # 5. 翻訳機能の無効化
    print(f"{Color.BOLD}Test 5: 翻訳機能の無効化{Color.RESET}")
    client.send_request("/set/disable/translation")
    
    # 6. 無効なエンドポイント
    print(f"{Color.BOLD}Test 6: 無効なエンドポイント{Color.RESET}")
    client.send_request("/invalid/endpoint")
    
    print(f"{Color.BOLD}=== サンプルテスト終了 ==={Color.RESET}\n")

class AutomatedEndpointTester:
    """backend_test.py のロジックを stdin/stdout 通信向けに移植した自動テストクラス

    Args:
        client: TestClient インスタンス
        silent: True の場合詳細ログを抑制
        export_path: テスト結果を JSON に書き出すパス (None なら書き出し無し)
        export_csv: True の場合 CSV も併せて書き出す
    """
    def __init__(self, client: TestClient, silent: bool = False, export_path: Optional[str] = None, export_csv: bool = False):
        self.client = client
        self.silent = silent
        self.export_path = export_path
        self.export_csv = export_csv
        # config 的な値をキャッシュ
        self.cache: Dict[str, Any] = {}
        # エンドポイント分類 (動的取得手段が無いため暫定的にハードコード)
        self.validity_endpoints = [
            "/set/enable/translation",
            "/set/disable/translation",
            "/set/enable/transcription_send",
            "/set/disable/transcription_send",
            "/set/enable/transcription_receive",
            "/set/disable/transcription_receive",
            "/set/enable/websocket_server",
            "/set/disable/websocket_server",
            "/set/enable/convert_message_to_romaji",
            "/set/disable/convert_message_to_romaji",
            "/set/enable/convert_message_to_hiragana",
            "/set/disable/convert_message_to_hiragana",
        ]
        self.set_data_endpoints = [
            "/set/data/selected_tab_no",
            "/set/data/selected_translation_engines",
            "/set/data/selected_your_languages",
            "/set/data/selected_target_languages",
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
            "/set/data/selected_ctranslate2_weight_type",
            "/set/data/selected_plamo_model",
            "/set/data/plamo_auth_key",
            "/set/data/selected_gemini_model",
            "/set/data/gemini_auth_key",
            "/set/data/selected_openai_model",
            "/set/data/openai_auth_key",
            "/set/data/selected_lmstudio_model",
            "/set/data/lmstudio_url",
            "/set/data/selected_ollama_model",
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
            "/set/data/selected_whisper_weight_type",
            "/set/data/overlay_small_log_settings",
            "/set/data/overlay_large_log_settings",
            "/set/data/send_message_format_parts",
            "/set/data/received_message_format_parts",
            "/set/data/websocket_host",
            "/set/data/websocket_port",
            "/set/data/osc_ip_address",
            "/set/data/osc_port",
            "/set/data/selected_translation_compute_type",
            "/set/data/selected_transcription_compute_type",
        ]
        self.run_endpoints = [
            "/run/send_message_box",
            "/run/typing_message_box",
            "/run/stop_typing_message_box",
            "/run/send_text_overlay",
            "/run/swap_your_language_and_target_language",
            "/run/update_software",
            "/run/update_cuda_software",
            "/run/download_ctranslate2_weight",
            "/run/download_whisper_weight",
            "/run/open_filepath_logs",
            "/run/open_filepath_config_file",
            "/run/feed_watchdog",
            "/run/lmstudio_connection",
            "/run/ollama_connection",
        ]
        self.delete_data_endpoints = [
            "/delete/data/deepl_auth_key",
        ]
        self.results: Dict[str, Dict[str, Any]] = {}

    # ---------------------------------- Utility ----------------------------------
    def _record(self, endpoint: str, status: Optional[int], result: Any, expected_status: list[int]):
        self.results[endpoint] = {
            "status": status,
            "result": result,
            "expected_status": expected_status,
            "success": status in expected_status if status is not None else False
        }

    def _get(self, endpoint: str) -> Any:
        """/get/data/* の結果をキャッシュしつつ取得"""
        resp = self.client.send_request(endpoint, silent=self.silent)
        if resp.get("status") == 200:
            self.cache[endpoint.split("/")[-1]] = resp.get("result")
            return resp.get("result")
        return None

    # ---------------------------------- Generators ----------------------------------
    def _gen_set_data(self, endpoint: str):
        expected = [200]
        data = None
        # ほぼ backend_test.py のロジックを踏襲
        if endpoint == "/set/data/selected_tab_no":
            data = sys.modules.get('__random_tab_choices', None) or None  # placeholder for future dynamic
            data = data or "1"
        elif endpoint == "/set/data/selected_translation_engines":
            engines = self._get("/get/data/selectable_translation_engines") or []
            data = {i: (engines and (engines[0] if len(engines) else None)) for i in ["1","2","3"]}
        elif endpoint == "/set/data/selected_your_languages":
            lang_list = self._get("/get/data/selectable_language_list") or []
            if lang_list:
                choice = lang_list[0]
                data = {i: {"1": {**choice, "enable": True}} for i in ["1","2","3"]}
        elif endpoint == "/set/data/selected_target_languages":
            lang_list = self._get("/get/data/selectable_language_list") or []
            if lang_list:
                base = lang_list[0]
                data = {i: {j: {**base, "enable": (j=="1")} for j in ["1","2","3"]} for i in ["1","2","3"]}
        elif endpoint == "/set/data/selected_transcription_engine":
            engines = self._get("/get/data/selectable_transcription_engines") or []
            data = engines[0] if engines else None
        elif endpoint == "/set/data/transparency":
            import random
            data = random.randint(0,100)
        elif endpoint == "/set/data/ui_scaling" or endpoint == "/set/data/textbox_ui_scaling":
            import random
            data = random.randint(50,200)
        elif endpoint == "/set/data/message_box_ratio":
            import random
            data = round(random.uniform(0.1,0.9),2)
        elif endpoint == "/set/data/send_message_button_type":
            import random
            data = random.choice(["show","hide","show_and_disable_enter_key"])
        elif endpoint == "/set/data/font_family":
            import random
            data = random.choice(["Arial","Verdana","Times New Roman"]) 
        elif endpoint == "/set/data/ui_language":
            import random
            data = random.choice(["en","ja","ko","zh-Hant","zh-Hans"]) 
        elif endpoint == "/set/data/main_window_geometry":
            import random
            data = {
                "x_pos": random.randint(0,1920),
                "y_pos": random.randint(0,1080),
                "width": random.randint(800,1920),
                "height": random.randint(600,1080)
            }
        elif endpoint == "/set/data/selected_translation_compute_device":
            lst = self._get("/get/data/selectable_translation_compute_device_list") or []
            import random
            data = random.choice(lst) if lst else None
        elif endpoint == "/set/data/selected_transcription_compute_device":
            lst = self._get("/get/data/selectable_transcription_compute_device_list") or []
            import random
            data = random.choice(lst) if lst else None
        elif endpoint == "/set/data/selected_ctranslate2_weight_type":
            dct = self._get("/get/data/selectable_ctranslate2_weight_type_dict") or {}
            keys = list(dct.keys())
            import random
            data = random.choice(keys) if keys else None
        elif endpoint == "/set/data/selected_plamo_model":
            lst = self._get("/get/data/selectable_plamo_model_list") or []
            import random
            data = random.choice(lst) if lst else None
            expected = [200,400]
        elif endpoint == "/set/data/plamo_auth_key":
            data = "PLAMO_DUMMY_KEY"
            expected = [200,400]
        elif endpoint == "/set/data/selected_gemini_model":
            lst = self._get("/get/data/selectable_gemini_model_list") or []
            import random
            data = random.choice(lst) if lst else None
            expected = [200,400]
        elif endpoint == "/set/data/gemini_auth_key":
            data = "GEMINI_DUMMY_KEY"
            expected = [200,400]
        elif endpoint == "/set/data/selected_openai_model":
            lst = self._get("/get/data/selectable_openai_model_list") or []
            import random
            data = random.choice(lst) if lst else None
            expected = [200,400]
        elif endpoint == "/set/data/openai_auth_key":
            data = "OPENAI_DUMMY_KEY"
            expected = [200,400]
        elif endpoint == "/set/data/selected_lmstudio_model":
            lst = self._get("/get/data/selectable_lmstudio_model_list") or []
            import random
            data = random.choice(lst) if lst else None
            expected = [200,400]
        elif endpoint == "/set/data/lmstudio_url":
            import random
            data = random.choice(["http://localhost:1234/v1","http://127.0.0.1:1234/v1","http://invalid_host:9999/v1"])
            expected=[200,400]
        elif endpoint == "/set/data/selected_ollama_model":
            lst = self._get("/get/data/selectable_ollama_model_list") or []
            import random
            data = random.choice(lst) if lst else None
            expected = [200,400]
        elif endpoint == "/set/data/deepl_auth_key":
            data = "DEEPL_DUMMY_KEY"
            expected=[200,400]
        elif endpoint == "/set/data/selected_mic_host":
            lst = self._get("/get/data/selectable_mic_host_list") or []
            import random
            data = random.choice(lst) if lst else None
        elif endpoint == "/set/data/selected_mic_device":
            lst = self._get("/get/data/selectable_mic_device_list") or []
            import random
            data = random.choice(lst) if lst else None
        elif endpoint == "/set/data/mic_threshold":
            import random
            val = random.randint(-1000,3000)
            data = val
            expected=[200] if 0 <= val <= 2000 else [400]
        elif endpoint == "/set/data/mic_record_timeout":
            import random
            val = random.randint(-1,10)
            phrase = self._get("/get/data/mic_phrase_timeout")
            data = val
            expected=[200] if (phrase is not None and 0 <= val <= phrase) else [400]
        elif endpoint == "/set/data/mic_phrase_timeout":
            import random
            val = random.randint(-1,10)
            record = self._get("/get/data/mic_record_timeout")
            data = val
            expected=[200] if (record is not None and record <= val) else [400]
        elif endpoint == "/set/data/mic_max_phrases":
            import random
            val = random.randint(-1,10)
            data = val
            expected=[200] if val >= 0 else [400]
        elif endpoint == "/set/data/hotkeys":
            data = {'toggle_vrct_visibility': None,'toggle_translation': None,'toggle_transcription_send': None,'toggle_transcription_receive': None}
        elif endpoint == "/set/data/plugins_status":
            plugins = self._get("/get/data/plugins") or []
            import random
            data = {p: random.choice([True,False]) for p in plugins}
        elif endpoint == "/set/data/mic_avg_logprob":
            import random
            data = random.uniform(-5,0)
        elif endpoint == "/set/data/mic_no_speech_prob":
            import random
            data = random.uniform(0,1)
        elif endpoint == "/set/data/mic_word_filter":
            import random
            data = random.choice([["test_0_0","test_0_1","test_0_2",None],["test_1_0","test_1_1",None],["test_2_0",None],[None]])
        elif endpoint == "/set/data/selected_speaker_device":
            lst = self._get("/get/data/selectable_speaker_device_list") or []
            import random
            data = random.choice(lst) if lst else None
        elif endpoint == "/set/data/speaker_threshold":
            import random
            val = random.randint(-1000,5000)
            data = val
            expected=[200] if 0 <= val <= 4000 else [400]
        elif endpoint == "/set/data/speaker_record_timeout":
            import random
            val = random.randint(-1,10)
            phrase = self._get("/get/data/speaker_phrase_timeout")
            data = val
            expected=[200] if (phrase is not None and 0 <= val <= phrase) else [400]
        elif endpoint == "/set/data/speaker_phrase_timeout":
            import random
            val = random.randint(-1,10)
            record = self._get("/get/data/speaker_record_timeout")
            data = val
            expected=[200] if (record is not None and record <= val) else [400]
        elif endpoint == "/set/data/speaker_max_phrases":
            import random
            val = random.randint(-1,10)
            data = val
            expected=[200] if val >= 0 else [400]
        elif endpoint == "/set/data/speaker_avg_logprob":
            import random
            data = random.uniform(-5,0)
        elif endpoint == "/set/data/speaker_no_speech_prob":
            import random
            data = random.uniform(0,1)
        elif endpoint == "/set/data/selected_whisper_weight_type":
            dct = self._get("/get/data/selectable_whisper_weight_type_dict") or {}
            import random
            keys=[k for k,v in dct.items() if v]
            data = random.choice(keys) if keys else None
        elif endpoint == "/set/data/overlay_small_log_settings" or endpoint == "/set/data/overlay_large_log_settings":
            import random
            data = {
                "x_pos": random.random(),
                "y_pos": random.random(),
                "z_pos": random.random(),
                "x_rotation": random.random(),
                "y_rotation": random.random(),
                "z_rotation": random.random(),
                "display_duration": random.randint(0,100),
                "fadeout_duration": random.randint(0,100),
                "opacity": random.random(),
                "ui_scaling": random.random(),
                "tracker": random.choice(["HMD","LeftHand","RightHand"])
            }
        elif endpoint == "/set/data/send_message_format_parts":
            fmt = self._get("/get/data/send_message_format_parts")
            data = fmt
        elif endpoint == "/set/data/received_message_format_parts":
            fmt = self._get("/get/data/received_message_format_parts")
            data = fmt
        elif endpoint == "/set/data/websocket_host":
            import random
            val = random.choice(["127.0.0.1","aaaaadwafasdsd","0210.1564.845.0"])
            data = val
            expected = [200,400] if val=="127.0.0.1" else [400]
        elif endpoint == "/set/data/websocket_port":
            import random
            data = random.randint(1024,65535)
            expected=[200,400]
        elif endpoint == "/set/data/osc_ip_address":
            import random
            val = random.choice(["127.0.0.1","aaaaadwafasdsd","0210.1564.845.0"])
            data = val
            expected = [200] if val=="127.0.0.1" else [400]
        elif endpoint == "/set/data/osc_port":
            import random
            data = random.randint(1024,65535)
        elif endpoint == "/set/data/selected_translation_compute_type":
            device = self.cache.get("selected_translation_compute_device") or self._get("/get/data/selected_translation_compute_device")
            if device and isinstance(device, dict):
                import random
                data = random.choice(device.get("compute_types", [])) if device.get("compute_types") else None
        elif endpoint == "/set/data/selected_transcription_compute_type":
            device = self.cache.get("selected_transcription_compute_device") or self._get("/get/data/selected_transcription_compute_device")
            if device and isinstance(device, dict):
                import random
                data = random.choice(device.get("compute_types", [])) if device.get("compute_types") else None
        return data, expected

    def _gen_run_data(self, endpoint: str):
        expected = [200]
        data = None
        import random
        if endpoint == "/run/send_message_box":
            choices=[{"data":{"id":"000001","message":"test"},"status":[200]},
                     {"data":{"id":"000002","message":"Hello World!"},"status":[200]},
                     {"data":{"id":"000003","message":"こんにちわ 世界！"},"status":[200]},
                     {"data":{"id":"000004","message":"안녕하세요 세계!"},"status":[200]},
                     {"data":{"id":"000005","message":"你好，世界！"},"status":[200]}]
            choice = random.choice(choices)
            data = choice["data"]
            expected = choice["status"]
        elif endpoint in ["/run/typing_message_box","/run/stop_typing_message_box","/run/send_text_overlay","/run/swap_your_language_and_target_language"]:
            data = "test_overlay" if endpoint == "/run/send_text_overlay" else None
        elif endpoint in ["/run/update_software","/run/update_cuda_software","/run/download_ctranslate2_weight","/run/download_whisper_weight","/run/open_filepath_logs","/run/open_filepath_config_file","/run/feed_watchdog"]:
            expected=[401]
        elif endpoint in ["/run/lmstudio_connection","/run/ollama_connection"]:
            expected=[200,400]
        return data, expected

    # ---------------------------------- Tests ----------------------------------
    def test_validity_single(self, endpoint: str):
        expected=[200]
        if endpoint == "/set/enable/websocket_server":
            expected=[200,400]
        resp = self.client.send_request(endpoint)
        status = resp.get("status")
        result = resp.get("result")
        self._record(endpoint, status, result, expected)
        ok = status in expected
        tag = f"{Color.GREEN}PASS{Color.RESET}" if ok else f"{Color.RED}FAIL{Color.RESET}"
        print(f"[Validity] {endpoint} -> {tag} ({status})")
        return ok

    def test_set_data_single(self, endpoint: str):
        data, expected = self._gen_set_data(endpoint)
        if expected == [404]:
            self._record(endpoint, None, None, expected)
            print(f"[SetData] {endpoint} -> {Color.RED}UNKNOWN{Color.RESET}")
            return False
        # data が None でも expected に 400 が含まれていれば送信してテスト
        if data is None and 400 not in expected:
            self._record(endpoint, None, None, expected)
            print(f"[SetData] {endpoint} -> {Color.YELLOW}SKIP(no data){Color.RESET}")
            return True
        resp = self.client.send_request(endpoint, data, silent=self.silent)
        status = resp.get("status")
        result = resp.get("result")
        self._record(endpoint, status, result, expected)
        ok = status in expected
        tag = f"{Color.GREEN}PASS{Color.RESET}" if ok else f"{Color.RED}FAIL{Color.RESET}"
        print(f"[SetData] {endpoint} -> {tag} ({status}) data={data}")
        return ok

    def test_run_single(self, endpoint: str):
        data, expected = self._gen_run_data(endpoint)
        if expected == [401]:
            self._record(endpoint, None, None, expected)
            print(f"[Run] {endpoint} -> {Color.YELLOW}SKIP(401){Color.RESET}")
            return True
        resp = self.client.send_request(endpoint, data, silent=self.silent)
        status = resp.get("status")
        result = resp.get("result")
        self._record(endpoint, status, result, expected)
        ok = status in expected
        tag = f"{Color.GREEN}PASS{Color.RESET}" if ok else f"{Color.RED}FAIL{Color.RESET}"
        print(f"[Run] {endpoint} -> {tag} ({status})")
        return ok

    def test_delete_single(self, endpoint: str):
        expected=[200]
        resp = self.client.send_request(endpoint, silent=self.silent)
        status = resp.get("status")
        result = resp.get("result")
        self._record(endpoint, status, result, expected)
        ok = status in expected
        tag = f"{Color.GREEN}PASS{Color.RESET}" if ok else f"{Color.RED}FAIL{Color.RESET}"
        print(f"[Delete] {endpoint} -> {tag} ({status})")
        return ok

    def run_all(self):
        print(f"{Color.BOLD}=== 有効/無効エンドポイントテスト ==={Color.RESET}")
        for ep in self.validity_endpoints:
            self.test_validity_single(ep)
        print(f"{Color.BOLD}=== データ設定エンドポイントテスト ==={Color.RESET}")
        for ep in self.set_data_endpoints:
            self.test_set_data_single(ep)
        print(f"{Color.BOLD}=== 実行エンドポイントテスト ==={Color.RESET}")
        for ep in self.run_endpoints:
            self.test_run_single(ep)
        print(f"{Color.BOLD}=== 削除エンドポイントテスト ==={Color.RESET}")
        for ep in self.delete_data_endpoints:
            self.test_delete_single(ep)

    def run_random(self, iterations: int = 500):
        import random
        print(f"{Color.BOLD}=== ランダムアクセステスト(iter={iterations}) ==={Color.RESET}")
        groups = ["validity","set","run","delete"]
        for i in range(iterations):
            g = random.choice(groups)
            if g == "validity":
                ep = random.choice(self.validity_endpoints)
                self.test_validity_single(ep)
            elif g == "set":
                ep = random.choice(self.set_data_endpoints)
                self.test_set_data_single(ep)
            elif g == "run":
                ep = random.choice(self.run_endpoints)
                self.test_run_single(ep)
            else:
                ep = random.choice(self.delete_data_endpoints)
                self.test_delete_single(ep)
        # 最後に disable 系を OFF
        for ep in self.validity_endpoints:
            if ep.startswith("/set/disable/"):
                self.client.send_request(ep, silent=True)

    def run_specific_random(self, iterations: int = 200):
        import random
        print(f"{Color.BOLD}=== 特定(osc/websocket)ランダムテスト(iter={iterations}) ==={Color.RESET}")
        set_specific = ["/set/data/osc_ip_address","/set/data/osc_port","/set/data/websocket_host","/set/data/websocket_port"]
        for i in range(iterations):
            ep = random.choice(set_specific)
            self.test_set_data_single(ep)

    def summary(self):
        total = len(self.results)
        passed = sum(1 for r in self.results.values() if r["success"])
        skipped = sum(1 for r in self.results.values() if r["expected_status"] == [401])
        failed = total - passed - skipped
        print(f"\n{Color.BOLD}==== テストサマリー ==== {Color.RESET}")
        print(f"総数: {total} / 成功: {passed} / 失敗: {failed} / スキップ(401): {skipped}")
        if failed:
            print(f"{Color.RED}失敗詳細:{Color.RESET}")
            for ep, r in self.results.items():
                if not r["success"] and r["expected_status"] != [401]:
                    print(f"- {ep} status={r['status']} expected={r['expected_status']} result={r['result']}")
        print(f"{Color.BOLD}======================={Color.RESET}\n")
        # インタラクティブ指定によるエクスポート
        if self.export_path:
            try:
                self.export_results(self.export_path)
                print(f"{Color.GREEN}[EXPORT]{Color.RESET} JSONに書き出しました: {self.export_path}")
                if self.export_csv:
                    csv_path = self._derive_csv_path(self.export_path)
                    self.export_results_csv(csv_path)
                    print(f"{Color.GREEN}[EXPORT]{Color.RESET} CSVに書き出しました: {csv_path}")
            except Exception as e:
                print(f"{Color.RED}[EXPORT ERROR]{Color.RESET} {e}")

    def _derive_csv_path(self, json_path: str) -> str:
        base, ext = os.path.splitext(json_path)
        return base + '.csv'

    def export_results(self, filename: str):
        """結果をJSONファイルへ書き出し"""
        payload = {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "total": len(self.results),
            "results": self.results,
        }
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def export_results_csv(self, filename: str):
        """結果をCSVへ書き出し (簡易)"""
        import csv
        with open(filename, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["endpoint", "status", "expected", "success"])
            for ep, r in self.results.items():
                w.writerow([ep, r.get("status"), ",".join(map(str, r.get("expected_status", []))), r.get("success")])

def run_interactive_mode(client: TestClient):
    """対話モードでテストを実行"""
    print(f"{Color.BOLD}=== 対話モード ==={Color.RESET}")
    print("エンドポイントとデータを指定してテストを実行します。")
    print("終了するには 'quit' または 'exit' と入力してください。\n")
    
    while True:
        try:
            # エンドポイントの入力
            endpoint = input(f"{Color.CYAN}エンドポイントを入力 (例: /get/data/version): {Color.RESET}").strip()
            
            if endpoint.lower() in ['quit', 'exit', 'q']:
                break
            
            if not endpoint:
                print(f"{Color.YELLOW}エンドポイントを入力してください{Color.RESET}\n")
                continue
            
            # データの入力
            data_input = input(f"{Color.CYAN}データを入力 (JSON形式, なければEnter): {Color.RESET}").strip()
            
            data = None
            if data_input:
                try:
                    data = json.loads(data_input)
                except json.JSONDecodeError:
                    print(f"{Color.YELLOW}JSONとしてパースできませんでした。文字列として送信します{Color.RESET}")
                    data = data_input
            
            # リクエスト送信
            client.send_request(endpoint, data)
            
        except KeyboardInterrupt:
            print(f"\n{Color.YELLOW}中断されました{Color.RESET}")
            break
        except Exception as e:
            print(f"{Color.RED}エラー: {e}{Color.RESET}\n")

def main():
    """メイン処理"""
    print(f"{Color.BOLD}{'='*60}{Color.RESET}")
    print(f"{Color.BOLD}  VRCT Backend Test Client{Color.RESET}")
    print(f"{Color.BOLD}{'='*60}{Color.RESET}\n")
    
    client = None
    try:
        # テストクライアントの初期化
        client = TestClient()
        
        # モード選択
        print("モードを選択してください:")
        print("1. サンプルテストを実行")
        print("2. 対話モードで実行")
        print("3. 自動テスト(全)を実行")
        print("4. ランダムアクセステスト")
        print("5. 特定(osc/websocket)ランダムテスト")
        mode = input(f"{Color.CYAN}選択 (1-5): {Color.RESET}").strip()

        # 追加オプション選択
        silent_choice = input(f"{Color.CYAN}詳細ログを抑制しますか? (y/N): {Color.RESET}").strip().lower()
        silent = silent_choice == 'y'
        export_choice = input(f"{Color.CYAN}結果をJSON出力しますか? (y/N): {Color.RESET}").strip().lower()
        export_path = None
        export_csv = False
        if export_choice == 'y':
            default_name = f"test_results_{int(time.time())}.json"
            path_in = input(f"{Color.CYAN}出力ファイル名[{default_name}]: {Color.RESET}").strip()
            export_path = path_in or default_name
            csv_choice = input(f"{Color.CYAN}CSVも出力しますか? (y/N): {Color.RESET}").strip().lower()
            export_csv = csv_choice == 'y'
        
        print()
        
        if mode == "1":
            run_example_tests(client)
        elif mode == "2":
            run_interactive_mode(client)
        elif mode == "3":
            tester = AutomatedEndpointTester(client, silent=silent, export_path=export_path, export_csv=export_csv)
            tester.run_all()
            tester.summary()
        elif mode == "4":
            tester = AutomatedEndpointTester(client, silent=silent, export_path=export_path, export_csv=export_csv)
            tester.run_random()
            tester.summary()
        elif mode == "5":
            tester = AutomatedEndpointTester(client, silent=silent, export_path=export_path, export_csv=export_csv)
            tester.run_specific_random()
            tester.summary()
        else:
            print(f"{Color.YELLOW}無効な選択です。対話モードを開始します。{Color.RESET}\n")
            run_interactive_mode(client)
        
    except KeyboardInterrupt:
        print(f"\n{Color.YELLOW}ユーザーによって中断されました{Color.RESET}")
    except Exception as e:
        print(f"{Color.RED}エラーが発生しました: {e}{Color.RESET}")
        import traceback
        traceback.print_exc()
    finally:
        if client:
            client.cleanup()

if __name__ == "__main__":
    main()
