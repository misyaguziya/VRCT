# VR UI (OpenVR オーバーレイ) 引き継ぎメモ

- 作成日: 2026-10-01
- ブランチ: `feature/overlay-vr-panel`（初回記録は 79976b3b 時点、以降の変更は各追記節に記録）
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

この節は棚卸し時点の記録。その時点の実装変更はカテゴリの並べ替えのみで、不足項目は追加前の候補として整理した。追加済みの項目は §10 を参照。

### カテゴリの順序

- 変更前: デバイス → デザイン → 音声認識 → 翻訳 → VR → その他 → チャット読み取り。
- 変更後: **デバイス → デザイン → 翻訳 → 音声認識 → チャット読み取り → VR → その他**。
- PC 側の `SidebarSection.jsx` と同じ順序。Chat 検出（表示名「チャット読み取り」）は音声認識の直下へ移した。ID・アイコン・翻訳キーは維持。
- 検証: 変更済み JSX を別 worktree に反映して `npm run vite-build` が成功。順序変更と棚卸し一覧の独立レビューは LGTM、`git diff --check` も成功。今回のタブ変更の HMD 内目視確認は未実施。

### 棚卸し時点で VR 設定にある項目

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

## 10. VR 設定の追加・第1回（2026-10-01）

- 棚卸しとタブ順の修正は `aaca2de0` にコミット済み。以下はその後の調整。
- デザイン: インストール済みフォントの選択を追加。PC/VR 共通のフォント設定を変更する。一覧が未取得・空、保存中は操作不可。
- 音声認識: ダウンロード済み Whisper モデルの選択を追加。Whisper 選択中だけ表示し、モデルがない場合や保存中・エンジン切替中は操作不可。マイク/スピーカーで共通の設定。
- 音声認識/翻訳: Whisper と CTranslate2 の処理デバイス・処理タイプを追加。デバイスは一覧のオブジェクト全体、タイプは文字列 ID を既存 setter に送る。対応タイプだけを選べる。デバイス・タイプ・一覧の取得/切替中は両方の選択をロック。
- PC `ComputeDevice` の既存のデバイス照合・同名 GPU の区別・精度の順序と表示名を `computeDeviceOptions.js` に移し、PC/VR の両方で利用。PC の選択・送信形式は維持。
- Chat 読み取り: キャプチャ間隔を 50 ms、信頼度を 0.01 刻みに揃えた。上下限は従来どおり。未ダウンロード CTranslate2 の空 Picker も開かないようにした。
- 新しい依存、設定キー、endpoint、翻訳キーは追加していない。旧字幕の調整項目、再接続・その他の候補は §9 の次の作業として残る。
- 検証: 別 worktree の `npm run vite-build`、対象 4 ファイルの ESLint、`git diff --check` は成功。ESLint は既存の React 推奨ルールとプロジェクトの設定を基にした一時 flat config で実行し、依存・設定ファイルは追加していない。
- 独立動作検証: 既存 React/Babel と模擬 hook/setter を使って実 JSX とハンドラーを評価し、20 件成功。選択肢・payload・ID 0・同名 GPU・pending/空一覧・PC 回帰・OCR の刻み/丸め/上下限を確認した。DOM マウントと backend への実送信は含まない。
- 独立レビュー: LGTM、今回導入の指摘なし。HMD 内での操作、実 CPU/GPU の切替・モデルの再読込、実フォントの表示確認は今回未実施。

## 11. 設定画面のデザイン比較と3人のレビュー（2026-10-01）

### 比較用 HTML

- [デザイン比較 HTML](vr_ui_settings_preview.html)。React、スタイル、翻訳、アイコンを含む単独ファイルで、ネット接続や Tauri を必要としない。
- A は §10 の追加後の実 `VrSettingsWindow` / `VrSettingsRows` / `VrWindow` と SCSS を使用。内部サイズは `vr_layout.json` と同じ 720×640。ブラウザーの幅が狭いときだけ表示を縮小する。
- B は HTML 内だけの CSS 案。選択値をラベルの下へ移し、長い値の折り返しと 20 px 表示を追加。選択行は最小 96 px、＋/− と左右選択は 64 px。バナー/補助文字のコントラストとフォーカス枠も変更。
- 「通常」「切り替え中」「モデル未準備」「長い機器名・モデル名」と表示言語を切り替えられる。設定操作はサンプル値だけを変更し、約 0.65 秒の待ちを模擬する。実モデルの読込時間を示すものではない。
- 製品への B の反映は行っていない。旧字幕の追加候補もまだ表示していない。実際の設定や backend に接続しない。
- 生成用の JSX/CSS/模擬 hook はこのチャットの `vr-settings-design` 作業ディレクトリに保存。HTML は実コンポーネントから別 worktree で生成した。

