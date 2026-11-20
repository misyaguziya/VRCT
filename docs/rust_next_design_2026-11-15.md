# Rust 版 次期開発の設計（2026-11-15）

状態: **承認済み。P0〜P2.5 段階 1 まで実装し `rust-full-backend` に入れた**（第 3 版: 2026-11-16 の進み具合を反映）
UI デザイン: `docs/rust_next_ui_design_2026-11-15.html`（2026-11-15 時点の案。P2.5 の決定は反映していない）

## 進み具合（2026-11-16）

| 段階 | 状態 | 実機の確認 |
|---|---|---|
| P0 | 済み（v3.6.1 の取り込み） | インストーラのプロキシは未 |
| P1 | 済み（#127・#126） | #127 の回線断は未 |
| P2 | 済み（オーバーレイの土台、キーボード、11-05 以降の MSKB の修正、キーボード辞書は VR UI を ON にしたときに準備、表示倍率への対応、見た目を今の MSKB に合わせる） | 全部未（VR） |
| P2.5 | 段階 1 済み（ログ窓の字幕の形）。段階 2〜4 は未着手 | 全部未（VR） |
| P3 | 検証済み（issue #128、AMD 3 機種と NVIDIA で CT2 4.9.0 が動いた）。設計を確認中、本体は未着手 | 実機の受け入れは未 |
| P4 | 済み（`claude/rust-p4-model-catalog`、未マージ。バックエンド。検証済みのモデルの一覧＝カタログ、再開・SHA-256 照合・中止・削除・取得元）。UI は `docs/model_catalog_ui_handover.md` | 実回線の取得・再開、プロキシ、ミラーは未 |
| P5 | やめた（2026-11-19、エンジンは CT2 に統一。P3 の方針） | — |
| P6 | 未着手 | — |

`rust-full-backend` はまだ push していない。

この文書は、Rust 版（`rust-full-backend`）を次に進める順番と、各段階の設計を決める。
調査で確認できたことと、確認できていないことを分けて書く。

## 決定事項（2026-11-15）

| 項目 | 決定 |
|---|---|
| キーボード | 見た目は MSKB を踏襲。機能は 2026-11-05 に決めた範囲に制限 |
| issue | 直近の 2 件（#127・#126）だけ |
| #127 | 連続 5 回の失敗は異常とみなして止める |
| AMD の実機 | 所有者がいる。P3-0 の確認を依頼できる |
| インストーラ | 現状を維持（エディション別。GPU を後から取得する形にはしない） |
| OCR | まず評価から |
| speech.cpp | `nyosegawa/speech.cpp`（P5 に記載） |
| UI | デザインは別の設計者に一任。この開発は**バックエンド（endpoint）を先に作り、UI は案の提示と引き継ぎまで** |

### UI の扱い

- `docs/rust_next_ui_design_2026-11-15.html` は**案**。確定したデザインではなく、UI の設計者が直す前提の叩き台。今の設定画面の大枠（左の項目・行の部品・配色）から外れない範囲で描いてある。
- 各段階で作るのはバックエンドまで: endpoint、設定キー、push、契約テスト。**新しい画面の仮実装はしない**（OCR のときと同じ進め方）。
- 段階ごとに、UI の設計者へ渡す引き継ぎを `docs/` に書く（`docs/ocr_ui_handover.md` と同じ形）: endpoint の名前・要求と応答の例・push のキー・エラーコード・状態の移り変わり・足す文言の案。UI 側はこれだけ見れば作れるようにする。
- UI が未対応でも壊れないようにする: 新しい endpoint と設定キーは足すだけで、既存のものは変えない。新しい機能は既定で OFF か、今の選択肢が既定のまま。
- 例外（UI のファイルに触るもの）:
  - P0 の master からの取り込み（座標ロックの鍵ボタン、locales）。master で公開済みの UI をそのまま持ってくるだけ。
  - P1 の #126（説明文の書き直し。文言だけ）。
  - P2 のキーボード。**UI も含めて全部こちらで作る**（VR の中の窓、歯車の設定パネル、デスクトップの設定画面に足すキーボードの項目）。見た目は MSKB を踏襲し、設定画面の項目は今の部品（`Templates.jsx` の行）だけで組む。

---

## 0. 全体の順番

| 段階 | 内容 | 規模 | 実機が要るもの |
|---|---|---|---|
| P0 | v3.6.1 の修正の取り込み | 小 | インストーラのプロキシ |
| P1 | issue #127・#126 | 小 | なし（単体テストで確認） |
| P2 | オーバーレイの土台の改善 + キーボード | 大 | VR 実機（SteamVR・VRChat） |
| P2.5 | 字幕（small / large）を VR UI のログ窓に吸収 | 中 | VR 実機 |
| P3 | CT2 4.9.0 への統一と AMD 版（ROCm のエディション）。**2026-11-19 に作ると決定** | 中〜大 | AMD の GPU（RDNA3 / RDNA3.5 / RDNA4） |
| P4 | 検証済みのモデルの一覧（カタログ）から入れる・消す | 中 | なし |
| P5 | ~~llama.cpp・speech.cpp（Vulkan 版を同梱、選べるエンジンとして追加）~~ **やめた（2026-11-19、CT2 に統一）** | — | — |
| P6 | OCR の評価 → 差し替え | 評価が先 | なし |

P0 → P1 → P2 → P2.5 は順番に進める。P5 は「付け加える形」で作ることが決まった（下の「推論エンジンの選定」）。**P3 を作るかどうかは、AMD の実機での Vulkan の評価で決まる。** P4 は独立に進められる。P6 の評価は、実装と並行していつでも始められる。

各段階は別ブランチで作り、`rust-full-backend` へ入れる。

---

## 推論エンジンの選定（P3・P5 の前に行う）

方針（2026-11-15）: **Rust 化を機に、推論エンジンを最適なものにする。エンジンを替えて認識・翻訳の結果が変わることは受け入れる。** Python 版と同じ出力であることは、もう条件にしない。

### 決定（2026-11-15）: 付け加える形（下の表の B）

今のエンジン（CTranslate2 の Whisper と NLLB / M2M100、CPU 版と CUDA 版）は**そのまま残し、既定も変えない**。今の利用者は、更新しても何も変わらない。speech.cpp と llama.cpp は、選べるエンジンとして足す。

- A（今のままで AMD 版を ROCm で足す）と C（全面的に載せ替え）は取らない。C は、今のものが使えなくなることが利用者に不利益になるため。
- AMD・Intel の GPU は、足したエンジン（Vulkan）で使えるようにする。**AMD 版（ROCm のエディション）は、評価で Vulkan が足りないと分かったときだけ作る。**
- 評価の目的は「置き換えるか」ではなく、「足すエンジンが出せる質か」「AMD で Vulkan が十分か」「どのモデルをおすすめに載せるか」になる。
- 将来、足したエンジンが広く使われて今のものより良いと分かったら、既定を替えることを改めて検討する（今回は決めない）。

### 比べた構成（経緯。採用は B）

