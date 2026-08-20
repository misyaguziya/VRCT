# 実装レビュー結果（develop~20..develop）

- 対象コミット範囲: `develop~20..develop`（マージ済み含む直近 20 コミット）
- 実施日: 2026-08-20
- 実施方法: レイヤー別に 3 サブエージェント（reviewer）を並列実行
  - Python バックエンド (`src-python/`)
  - TypeScript UI (`src-ui/`)
  - Tauri / ビルド (`src-tauri/`, `utils/dev_sidecar/`, `utils/clean.py`, `bat/`)
- 位置付け: ユーザー「大体のバグはなんとかしました」時点での最終確認レビュー

---

## 最優先対応（Critical / High-Critical）

### 1. インストーラで `config.json` が全上書きされる（Tauri C1）※対応済み (2026-08-20)
- 該当: [src-tauri/nsis/template.nsi](../../../src-tauri/nsis/template.nsi), [src-python/config.py](../../../src-python/config.py)
- `.onInstSuccess` が毎回 `{"UI_LANGUAGE": ...}` だけを書き込み、`Section Uninstall` が `config.json` を無条件削除。アップデート／CPU⇄GPU 切替でも setup.exe が走るため、**API キー・翻訳エンジン・音声デバイス設定が全部消えて UI 言語だけ残る**リスクがあった。
- 対応:
  - NSIS `.onInstSuccess`: 既存 `config.json` があれば `nsJSON` で読み込み `UI_LANGUAGE` のみ差し替え、他ユーザー設定を保持。無ければ新規作成。パース失敗時は上書きせず Python の `load_config` に回復を委ねる
  - NSIS `Section Uninstall`: `config.json` / ログ / weights の削除を `$DeleteAppData` チェック時のみに限定
  - `nsJSON.dll` は既に `src-tauri/nsis/plugins/x86-unicode/` に配置済み。追加パッケージ不要
- 検証観点:
  1. 新規インストール: 選択言語で `config.json` が作られる
  2. 上書きインストール（アップデート／エディション切替）: 事前に入れた API キー等が保持され、`UI_LANGUAGE` は新選択で更新される
  3. `config.json` を故意に壊した状態で上書き: 上書きされず、次回起動で Python 側が既定値再構築

### 2. モデル ZIP（〜3.5GB）のハッシュ／署名検証なし（Tauri C2）
- 該当: [src-tauri/nsis/template.nsi:669](../../../src-tauri/nsis/template.nsi)
- Hugging Face 側が差し替えられたら任意コード実行が `$INSTDIR` に展開される。setup.exe の Authenticode 署名は届かない。
- 対応: ビルド時 SHA-256 を埋め込み、NScurl の `/HASH` or `Crypto::HashFile` で照合。

### 3. ダウンロード失敗ステータスを検知せず無限ループ（Tauri C3）
- 該当: [src-tauri/nsis/template.nsi:673-688](../../../src-tauri/nsis/template.nsi)
- `Complete` 以外（Aborted/Failed）でループを抜けず「Downloading...」で固まる。
- 対応: ループ条件を「`Complete` 以外は break」にして `@ERROR@` 判定へ流す。

### 4. StartPythonController の watchdog interval が dev で漏れる（UI C1）
- 該当: [src-ui/views/app/_app_controllers/StartPythonController.jsx:11-29](../../../src-ui/views/app/_app_controllers/StartPythonController.jsx)
- interval id が Promise `then` 内でしか代入されないため、StrictMode 初回 cleanup で常に null。dev で `/run/feed_watchdog` が多重送信。
- 対応: `hasRunRef` は effect 実行時に即セット、interval id を ref に格納、`asyncStartPython()` を await する。

---

## High（バグ源として次に危険）

### Python