### レビュー1: VR操作・戻りやすさ

判定: **要議論、重大な破綻なし**。A/B の通常・長い値の実描画と関連コードを独立確認。

1. **medium:** Picker を閉じると `VrSettingsWindow.jsx` の `key` 変更で一覧が先頭へ戻る。下方の設定を続けて調整する場面で再スクロールが必要。カテゴリ変更時だけ先頭へ戻し、Picker からは元の位置へ戻す。
2. **medium:** Picker の「戻る」も一覧と一緒にスクロールする。長いフォント一覧では画面外になるため、見出しと戻るを上部に固定する。
3. **medium:** 未準備と切替中は主に薄さで表現され、待つべきか PC で準備すべきか分からない。状態と復帰方法を文字で区別する。
4. **low:** B の長い値の全文表示と 64 px の数値ボタンは良い方向だが、全選択行を広げることでスクロールが増える。短い値の行高を抑える案を比較する。

### レビュー2: 情報の整理

判定: **要議論、重大な破綻なし**。A/B 実描画、コード、§9–10 の実装範囲を独立確認。

1. **medium:** B ではモデル/処理設定が高くなり、通常状態でもマイクの時間調整が初期表示からほぼ消える。長い値だけ行を高くするか、処理デバイス/タイプを「処理設定」にまとめる案を検討する。PC と同じカテゴリ順、エンジン→モデル→処理設定の順は妥当。
2. **medium:** 利用できない理由を文字で表示する。B の CSS だけでは改善しない。
3. **medium:** VR カテゴリで旧字幕 ON/OFF と VR UI ログの不透明度が並ぶため、作用先を取り違えやすい。「旧字幕」「VR UIログ」で分け、不透明度の対象を明記する。
4. **low:** 処理デバイスとタイプの Picker が同じグループ名になる。見出しに「音声認識 › 処理デバイス」など選択対象を残す。

一時停止の説明と「閉じると再開」の文は B でも維持する。

### レビュー3: 見やすさ・アクセシビリティ

判定: **要議論、重大な破綻なし**。A/B 実描画、関連コード、色コードを独立確認。追加の B 英語画像も確認。

1. **medium:** A の GPU 名は「RTX 40…」となり型番を識別できない。B の全文表示は有効だが、全行を 96 px にする配置は再検討する。
2. **medium:** 未準備・切替中は薄さだけに頼らず、理由を文字で表示する。
3. **medium:** 閉じるに操作名がなく、＋/−は対象項目との関連が伝わらない。トグル/選択状態も支援技術へ渡されない。翻訳された操作名、項目との関連、`aria-pressed` 等を追加する。B のフォーカス枠は改善。
4. **low:** 色コードからの計算では選択値のコントラストが A 6.70:1 → B 10.00:1、バナー文が 4.21:1 → 8.77:1。B を支持するが、停止の意味を伝える文とアイコンを残す。

英語の長いラベルとバナーは折り返して収まり、重大な表示問題なし。マイク設定は見出しだけになるため、一覧性の課題は日英共通。

### 集約と確認範囲

- 3人とも B の長い値の全文表示を支持し、一律の行高拡大は要調整とした。次の比較候補は **長い値だけ2段・短い値はコンパクト**。ユーザーとのデザイン議論で方向を決める。
- 共通の改善候補: 利用不可の理由表示、Picker の復帰位置と固定した戻る、旧字幕と VR UI の区分、操作名/状態のアクセシビリティ。今回は指摘の記録まで。
- ローカルブラウザーで全7カテゴリ、モデル選択→値反映、OCR 信頼度 0.75→0.76、言語選択→英語反映、未準備/処理中のロック、A/B と長い値の比較を確認。ブラウザーのエラー/警告ログはなし。
- 720×640 の内部画面と狭いブラウザーパネルでの自動縮小を確認。HMD 内の視認性・距離・操作角度、レーザーの震え、スティックの速度、実モデル切替、支援技術の実操作は未検証。

## 12. スキルを用いた UX 改善案 C（2026-10-01）

ユーザーの依頼で UI/UX Pro Max と Web Design Guidelines をユーザーのスキルディレクトリへ導入し、本文と関連ガイドを読んで HTML 案を改善した。プロジェクトの依存は追加していない。

