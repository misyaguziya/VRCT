# Clipboard 機能設計書

## 概要
VRCT のクリップボード機能は、VRChat 内でのテキスト送信効率を向上させるため、翻訳結果をクリップボードにコピーし、ペースト機能を提供します。

## 主要機能

### 1. テキストコピー
- 翻訳結果をシステムクリップボードにコピー
- 複数のバックエンド対応（Windows clip、pyperclip、tkinter）
- UTF-16LE BOM 対応でクロスプラットフォーム互換性を確保

### 2. テキストペースト
- `Ctrl+V` による自動ペースト
- VRChat ウィンドウの自動フォーカス
- カウントダウン機能で準備時間を確保

### 3. VR アプリ検出
- OpenVR を用いた VRChat アプリ名の自動検出
- バックグラウンドスレッドによる非同期監視
- SteamVR の起動を待機・検出

## クラス設計

### Clipboard クラス
```python
class Clipboard:
    def __init__(self)
    def enable(self) -> None
    def disable(self) -> None
    def copy(self, message: str) -> bool
    def paste(self, window_name: str|None = None, countdown: int = 0) -> bool
```

#### メンバ変数
- `is_enabled`: クリップボード機能の有効/無効状態
- `app_name`: VRChat アプリケーション名（自動検出）
- `_vr_monitor_thread`: SteamVR 監視スレッド
- `_stop_monitoring`: スレッド停止フラグ

### 主要メソッド

#### `__init__()`
初期化処理：
1. VR 監視スレッドを起動
2. SteamVR の起動を待機（10秒間隔で確認）

#### `enable()`
クリップボード機能を有効化：
1. `is_enabled` フラグを True に設定
2. `_initialize()` を呼び出し VR 監視を再開

#### `disable()`
クリップボード機能を無効化：
1. `is_enabled` フラグを False に設定
2. `_stop_monitoring` フラグを設定しスレッド停止
3. スレッド終了を待機（タイムアウト 1秒）

#### `copy(message: str) -> bool`
**パラメータ：**
- `message`: クリップボードにコピーするテキスト

**戻り値：**
- `True`: コピー成功
- `False`: コピー失敗または無効状態

**動作：**
1. `is_enabled` チェック
2. `copy_to_clipboard()` 関数を呼び出し

#### `paste(window_name: str|None = None, countdown: int = 0) -> bool`
**パラメータ：**
- `window_name`: フォーカス対象ウィンドウ（タイトル部分一致 or プロセス名）
- `countdown`: ペースト前の待機秒数

**戻り値：**
- `True`: ペースト送信成功
- `False`: ペースト失敗または無効状態

**動作：**
1. `is_enabled` チェック
2. `window_name` 未指定時は自動検出した VRChat アプリ名を使用
3. Windows 環境下でウィンドウをフォーカス（以下の順序）
   - ウィンドウタイトルで部分一致検索
   - マッチしない場合、プロセス名で検索
4. ウィンドウフォーカス成功時、`paste_via_pyautogui()` でペースト実行

### 内部メソッド

#### `_initialize()`
VR 監視スレッドの初期化：
1. `_stop_monitoring` を False に設定
2. デーモンスレッドで `_monitor_steamvr()` を起動

#### `_monitor_steamvr()`
バックグラウンドスレッド処理：
1. 10秒間隔で `checkSteamvrRunning()` を確認
2. SteamVR 検出時に `_setup_vr_app_name()` を呼び出し
3. `_stop_monitoring` が True になるまで監視

#### `_setup_vr_app_name()`
OpenVR を用いた VR アプリ名検出：
1. OpenVR 初期化（`VRApplication_Background` モード）
2. すべてのアプリケーション情報を取得
3. `steam.app` で始まるキーを検索し `app_name` に設定
4. 例外発生時は `app_name` を None に設定

## 支援関数

### `checkSteamvrRunning() -> bool`
SteamVR が起動しているかを確認
- プロセス名 `vrmonitor.exe`（Windows）または `vrmonitor`（その他）を検索

### `copy_to_clipboard(text: str) -> bool`
複数バックエンド対応のコピー関数
1. Windows: `clip` コマンド + UTF-16LE BOM
2. 汎用: `pyperclip` ライブラリ
3. フォールバック: `tkinter` 使用

### `paste_via_pyautogui(countdown: int = 0) -> bool`
PyAutoGUI を用いたペースト
- `pyautogui.hotkey('ctrl', 'v')` で Ctrl+V を送信
- カウントダウン実行

### ウィンドウ検索関数（Windows のみ）

#### `find_windows_by_title_substring(substring: str) -> list`
ウィンドウタイトルで部分一致検索