#### H-P1: `_AudioDeviceSession._stop` の TypeError リスク
- 該当: [src-python/model.py:374-376](../../../src-python/model.py)
- `BaseEnergyAndAudioRecorder.__init__` は `stop = pause = resume = None` で初期化。`_start` 内で `recordIntoQueue` が例外（`listen_energy_and_audio_in_background` 失敗）を投げると、None のまま `self._recorder` に残る。次に `_stop` が呼ばれると `None()` で `TypeError` になり、途中 abort で `_recorder = None` にも至らず内部状態が partial のまま (features も clear されない・active_device も残る)。
- 対応: `_start` を try/except で括り失敗時に `_recorder = None` にリセット、あるいは `_stop` に `callable(...)` ガード。

#### H-P2: `ActiveEndpointTracker.stop` タイムアウト後の COM apartment 競合
- 該当: [src-python/active_endpoint_tracker.py:160-197](../../../src-python/active_endpoint_tracker.py)
- `stop()` が STOP_JOIN_TIMEOUT (2s) で戻ったあとに tracker スレッドがまだ COM 呼び出しで滞留していると、旧 `_thread` の最終 `CoUninitialize()` タイミングは制御不能。その頃には別スレッドで新 tracker が別 apartment を初期化済み。旧スレッドの COM ポインタ `__del__` が非登録 apartment 上で発火する経路が残る。
- 対応: `stop()` タイムアウト時は新規 tracker の生成を「旧スレッドが実際に死ぬまで」拒否 or 待つフラグを持たせる。少なくとも「stop タイムアウトが起きたら telemetry で観測可能にする」までは追加する。

#### H-P3: `_create_microphone` タイムアウトによる WASAPI ハンドルリーク
- 該当: [src-python/models/transcription/transcription_recorder.py:110-138](../../../src-python/models/transcription/transcription_recorder.py)
- タイムアウト時に daemon スレッドを放置する設計だが、放置された mic-open スレッドが遅れて PyAudio open に成功した場合、その `Microphone` は誰も close しない = WASAPI ハンドルが「アプリ終了まで」占有される。デバイス切替で 8s タイムアウトを何度も踏むと同一デバイスがロックされたままになる。
- 対応: `_run` 成功パスで `done.is_set()` かつ既にタイムアウト経過しているケースを検出したら、その場で `source.__exit__(None,None,None)` してから捨てる。

### Tauri

- **H-T1**: インストール失敗時にゴミが残り uninstaller も未書き込み — [src-tauri/nsis/template.nsi:709-720](../../../src-tauri/nsis/template.nsi)
  - Abort 前に `RMDir /r "$INSTDIR"` と `Delete "$TEMP\$file_name"` を必ず実行。理想は `WriteUninstaller` を先に行い失敗時にサイレント uninstaller を呼ぶ。
- **H-T2**: 成功時に `$TEMP\VRCT[_cuda].zip` を消していない（最大 3.5GB のゴミ）— [src-tauri/nsis/template.nsi:666](../../../src-tauri/nsis/template.nsi)
- **H-T3**: アンインストール時にレジストリキー (`Software\<MANUFACTURER>\<PRODUCTNAME>`) が非対称に残る — [src-tauri/nsis/template.nsi:895](../../../src-tauri/nsis/template.nsi)
- **H-T4**: WebView2 ダウンロード経路にも TLS/ハッシュ検証なし、失敗時の TEMP クリーンアップも無し — [src-tauri/nsis/template.nsi:549-555](../../../src-tauri/nsis/template.nsi)
- **H-T5**: dev-fast `bin/_internal` 空プレースホルダが本番ビルドに混入するリスク — [bat/sidecar_dev.bat:29](../../../bat/sidecar_dev.bat)

### UI

- **H-U1**: `AdvancedSettings.jsx` の 8 個の ObsBrowserSource*Container が丸ごとコピペ — [src-ui/views/app/config_page/setting_section/setting_box/advanced_settings/AdvancedSettings.jsx:616-829](../../../src-ui/views/app/config_page/setting_section/setting_box/advanced_settings/AdvancedSettings.jsx)
  - DRY 違反。共通ラッパを 1 個作れば依存配列問題と空値保存の統一処理も同時に片付く。