| | A. 今のまま | B. 併用 | C. 全面的に載せ替え |
|---|---|---|---|
| 文字起こし | CTranslate2 の Whisper | CTranslate2 + 内蔵（speech.cpp か whisper.cpp） | speech.cpp か whisper.cpp だけ |
| 翻訳（ローカル） | CTranslate2 の NLLB / M2M100 | CTranslate2 + 内蔵 LLM（llama.cpp） | llama.cpp だけ |
| GPU | CUDA（+ AMD 版を ROCm で追加） | CUDA は今のまま。AMD・Intel は Vulkan | Vulkan だけ |
| 配布 | CPU 版 / CUDA 版 / AMD 版 | CPU 版 / CUDA 版 | **1 つ**（約 4GB の CUDA 版が不要になる） |
| 消せるもの | — | AMD 版の作業（ROCm のビルドと同梱） | `vrct-ct2`・`vrct-whisper`・CUDA の DLL・エディションの分岐・ROCm |

C は配布と保守では最も軽いが、今のエンジンが使えなくなるので取らない。次の測定は、B の中身（おすすめに載せるモデル、AMD 版を作るか）を決めるために行う。

### 測るもの

同じ音声・同じ文（日・英・韓・中、VRChat の会話に近い短い発話）で、次を比べる。

| 項目 | 見る理由 |
|---|---|
| 1 発話の遅延（話し終わりから文字が出るまで） | リアルタイムの字幕で最も効く |
| 認識の正しさ、無音での誤認識（「ご視聴ありがとうございました」の類） | 今の利用者の不満の中心 |
| 翻訳の質と 1 文の遅延 | NLLB から LLM へ替えたときの差 |
| VRChat を動かしながらの負荷（フレームレートの落ち方、VRAM） | GPU を取り合うため |
| **CPU だけのときの速度** | GPU を VRChat に譲っている利用者が多い。ここが遅くなるなら C は取れない |
| 起動とモデルの読み込みにかかる時間、メモリ | 常時動かすため |

環境: NVIDIA（CUDA と Vulkan の両方）、AMD（所有者に依頼。Vulkan と CPU）、CPU だけ。

候補のエンジン:

- 文字起こし: speech.cpp（Qwen3-ASR 0.6B / 1.7B、日本語は ReazonSpeech v2 / Parakeet ja）、whisper.cpp（Whisper。今と同じモデル系統で比べやすい）
- 翻訳: llama.cpp + HY-MT1.5-1.8B、ほかに小さい翻訳向けの GGUF

### 決め方

構成は B で決まっている。評価で決めるのは次の 3 つ。

| 結果 | 決まること |
|---|---|
| 足したエンジンの精度・遅延・安定性が、今のものと並べて出せる水準 | そのエンジンを選択肢として出す。足りないものは出さない |
| AMD の実機で、Vulkan の速度と安定性が実用になる | AMD 版（ROCm、P3）は作らない |
| AMD の実機で、Vulkan が実用にならない | P3 を作る |
| モデルごとの精度と重さ | 「おすすめ」に載せるモデル |

### 気をつける点

- **speech.cpp は v0.10 で、作者 1 人の新しいプロジェクト**（公開は活発だが、既定のエンジンにするには依存の危険がある）。既定にするなら版を固定して同梱し、whisper.cpp（ggml-org、実績が長い）を代わりにできる形にする。
- 翻訳を LLM にすると、モデルが大きくなる（NLLB 600M の int8 は約 600MB、HY-MT1.5-1.8B の Q4 は約 1.1GB）。CPU での 1 文の遅延は未実測。
- 今のエンジンの基準データ（`testdata/` の Whisper と NLLB の分）と照合テストは、そのまま残す。足したエンジンの回帰テストは「確認済みの出力」を基準に別に作る。
- endpoint の形は変えない（選べるエンジンとモデルの名前が増えるだけ）。既存の設定（`*_WEIGHT_TYPE` など）と既定値は変えない。

### 評価の進め方

評価用の小さい実行ファイル（`tools/` に置く。配布物には入らない）を作り、上の環境で同じ入力を流して、遅延と結果を JSON で出す。結果は `docs/` に記録する。**同梱する実行ファイル（Vulkan 版の speech.cpp と llama.cpp、合わせて約 70MB）は、評価で出せる水準と分かったものだけ入れる。**

---

## P0. v3.6.1 の取り込み

`git log rust-full-backend..master` の先頭 19 件を 1 件ずつ見た結果。

| master のコミット | 内容 | Rust 版での扱い |
|---|---|---|
| 12d3ebe0 | VR UI がテキストサイズでずれる（#125） | 取り込み済み（2cf8cd65） |
| 76a5c5be | 空の翻訳で大ログが落ちる（#121） | コードは安全（`vrct-overlay/src/image.rs:257,349,366,410,449`）。**空の翻訳を入れるテストを 1 本足す** |
| e9724e32 | インストーラのプロキシ（#124） | **未**。`claude/issue-124-rust-full-backend`（73f39945）を入れる。`lib.rs` と Cargo の差分が 73f39945 自身のものかを先に確認 |
| f432f084 | 1行・複数行字幕の座標ロック | **未**。下の P0-1 |
| e60ba6cf 6590583f | `max_phrase` の用語と説明 | **未**。locales の cherry-pick。文言は Rust の実装（結果を溜める件数の上限、`transcriber.rs:212`）と合う |
| 0a4e4714 a9a638dc 12d29f92 8ec05bc3 | 韓国語 | **未**。cherry-pick |
| d2bdcf3c | アップデーターで選べる版を 3.6.0 以降に | **未**。`update.rs:16` の `MIN_SUPPORTED_VERSION`。`3.6.0-beta.N` の扱いは Python 版の実装と突き合わせる |
| cb9850fc | リリースノート | docs だけ。入れる |
| a71847f9 ee10e2f1 563c4af9 | Python の警告 | 該当なし（Python を削除済み） |
| 4908b521 | `init()` の並行実行 | 該当なし（Rust は起動時に 1 回、`app/init.rs:427`） |
| bdb84b4b | WASAPI のステレオ入力 | 該当なし（Rust はモノラル化、`app/audio.rs:86`）。実機のステレオマイクは未確認 |

### P0-1. 座標ロック

Python 版と同じ形にする（新しい endpoint は作らない）。

- `OVERLAY_SMALL_LOG_SETTINGS` / `OVERLAY_LARGE_LOG_SETTINGS` に `locked: bool`（既定 false）。保存済みの設定に無ければ false で補う。
- 掴めるかの判定: `(パネル && panel_locked) || そのサイズの locked`。今は `panel_locked` だけを見ている（`vrct-overlay/src/overlay.rs:231,444`）。
- 触る場所: `vrct-backend/src/app/overlay.rs`（`Settings`、既定値）、`vrct-overlay/src/overlay.rs`、`overlay_tests.rs`、契約テストの基準。
- UI は master の変更をそのまま持ってくる（`ui_configs.js`、`Vr.jsx`、`Vr.module.scss`、`lock.svg` / `unlock.svg`、locales）。

### P0 の確認

