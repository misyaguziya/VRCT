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
