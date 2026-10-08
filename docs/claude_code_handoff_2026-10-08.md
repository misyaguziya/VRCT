# Claude Codeへの引継ぎ — Rust音声処理移行

2026-10-08、ユーザーの「一旦ここまでをコミット」依頼で作業を停止したチェックポイント。詳細な経緯はリポジトリ直下の`progress.md`、当初設計は`docs/rust_backend_migration_plan_2026-10-07.md`。

## 作業場所と保存状態

- Checkout: `D:/codex/home/worktrees/4508/VRCT`
- Branch: `codex/rust-audio-pipeline`
- develop基準: `e1c24d1b0434e562a02bd4f00106e8bd3974f789`
- サイクル1〜9のcheckpoint: `b9be99e7f27ff97abbad2c6f3abd1d218263404b`
- その次のコミットが今回の10〜13 checkpoint。`git log -2 --oneline`で確認する。push・developへのマージは未実施。
- `tmp/`はGit対象外。同じPCには残しているが、別checkoutへのcloneでは復元されない。配布exe・wheel・録音/画像・モデル重みはコミットしない。

## 実装済みの範囲

音声のPCM変換、downmix、RMS/発話区間検出、通常レートFLACをRust/PyO3拡張へ移行。Google通信をPython clientへ独立し、録音source/listenerを自前化して`custom_speech_recognition`依存を除去した。認識前のraw/WAV再利用とRust入力コピー削減も実装済み。PyAudioWPatchのデバイスI/O、Whisper/CTranslate2・Sileroの推論、`audioop.ratecv`は維持する。PyAudioは既存C実装でGILを解放するため、単純なRust置換より互換性と実測を優先する。

今回の本番差分は次の2件。

1. `bat/install.bat`のCPU/CUDA両経路で、通常版OpenCVを除去して固定headless 4.10.0.84を復元する。両packageが同じcv2ファイルを上書きするため、除去だけでは足りない。失敗時は即終了し実version/metadataも検査する。`requirements.txt`は説明コメントのみ変更。
2. `Model.feedWatchdog()`が未初期化時に重い初期化を開始しないよう修正。生成済みwatchdogがあれば初期化中でもfeedする。先行heartbeatがhandler threadで初期化を奪い、main threadのOverlay等callback登録が早過ぎる問題を修正した。全ての早期IPCの並行初期化を一般的に解決したわけではない。

## 検証結果と未完了を区別する

| 範囲 | 結果 |
|---|---|
| サイクル9の音声回帰 | CPU/CUDA各667件＋3 subtests、Rust13件、clippy/fmt成功。今回全件の再実行はしていない |
| サイクル10 | CPU/CUDA全sidecar build・限定smoke、実マイク/loopback開始停止各3回、隔離source起動成功 |
| サイクル11の配布 | 全依存再解析/build/限定smoke成功。余剰FFmpeg 4110 DLLを除去し、4100だけ収集 |
| サイクル11のfrozen起動 | **PARTIAL**。CPUはexit 0/IPC 200でもcallback登録のAttributeErrorがあった。旧runnerのPASSを独立監査で訂正。CUDAの当該試行は成功 |
| 実Whisper base | ローカルSAPI合成英文をsource経路でCPU/CUDA各2回推論成功。配布exe内のモデル推論や認識精度評価ではない |
| OpenCV修復 | 使い捨てvenvで実cmd/pipを11段階実行。衝突・修復・再実行・失敗即終了・復旧を確認。独立レビューLGTM、encoding試験3件成功 |
| heartbeat修正 | 設計・実装レビューLGTM。CPU/CUDA関連24件＋2 subtests成功。CPUはテスト内lint修正前、CUDAは修正後。製品コードは同一。ruff 0.14.4成功 |
| 修正後のexe | 11のAnalysis TOCを再利用したPYZ/EXE/COLLECTの完了ログあり。限定smoke両PASS。**全PYZ/資産hash照合とfrozen起動結果は未完了** |