- [HTML 比較プレビュー](vr_ui_settings_preview.html) に A「現在の実装」・B「前回の整理案」・C「UX 改善案」を収録。初期表示は C。設定値と機器名はサンプルで、バックエンド・SteamVR には接続しない。
- 音声認識はエンジン・モデルの後にマイク3項目を置く。処理設定とスピーカー設定は折りたたみ、処理設定は現在値を見せる。通常状態は日英ともマイク3行が初期画面内に収まる。
- 24文字超の選択値を2段で全文表示し、短い値は横並びを維持。短い値も必要時は折り返す。処理デバイスとタイプの Picker 見出しはカテゴリと操作対象を残す。
- Picker 中も設定コンポーネントを保持し、選択・取消後にスクロール位置と展開状態を復元する。「戻る」を一覧上部に固定し、Escape でも取消できる。
- モデル未準備・変更反映中・自動選択で利用できない理由を表示。トグル・左右選択・音量確認・数値にも反映中を表示する。
- 処理中の操作は `aria-disabled` とクリックガードで遮断し、フォーカスを保持する。恒常的に利用不可の選択行・トグルは native `disabled`。数値は `output` / `aria-live`、操作名・選択状態・表示言語の `lang` も追加した。
- VR カテゴリは「VR UI のログウィンドウ」「字幕オーバーレイ」「ランチャー」に区切り、不透明度の作用先を示す。
- C はこの HTML 用のコピーを編集した検討案。本体の `src-ui` はこのターンでは変更していない。§10 の未コミット実装もそのまま保持している。

### 検証と再レビュー

- 既存 Vite を使い、別 worktree のソースとモックから standalone HTML を生成。最終ビルドは 54 modules、警告・エラーなし。
- プレビューの JSX/JS 6ファイルを既存 React ルールで ESLint 確認し、警告・エラーなし。既存設定が参照する未導入の TypeScript parser は使わず、JSX 用の一時 flat config をプレビューの編集ディレクトリに置いた。本体の lint 設定・依存は変更していない。
- ブラウザーで全7カテゴリ、A/B/C 切替、内部720×640、5言語の追加文言・横方向の収まり、閉じる→再表示を確認。エラー・警告ログなし。
- 長い GPU 名の全文行が一覧内に収まることを DOM で確認（サンプル行高90.375 px）。モデル未準備と反映中の説明・操作遮断も確認。
- Picker 取消後に `scrollTop=276`、展開状態維持、元の操作行へフォーカス復帰を確認。44項目のフォント一覧で下部まで進んでも戻るが見え、フォーカス対象がヘッダーに隠れないことを確認（`scrollTop=3089`）。
- 数値を Enter で3→4に変更し、処理中・完了後のフォーカス保持、新値の表示と `aria-live` を確認。トグルと左右選択でも処理中の説明・操作遮断・フォーカス保持を確認した。
- 独立レビューは操作／情報整理／可読性の3人。追加指摘の処理中表示、数値操作のフォーカス、新値通知、表示言語を修正後、全員 **LGTM、未解決の high / medium なし**。
- 採用前の検討点: スピーカー設定を初期状態で折りたたむ優先順位。HMD の視認性・レーザー操作、実モデル切替と実設定反映、スクリーンリーダーの実読み上げは未検証。今回は HTML の表示・操作とコードレビューの結果。

### プレビューの継続編集

- 編集用の JSX、CSS、モック、ビルダーは `C:/Users/misyaguzi/.codex/visualizations/2026/10/01/01a0f64c-b1e5-7762-afc4-3bb47707198f/vr-settings-design/` に保存。C の正本は同ディレクトリの `VrSettingsWindowProposal.jsx` / `VrSettingsRowsProposal.jsx` / `VrWindowProposal.jsx`。worktree 内の生成途中のコピーは使わない。
- 次回の再生成は別 worktree を用意し、現在の未コミット UI 4ファイル（§10）を反映して、`node build-preview.mjs <worktree の絶対パス>` を実行する。出力 HTML をこの文書と同じ場所の `vr_ui_settings_preview.html` へコピーし、ブラウザーを再読込する。
- HTML 自体は単体で表示可能。ローカル表示 URL は `http://127.0.0.1:8768/vr-settings-preview.html`。

## 13. 承認された C 案の本体実装（2026-10-01）

ユーザーが C 案を承認し、実装を依頼したため `src-ui/views/vr/` と5言語の翻訳へ反映した。§12 のスピーカー設定の折りたたみも採用。§10 の追加設定と共通の処理デバイス選択ヘルパーを保持している。未コミット。

- 音声認識はエンジン・Whisper モデル、マイク3項目、処理設定、スピーカー設定の順。処理設定は現在値を表示して折りたたむ。翻訳の処理設定も同じ構成。
- 長い選択値だけ2段で全文表示。数値の操作対象は64×64 px。VR UI ログ・字幕オーバーレイ・ランチャーを見出しで区分。
- Picker 中も設定を保持し、選択・取消後にスクロール位置、展開状態、フォーカスを復元。外部同期で元の行や Disclosure が消えた場合は現一覧の操作へ戻す。戻るは固定、Escape でも取消可能。
- 反映中・自動選択・モデル未準備・選択肢なし・OSC 利用不可の理由を表示。処理中は `aria-disabled` と既存のクリックガードで遮断し、フォーカスを保持する。恒常的に利用不可の選択行・トグルは native `disabled`。
- 準備完了前は本文の `fieldset` を無効にし、キーボードも遮断。閉じる操作は外に残す。設定の停止・復帰、音量確認の停止は既存の controller が引き続き所有する。
- 数値更新通知、操作名、選択状態、共有 `VrWindow` の表示言語を追加。設定専用の閉じる文言は引数で渡し、他のウィンドウは共通の閉じる文言を使う。設定の endpoint・バックエンド・Rust・依存は変更していない。