- **H-U2**: `useSaveButtonLogic` 入力中に state 更新で入力が消える可能性 — [src-ui/logics/configs/config_page_setter/useSettingsLogics.js:352-356](../../../src-ui/logics/configs/config_page_setter/useSettingsLogics.js)
  - フォーカス中は上書きしないガードを追加。
- **H-U3**: `useEffect` 依存にオブジェクト全体を指定（`{data, state}` の参照が毎回変わり毎レンダー発火）— [AdvancedSettings.jsx:628-632](../../../src-ui/views/app/config_page/setting_section/setting_box/advanced_settings/AdvancedSettings.jsx)
  - 依存を `[obj.data, obj.state]` に明示。
- **H-U4**: `_useBackendErrorHandling` の endpoint 判定が文字列一致で脆い — [src-ui/logics/_useBackendErrorHandling.js:178-190](../../../src-ui/logics/_useBackendErrorHandling.js)
  - 将来 IP 系フィールドが増えるとサイレントに別 setter を叩く。エラー種の細分化を推奨。
- **H-U5**: Clipboard 書き込み失敗が UI に伝わらない — [ActionButton.jsx:70-83](../../../src-ui/views/app/config_page/setting_section/setting_box/_components/action_button/ActionButton.jsx)

---

## Medium（設計・運用面）

### Python
- **M-P1**: `_ensureTranslatorsLoaded` にスレッドロックが無く 2 スレッド目が None を掴む窓 — [translation_translator.py:10-31](../../../src-python/models/translation/translation_translator.py)
- **M-P2**: `model.py` グローバルスコープで `open("a")` する副作用 — [model.py:64-76](../../../src-python/model.py)
  - `Model.init()` へ移動。
- **M-P3**: `endTranscript` が別スレッドの `_transcriber` を上書きし得る（競合）— [model.py:334-343](../../../src-python/model.py)
- **M-P4**: `pauseMic/SpeakerEndpointTracker` の 5s タイムアウト時に telemetry event を残していない — [device_manager.py:466-511](../../../src-python/device_manager.py)
- **M-P5**: monitoring スレッドの Before/After が worker enqueue で非同期化され、コメントの順序保証が実態と乖離 — [controller.py:1307-1320](../../../src-python/controller.py)
- **M-P6**: `WEBSOCKET_HOST=0.0.0.0` で OBS/翻訳結果が LAN に無認証で垂れ流し。UI 警告を推奨 — [obs_browser_source_server.py:319](../../../src-python/models/obs/obs_browser_source_server.py) / [controller.py:3498](../../../src-python/controller.py)

### Tauri
- **M-T1**: dev_sidecar の `SetInformationJobObject` / `AssignProcessToJobObject` 戻り値未確認 — [utils/dev_sidecar/src/main.rs:129-147](../../../utils/dev_sidecar/src/main.rs)
- **M-T2**: dev_sidecar の `.venv` マーカー検索が最大 10 階層ハードコード — [utils/dev_sidecar/src/main.rs:106](../../../utils/dev_sidecar/src/main.rs)
- **M-T3**: dev_sidecar の Windows argv quoting 罠（将来 sidecar 引数追加時のリスク）
- **M-T4**: `NScurl.dll` の上流バージョン・SHA-256・取得元 URL が git に記録されていない
  - `src-tauri/nsis/plugins/README.md` に「NScurl 上流 vX.Y.Z、URL、SHA-256、取得日、更新手順」を記録。ADR 化も検討。
- **M-T5**: `nsisunz::UnzipToStack` の戻り値未確認、部分展開の壊れ方に対応不能 — [src-tauri/nsis/template.nsi:709](../../../src-tauri/nsis/template.nsi)
- **M-T6**: `SetOutPath $INSTDIR` 後にダウンロード失敗すると `$INSTDIR` が新規作成されて空のまま残る — [src-tauri/nsis/template.nsi:632](../../../src-tauri/nsis/template.nsi)

