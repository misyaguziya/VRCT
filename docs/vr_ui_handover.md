# VR UI (OpenVR オーバーレイ) 引き継ぎメモ

- 作成日: 2026-10-01
- ブランチ: `feature/overlay-vr-panel`（最新コミット 79976b3b 時点）
- 対象: 手首のランチャー + ログ / 言語 / VR設定ウィンドウ。VR 内で掴んで動かし、機能の ON/OFF とログ閲覧ができる。

## 1. 構成

```
Tauri (src-tauri/src/lib.rs)
  └─ "VRCT VR Panel" ウィンドウ (画面外 -10000,-10000 / vr.html / src-ui/views/vr/)
        ↑ 状態は VrPanelSyncController.jsx が全 atom を一方向に同期
Python (src-python/models/overlay/)
  ├─ overlay.py        Overlay クラス (1 本の mainloop)
  ├─ window_capture.py ウィンドウ撮影 + マウス入力 (PostMessage)
  └─ overlay_utils.py  行列ユーティリティ
```

- VR 画面は **1 枚の画面外 WebView に全領域を並べて描き、1 回撮影して** `setOverlayTexture` を各オーバーレイ (log / launcher / popup / toolbar) に渡し、`setOverlayTextureBounds` で切り出す。並びは `src-ui/views/vr/vr_layout.json` と `computeVrLayout` (overlay.py)。
- VR ウィンドウは VR UI が **ON の間だけ** 作る（Tauri コマンド `set_vr_panel_window`、`VrPanelSyncController` から呼ぶ）。
- 入力は WebView 内部の `Chrome_RenderWidgetHostHWND` へ PostMessage（OS のカーソルは動かさない）。

## 2. 撮影の流れ（重要）

1. `collectCapture` / `startCapture`（overlay.py）が撮影を頼む。
2. 既定は `window_capture.WindowStream`（Windows.Graphics.Capture、`windows-capture==2.0.1`）。届いた最新の画像を受け取るだけ。
   - 大きさを変えた直後は、画面が変わるまで新しい大きさの画像が届かない（実機で最大 40 秒）。古い大きさの画像しか無い間 (`stale`) は PrintWindow で撮る。
   - `windows-capture` が無い (`stream_missing`) / 始められない・止まった (`stream_unavailable`、次の ON で再試行) 場合も PrintWindow に戻る。
3. PrintWindow は **使い捨てスレッド** (`startCaptureJob` / `runCaptureJob`) で実行する。VRCT の画面が固まると数秒戻らないため、overlay のスレッド（レーザー処理）を止めない。同時に 1 件まで。結果は overlay スレッドの `transferCapture` が処理する（状態を書き換えるのは overlay スレッドだけ）。
4. 画像は BGRA のまま OpenGL テクスチャ（左上に書く）へ → 全オーバーレイに `setOverlayTexture`。

## 3. 実機で確定した罠（必読）

| 罠 | 対処 |
|---|---|
| SteamVR の GL テクスチャは **最初の大きさ固定**。大きさの違うテクスチャを渡すと GL エラー 1281 を残して前の画像を映し続ける | 最大の並び (`MAX_LAYOUT`) が入る大きさで 1 回だけ作り、`setOverlayTextureBounds` で縮める (`newPanelTexture` / `applyLayout`) |
| `setOverlayTexture` 後に GL エラーが残る | `prepareGl` で毎回捨てる |
| GL コンテキスト無しのスレッドで `VR_Shutdown` すると access violation | `teardown()` を overlay スレッドで: destroyOverlays → releaseSession → shutdownPanelTexture |
| `setOverlayRaw` は約 190 回で RequestFailed | テクスチャ経由で渡す |
| `getDeviceToAbsoluteTrackingPose` は None を渡すと None を返す | 配列を自前確保 |
| `PrintWindow` は相手の UI スレッドを待つ | 別スレッド化済み (§2) |
| Windows で `WebviewWindowBuilder.position()` が効かない | 非表示で作り `set_position` 後に `show` |
| `reset.css` が button の text-align を inherit にする | VR のボタンは `display:flex` + 中央寄せを明示 |
| Quest コントローラは本体の -Z が先端より約 37° 上 | レーザーはコントローラ先端 (render model の `tip`) の向きで出す (`tipOffset`)。上下の調整は `_LASER_PITCH_UP_DEG`（現在 12） |
| D3D11 テクスチャへの置換は実機で「後から ON で表示されない・ポインタ追従悪化」 | 撤回済み。`git stash` の「wip: D3D11 overlay texture attempt」に退避。第一容疑は `setOverlayTexture` 後に Flush / GPU コピー完了待ちをしていないこと。OyasumiVR は Query で GPU コピー完了を待ち、描画後 1 秒は毎フレーム `SetOverlayTexture` している |
| develop マージ後にランチャーが真っ黒 | OCR の ON/OFF が `useOcr` → `useMainFunction` (`currentOcrCaptureStatus` / `toggleOcrCapture`) へ移ったため。VrLauncher を差し替え済み |