#### `find_windows_by_process_name(proc_name: str) -> list`
プロセス名でウィンドウを検索

#### `focus_window(hwnd) -> bool`
指定ウィンドウをアクティブ化

## 依存ライブラリ

| ライブラリ | 用途 | オプション |
|-----------|------|----------|
| pyautogui | キー入力シミュレーション | 必須（ペースト機能） |
| pyperclip | クリップボード操作 | オプション（フォールバック） |
| tkinter | クリップボード操作 | オプション（フォールバック） |
| openvr | VR アプリ名検出 | 必須 |
| psutil | プロセス検索 | 必須 |

## 動作フロー

### 初期化フロー
```
Clipboard.__init__()
  └─ _initialize()
      └─ スレッド起動: _monitor_steamvr()
          └─ 10秒間隔で SteamVR 監視
             └─ 検出時: _setup_vr_app_name()
                └─ VRChat アプリ名を app_name に設定
```

### コピー・ペーストフロー
```
Model.setCopyToClipboard(text)
  └─ clipboard.copy(text)
     └─ copy_to_clipboard(text)  [成功/失敗]

Model.setPasteFromClipboard()
  └─ clipboard.paste(window_name=self.app_name)
     └─ find_windows_by_title_substring() [Windows]
        or find_windows_by_process_name()
     └─ focus_window(hwnd)
     └─ paste_via_pyautogui(countdown)
```

## 有効/無効制御

### コンフィグ設定
- `config.ENABLE_CLIPBOARD`: True/False でクリップボード機能を制御
- Controller 側で `config.ENABLE_CLIPBOARD` をチェックし、True の場合のみ `setCopyToClipboard()` と `setPasteFromClipboard()` を呼び出し

### 制御メソッド（Clipboard クラス内部）
```python
# 有効化（内部API、通常は使用しない）
clipboard.enable()

# 無効化（内部API、通常は使用しない）
clipboard.disable()
```

**注意**: 現在の実装では、Controller は `clipboard.enable()/disable()` を呼び出さず、`config.ENABLE_CLIPBOARD` フラグのみで制御します。Clipboard インスタンスは常に初期化されており、VR 監視スレッドも稼働し続けます。

### API エンドポイント（Controller）
```
/get/data/clipboard          - 現在の有効/無効状態を取得
/set/enable/clipboard        - config.ENABLE_CLIPBOARD を True に設定
/set/disable/clipboard       - config.ENABLE_CLIPBOARD を False に設定
```

## エラーハンドリング

### 失敗時の動作
- コピー失敗: `False` を返却、リトライなし
- ペースト失敗: `False` を返却、リトライなし
- VR アプリ名検出失敗: `app_name` を None に設定、現在フォーカス中のウィンドウにペースト

### 例外処理
- OpenVR 初期化失敗時は `app_name = None` に設定
- プロセス検索例外も握りつぶし
- ウィンドウフォーカス失敗はログのみ出力

## パフォーマンス考慮

### スレッド設計
- VR 監視スレッドは **デーモンスレッド**（アプリ終了時の強制停止可能）
- 10秒間隔で監視（CPU 負荷最小化）

### クリップボード操作
- コピー・ペースト操作はメインスレッド実行
- ウィンドウフォーカス後に 0.2秒スリープで安定性向上

## セキュリティ・プライバシー

### データ保護
- クリップボードデータは一切ログ出力されない
- VR アプリ名のみ app_name として保持

### OS 依存性
- Windows: `clip` コマンド、ctypes によるウィンドウ制御
- その他 OS: pyperclip/tkinter フォールバック、自動フォーカス機能なし

## 制限事項・既知の問題

1. **非 Windows 環境**
   - ウィンドウフォーカス機能は Windows のみ対応
   - その他 OS では現在フォーカス中のウィンドウにペースト

2. **VRChat アプリ名検出**
   - OpenVR が利用可能で SteamVR が起動している必要がある
   - `steam.app` 接頭辞のアプリのみ認識

3. **PyAutoGUI の制限**
   - キー入力シミュレーションはOS依存
   - 一部アプリケーションではセキュリティ制限により失敗する可能性あり

4. **クリップボードバッファ**
   - Ctrl+V 送信のタイミングはユーザー判断（カウントダウン機能あり）
   - クリップボード内容の永続化はしない

## 参考資料

- [PyAutoGUI 公式ドキュメント](https://pyautogui.readthedocs.io/)
- [OpenVR Python バインディング](https://github.com/ValvePython/openvr)
- [psutil ドキュメント](https://psutil.readthedocs.io/)
