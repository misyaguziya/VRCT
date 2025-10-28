"""
フロントエンドを模擬したテストクライアント
stdin/stdoutを介してバックエンドと通信し、エンドポイントをテストします。

使用方法:
1. バックエンドを起動: python mainloop.py
2. 別のターミナルでこのスクリプトを実行: python test_client.py
3. エンドポイントとデータを指定してテストを実行
"""

import subprocess
import json
import base64
import sys
import time
from typing import Optional, Dict, Any

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
        
        # 初期化完了を待つ
        print(f"{Color.CYAN}バックエンドの初期化を待機中...{Color.RESET}")
        self._wait_for_initialization()
        print(f"{Color.GREEN}バックエンド起動完了{Color.RESET}\n")

    def _wait_for_initialization(self, timeout: float = 60.0):
        """
        バックエンドの初期化完了を待機
        /run/initialization_complete のレスポンスを受信するまで待つ
        """
        start_time = time.time()
        while True:
            if time.time() - start_time > timeout:
                print(f"{Color.RED}[ERROR]{Color.RESET} 初期化タイムアウト ({timeout}秒)")
                raise TimeoutError(f"Backend initialization timeout after {timeout} seconds")
            
            # stdoutから1行読み込み
            line = self.process.stdout.readline()
            
            if not line:
                # プロセスが終了した場合
                if self.process.poll() is not None:
                    raise RuntimeError("Backend process terminated during initialization")
                continue
            
            # JSON解析を試みる
            try:
                response = json.loads(line.strip())
                endpoint = response.get("endpoint", "")
                status = response.get("status", 0)
                
                # 初期化メッセージを表示
                print(f"{Color.CYAN}  [初期化中]{Color.RESET} {endpoint} (Status: {status})")
                
                # 初期化完了を検出
                if endpoint == "/run/initialization_complete" and status == 200:
                    print(f"{Color.GREEN}  [初期化完了]{Color.RESET}")
                    return
                    
            except json.JSONDecodeError:
                # JSON以外の行（ログなど）を表示
                stripped = line.strip()
                if stripped:
                    print(f"{Color.CYAN}  [Backend]{Color.RESET} {stripped}")
                continue

    def send_request(self, endpoint: str, data: Optional[Any] = None, timeout: float = 30.0) -> Dict[str, Any]:
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
                    if status == 200:
                        print(f"{Color.GREEN}[受信]{Color.RESET} Status: {status}")
                    elif status == 400:
                        print(f"{Color.YELLOW}[受信]{Color.RESET} Status: {status}")
                    else:
                        print(f"{Color.RED}[受信]{Color.RESET} Status: {status}")
                    
                    # 結果を整形して表示
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

    def cleanup(self):
        """バックエンドプロセスを終了"""
        print(f"\n{Color.CYAN}バックエンドプロセスを終了中...{Color.RESET}")
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
        mode = input(f"{Color.CYAN}選択 (1 or 2): {Color.RESET}").strip()
        
        print()
        
        if mode == "1":
            run_example_tests(client)
        elif mode == "2":
            run_interactive_mode(client)
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