## 4. 主な機能の挙動

- **ランチャー**: 手首を見たとき表示（45° 固定）。`launcher_auto_hide`、左右の手切り替え。ログボタン長押し（600ms）で見失ったログを目の前へ呼び戻す。
- **掴み移動**: グリップ長押しで掴む。ウィンドウは「目を中心とした球面上で常に頭の方を向く（上は頭の上）」。距離はスティック + 腕の前後（目-手距離の比、`sphereRadius`）。
- **角を掴んで伸ばす (C)**: ログの角を掴んで大きさを変える。放すと `setPanelSize` → 並びを変えて新しい並びで撮れたら表示切り替え。伸ばしている間は枠 (ghost) のみ動く。
- **操作バー**: ログの下。ログを 0.3 秒指すと出て、外れて 2 秒後に消える。出入りは 0.25 秒フェード（`_TOOLBAR_FADE_SEC`）。ログ非表示・VR UI OFF 時は即消す。
- **SteamVR 待機中の OFF**: `start_cancelled` + `start_lock` で起動を取りやめる。`checkSteamvrRunning` は `process_iter(["name"])`。
- **診断ログ**: `overlay: 処理に時間がかかっています`（10 秒ごとの最大 ms）、`処理が止まっています`（2 秒以上同じ段階）、`VR画面の撮影に時間がかかっています/戻りました`、`overlay layout: ...`。段階名は `markStep`（update/grab/grab:ghost/grab:finish_resize/panel:capture/convert/upload/set_texture/sleep/teardown/idle）。

## 5. 依存・ビルド

- `requirements.txt`: `glfw==2.7.0`, `PyOpenGL==3.1.7`（以前は宣言漏れ）, `windows-capture==2.0.1`。
- `windows-capture` は `opencv-python` を要求するため rapidocr と同様 `--no-deps`（`bat/install.bat`、`.venv` / `.venv_cuda` 両方）。
- `spec/backend.spec` / `backend_cuda.spec`: `glfw` フォルダ同梱、hiddenimports に `windows_capture`。
- **配布ビルドで `_internal/glfw/glfw3.dll` と `windows_capture` が入り、VR UI が表示されるかは未確認。**
- リリース系コマンド (`npm run build` 等) は依頼があるまで実行しない。

## 6. テスト・検証

```powershell
.\.venv\Scripts\python.exe -m pytest -q
ruff check --select F,E9 src-python/models/overlay src-python/test/test_overlay_grab_move.py
npm run vite-build
```

- 全体: 1087 件成功 + 既知の 1 件失敗 `test_ui_endpoint_contract::test_every_setting_has_a_get_endpoint`（OCR の UI 対応待ち、本件と無関係）。
- 主なテスト: `test_overlay_grab_move.py`（掴み・レイアウト・撮影 job・WindowStream・操作バー）、`test_overlay_shutdown_timeout.py`（起動取りやめ・停止検知）。
- 実機テスト表（Artifact）: https://claude.ai/artifact/F1gKje1Ned6gb78neUaKqF（53 項目すべて確認済みだが、以降の変更分は未更新）。