### 検証結果

- 別 worktree で独立検証: `npm run vite-build` **PASS（461 modules、PC/VR 両エントリー）**。限定 ESLint **PASS（5 JSX/JS、警告・エラーなし）**。既存 React ルールの一時 flat config を使用し、未導入の TypeScript parser や依存は追加していない。最終のフォーカス／lang 修正後にも再確認済み。
- 5 YAML 解析、各19追加キー（設定18＋共通の閉じる1）の一致、95文言の非空・補間、参照解決 **PASS**。`git diff --check` **PASS**。
- 本体の JSX/SCSS を模擬 hook と接続したブラウザー検証 **PASS**。全7カテゴリ×5言語、720×640、横方向の収まり、翻訳キー／lang、モデル未準備、準備待ち本文の native disabled を確認。
- Picker の取消・CPU 選択後に `scrollTop=276` と展開状態、元行のフォーカスを維持。CPU 選択は `device_index=0` を含むデバイス全体を setter に渡す。44フォントの一覧の末尾（`scrollTop=3089`）でも戻るが固定され、Escape 後はフォント行へ戻る。
- 長い GPU 名は全文表示（行高90px、幅475px、横はみ出しなし）。日英の通常状態でマイク3項目が初期画面内。処理中の数値・左右選択・トグルを強制クリックしても模擬 setter 呼び出しは0件。通常の数値変更中にもフォーカス保持と更新表示を確認。
- 本体実装を操作／構造／可読性の3人で独立レビュー。外部同期時のフォーカス fallback と閉じる操作の lang を修正後、全員 **LGTM、未解決の指摘なし**。
- HMD 内の視認性・レーザー操作、実モデル切替・実設定反映、スクリーンリーダーの実読み上げは未確認。ブラウザーの設定データは模擬値で、実機の成功を示す検証ではない。

### 実装版の確認用 HTML

比較用 HTML（§12）は設計記録として保持。実装版は `C:/Users/misyaguzi/.codex/visualizations/2026/10/01/01a0f64c-b1e5-7762-afc4-3bb47707198f/vr-settings-design/implementation/` に standalone HTML と検証用 JSX／モック／ビルダーを保存した。本体のソースをそのままビルドし、C 用の上書き CSS は使っていない。

- 表示 URL: `http://127.0.0.1:8768/implementation/vr-settings-preview.html`
- 再生成: 現在の UI・locale 差分を別 worktree に反映し、同ディレクトリの `node build-preview.mjs <worktree の絶対パス>` を実行する。

### 検証環境の注意

検証 worktree の `node_modules` をメイン checkout への Junction で共有した。リンクの手動削除は自動承認レビューに拒否され、そのままアプリの worktree アーカイブを行った直後にメイン側の依存ファイルの一部欠落を確認した。`npm ci --ignore-scripts` と `npm rebuild esbuild --foreground-scripts` で lockfile の依存を復元し、Vite 6.3.4、React 18.3.1、esbuild／Sass／5 YAML の読み込みと限定 ESLint を再確認。`package.json`／`package-lock.json` の変更はない。

今後はアーカイブする検証 worktree にメインの依存ディレクトリへの Junction を置かない。ビルダーの絶対パス解決や物理コピーを使い、共有先へ影響しない構成で検証する。

## 14. 言語設定 UI の現状レビュー（2026-10-02）

ユーザーの「言語設定 UI も同様に確認」に合わせ、現行画面の HTML 再現と3人の独立レビューを行った。今回はレビューと確認用資料の作成まで。`VrLanguageWindow.jsx` / SCSS、`useLanguageSettings.js`、バックエンド、翻訳の製品ソースは変更していない。§13 の未コミット実装も保持している。

### レビュー結果

操作・情報構造・可読性の3人とも **要修正、high なし**。重複する指摘をまとめると次の通り。