13の起動harnessは独立レビューLGTM。先行heartbeatの無初期化、Overlay 5個＋mute＋watchdogのcallback実体、JSON stdout、空stderr、期待したHTTPガード例外だけを検査する。ユーザーの引継ぎ依頼で実行を止めたため、`tmp/cycle13-startup/startup-{cpu,cuda}`に途中の配布copy・ログがあり、`result.json`はない。起動成功として扱わない。build process終了コードもセッション中断で直接回収できていない。

## 再開時の最初の作業

1. 作業treeとHEADを確認し、`docs/benchmarks/audio_startup_heartbeat_cycle13_2026-10-08.json`のソースhashと現行を照合する。
2. `tmp/cycle13-startup/dist-{cpu,cuda}`と11の配布物を照合する。全PYZ module集合、model以外の全code object（co_filenameを再帰正規化）、現行modelと新startup_hook一致、mainloop/他hook一致、`_internal`全相対パスとSHA256不変を検証する。13は依存関係の全再解析ではない。必要な旧TOC/配布物が無ければfresh full buildでやり直す。
3. レビュー済み`run_startup.py`を**新しいsuffix付き**でCPU/CUDA各1回実行する。以前の失敗・中断フォルダは上書きしない。

```powershell
& 'D:/WORKSPACE/WORK/VRChatProject/VRCT/.venv/Scripts/python.exe' -B tmp/cycle13-startup/run_startup.py cpu claude1
& 'D:/WORKSPACE/WORK/VRChatProject/VRCT/.venv/Scripts/python.exe' -B tmp/cycle13-startup/run_startup.py cuda claude1
```

4. `result.json`だけでなく、worker結果・stdout/stderr/error.log・early-heartbeat・実exe hashを監査する。7 callback、初期化/IPC/停止/exit 0を確認し、独立レビューを閉じる。実行結果を永続JSONとprogressへ追記する。
5. その後、通常GUIとの結合・配布版実モデル推論・物理hotplug/endpoint切替・無データ停止・発話終了から表示までの時間を検証する。全体計測の結果から次のRust化対象を選ぶ。

## 検証環境と注意点

- 共有メインcheckoutの`.venv/Scripts/python.exe`と`.venv_cuda/Scripts/python.exe`は読み取り利用だけにした。`bat/install.bat`全体は既存venvを削除・再作成するので、この共有環境で安易に実行しない。
- Native: `tmp/cycle9/native-site`。pyd SHA256は`8286bd9ca1f1221d1b14e7f4ccd7040d1d586a6b6fc469e5e15ffa148ca8fc53`。
- 固定cv2: `tmp/cv2-pinned`。共有venvには通常版/headless版が併存しており未修復。ビルドプロセス開始前の`PYTHONPATH`も固定cv2に揃える必要がある。PyInstallerの`pathex`だけではhookの参照先が揃わなかった。
- pytest補助: `tmp/cycle4a-pytest`（CUDA venvにはpytestなし）。旧SR import禁止runner: `tmp/cycle6/no_sr_runner.py`。ruff: `tmp/devtools/bin/ruff.exe` 0.14.4。PATHの別versionと混同しない。
- Pythonテスト時の`PYTHONPATH`は`tmp/cycle9/native-site;tmp/cv2-pinned;src-python;tmp/cycle4a-pytest`の各絶対パスを使用し、`PYTHONDONTWRITEBYTECODE=1`を設定する。
- frozen configの保存先はexeの横、sourceではconfig.pyの場所。cwdを変えるだけではユーザー設定を隔離できない。起動harnessは配布全体copyと専用configを使用する。
- Python socket/requests拒否、HF offline、録音open拒否、SteamVR検出の差替えを使用。OS firewall隔離ではない。ユーザー音声の保存・外部送信・新規モデルdownloadはしていない。
- exeには検証専用runtime hookが入っている。検証配布物をそのまま正式リリースしない。
- 起動/推論時間は並行build・trace・ガードの影響がある。性能改善率として利用しない。

永続JSONは`docs/benchmarks/`のcycle10〜13。各レポートに検証scriptとhashを保存した。13のspecは11のTOC/依存資産を前提にするため、JSONからscriptだけ復元してもfresh checkoutで直ちに再実行できるわけではない。