### 2026-10-01: VR UI OFF/ON による撮影復旧の確認

- 修正: `setVrPanelEnabled` の要求をキューで所有スレッドへ渡し、OFF→ON で撮影の停止・失敗状態を解除する。旧字幕が ON のため Overlay 全体を再初期化しない場合も、WGC を再接続する。
- 自動テスト: 復旧の回帰テスト 8 件と関連テスト 120 件が成功。対象の Ruff (`F,E9`) と独立レビューも成功。
- 実機: HMD 接続済みの SteamVR と既存 Tauri 開発版（現在の Python ソースを読む dev sidecar）で、旧一行字幕を ON にして検証した。
- 実 WGC を停止し、`stream_unavailable=True` / PrintWindow への移行を確認後、UI の OFF→ON で新しい Tauri ウィンドウと WGC stream を作り、全 4 VR 領域への `setOverlayTexture` が成功した。
- `updatePanel` に 30 周の例外を注入し、実 mainloop の停止処理で `panel_stopped=True` になった後も、UI の OFF→ON で停止状態・エラー数を解除し、WGC と SteamVR への画像転送が復旧した。
- 復旧中も旧字幕 ON、Overlay 所有スレッド、OpenVR 接続・全ハンドル、GL コンテキスト・テクスチャが不変。同じ ON の再同期でも stream を維持した。ログの独立確認済み。
- 検証用の計測・障害注入は一時ディレクトリ内のみ。通常終了で所有スレッドから後片付けし、設定値は検証前と完全一致することを確認した。
- 範囲: 実 Tauri/WebView2 → endpoint → Python → WGC → GL → SteamVR API まで。HMD 内の目視確認、自然発生障害、長期稼働は今回の成功判定に含めない。

## 7. 未解決・次の候補

1. **ログのリサイズ後に PC 全体が数秒重くなり VRChat が止まる件**（要原因特定）。ウィンドウのリサイズ単体では再現せず（`resize_stress.py` 相当の計測で DWM の詰まりなし）、アプリ側の処理（状態送信・再描画・ghost 描画）を疑っている。角を掴んで伸ばしている最中に `grab` が 1.2 秒止まった記録あり（`grab:ghost` / `grab:finish_resize` で切り分ける記録を追加済み）。VRChat が止まった時刻と process.log を突き合わせること。
2. **画面の拡大率 125% / 150% での確認**（`resizeClient` と `WindowStream` の client 範囲の一致は glfw が PMv2 にする前提）。
3. **配布ビルドでの動作確認**（§5）。
4. **Windows 10 での WGC 動作**（`draw_border` / `minimum_update_interval` は Win11 前提の可能性。失敗時は PrintWindow に戻る設計）。
5. **VRCT の画面が固まっている間も WGC の画像が届き続けるか**（未確認）。
6. **VR 内日本語入力**（librime + rime-jaroomaji）: Tapi (BOOTH) の構成を調査済み（librime=BSD-3、jaroomaji の辞書は Mozc BSD-3 / JMdict・KANJIDIC2 CC BY-SA 4.0）。試作は未着手。ダウンロードは試験用の別場所でのみ承認済み。VR 内キーボードの設計は Artifact で提案してから。
7. 詳細設計書 (`src-python/docs/詳細設計書.md`) への VR UI 追記、develop マージ、push。要件メモ: D3D11 を使わないので glfw/PyOpenGL は必要。
8. 旧字幕オーバーレイ（一行/複数行）は legacy として一定期間残す方針。

## 8. 作業ルール（このプロジェクトでユーザーが求めたこと）

- 返答は日本語。`git commit` / `push` は依頼があったときだけ。`AGENTS.md` はコミットしない。
- 新しい依存は事前承認。共有 checkout でビルドせず worktree を使う（別セッションが HEAD を切り替えるため）。
- 稼働中アプリへのライブ接続テストは確認してから。実機・GPU 依存の確認を「通った」と言わない。
- medium 以上の変更（スレッド・公開 API・配布物）は独立レビューを通す。

## 9. VR 設定画面の棚卸し（2026-10-01）