`cargo clippy --workspace --all-targets -- -D warnings`、`cargo test --release -p vrct-overlay -p vrct-backend`、契約テスト、`npm run vite-build`、`cargo check --manifest-path src-tauri/Cargo.toml`。
インストーラのプロキシは実機（プロキシのある環境）でしか確かめられない。

---

## P1. issue #127・#126

今回入れるのはこの 2 件だけ。ほかの open の issue は、この開発では触らない（#88 と #78 は、P3 と P5 の結果として解決する）。

### P1-1. 一時的な通信エラーで止めない（#127、#121 の続き）

Rust 版も Python 版と同じ動作をしている。`vrct-backend/src/transcriber.rs:204-206` は、プロバイダの呼び出しが失敗して結果が空なら、原因を見ずに `ASR_ERROR`（`recoverable: false`）で止める。

- 一時的な通信エラー（タイムアウト・接続エラー・サーバーの 5xx）は、その文だけ飛ばして続ける。**リトライしない。**
- 待っても直らないもの（API キーの誤り・利用上限）は今までどおり 1 回で止める。
- **一時的なエラーが連続 5 回続いたら、異常とみなして止めて通知する。** 1 回でも成功したら数え直す。回数は定数。
- 設定は足さない。飛ばしたことはログに 1 行だけ書き、画面の通知は出さない。
- 止まったときの通知は今ある経路（デスクトップの通知）だけ。VR の中の知らせは足さない。

実装の形: `transcribe_one` の `Err(String)` を、一時的かどうかが分かる型にする（`enum AsrError { Transient(String), Fatal(String) }`）。分類は各プロバイダの呼び出し側（`asr.rs`、`app/transcription_api.rs`）で、HTTP の状態と通信エラーの種類から決める。文字列の中身で判定しない。

確認: プロバイダを差し替えた単体テストで、タイムアウトでは次の文が処理される・認証エラーでは 1 回で止まる・連続 5 回で止まる・途中で成功すると数え直す、の 4 つ。

### P1-2. No Speech Prob の説明文（#126）

5 言語の `mic_no_speech_prob` / `speaker_no_speech_prob` を書き直す（10 か所）。Rust の判定は `vrct-whisper/src/lib.rs` の `no_speech_prob > 閾値` で、説明は次の趣旨にする。

- この確率を超えた区間を無音として無視する。
- 0 に近いほど無音とみなす区間が増え、ノイズからの誤認識は減るが、小さな声は無視されやすくなる。
- 1 に近いほど小さな声も拾うが、無音やノイズから誤認識しやすくなる。

---

## P2. オーバーレイの土台とキーボード

### 現状

- キーボードは `claude/mskb-keyboard-scope-b5f8eb`（59a3c884）に、2026-11-05 時点の MSKB を移植したものがある。`rust-full-backend` には**まだ入っていない**（共通の祖先は 3fb18b41）。差分は 61 ファイル・約 24,000 行（うち約 15,700 行はライセンス表記）。
- そのブランチには、オーバーレイの土台の改善（SteamVR Input で手を読む、指している手の入力を VRChat に渡さない、60Hz、`command_wait`、開閉ショートカット）も入っている。
- 11-05 より後に MSKB で直したものは入っていない。

### 今の VRCT（rust-full-backend）のオーバーレイで良くない点

| 点 | 今の VRCT | MSKB / OverRec |
|---|---|---|
| 手の読み取り | 旧式の `controller_state`（ボタンのビット、`vr_ui.rs:16,125`） | SteamVR Input（アクションマニフェスト） |
| ゲームへの入力 | 指している間もトリガー・グリップが VRChat に届く | 指している手の分だけ overlay-global の優先度で押さえる。押さえ始めと終わりは離しているときだけ |
| 更新の頻度 | 30Hz / 20Hz、PostMessage と PrintWindow | 指している間とキャプチャは 60Hz、`command_wait` で即時に起こす |
| 触覚 | なし | ホバー・押下・成功・失敗で振動を変える |
| SteamVR の終了 | `vrmonitor.exe` の有無と Quit イベントだけ（`vrct-openvr/src/lib.rs:211`、`overlay.rs:945`） | `vrserver` のプロセスハンドルを見て、強制終了も検知。終了中のサーバーへ再接続しない |
| ダッシュボードを開いたとき | 扱いなし | 中断し、復帰はボタンを離してから |

VRCT の方が良い点（残す）: SteamVR の交差判定とマウス座標を使う、コントローラー先端の機種別の補正、複数の固定先、角でのリサイズ、スレッドの停止と join。

### キーボードの方針（決定）

- **見た目は MSKB を踏襲する。** キーの配置・段組み・変換中の表示・候補の並び・言語メニュー・タイトルバー・歯車の設定パネルは、MSKB の現在の作りに合わせる。移植済みのブランチ（b6d2cc2f）は 11-05 時点の MSKB の UI なので、**今の MSKB との見た目の差分を取り、制限した機能に関係しない差（配置・寸法・配色・押したときの表示）を持ってくる。**
- **機能は 11-05 の範囲に制限する。**
  - 入れる: 英・日（ローマ字）・韓・中（拼音 簡/繁・注音・倉頡・速成）、半/全、Ctrl（選択・単語移動・undo/redo・コピー/貼り付け）、入力欄タップでカーソル、Shift+↵ で改行、不透明度・ピン、送り先 2 つ（VRCT で送る＝翻訳 / VRChat に貼る）、キーの音（ON/OFF と音量）、開閉ショートカット、▲▼ は VRCT の送信履歴、マイクは VRCT の文字起こし。
  - 入れない（MSKB だけ）: 色・背景画像・音のカスタム、フリック、英単語予測、記号/絵文字/顔文字・定型文、入力欄連動の自動表示、手首ボタンのランプ、SteamVR と一緒に起動、グリップ+トリガーの拡縮、入力診断・遅延計測。
- MSKB の UI に「入れない機能」のキーや項目がある場所は、キーを抜いて残りの幅を詰める（移植済みのブランチと同じやり方: `#+=` が無い分、空白を 7.75 キーに）。色は VRCT の配色に固定する。

### 進め方

1. **土台**: `claude/mskb-keyboard-scope-b5f8eb` の中のオーバーレイの部分（79824cf5 と関連）を先に `rust-full-backend` の上へ持ってくる。座標ロック（P0-1）と同じ「掴めるか」の判定を触るので、P0 の後に行う。
2. **11-05 以降の MSKB の修正を足す**:
   - 707a373: SteamVR の終了・再起動に追従（OverRec の `ProcessWatch` と同じ考え。`vrct-openvr` の `acquire` に入れる）
   - `launcher_haptic_due`: 触覚
   - IME の 0668271・c9296a9・045ec0c。**045ec0c（日本語のユーザー名で librime が落ちる）は、移植済みの `keyboard.rs:244` が絶対パスの `log_dir` を渡しているので同じ不具合を持つ見込み**（実機は未確認）
   - d3d2fe8（ウィンドウなしの WebView をキャプチャする大きい変更）は、**今回は入れない**。VRCT で症状が出ているかを先に確かめる