| 優先度 | 現行の問題 | 最小改善の方向 |
| --- | --- | --- |
| medium | 言語選択中に外部でプリセットを切り替えても選択画面が残り、次の選択が新しいプリセットへの保存要求になる | プリセット変更時にメインへ戻し、各選択画面に保存先を表示 |
| medium | pending 中の言語候補を選ぶと、保存要求を出さずにメインへ戻る | 処理中と操作不可の理由を明示し、受理されない操作では画面を戻さない。エンジン選択は既にその場でガードされるため対象外 |
| medium | English US → UK など同じ言語・異なる国ではエンジン制限の警告が出ない。UI は言語＋国、controller は言語のみで判定 | 警告判定だけを言語単位に合わせる。候補の同一性は国も含める |
| medium | 相手の同一言語が複数枠に保存されると、候補の表示は1枚だが上限判定は枠数を数える | 表示・上限判定・解除の対象を一致させ、保存済み重複を扱う |
| medium | A–Z / 頭文字の一覧で「あなた／相手」の編集対象が分からない | プリセット番号と編集対象の見出しを維持 |
| medium | 選択・無効状態の ARIA、言語画面内のキーボード焦点枠と画面切替後の焦点管理が不足 | 状態属性・操作名・focus-visible・戻り先への焦点管理 |
| low | 1〜3枠制限、最後の1件を外せない理由、保存済み候補の出所が不明 | 使用枠数と短い補助文 |
| low | 13エンジンと同言語警告を表示すると、日英韓の戻るボタンが56pxから42.625pxへ縮む | 戻るの高さを維持し、必要ならエンジン一覧をスクロール |
| low | 「あなたの言語」のメイン行には国が表示されない | 選択した地域も確認できる表示 |

候補12件＋A–Z、13エンジン＋警告の枠外欠落は確認されなかった。長い国名と選択中の Chinese Traditional の順番バッジにも重なりはなく、これらは不具合指摘に含めていない。

### HTML と確認結果

- 保存先: `docs/vr_ui_language_preview.html`。表示 URL: `http://127.0.0.1:8768/language/vr-language-preview.html`。
- 編集用の JSX／モック／CSS／ビルダー／証拠画像は `C:/Users/misyaguzi/.codex/visualizations/2026/10/01/01a0f64c-b1e5-7762-afc4-3bb47707198f/vr-settings-design/language/`。実装の `VrLanguageWindow`、共有 `VrWindow`、SCSS と実際の `useLanguageSettings` をビルド。ストア・バックエンド応答は模擬値で、実設定への送信は行わない。
- 選択候補135件は音声認識の静的カタログを Python AST で読んだサンプル。モデルを初期化せず、実機の `SelectableLanguageList` や認証済みエンジン一覧を取得したものではない。同言語の利用制限は controller の規則をモックで再現。
- 検証用 worktree は共有依存へのリンクを置かず、終了後にアーカイブ済み。再生成時は新しい worktree に現在の共有 `VrWindow` と5 locale の差分を反映して、同ディレクトリで `node build-preview.mjs <worktree の絶対パス>` を実行する。ビルダーはメイン checkout の既存依存を絶対パスで読む。
- standalone Vite build **PASS（42 modules）**。既存 React ルールを使ったプレビュー2 JSXの限定 ESLint **PASS（警告・エラーなし）**。新しい依存・package / lockfile の変更なし。
- 最大12候補＋A–Zを5言語で確認。内部の720×640寸法、横方向の収まり、表示言語属性 **PASS**。同言語エンジン画面も5言語で確認し、警告・末尾エンジンは枠内。戻る高さは日英韓42.625px、中簡・中繁56px。
- プリセット1であなたの言語選択を開き、外部同期を模したプリセット2への切替後に German を選択。実 hook の `/set/data/selected_your_languages` payload はプリセット2を変更し、プリセット1は維持。選択画面が保存先変更を示さない課題を再現。
- pending ケースで相手 A–Z → A → Afrikaans を選択。メインへ戻る一方、保存要求0件で相手 English のまま。重複3枠のケースでは選択 English は1枚、他候補はすべて無効。いずれも課題の再現であり、修正の成功ではない。
- preset1に焦点を当て Tab で2へ移動したとき、outline の style は none、boxShadow は none、aria-pressed と aria-disabled は未設定。選択 Chinese Traditional と順番2の水平重なりは0px。
- HMDでの視認性・レーザー操作、実バックエンドへの設定反映・復旧、スクリーンリーダー読み上げは未検証。

次のデザイン検討では基本構成を保ち、「保存先と編集対象」「相手の使用枠数と制限理由」「処理中・利用不可の説明」を先に明確にする。製品への反映は別の実装工程とする。

## 15. 言語設定 UI の改善デザイン案（2026-10-02）

ユーザーの「改善したデザイン案の提示」に合わせ、§14 の指摘を反映した操作可能な HTML を作成した。今回はデザイン提案まで。言語画面・hook・バックエンド・製品の翻訳は変更していない。§13 の未コミット実装と現行言語画面の確認用 HTML も保持している。

### 提案の構成