今回の実装変更はカテゴリの並べ替えのみ。不足項目は追加前の候補として整理した。

### カテゴリの順序

- 変更前: デバイス → デザイン → 音声認識 → 翻訳 → VR → その他 → チャット読み取り。
- 変更後: **デバイス → デザイン → 翻訳 → 音声認識 → チャット読み取り → VR → その他**。
- PC 側の `SidebarSection.jsx` と同じ順序。Chat 検出（表示名「チャット読み取り」）は音声認識の直下へ移した。ID・アイコン・翻訳キーは維持。
- 検証: 変更済み JSX を別 worktree に反映して `npm run vite-build` が成功。順序変更と棚卸し一覧の独立レビューは LGTM、`git diff --check` も成功。今回のタブ変更の HMD 内目視確認は未実施。

### 現在 VR 設定にある項目

| カテゴリ | 現在の項目 |
|---|---|
| デバイス | マイクの自動選択・ホスト・機器、スピーカーの自動選択・機器、両方の自動/手動しきい値・音量確認 |
| デザイン | UI 言語 |
| 翻訳 | ダウンロード済み CTranslate2 モデル、一覧を取得できている AI プロバイダーのモデル |
| 音声認識 | Google/Whisper、マイク/スピーカーの記録時間・無音区切り時間・最大語数 |
| チャット読み取り | 読み取り言語、キャプチャ間隔、信頼度下限、最小文字数 |
| VR | 旧一行/複数行字幕 ON/OFF、翻訳のみ表示、VR UI ログの不透明度、ランチャーの左右・自動表示 |
| その他 | VRChat への送信、翻訳のみ送信、受信文送信、通知音、マイクミュート同期、ローマ字/ひらがな変換 |

### 優先して追加する候補

既存の hook / endpoint と Picker・Toggle・Stepper を再利用でき、文字入力を必要としない項目。

| カテゴリ | 不足する設定 | 操作と条件 |
|---|---|---|
| 音声認識 | Whisper モデル | ダウンロード済みモデルだけ Picker で選ぶ。Whisper 選択中のみ表示 |
| 音声認識 | 計算デバイス、計算精度 | CPU/GPU と対応する精度を選ぶ。Whisper 用。デバイス切替中は両方を操作不可にする |
| 翻訳 | 計算デバイス、計算精度 | CTranslate2 用。デバイス一覧の対応精度と既存 PC の送信形式を再利用 |
| デザイン | フォント種類 | インストール済み一覧から選ぶ。`VrApp` にも `FontFamilyController` があり、VR の表示に反映される。PC/VR 共通設定 |
| VR | 旧字幕小・大の追従先、不透明度、表示サイズ | HMD/左手/右手を選び、数値を −/＋ で調整。現設定の「ログ不透明度」は VR UI 用であり旧字幕には効かない |
| VR | 旧字幕小・大の表示時間、フェード時間 | −/＋ で調整。旧字幕ごとの設定オブジェクトの他フィールドを保持 |
| VR | 旧字幕小・大の位置 XYZ、回転 XYZ | −/＋ で調整可能。VR UI 自体の掴み移動とは別。項目数が多いため字幕種別と位置/回転を切り替える構成を検討 |

### 次に追加できる候補

| カテゴリ | 項目 | 操作と条件 |
|---|---|---|
| 音声認識 | マイク/スピーカーの Avg Logprob、No Speech Prob（計 4 項目） | Whisper の誤認識調整。高度な項目としてまとめ、PC と同じ範囲・刻みを利用 |
| 翻訳 | LM Studio / Ollama の接続確認・再接続 | PC で接続先を設定済みならボタンで操作。モデル一覧が空で現 VR のモデル行が隠れる場合の復帰経路にもなる |
| VR | 旧字幕のサンプル表示、初期値復元 | 文字入力なしで配置確認できる。復元は PC と同様に小・大を一括で戻す既存処理。設定変更を伴うことを明示 |
| その他 | メッセージログ自動保存 | ローカル保存の ON/OFF。フォルダーを開く操作は PC 側に残す |
| その他 | 送信/受信書式の原文・翻訳の順序 | それぞれ `translation_first` のみ切り替える。他の書式フィールドは保持。文字列の編集は不要 |
| その他/外部連携 | WebSocket、OBS Browser Source の ON/OFF | 接続先や OBS 登録は PC で済ませる。OBS 有効中は WebSocket の OFF をロックする既存条件を維持 |
| その他/外部連携 | OBS の最大表示件数、表示時間、フェード時間、文字サイズ、縁取り太さ | 数値操作で変更可能。VR 内で配信を使う場合の候補。追加時に範囲・刻みと依存状態を確認 |