3. **キーボード本体**: 5f56258b（IME）・f235a88a（設定）・b6d2cc2f（UI）・0e8b04b2（マイク）・f335e5c4（貼り付け）・59a3c884 を入れる。
4. **見た目を今の MSKB に合わせる**（上の方針）。

アプリの種別: VRCT は Background 型で SteamVR に入っている（`overlay.rs:482`）。SteamVR Input を使う構成は移植済みのブランチで既に動かしているので、その構成を引き継ぐ。

### ライセンス

- librime は BSD-3、jaroomaji は Apache-2.0、Mozc の辞書は BSD-3。
- **JMdict と KANJIDIC2 は CC BY-SA 4.0、中国語のスキーマは LGPL-3.0。** 辞書は初回に取得する形（同梱しない、約 29.6MB）で、出典を `_internal` のライセンス表記に入れる。`rime.dll`（約 4MB）と OpenCC（約 1.3MB）は同梱。
- MSKB のコードと見た目を MIT の VRCT へ入れることは、上の範囲で了承済み。それ以外の MSKB の機能を足すときは先に確認する。

### P2 の確認

- 自動: `overlay_tests.rs`（偽の SteamVR の 20 場面）に、座標ロック・入力を押さえる・中断と復帰の場面を足す。IME は実 RIME のテスト。
- 実機（VR）でしか確かめられないもの: 指している間に VRChat が反応しないこと、触覚、SteamVR の再起動、キーボードで VRChat へ貼り付け、日本語のユーザー名の PC での起動。

---

## P2.5. 字幕（small / large）を VR UI に吸収する

最終形: オーバーレイは VR UI だけにする。small（1 行）と large（複数行）は VR UI のログ窓に吸収し、ロックは設定画面ではなく、窓のツールバーで窓ごとに行う（今のログ窓と同じ）。P0-1 で入れる設定画面の鍵は、吸収が終わった時点で不要になる。

### 案: ログ窓に「表示の形」を持たせて切り替える

ランチャーに「字幕 1 行」「字幕 複数行」のボタンを足すのではなく、ログ窓のツールバーに切り替えを 1 つ足す。

| 形 | 中身 | 今のどれに当たるか |
|---|---|---|
| 履歴 | 今のログ窓（スクロールできる一覧、ツールバーあり） | VR UI のログ |
| 字幕（複数行） | 直近の数件だけ。背景は透明寄り。ツールバーは指したときだけ出る | large |
| 字幕（1 行） | 最新の 1 件だけ。数秒で消える | small |

- **位置・角度・固定先・大きさ・不透明度・文字の大きさ・秒数・ロックは形ごとに覚え、切り替えると、その形をユーザーが最後に置いた状態に戻る。** ただし、まだ使ったことのない字幕の形（`placed` が false）は、初めて切り替えたときに今の窓の位置・角度・固定先と縮尺（1 px あたりの m）を受け継ぎ、ロックを外した状態で出る（2026-11-17 実機で決定。初めは形ごとの既定の場所へ飛び、しかもロックされていて触れず戻せなかった）。
- 既定の大きさは履歴と同じ縮尺（900 px で 0.4 m）。複数行は 0.4 m、1 行は 0.5333 m。
- ロック中の字幕は、レーザーが当たっても反応しない（操作を止めない、触覚も出さない）。解除は、ランチャーのログのボタンの長押し（今の「呼び戻す」と同じ場所）から。
- 消えるときの演出は、描き直さずオーバーレイの不透明度で行う（WebView のキャプチャを回し続けない）。

### 同時に出したい場合

今は small・large・VR UI のログを同時に出せる。切り替え式にすると、同時には 1 つになる。

- 設定は最初から「形ごとの置き場所」として持つので、後から「2 枚目の窓を出す」を足すときに保存の形を変えなくて済む。
- 2 枚目を最初から作るかは、同時に使っている利用者がどれだけいるかで決める（テレメトリーで `OVERLAY_SMALL_LOG` / `OVERLAY_LARGE_LOG` / VR UI の ON の組み合わせが取れるなら、それを見る）。

### 移し方（今のものを急に消さない）

**方針（2026-11-17 決定）: small / large は廃止して VR UI に統合する。** ただし今は方針だけで、small / large と VR UI の字幕は並べてどちらも動くようにしておく（デスクトップの設定画面は別の設計者の担当なので、廃止の時期と画面は合わせて決める）。

1. VR UI のログ窓に字幕の形を足す。small / large はそのまま残す。（済み）
2. 既定は small・large・VR UI とも OFF のまま。VR UI は ON でも、SteamVR に一度つながるまでは VR 画面の窓とキーボードの辞書を用意しない（VR を使っていない間に負荷をかけない）。窓は SteamVR が切れても VR UI を OFF にするまで残す（作り直すと、作った直後の撮影の失敗に毎回入るため）。（済み、2026-11-18）
3. 廃止の版で: 今 small / large を使っている人の位置・大きさ・秒数・不透明度・ロックを対応する字幕の形（small → 1 行、large → 複数行。座標は同じ形で写せる。幅は small はそのまま、large は 0.25 倍）へ写し、ON だった人は VR UI を ON にしてその形で出す（両方 ON なら複数行）。
4. small / large の endpoint・設定・画像の描画（`image.rs`）と設定画面の欄を消す。デスクトップの画面は引き継ぎ文書で渡す。

### 決定（2026-11-16、段階 1 の実装で決めたこと）

- **板は不透明**（今の small / large と同じ rgb(41,42,45)）。**不透明度の設定は字幕全体**に効く（small / large と同じ）。板だけを半透明にする案は、VR UI の撮影が透明度を捨てる作りでシェーダーの手当てが要り、設定も二重になるので採らない。
- 見た目は、複数行＝今の large、1 行＝今の small と同じ並び。1 行は受信だけ（OCR を除く）で、その形で出し始めて（切り替える・ログ窓を開く）から受けた発言だけを出す（過去の発言は出さない。2026-11-17 決定）。履歴と複数行は過去の件も出す。
- **文字の大きさは形ごと**。操作バーの A−/A＋ はどの形でも同じ並びで出す。字幕は訳文の px（16〜56、既定 27 / 28）、原文・時刻は約 2/3。
- 1 行の板の高さの最小は 120px（既定 1200×180、約 0.15 m）。履歴は 400px のまま。
- ロック中と、形を変えて新しい中身を待つ間の字幕は、レーザーの当たり判定から外す（VRChat の入力を取らない）。**ロックしていない字幕は、消えた後もレーザーで 0.4 秒指し続けると出る**（2026-11-17 実機で変更。指しても出ないと設定を変えられなかった。ただ横切っただけで出ると、見えない板が VRChat の操作を横取りするので、出るまでは入力を VRChat に渡す）。ロック中の字幕を出すのは新着・ログ窓を開いたとき・ランチャーのログボタンの長押し。
- 字幕の種類の表記はメイン画面のログと同じ（送信 / 受信 / 受信 (チャット読み取り)）。チャット読み取りの受信も通常の受信と同じ紫で、文字だけで見分ける（補足なので目立たせない）。
- 時刻・種類の小さい文字は、板に対して 4.5:1 以上の色にした（2026-11-17 のデザインレビュー。VR はにじむため。旧来の small / large の画像より少し明るい）。
- ロックした字幕からは外し方がわからないので、その間はランチャーのログボタンに錠前を出し、ヒントで「長押しでロックを外して呼び戻す」と案内する。
- HMD に付けた字幕は、長押しで視界の中ならその場で出すだけ、視界の外なら頭に付けたまま目の前へ。
- 設定は `OVERLAY_VR_PANEL_FORM` と `OVERLAY_VR_SUBTITLE_SETTINGS`（形ごとの位置・大きさ・秒数・不透明度・ロック・文字の大きさ）。既存の `overlay_vr_panel_{anchor,locked,opacity}` は「今の形」の値を扱う。引き継ぎは `docs/vr_ui_subtitle_form_handover.md`。