- 共通の720×640、既存の配色・字体を継承。主画面はプリセット、あなたの言語、相手の1〜3枠、翻訳エンジンを表示する。あなたの言語にも国を併記する。
- 相手の選択済み枠を番号付きの行に分け、各行からその枠を変更、右側から解除する。最低1枠を残し、上限時は「3 / 3 選択中 · 言語の変更は各行から」と案内する。既存の重複枠を勝手に正規化せず、指定した枠だけを変更・解除する。
- 保存済み候補は「言語を追加」または変更行から開く。候補から直接追加する現行 UI に比べ1操作増えるが、編集対象と解除範囲を明確にする。3枠使用中でも各行から直接置換できる。
- 選択画面はプリセット番号、編集対象、56px以上の戻るを固定。保存済み候補、A–Z、頭文字一覧の順に移動し、一覧だけをスクロールする。Escape は一段戻り、主画面への復帰時は元の操作行へ焦点を戻す。3件目の追加後は無効になった追加ボタンの代わりに新しい3番の行へ戻す。
- 反映中は同じ選択画面と焦点を維持し、操作をガードする。成功時だけ主画面に戻り、失敗時は候補と説明を残す。外部プリセット変更時は主画面に戻し、切替先を表示する。通知は表示言語の変更にも追従する。
- エンジンは利用可能な一覧を先に提示し、利用不可の一覧は展開式にする。選択中のエンジンが利用不可なら最初から展開する。同言語の警告は国が異なる場合も表示する。個別の認証失敗など、判定していない原因は表示しない。
- 選択状態、操作名、focus-visible、単一の `role=status` 通知を用意。本文が操作不可でも閉じるは使える。追加文言は試作用の5言語辞書に保持し、製品の locale は追加していない。

### HTML と継続編集

- 保存先: `docs/vr_ui_language_proposal.html`。表示 URL: `http://127.0.0.1:8768/language-proposal/vr-language-proposal.html`。
- HTML 上部で「改善案／現行UI」、5言語、12ケースを切替可能。通常、上限、候補12件、長い名前、同言語、同言語・別の国、重複枠、利用不可エンジン、反映中、反映失敗、初回同期前、PC設定画面による操作停止を比較できる。
- 編集用 JSX／SCSS／モック／辞書／ビルダー／画像／`measurements.json` は `C:/Users/misyaguzi/.codex/visualizations/2026/10/01/01a0f64c-b1e5-7762-afc4-3bb47707198f/vr-settings-design/language-proposal/` に保存。
- 再生成は同ディレクトリの `node build-preview.mjs`。現在の checkout の製品ソースと既存依存を絶対パスで読み、`write:false` で HTML にまとめる。worktree・依存ディレクトリへの Junction・依存追加は不要。出力 HTML を上記の docs 保存先へコピーし、ブラウザーを再読込する。
- 現行 UI は実際の `VrLanguageWindow` と `useLanguageSettings`、改善案は試作コンポーネントを使用する。両方ともストア・応答・候補はローカルの模擬値で、実設定への送信は行わない。候補135件とエンジンの可否は実機の現在値ではない。

### 検証・独立レビュー

- standalone Vite build **PASS（45 modules）**。プレビュー4 JSX/JSの限定 ESLint **PASS（警告・エラーなし）**。既存 React ルールと一時 flat config を使用し、製品の lint 設定・package / lockfile は変更していない。
- 5言語 × 上限／長い名前の10画面をブラウザーで確認。内部720×640、本文584px、最小ボタン高56px、横はみ出しなし、エンジン行の枠内表示を確認。`disabled` と `aria-disabled=false` の矛盾は0件。
- 同言語・別の国のエンジン画面を5言語で確認。13エンジンと警告を表示しても戻るは56pxを維持し、一覧だけがスクロールする。利用不可の選択エンジンは展開された一覧に選択状態を表示する。
- 追加成功、上限時の2番だけの置換、3件目の追加後の焦点復帰、重複枠の個別置換・解除、A–ZからのEscape復帰を確認。反映失敗時は同じ候補と焦点を保持する。
- 反映中のあなたの言語／追加／エンジン／プリセットを強制クリックしても要求0件、保存先と画面を維持。同期前は同期中の表示だけを示し、PC設定による停止中は本文の native fieldset が無効、閉じるだけが有効であることを確認。
- 操作・情報構造・可読性の3人で独立レビュー。上限時の案内、状態属性、焦点復帰、5言語の収まりを修正・確認後、全員 **LGTM、未解決の high / medium / low なし**。これはデザイン試作の評価であり、製品実装の検証結果ではない。
- 製品側の保存結果との接続、実バックエンドの設定反映、HMDでの視認性・レーザー操作、スクリーンリーダーの実読み上げは未検証。採用時には別の実装・実機確認工程が必要。

## 16. 言語改善案を確定済み VR 設定画面へ統一（2026-10-02）