### UI
- **M-U1**: `useMainFunction.toggleFn` の updater と副作用分離のコメント補足 — [useMainFunction.js:43-58](../../../src-ui/logics/main/useMainFunction.js)
- **M-U2**: `ColorEntryWithSaveButton` a11y 不足（aria-haspopup / role="dialog" / focus trap / Tab 抜け時の close 無し）— [ColorEntryWithSaveButton.jsx:271-296](../../../src-ui/views/app/config_page/setting_section/setting_box/_components/color_entry_with_save_button/ColorEntryWithSaveButton.jsx)
- **M-U3**: `ColorEntryWithSaveButton` 無効な HEX でも saveFunction が呼ばれる — [ColorEntryWithSaveButton.jsx:193-196](../../../src-ui/views/app/config_page/setting_section/setting_box/_components/color_entry_with_save_button/ColorEntryWithSaveButton.jsx)
- **M-U4**: OpenAICompatible URL の delete が「OpenAI 固定 URL」にリセット → 意図せず外部 API 呼び出しの懸念 — [Translation.jsx:597-616](../../../src-ui/views/app/config_page/setting_section/setting_box/translation/Translation.jsx)
- **M-U5**: `usePlugins` の Zip Slip 対策が `\` セパレータを見落とす — [usePlugins.js:167-179](../../../src-ui/logics/configs/config_page_setter/plugins/usePlugins.js)
- **M-U6**: `OBS_BROWSER_SOURCE_SERVER_UNAVAILABLE` の hint データ取扱いが曖昧 — [_useBackendErrorHandling.js:317-320](../../../src-ui/logics/_useBackendErrorHandling.js)

---

## Low / Nit

### Python
- **L-P1**: `getTranslationHistory(max_items: int = None)` の型ヒント（`Optional[int]`）— [model.py:842](../../../src-python/model.py)
- **L-P2**: `transcribeAudioQueue` 内の関数スコープ `import torch` と `time.sleep(0.01)` — [transcription_transcriber.py:99,133](../../../src-python/models/transcription/transcription_transcriber.py)
- **L-P3**: `TelemetryState.reset()` が完全 no-op なのに docstring は「実行時リセット」— [state.py:113-116](../../../src-python/models/telemetry/state.py)
- **L-P4**: `_writeStdoutLine` 失敗時に `errorLogging()` → `printLog` → `_writeStdoutLine` の再帰リスク — [utils.py:37-38](../../../src-python/utils.py)
- **L-P5**: `_applyDeviceDiffs` の dict 比較・list 内包の繰り返し（軽微）— [device_manager.py:301-323](../../../src-python/device_manager.py)
- **L-P6**: `Model.ensure_initialized` に lock が無い（複数スレッド初回同時アクセスで二重 init 可能性）— [model.py:499-509](../../../src-python/model.py)

### Tauri
- **L-T1**: `template.nsi` の変数群 `cmder_dl` / `cmder_version` が歴史的名残（意味不明）
- **L-T2**: `NScurl::http /BACKGROUND` と `NScurl::wait` の重複（wait が実質 no-op）
- **L-T3**: `bat/sidecar_dev.bat` の複数 target dir 同期がクロスコンパイル `target\<triple>\...` を網羅していない
- **L-T4**: `utils/clean.py` のエラーハンドリング皆無・型ヒント無し・グローバル副作用
- **L-T5**: dev_sidecar Cargo.toml `strip = true` で .pdb が消える

### UI
- **L-U1**: `useSliderLogic` の `console.error` が毎レンダー吐く可能性 — [useSettingsLogics.js:283-295](../../../src-ui/logics/configs/config_page_setter/useSettingsLogics.js)
- **L-U2**: `useReceiveRoutes` partial 削除で Python 側 route の使われ方要確認 — [useReceiveRoutes.js:41-45](../../../src-ui/logics/useReceiveRoutes.js)
- **L-U3**: `useLanguageSettings` deep spread が浅い層依存で `TypeError` 可能性 — [useLanguageSettings.js:77-127](../../../src-ui/logics/main/useLanguageSettings.js)
- **L-U4**: `ColorEntryWithSaveButton` が `deepl_auth_key.save` の i18n キーを流用 — [ColorEntryWithSaveButton.jsx:293](../../../src-ui/views/app/config_page/setting_section/setting_box/_components/color_entry_with_save_button/ColorEntryWithSaveButton.jsx)
- **L-U5**: `translator_status` から `DeepL` を消したが既存保存済み設定のフォールバック要確認 — [ui_configs.js:82-92](../../../src-ui/logics/ui_configs.js)
- **L-U6**: `ColorEntryWithSaveButton` の `remToPx` が特殊メディアで NaN 化 — [ColorEntryWithSaveButton.jsx:154-157](../../../src-ui/views/app/config_page/setting_section/setting_box/_components/color_entry_with_save_button/ColorEntryWithSaveButton.jsx)
- **L-U7**: `ActionButton` の `!clicked_duration` truthiness チェック — [ActionButton.jsx:77](../../../src-ui/views/app/config_page/setting_section/setting_box/_components/action_button/ActionButton.jsx)

---

## テスト不足（追加推奨）

1. `_AudioDeviceSession._start` の Recorder 例外／`recordIntoQueue` 例外時の内部状態リセット（H-P1 を捕まえる）
2. `_LockedAudioSource.__enter__/__exit__` が `pyaudio_op_lock` を確実に取ること（mock で ok）
3. `_create_microphone` タイムアウト経路（`_MIC_OPEN_TIMEOUT_SEC` 動作とリークスレッドの後始末）
4. `ActiveEndpointTracker.stop` タイムアウト → `start` 再呼び出しでの復帰可否
5. `_ensureTranslatorsLoaded` のスレッド競合（2 スレッド同時呼び出しでの整合）

---

## 総評

- **バックエンド（音声 I/O 領域）**: 直近の反復修正で即クラッシュ・確実な hang 経路は塞がれており、Critical は無し。ただし「発火頻度は低いが分かりづらい」残リスク（`_stop` の TypeError、mic-open タイムアウト時の WASAPI ハンドルリーク、tracker stop タイムアウト後の COM 寿命）が 3 点残っており、CLAUDE.md が警告する反復修正のトリガーになりやすい領域なので、少なくとも **telemetry 計装の追加**を推奨。
- **UI**: 大部分の修正は正しい方向で crash 系は概ね塞がっているが、`StartPythonController` の watchdog interval リーク（dev 限定）と `AdvancedSettings.jsx` の 8 個コピペ（DRY 違反）は要対応。
- **インストーラ（Tauri/NSIS）**: **今回のリリースで最大の懸念**。C1（config.json 上書きで全ユーザー設定消失）は、旧 update.exe 経路では起きなかった問題で、setup.exe に統一した副作用としてアップデート全員に影響する読み。C2/C3（3.5GB 経路のハッシュ検証・失敗検知）と併せて、リリース前に必ず確認と対処を強く推奨。

---

## 推奨着手順

1. **リリース前必須**: Tauri C1 / C2 / C3、UI C1
2. **音声 I/O 領域の telemetry 計装追加** → 実機フィードバックで反復修正の切り分け材料化
3. **Python High 3 件**（`_stop` ガード、tracker stop の観測、mic-open リーク回収）
4. **UI DRY リファクタ**（8 個コピペを共通コンポーネント化） — 副次的に他の指摘も解消
5. **Medium / Low は緊急度に応じて順次**

## 実機検証セット（音声 I/O 領域）

pytest green ≠ 実機動作なので、以下を手動で連続実行して確認する:

- マイク/スピーカー Host 切替 → Transcript ON→OFF→ON
- デバイス抜き差し
- Auto Select ON 中に他アプリで音を鳴らす