### 決定（2026-11-15）

- **切り替えだけにする。** 複数枚を同時に出す必要はない（2 枚目の窓は作らない）。
- **VR UI のデザインはこちらで持つ**（キーボードと同じ）。字幕の形の見た目（背景、文字の縁取り、消えるまでの秒数）は、実装の前に案を出して確認する。
- 時期: P2（土台の改善）の後。指している間の入力の扱いと 60Hz 化が、字幕の形の前提になる。

### サイドカーをやめる移行で行うこと（2026-11-18 決定）

- **VR 画面の描き方を MSKB と同じにする**: 画面外の窓（`vr_panel` の WebView 窓）を撮るのをやめ、窓を持たない WebView2（CompositionController）を Windows.UI.Composition の visual に描かせて、その visual を撮る。レーザーのマウス入力は窓へのメッセージではなく WebView2 へ直接渡す（MSKB の `src-tauri/src/vr_panel.rs`・`mskb-overlay/src/host.rs`）。表示倍率・テキストのサイズ・画面外の置き場所の影響、PrintWindow への切り替え、作った直後の撮影の失敗が無くなる。
- visual は同じプロセスの中でしか撮れないので、オーバーレイが WebView と同じプロセスにあることが前提。今はオーバーレイがサイドカー（別プロセス）なので移せない。全体の移行（サイドカーをやめる）と同時に行う。
- それまでの折衷: VR 画面の窓は SteamVR に一度つながったら作り、VR UI を OFF にするまで残す（作り直さない）。

---

## P3. CT2 4.9.0 への統一と AMD 版（3 つ目のエディション）

**方針（2026-11-19 確定、issue #128）: 推論エンジンは CTranslate2（CT2）に統一し、4.9.0 を基準に CPU・NVIDIA（CUDA）・AMD（ROCm）を対象にする。** P5 の Vulkan のエンジン（llama.cpp・speech.cpp）の追加と、CT2 との比較はやめる（これまでの比較は issue #128 に履歴として残す）。

### 確認できたこと（検証ツール 0.3.1、`native/vrct-amd-check`）

- CT2 4.9.0 で、Radeon RX 7800 XT（gfx1101）・RX 7900 XTX（gfx1100）・RX 9070 XT（gfx1201）の ROCm 版と、GeForce RTX 2080 Ti の CUDA 版が、同じ 11 ケース（Whisper large-v3-turbo と NLLB 600M。GPU の float16 / int8_float16、CPU int8、同じモデルへの 2 スレッド同時）・ウォームアップ込み 48 回の推論に成功。
- RX 7900 XTX で旧版に出た `LLVM ERROR: Can't get available size`（0xC0000409）は、ROCm COMGR のキャッシュ整理が非 ASCII のパスを扱えないことが最有力の原因。`AMD_COMGR_CACHE=0` を DLL の読み込みより前に設定した 0.3.1 では起きなかった（対照試験ではないので、恒久的な解決の証明とはしない）。
- 検証ツールは HIP SDK 7.2 から取り出した DLL とカーネルを同梱し、協力者の PC に SDK をインストールせずに動いた。
- まだ: 本体に組み込んだ後の 4.6 → 4.9 の回帰、モデルの解放・再読み込みと VRAM の解放、Whisper と翻訳の同時常駐、長時間・多言語・実音声。

### 設計

#### 1. 3 つのエディションで同じサイドカーを使う

| 配布物 | `_internal` の構成 |
|---|---|
| CPU 版 | PyPI の CT2 4.9.0 と共通の DLL・データ |
| CUDA 版 | CPU 版に cuBLAS 12 と cuDNN 9 を追加 |
| AMD 版 | CPU 版に `ct2-rocm/` を追加 |

AMD 版は起動時に System32 の `amdhip64_7.dll` を確認し、`ct2-rocm/ctranslate2.dll` を絶対パスで先に読み込む。以降の CT2 呼び出しはその DLL を使う。どちらかの読み込みに失敗したら、理由を `process.log` に残し、通常の `_internal/ctranslate2.dll` で起動する。実行ファイルは全版共通。

#### 2. CT2 を 4.6.0 から 4.9.0 に上げる（全エディション）

- `third_party.toml` の `ctranslate2` を 4.9.0 の wheel・ヘッダー（タグ v4.9.0）・ライセンスに上げる。AMD 版用に `[ctranslate2-rocm]` を足す（上流の `rocm-python-wheels-Windows.zip` の SHA-256 と、その中の cp311 の wheel）。
- `vrct-ct2` の shim を 4.9.0 のヘッダーで作り直す。CRT（/MD）・MSVC の設定をそろえる。検証ツールの 4.9.0 用の部品は参考にするだけで、そのまま使わない。
- `vrct-ct2/build.rs` の DLL のコピーは、大きさだけでなく中身（SHA-256）でも更新を判定する（同じ大きさの別の版が残らないように）。
- **ここだけを先に入れて、CPU と NVIDIA での 4.6 → 4.9 の回帰を確かめる**（AMD の作業から切り離せる）。契約テストのチャットの翻訳は完全一致で比べているので、訳が変わったら中身を読んで基準を取り直すかを決める。
- **結果（2026-11-20、この PC の CPU と RTX）**: 4.6.0 は Python 版の基準と全件一致。4.9.0 は計算の変化（MKL の GEMM、int8 のスケール、CUDA の softmax・Conv1D など）でモデルの出力が変わる（NLLB 600M の訳は CPU 29 / CUDA 35 件（172 件中）、Whisper base の文字は CPU 17 / CUDA 10 件（58 件中）。言語の判定は変わらない。良くなったものも悪くなったものもある）。VRCT 自身の処理（トークン化・復号・メル・抑制トークン）は差なし。
  - 基準の扱い: Python 版の基準（`testdata/`）は書き出し直さず、VRCT 自身の処理の照合に使い続ける。CT2 の出力は、確認した Rust 版の出力を CT2 の版ごとの基準（`vrct-backend/tests/nmt-ct2-4.9.0/`、`vrct-whisper/tests/transcribe-ct2-4.9.0/`）として持つ（`native/README.md`）。M2M100 と large-v3-turbo は重みが無く、基準はまだ無い。
  - 契約テスト: 420 件中 1 件（チャットの英訳 "Tokyo train station" → "Tokyo station"）が変わり、基準を取り直した。
  - 速さ: 推論照合の所要時間（CPU と CUDA の合計）は 4.6 と同程度（NLLB 238 秒 → 221〜240 秒、Whisper 107 秒 → 98〜106 秒）。
  - 読み直し: CUDA で NLLB の読み込み・解放を 5 回繰り返して落ちない。解放後の VRAM の増え方（1 回あたり約 8MiB）は 4.6 と同じ。読み込み中の VRAM は 4.9 の方が約 250MiB 多い（約 900MiB、4.6 は約 640MiB）。