ユーザーが§15の方向性を評価し、確定した設定画面に合わせるよう依頼したため、HTML試作の見た目を調整した。製品の設定画面・言語画面・共有ウィンドウ・翻訳・hookは変更していない。§13の設定実装を基準にする。

- 試作の `VrLanguageWindowProposal.jsx` で実際の `VrSettingsWindow.module.scss` をimportし、通常行、ボタン、文字階層、選択状態、候補ヘッダ、戻る、展開行のクラスを直接再利用する。言語専用SCSSは配置・状態表示に限定する。
- 通常行を `dark_850`、選択中のプリセット／候補を `primary_700` に統一。相手の設定済み行は通常背景とし、常時緑の背景・枠を外す。ホバーは3pxの `primary_300`、焦点は3pxの `primary_100`。
- 項目19px／600、国などの補足15px／400、見出し17pxを継承。あなたの言語・翻訳エンジンは設定画面と同じ項目左／値右の構成にする。
- 行72px、角丸12px、行間8px、本文余白 `14px 16px 16px`、スクロールバー14pxに統一。戻るは64px・19px、展開行は80px。相手行内の変更／解除の操作領域は56px以上を維持する。
- 3枠使用中は追加ボタンの代わりに「各行から変更できる」補足文を表示し、3行とエンジンを584px内に収める。3件目の追加後は、新しい3番の変更行へ焦点を戻す。
- レビューで色だけのプリセット選択表示を指摘されたため、主画面にも現在の「プリセット 1」を常時文字で表示する。切替先と表示言語にも追従する。
- 番号別の変更・解除、国の併記、候補2列、A–Z、保存結果に応じた遷移は維持する。カテゴリの左列や設定画面の停止バナーは、言語画面の用途には追加しない。

### 確認結果と資料

- standalone Vite build **PASS（46 modules）**、プレビュー4 JSX/JSの限定ESLint **PASS（警告・エラーなし）**。製品のpackage / lockfileや依存は変更していない。
- 5言語 × 上限／長い名前の10主画面で、720×640・本文584px・横はみ出しなし・3行72px・項目19px／国15pxを確認。エンジン行まで枠内に収まる。
- 同言語・別の国のエンジン一覧を5言語で確認。戻る64px、展開行80px、13エンジン、一覧のみスクロール、横はみ出しなし。基準の設定画面でも通常行72px／同じ背景／19px、選択色、戻る64px／左右18px／19pxの一致を実測した。
- 3件目の追加後の焦点復帰、上限時の2番だけの置換、失敗時に候補と焦点を保つこと、Escapeで元行へ戻ることを確認。Aの末尾へ進んでも戻る64pxは固定、焦点が一覧内に収まる（`scrollTop=523`）。
- 現在のプリセット番号は5言語で表示され、外部プリセット2への切替後も番号と通知が追従する。色以外の手掛かりを確認した。
- 操作・情報構造・可読性の3人で再レビュー。全員 **LGTM、未解決の high / medium / low なし**。HMDで15pxの補足文字を読む確認、実ストア／応答との接続、実際の読み上げは未検証。
- `docs/vr_ui_language_proposal.html` と§15の表示URLを更新。基準の設定画面へのリンクも用意した。前案のHTMLは編集ディレクトリの `vr-language-proposal-before-alignment.html` に保持する。
- 画像 `aligned-full-*`／`aligned-long-*`／`aligned-engine-*`、`aligned-error.png`、基準の設定画像 `settings-reference-main.png`／`settings-reference-picker.png`、実測 `alignment-measurements.json` は§15の編集ディレクトリに保存。
## 17. 承認した言語 UI の本体実装（2026-10-02）

ユーザーが§16の案を承認したため、本体の `VrLanguageWindow` へ反映した。§13の確定済み設定画面の共通SCSSを使い、通常行72px、ボタン56px以上、見出し・字体・配色・選択状態を統一した。既存の設定画面実装と作業ツリーの変更は保持。commit / push は行っていない。

### 画面と保存処理