### 既に別の VR 画面にある項目

- UI ログの文字サイズ、固定先、ロック、呼び戻しは `VrToolbar` にある。未実装ではなく、設定画面にもまとめるかを検討する項目。
- 翻訳元/先言語、プリセット、翻訳エンジンは `VrLanguageWindow` にある。
- 翻訳・マイク/スピーカーの音声認識・Chat 読み取りの ON/OFF はランチャーにある。
- VR UI 自体の OFF は復帰操作を失うため、VR 設定には置かない。

### 値の選択精度の差

- Chat キャプチャ間隔: PC は 50 ms 刻み、VR は 100 ms 刻み。
- Chat 信頼度: PC は 0.01 刻み、VR は 0.05 刻み。
- 項目は存在するが PC と同じ細かい値を選びにくい。細かい調整が必要なら刻みの統一、または粗い/細かい調整切替を検討する。

### PC 側に残す項目・用途限定の候補

- API キー、任意 URL、単語フィルター、OCR ウィンドウ名、書式の前後文字列: 自由な文字入力が必要。
- モデルのダウンロード、更新・インストール、ホットキー登録、設定フォルダーを開く/URL をコピー: 初期設定や PC 作業向け。
- PC UI 倍率、PC ログ倍率、入力/再送ボタン、透明度、自動入力欄クリア: PC ウィンドウ用。フォント種類と UI 言語は VR にも影響するため、この除外には含めない。
- 音声入力モード: トグルは可能だが、PC アプリへのフォーカスとクリップボード貼り付けが前提。VR UI には入力欄がないため用途限定。
- OSC IP/ポート、WebSocket host/port、OBS port: 接続先の初期設定向け。ポートを −/＋ で任意指定する操作は実用性が低い。
- OBS 文字色/縁取り色: 現 PC UI は HEX 入力。VR に入れるなら色パレットなどの新 UI が必要。
- テレメトリー: トグル自体は追加可能。VR 中の調整用途は低いため後回し。追加する場合は PC と同じ説明・プライバシー参照を付ける。

### 実装時の共通条件と根拠

- 現在の設定値は PC/VR で共通。VR 設定から変更すると PC 側にも反映される。VR 時だけ別の値を保存する方式は今回の棚卸しでは追加しない。
- 設定画面を開くとメイン機能を一時停止する既存動作を維持し、pending、未接続、未ダウンロード、OSC 不可などの条件も PC と同様に扱う。
- 現 VR の AI モデル行は「モデル一覧が空でないこと」で表示を決めており、PC 側の認証・接続状態による操作可否とは条件が違う。モデル選択を追加する際はこの差も確認する。
- 追加候補は既存 `useAppearance` / `useTranscription` / `useTranslation` / `useVr` / `useOthers` / `useAdvancedSettings` / `useLLMConnection` と `ui_config_setter.js` / `mainloop.py` に処理がある。新しい設定キーや公開 endpoint の追加は現時点では不要。
- 主な照合元: `VrSettingsWindow.jsx`、`VrToolbar.jsx`、`VrLanguageWindow.jsx`、PC の `appearance/Appearance.jsx`、`transcription/Transcription.jsx`、`translation/Translation.jsx`、`vr/Vr.jsx`、`others/Others.jsx`、`ocr/Ocr.jsx`、`advanced_settings/AdvancedSettings.jsx`、共通 `ComputeDevice.jsx` / `MessageFormat.jsx`。