#### 3. COMGR のキャッシュ

全版で `main` の最初にプロセス内の `AMD_COMGR_CACHE=0` を設定する。値と、設定時に HIP と CT2 が未ロードだったかを `process.log` に記録する。

#### 4. GPU の列挙と計算の型

ROCm 版 CT2 の読み込み後、`ROCBLAS_TENSILE_LIBPATH` と `HIPBLASLT_TENSILE_LIBPATH` を exe からの相対パス `_internal\ct2-rocm\rocblas\library` と `_internal\ct2-rocm\hipblaslt\library` で上書きする。

CT2 で GPU を数え、HIP の `hipDeviceGetName` で名前を、`hipGetDevicePropertiesR0600` で gfx 名を取る。同梱の両ライブラリが対応する Radeon だけを一覧に載せ、CT2 に渡すデバイス名は `cuda`、番号は元の HIP デバイス番号とする。各 GPU の gfx 名と採否は `process.log` に残す。翻訳・文字起こしのデバイス一覧は GPU に `vendor`（`amd` / `nvidia`）を持つ。AMD 版の `COMPUTE_MODE` は使える Radeon があれば `amd`、なければ `cpu`。

Radeon の選択肢は CT2 が報告した型と `auto`。自動選択は float16 → int8_float16 → int8_float32 → float32 の順で、最初に対応する型を使う。

#### 5. AMD 版の配布物