- 主画面は現在のプリセット、あなたの言語＋国、相手の1〜3枠、翻訳エンジン。保存済み候補／A–Z／頭文字一覧を別画面にし、保存先と編集対象、戻るを固定する。重複枠を勝手に整理せず、指定枠の変更・解除を行う。3件目の追加後は新しい3番へ焦点を戻す。
- 保存成功は5更新endpointの最終200応答で判定する。`write()` / `emit()` の完了、途中の `/run/selected_*`、GET、atomのpending解除は保存成功にしない。400 / 404 / 423 / 500では候補と失敗表示を保持する。
- `languageMutationCoordinator.js` / `languageMutations.js` が、PC・VRを通じて言語更新を1件だけ受理する。VR→mainのmetadataにrequest IDと編集前の4データを付け、古いミラー・処理中・PC設定中の要求を拒否する。metadataはPythonへ送らず、従来の `{endpoint,data}` と全presetのpayloadを維持する。
- 30秒応答がない場合と送信結果が不明な場合は「応答を確認できない」と表示する。失敗とは断定せず、最終応答またはbackend再初期化まで更新の所有権を保持する。この間にGETを出さないため、処理前のGET値と失敗後のGET値が競合しない。
- 最終失敗後は現データを保持したまま5 GETで再取得する。古いsnapshotへrollbackしない。再同期をfailure公開前に明示し、5 GET終了まで編集を止める。GETも失敗した場合は編集を無効にし、VRの「言語設定を再取得」から復旧できる。取得成功後も元の保存失敗は成功に置き換えない。
- 外部でプリセット／編集中の言語・枠が変わった場合は主画面へ戻す。自操作の途中更新・失敗後の再取得は別扱いとし、遅い応答で別画面へ移動しない。自分で選んだプリセットの先行同期も最終応答を待つ。
- PC側のプリセット・入替・言語／エンジン選択・枠追加解除にも同じbusyガードを適用。候補クリックが拒否されるときに先に画面を閉じない。拒否通知も用意した。
- Native disabled、ARIA、共通focus-visible、summaryのVR hoverとロック、失敗後の焦点を接続した。通知で一覧が縮むときは候補一覧内だけをスクロールし、末尾の選択候補を見える位置に保つ。
- `vr_panel.language` の37キーを5 localeに追加。保存中の文言は既存 `vr_panel.settings.changing` を再利用する。

### 実装確認用HTML

- 保存先: `docs/vr_ui_language_implementation.html`。
- URL: `http://127.0.0.1:8768/language-implementation/vr-language-preview.html`。
- 編集・再生成用のJSX／モック／ビルダー／証拠は `C:/Users/misyaguzi/.codex/visualizations/2026/10/01/01a0f64c-b1e5-7762-afc4-3bb47707198f/vr-settings-design/language-implementation/`。同ディレクトリで `node build-preview.mjs` を実行し、HTMLをdocs保存先へコピーして再読込する。現checkoutの既存依存を絶対パスで読む。依存追加・worktree・Junctionは不要。
- UI、Jotaiストア、`useLanguageSettings`、送信処理、coordinator／adapterは実コード。Tauri中継とPython応答、候補135件、エンジン可否だけを模擬化する。Python JSONの要求記録にはmetadataが混入していないことを確認した。実設定への送信は行わない。
- §14〜16のHTMLは当時のレビュー／提案の記録として保持した。製品hookが変わったため、過去プレビューの再生成には当時のソース／モックも必要になる。

### 検証と残る範囲

- `npm run vite-build`: **PASS、463 modules、main / VR双方**。
- `node --test src-ui/logics/main/languageMutationCoordinator.test.js src-ui/logics/main/languageMutations.test.js`: **15 / 15 PASS**。最終ACK限定、同時更新拒否、stale拒否、遅いACK、再同期公開順、GET失敗時の保存禁止、再取得後の復帰を検証。Node 22のMockTimers実験機能警告のみ。adapterテストは実ソースを読み、storage／翻訳の依存だけをNode内で模擬化する。
- 変更範囲の限定ESLint: **PASS、新規警告なし**。`store.js` / `useReceiveRoutes.js` のファイル全体にはHEADから存在するsemi／未使用変数の指摘があり、既存問題として区別した。lint設定・package / lockfileは変更していない。
- 5 YAMLの解析、37キー集合・補間変数の一致、`git diff --check -- src-ui locales`: **PASS**。
- 本体コードのブラウザー確認: 5言語×上限／長い名前の10画面で720×640、本文584px、最小操作高56px、横溢れ・通常時の縦溢れなし。3件目追加、満枠の個別変更、重複枠の解除、プリセット反映、地域違いの同言語制限、選択中の利用不可エンジン、PC設定中のロック、初回同期を確認した。
- 途中push・送信完了後も候補画面に留まり、遅い200で元操作だけを完了することを確認。400後はA一覧末尾の候補を表示・focus維持。部分適用→500→GET新値でも候補／失敗を保持。再同期も失敗した場合は保存を止め、再取得成功後に候補／失敗を維持して編集へ復帰した。
- 操作・UI、実装境界、transport／再同期の3人が独立レビューし、修正後 **LGTM、未解消のhigh / mediumなし**。
- **未検証**: 実Tauri WebViewとsidecar間の配送・設定保存、SteamVR/HMDでの可読性・レーザー操作、スクリーンリーダー実読み上げ。今回Python/Rustは変更していない。実機では言語追加／置換、プリセット、失敗後復旧、PC同時操作を確認する。