- `cargo xtask fetch-native --amd` で CT2 の Windows zip（194,022,876 バイト）と AMD の wheel（492,439,790 バイト）を取得する。CT2 は zip 内の cp311 wheel を使う。SHA-256 は `third_party.toml` に固定した。[CT2 v4.9.0 ROCm 版](https://github.com/OpenNMT/CTranslate2/releases/download/v4.9.0/rocm-python-wheels-Windows.zip)・[AMD 公式 ROCm 7.2 wheel](https://repo.radeon.com/rocm/windows/rocm-rel-7.2/rocm_sdk_libraries_custom-7.2.0.dev0-py3-none-win_amd64.whl)
- `cargo xtask stage-sidecar --out target\sidecar-stage-amd --release --amd` で追加する `_internal/ct2-rocm/` は 975.11 MiB。内訳は CT2 と BLAS 関連の DLL 5 本（222.97 MiB）、`rocblas/library/`（117.75 MiB）、`hipblaslt/library/`（634.39 MiB）。hipBLAS が使う rocSOLVER も同じ wheel から取る。対象は gfx110x、gfx115x、gfx120x。
- HIP と COMGR は Adrenalin ドライバのものを使う。OpenMP は共通の `_internal/libiomp5md.dll` を使う。どちらの wheel にもライセンス本文がないため、同じ版の公式ソースから本文を取り、wheel の dist-info の METADATA と一緒に `_internal/licenses/` に置く。
- 検証ツール 0.3.1 に同梱した HIP SDK と今回の wheel では DLL の構成が異なる。今回の配布物とドライバでの推論は RDNA3 と RDNA4 の実機で確認する。

#### 6. インストーラー・アップデーター・UI

- インストーラー（`template.nsi` の CPU / GPU の選択）とアップデーター（`/EDITION=`。今は `/run/update_software` が CPU 版、`/run/update_cuda_software` が `gpu`）に `amd` を足す。AMD 版への更新は、新しい endpoint `/run/update_amd_software` にする（既存の 2 つは変えない）。
- アップデーターの更新先の選択肢（Updater.jsx）と版の表示（VersionLabel.jsx の CUDA の印）に AMD を足すのは、デスクトップ UI の担当の方へ引き継ぎ文書で渡す（新しい値 `COMPUTE_MODE = "amd"`、`vendor`、`/run/update_amd_software`）。

#### 7. 変えないもの

- 本体の音声処理（言語の自動判定、多言語、80 メルのモデル、長い音声の分割、beam などの生成の設定）。検証ツールの英語固定・128 メル・30 秒の上限・beam 1 は持ち込まない。
- モデルの持ち方と寿命（`vrct-ct2` の所有型、`translate/ctranslate2.rs`、`app/model.rs`、`app/pipeline.rs`）。推論中にモデルや DLL を捨てない。
- IPC の endpoint と、設定のキー。モデルの一覧（カタログ）も、このついでには変えない。

### 進める順番

1. **CT2 4.9.0 への更新**（全エディション共通）。この PC の CPU と NVIDIA で回帰を確かめる（文字起こし・翻訳の結果、契約テスト、速さ、モデルの読み直し）。
2. **AMD 版のビルドと起動**（共通の exe と `ct2-rocm/`、CPU への切り替え、GPU の列挙と計算の型）。この PC では AMD 版が「Radeon が無い」と CPU で正しく動くところまでを確かめる。並行して、検証ツールを公式の wheel の組み合わせとドライバのランタイムで作り直し、RDNA3 / RDNA4 の協力者にもう一度回してもらう。
3. **インストーラー・アップデーター**と、UI の引き継ぎ文書。
4. **AMD の実機での受け入れ**（協力者）: AMD 版の VRCT を入れて、文字起こし・翻訳が GPU で動くこと、モデルの読み直し・VRAM の解放、Whisper と翻訳の同時利用、長時間、GPU を使えないときに CPU に戻ること。RDNA3 と RDNA4 をそれぞれ 1 台以上。

### 決めておきたいこと

- ~~AMD 版の対象 GPU~~ → **RDNA3（gfx110x）・RDNA3.5（gfx115x）・RDNA4（gfx120x）に限る（2026-11-20 決定）。** 検証した ROCm 7.2 を保つため。AMD 公式の 7.2 の wheel には RDNA2（gfx103x）のカーネルが無い（RDNA2 用の世代別 wheel は 7.13 からで、CT2 4.9.0 との組み合わせは未確認）。CT2 の DLL 自体は gfx1030〜1035 も含む。**RX 6000 番台の検証に協力してくれる人が出てきたら、もう一度検討する。**
- ~~HIP SDK の DLL とカーネルの置き場所~~ → **AMD 公式の wheel から取る（2026-11-20 決定）。** VRCT の Hugging Face には置かない。

---

## P4. 検証済みのモデルの一覧（カタログ）

### 決定（2026-11-16）

- **自由な検索はやめ、VRCT が確かめたモデルの一覧（カタログ）だけを使う。** 理由: 翻訳の言語表が
  モデル名ごと（`languages.yml["CTranslate2"][weight_type]`）でトークナイザーも系統ごとに要る、
  英語専用の Whisper は黙って `en` にされる、派生や別系統は動かない。
- 最初の一覧は今の 14 個だけ。各リポジトリは 2026-11-16 時点の main の commit に固定する。
- 今の `/run/download_*_weight` もカタログ経由に寄せる。
- 取得元（`HF_ENDPOINT`）は https だけ。
- 今回作らないもの: 一覧の取り直し（配布の URL・署名が未決）、英語専用 Whisper と言語の絞り込み、
  自由な検索、GGUF（P5 で family を足す）。

### カタログ

- `native/data/model_catalog.json`（exe に埋め込み）。モデルごとに `id`・`family`（`whisper` / `m2m100` / `nllb`）・
  `license`・`repo`・`revision`（40 桁の commit）・ファイル（パス・大きさ・SHA-256）。翻訳は加えて
  `languages`（`languages.yml["CTranslate2"]` のキー）とトークナイザーのリポジトリ・commit・ファイル。
- 生成: `cargo xtask model-catalog-files <repo> [--revision <rev>] [--only a,b]`（Hub の公開 API、認証なし。
  LFS は `lfs.oid`、それ以外は取って SHA-256 を計算）。
- 読み込み時に検証する: id の文字、commit と SHA-256 の形、大きさ > 0、パス（`..`・絶対パス・ドライブ・`:`・`\` を拒否）、
  pickle（`.pt` `.pth` `.pkl` `.pickle` `.ckpt` と `model.bin` 以外の `.bin`）を拒否、未知の family を拒否。
- 種類（設定キー・フォルダー `weights/<whisper|ctranslate2>/<id>`）とトークナイザーの種類は family から決める。
- テストで「カタログの id（種類ごと、順序込み）= `SELECTABLE_*_WEIGHT_TYPE_LIST` = `DICT` のキー」を保証する。

### 取得

- URL は `{HF_ENDPOINT}/{repo}/resolve/{revision}/{path}`（tree などの API は使わない）。
- 1 ファイルずつ `<name>.part` に取り、`Range: bytes=N-` で再開（206 で始まりが合うときだけ。無視されたら 0 から）。
  3 回まで。4xx（429 を除く）ではやめる。失敗しても `.part` は消さない。
- 取り終えたら SHA-256 を照合し、合えば本来の名前にする。合わなければ `.part` を消して失敗。
- 始める前に空き容量（残りの合計 − 既存の `.part` + 64MB）を確かめる。
- トークナイザーは同じ取得の中で Hugging Face のキャッシュの並びに置き、揃ってから `refs/main` を書く。
- 進み具合はモデル全体のバイト数。中止は push しない。失敗の push は今のキー・コードのまま `details` に
  `{"weight_type", "reason": "network" | "sha256" | "disk_space"}`。
- 同じモデルの二重起動はしない。終了時は中止の旗を立てるだけ（待たない）。中止されたモデルは起動時に取り直さない。
- 新しい crate は足さない（`windows-sys` の `Win32_Storage_FileSystem` だけ）。

### endpoint

| endpoint | 内容 |
|---|---|
| `/get/data/model_catalog` | `[{id, family, size, license, repo}]` |
| `/get/data/model_list` | `[{id, family, bytes, installed, partial, in_use, downloading}]` |
| `/delete/data/model` | id。未知は `WEIGHT_UNKNOWN`、選択中・取得中は `WEIGHT_IN_USE`。成功で `model_list` |
| `/run/cancel_weight_download` | id。止めたら true |
| `/get/data/hf_endpoint` `/set/data/hf_endpoint` | 取得元 |
| `/run/download_*_weight`（既存） | 中身がカタログ経由に |

既存の endpoint と push のキーは変えない。契約テスト（`100_models.toml`）に削除が成功するケースは置かない
（重みのフォルダーは本物へのジャンクション）。UI の引き継ぎは `docs/model_catalog_ui_handover.md`。

### 実機・実回線で確かめること（未）

huggingface.co と hf-mirror.com からの実取得、途中で切っての再開（206）、プロキシ越し・中国の回線、
3.3B の取得の安定性と照合の時間、ウイルス対策ソフトの下での名前の付け替え、空き容量不足の通知、
既存の利用者の weights（印あり）で取り直しが起きないこと、選択を外した直後のモデルの削除。

---

## P5. llama.cpp と speech.cpp

> **2026-11-19: やめた。** エンジンは CT2 に統一する（P3）。以下は検討の記録として残す。

どちらも「VRCT が自分で起動する、OpenAI 互換のローカルサーバー」として扱う。VRCT は既に、翻訳の OpenAI 互換クライアント（`translate/llm.rs`、`app/translation_api.rs`）と、文字起こしの OpenAI 互換クライアント（`app/transcription_api.rs` の OpenAI / Custom）を持っているので、新しく書くのは「子プロセスの起動と停止」だけになる。

### 共通の設計

- 公式のビルド済みバイナリを使う。自分でビルドしない。
- **同梱する（2026-11-15 決定）。** Vulkan 版の実行ファイル（llama.cpp 約 38MB、speech.cpp 約 30MB、合わせて約 70MB）を、CPU 版・CUDA 版（作る場合は AMD 版も）の全エディションに同じものを入れる。版と SHA-256 は `third_party.toml` に固定し、`cargo xtask fetch-native` と `stage-sidecar` で今の DLL と同じ並びに置く。モデルは同梱せず、P4 のカタログに載せて取得する（GGUF の family を足す）。
- Vulkan が使えない PC（GPU が無い・ドライバーが古い）では CPU で動かす。起動に失敗した理由は隠さず通知する。
- **今のエンジンと既定値は変えない。** 足したエンジンは、利用者が選んだときだけ使われる。
- 選んだときに初めて起動する（起動時に重い初期化を増やさない）。`127.0.0.1` の空いているポートで動かし、VRCT の終了時に必ず止める（Job Object で子プロセスを親に結ぶ）。落ちたら 1 回だけ起動し直し、それでも駄目ならエンジンを使えない状態にして通知する。
- VRChat と GPU を取り合うので、GPU の使い方は設定で変えられるようにする。

プロセス内にリンクする案（`llama-cpp-2`、`libspeech` の C API）と比べた理由: GPU の種類ごとのビルドを自分で持たなくてよい、落ちても VRCT 本体が落ちない、既存のクライアントを使えて新しいコードが少ない。欠点はプロセスの管理と、起動に数秒かかること。

### llama.cpp（翻訳の内蔵 LLM）

- 公式のリリースに Windows 用の CPU・CUDA・Vulkan・ROCm/HIP のビルドがある。**全エディションで Vulkan 版を使う**（NVIDIA・AMD・Intel を 1 つで賄える。CUDA 版は本体約 320MB + ランタイム約 390MB と大きいので入れない）。NVIDIA で Vulkan が CUDA より明らかに遅いと評価で分かったら、CUDA 版のエディションだけ差し替えることを改めて検討する。
- 翻訳エンジンに「内蔵 LLM」を足す。`llama-server` を起動し、今の OpenAI 互換の経路で要求を送る。
- モデルは P4 のカタログに GGUF として載せて取得。HY-MT1.5-1.8B は公式の GGUF がある（Q4_K_M で約 1.1GB、#78）。
- 画像入力（mtmd）は P6 の VLM 型 OCR でも使える。

### speech.cpp（文字起こしの追加エンジン）

`nyosegawa/speech.cpp` を確認した（2026-11-15）。

- MIT。C++ / ggml。v0.10.1（2026-11-01）、更新は活発（最後の push は 11-14）。
- **Windows は x64 の Vulkan ビルド 1 つ**（`speech-0.10.1-windows-x64-vulkan.zip`、SHA256SUMS つき）。CUDA は不要で、NVIDIA・AMD・Intel を Vulkan で賄う。
- `speech serve` が **OpenAI の音声 API と Realtime の文字起こし**を返す。`libspeech` の C API もある。
- 認識モデル（GGUF、モデル名で自動取得）: Qwen3-ASR 0.6B / 1.7B（30 言語、言語を自動判定、名前や用語のプロンプト）、ReazonSpeech v2・Parakeet ja・Haas ja（日本語）、Parakeet v3（欧州 25 言語）。Silero VAD、話者分離もある。
- 音声合成（Qwen3-TTS、Irodori-TTS）と雑音除去もあるが、今回は使わない。作者自身が「雑音除去は ASR の前処理には向かない」と書いている。

設計:

- 文字起こしエンジンに「内蔵（speech.cpp）」を足す。`speech serve` を起動し、今の OpenAI 互換の文字起こしの経路（`/v1/audio/transcriptions`）で、VRCT が区切った 1 発話ずつを送る。**区切り（VAD）と、その後の翻訳・表示は今のまま。** Realtime の経路は使わない（今の処理の形を変えないため）。
- モデルの取得は speech.cpp 自身の機能に任せず、P4 のカタログで行う（進み具合の表示・接続先・検証を VRCT に揃える）。
- **Whisper（CTranslate2）は既定のまま残す。** speech.cpp は追加の選択肢。

先に確かめること（入れるかどうかはこの結果で決める）:

1. 日・英・韓・中の短い発話で、Qwen3-ASR 0.6B と今の Whisper（`large-v3-turbo-int8`）の精度と 1 発話の遅延を比べる。
2. VRChat を動かしながらの負荷（Vulkan で GPU を取り合う）。
3. v0.10 と若いので、API の形が変わる頻度。版を固定して同梱する。

---

## P6. OCR: まず評価

### 候補

| | 今の RapidOCR（PP-OCRv6 small） | Indra OCR 1.1 | Xiaomi-OCR-0 | YomiToku v0.16 |
|---|---|---|---|---|
| 作り | 検出 + 認識 | 検出 + 認識 + 行の分類。全体で約 76MB | 0.8B の VLM。ページ全体を Markdown で出す | 日本語の文書向け。検出 + 認識 + レイアウト。軽量モデル（`parseq-tiny`）あり |
| 動かし方 | ONNX Runtime | ONNX Runtime（GPU 不要） | transformers / vLLM。GGUF はコミュニティ製 | PyTorch。検出は ONNX にできる |
| 言語 | 日英韓中 | 80 以上。**言語ごとの数値は未確認** | 例は中・英だけ。**日・韓は未確認** | 日本語（と英語） |
| ライセンス | Apache-2.0 | コードは Apache-2.0、**重みは条件つき**（研究・個人・小規模な事業は無料） | Apache-2.0 | **CC BY-NC-SA 4.0（非商用）**。商用は別のライセンス |
| VRCT に載せるとき | 今のまま | 同じ ONNX Runtime に乗る | P5 の `llama-server` に画像を渡す | Rust へ載せるには ONNX への書き出しと前後処理の移植が要る |

- YomiToku v0.16.0 の新機能（紙の湾曲・歪みの補正）は、撮影した書類が対象。VRChat の吹き出しは平らな画面の文字なので、この補正は効かない。
- **YomiToku は非商用のライセンス。** MIT の VRCT に同梱できず、支援（Patreon / FANBOX）のある VRCT が「非商用」に当たるかは作者のガイドラインの判断になる。評価の対象には入れるが、採用するなら作者への確認が先。
- Indra も重みに条件がある。評価は進め、採用するなら Datalab への確認が先。

### 評価のやり方

手元の吹き出しのデータ（`docs/ocr_dataset_collection.md` の収集分）から、日・英・韓・中の評価用の組を作る（正解の文字つき）。YOLOX で切り出した吹き出しの画像を、各エンジンの Python の公式実装にそのまま渡して比べる（Rust への移植は評価の後）。

見るもの:

1. 文字の正解率（言語ごと）。
2. 1 枚あたりの時間（CPU、GPU）。
3. VRChat を動かしながらの負荷。

評価のスクリプトは `tools/` に置く（配布物には入らない）。**今の RapidOCR より良くならないものは入れない。** 結果は `docs/` に記録する。

### 評価の後（採用するものがあれば）

- 差し替えの境目は 1 つ: **「切り出した吹き出しの画像 → 文字と信頼度」**。検出（YOLOX）と、その後の翻訳・表示は今のまま。
- 設定に `OCR_ENGINE` を 1 つ足す。モデルは P4 の仕組みで取得し、同梱しない。

---

## 実装の分担（承認後）

司令塔（このセッション）は、段階ごとに作業を切って implementer（sonnet）へ渡し、tester と reviewer を独立に回す。書き手は 1 つの checkout に 1 つ。

| 段階 | explorer | architect | implementer | tester | reviewer | 実機 |
|---|---|---|---|---|---|---|
| P0 | 済 | 不要 | 1（座標ロック）+ 1（cherry-pick 類） | ○ | ○ | プロキシ |
| P1 | 済 | 不要 | 1 | ○ | ○ | — |
| P2 | 1（今の MSKB との見た目の差分） | ○（Input と種別） | 土台 → 修正 → キーボード → 見た目の順に 1 つずつ | ○ | ○ | VR |
| P2.5 | 1（今の字幕の経路） | ○（表示の形の持ち方） | 見た目の案の確認 → 1 | ○ | ○ | VR |
| P3（作る場合） | — | 不要（この文書で足りる） | 確認用の実行ファイル → P3-0 の後に本体 | ○ | ○ | AMD |
| P4 | — | 不要 | バックエンド 1 → UI は引き継ぎ文書（済み） | ○ | ○ | 実回線 |
| P5 | — | ○（プロセス管理） | 評価 → 1 | ○ | ○ | GPU 各社 |
| P6 | — | 評価の後に | 評価のスクリプト 1 | ○ | ○ | — |

完了の条件は `AGENTS.md` のとおり（clippy を `-D warnings`、変更した crate のテスト、契約テスト、UI のビルド、独立したレビュー。実機が要るものは「未確認」と明記して返す）。

---

## 残っている確認

1. エンジンの評価をいつ始めるか（P1 と並行か、P2 の後か）。AMD の所有者への依頼が要る。
2. CPU だけで使っている利用者の割合が、テレメトリーで分かるか（おすすめのモデルを決める材料）。
3. YomiToku と Indra のライセンス: 評価の結果が良かった場合、作者への確認を誰が行うか。
