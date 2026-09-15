# VRCT バックエンド（Python）再評価レビュー

- 対象: `src-python/` 全体（develop `e1fa1e4a` 時点）
- 実施日: 2026-09-14
- 前回レビュー: [`backend_review_2026-08-27.md`](./backend_review_2026-08-27.md)
- 観点: **構造面 / 処理速度面 / 処理のパイプライン**
- ベースライン: バックエンドテスト **709 件全パス**（39 秒）

## ステータス記号

| 記号 | 意味 |
|---|---|
| ⬜ | 未着手 |
| 🟡 | 着手中 |
| 🟢 | 修正済み（コミット SHA を併記） |
| ⛔ | 対応不要と判断（理由を併記） |

---

## エグゼクティブサマリ

前回レビュー（2026-08-27）以降の改善は実際に効いている。本再評価で確認した「良くなっている点」:

- **モジュール間の循環依存はゼロ**。層は `mainloop → controller → {config, model, device_manager, errors, models/*}` の一方向で、`errors.py` は標準ライブラリのみに依存する完全な葉。
- **`models/` の config 依存はほぼ解消済み**。`models/` 配下から `config` を import しているのは 1 ファイルのみ（後述 S-4）。他は全て `model.py` 側から値を注入する設計どおりに完成している。
- **メッセージ処理の 3 重複は解消済み**。`MessageDirectionSpec` により mic/speaker/chat の差分が 1 箇所に集約された（前回項目 25）。
- **パイプラインの中継段は最小限**。キュー境界は「録音コールバック → 文字起こしスレッド」の 1 回だけで、以降は関数呼び出し。過剰なコピーや無意味な抽象層は無い。
- **ロックの粒度は概ね妥当**。`pyaudio_op_lock` は PyAudio の open/close/stop の瞬間だけを直列化しており、読み取りループは絞っていない。

したがって **「大まかな構造的問題は解消されている」という認識は正しい**。本レビューで残ったのは、性質の異なる次の 3 種類である。

1. **起動時・異常時に効く実害**（P-1 〜 P-4）— 小さく直せて、効果が具体的。
2. **コピペ重複の残り**（S-1 〜 S-3）— 分割ではなくテーブル/レジストリ化で約 1000 行が消える。
   ただし **S-1 は実際にやってみたら見積もりが大きく外れ、巻き戻した**（S-1 の項参照）。
   この「約 1000 行」という数字を根拠に着手しないこと。
3. **計測の欠落**（M-1）— 以降の性能改善の判断基盤そのもの。

また、前回「大規模構造変更なので着手前に個別スコープ相談が必要」としていた項目 33〜36 の 4 つは、**現在のコードを実測した結果、3 つが不要、1 つが既に完了間近**と判定を改める（後述「対応不要と判断した項目」）。

---

## 優先度サマリ

| # | 項目 | 規模 | 状態 |
|---|---|---|---|
| M-1 | ホットパスの所要時間計測を追加 | +数十行 | 🟢 `93eb9112` |
| M-2 | 候補言語ごとの ASR 呼び出し内訳をログに追加 | +15 行 / 1 ファイル | 🟢 `d86db2ad` |
| P-1 | `available_releases` を init_mapping から除外 + getter 失敗の隔離 | +10 行 / 2 ファイル | 🟢 `86a91ca0` |
| P-2 | `Model.init()` の失敗後再試行を止める | +6 行 / 1 ファイル | 🟢 `d66d4d6c` |
| P-3 | 翻訳フォールバックの最大 2 秒 sleep を廃止 | 数行 | 🟢 `5139ece3` |
| P-4 | `shutdown()` に `stopWatchdog` を追加 | 1 行 | 🟢 `28b836c3` |
| S-1 | 文字起こしエンジンのレジストリ化 + `OpenAI_Compatible` 編入 | **−600 行** / 4 ファイル | ⛔ **一度実装したが巻き戻し**（下記） |
| S-2 | UI 契約の整合テスト 1 本 | 新規 80 行 | ⬜ |
| S-3 | トグル 23・数値 setter 12・委譲 35 のテーブル化 | −300 行 / 1 ファイル | ⬜ |
| P-7 | 文字起こし結果が配信されず埋もれる（push/pop の非対称） | +10 行 / 2 ファイル | 🟢 `3e8413a3` |
| P-8 | 遅延時の無駄な中間 ASR をドレイン単位で畳む | +15 行 / 1 ファイル | 🟢 `942cf224` |
| P-9 | 結果がまとめてドッと出る（1回の呼び出しで ASR を複数回まわす） | +10 行 / 1 ファイル | 🟢 `4bb8cbc6` + VAD 経路 `f5e2e2f3` |
| P-5 | 複数ターゲット言語の翻訳を並列化 | +20 行 / 1 ファイル | 🟢 **再導入・実機検証済み `f5e2e2f3`**（1 回目 `73366d0a` は回帰、`afa73518` で取り消し） |
| S-4 | `models/obs` の config 依存を注入に | 30 行 / 3 ファイル | ⬜ |
| S-5 | `device_manager.py` のコメントを実態に合わせる | 3 行 | ⬜ |
| P-6 | `Clipboard.stop()` を追加し shutdown から呼ぶ | 8 行 / 2 ファイル | ⬜ |

---

## M. 計測

### 🟢 M-1 [最優先] ホットパスに所要時間の計測が一切ない（`93eb9112`）

`perf_counter` / `time.time()` / `elapsed` / `duration_ms` を
`transcription_transcriber.py` / `controller.py` / `translation_translator.py`
に対して grep した結果、**ヒット 0 件**。

現存する計装は次の 2 つだけで、いずれも所要時間を持たない:

- `audio_vad.py:325-328` の `diagnostic_callback` → `process.log` に `speech_start` / `speech_end` を出力（VAD の区間判定のみ）
- `transcription_transcriber.py:494-499` の `[ASR-stats]` → **成功率のみ**、時間は記録していない

```python
# transcription_transcriber.py:495-499
printLog(
    f"[ASR-stats][{'speaker' if self.speaker else 'mic'}][{self.transcription_engine}] "
    f"this_call={'success' if succeeded else 'failure'} "
    f"attempts={self.asr_attempts} successes={self.asr_successes} rate={success_rate:.1f}%"
)
```

**実害**: 「発話終了 → 画面表示」の所要時間の内訳（VAD hangover / ASR / 翻訳 / オーバーレイ生成）を数字で言えない。
VAD 導入の 1 回目・2 回目が「体感が遅い」という主観だけで判断できずに終わった経緯は、この計測欠落が直接の原因である。
以降の性能改善（P-3 / P-5 など）の効果測定も、現状では実施できない。

**対応方針（案A を採用）**: ASR 呼び出し以降を測り、`[latency]` として `process.log` に 1 行出す。
既存の `printLog` に載せるだけなので新規機構は不要。

```
[latency][mic] asr=890ms translate=340ms output=25ms total=1255ms
```

- `asr=` … `AudioTranscriber._finalizeAndTranscribe` のプロバイダ呼び出し。成功時は `best` dict に
  `asr_ms` として載せ、`getTranscript()` → `transcript_fnc` → `Controller._processMessage` まで運ばれる
  （既存の `recognition_error` と同じ作法）。失敗時は `[ASR-error]` 行に付記。
- `translate=` / `output=` … `Controller._processMessage` で計測。`output` は翻訳以外の全て
  （transliteration / OSC / オーバーレイ生成 / クリップボード / UI 配信 / WebSocket / ロガー）。
- `chat` には ASR 段が無いため `asr=` を省略する。早期 return（ワードフィルタ等）では出力自体が
  無いので計測行を出さない。

**案B（VAD の `speech_end` からの通し計測）は見送り**。`VadSegmenter` のタイムスタンプをキュー経由で
`AudioTranscriber` まで運ぶ必要があり、パイプラインのデータ構造に手が入る。VAD の hangover は
固定値（約 0.77 秒）なので、当面は上記 `total` への足し算で評価できる。案A の実測で内訳が
足りないと分かった時点で改めて検討する。

---

## P. 処理速度 / 実行時の実害

### 🟢 P-1 起動完了通知が GitHub API の応答待ちで最大 70 秒ブロックしうる（`86a91ca0`）

`Controller.init()` の最終行 `controller.py:4868` が `updateConfigSettings()` を呼ぶ。

```python
# controller.py:747-757
def updateConfigSettings(self) -> None:
    settings = {}
    for endpoint, dict_data in self.init_mapping.items():
        response = dict_data["variable"](None)   # ← try/except なし
        result = response.get("result", None)
        settings[endpoint] = result
    self.run(200, self.run_mapping["initialization_complete"], settings)
```

`init_mapping` は `mainloop.py:563` で `/get/data/` 前方一致の全エンドポイント。
ここに `/get/data/available_releases`（`mainloop.py:224`）が含まれており、その実体は
`Controller.listAvailableReleases` → `Model.listAvailableReleases`（`model.py:1645`）
→ `Model._fetchGithubReleases`（`model.py:1600-1610`）で、**GitHub API への同期 HTTP リクエスト**である。

```python
# model.py:1605   _HTTP_TIMEOUT = (10, 60)  (model.py:69)
response = requests_get(config.GITHUB_RELEASES_LIST_URL, timeout=_HTTP_TIMEOUT)
```

つまり UI のローディング画面を解除する `/run/initialization_complete` が、**最悪 70 秒ネットワーク待ちで遅れる**。
しかも同じ `_fetchGithubReleases` を呼ぶ `checkSoftwareUpdated()` は、まさにこれを避けるために
`controller.py:4761-4772` でバックグラウンドスレッドへ追い出されている。**その意図が最終行で打ち消されている。**

さらに `controller.py:750` に try/except が無いため、いずれかの getter が例外を投げると `init()` がそこで死に、
`/run/initialization_complete` が永久に送られず **UI がローディング画面のまま固まる**。
現状は全 getter が内部で例外を握っている（`listAvailableReleases` は `model.py:1664-1665` で握る）ため
直ちには発火しないが、**getter を 1 つ追加するだけで踏める構造**である。

**対応方針**:
1. `init_mapping` から `/get/data/available_releases` を除外する（`mainloop.py:563` に除外集合を足す）。
   フロント側は `src-ui/logics/useReceiveRoutes.js:157` が `/run/initialization_complete` を受けているだけなので UI 変更不要。
2. `controller.py:750` を try/except で包み、失敗した endpoint は `None` を入れて続行する。

**除外が 1 件で足りることの確認**: `init_mapping` の 131 個の `/get/data/*` のうち、
ネットワークに触れうるハンドラは 8 個。うち認証キー型 5 エンジンのモデル一覧は
`_getTranslationEngineModelList`（`controller.py:2601-2603`）が `getattr(config, ...)` を
返すだけで**ネットワークを叩かない**。LMStudio / Ollama の 2 つは実際に HTTP を叩くが、
`timeout=0.2` で上限が固定されている（`translation_lmstudio.py:20,32`、`translation_ollama.py:19`）。
**桁違いに突出しているのは `available_releases`（timeout (10, 60)）だけ**であり、除外対象はこれで過不足ない。

---

### 🟢 P-2 `Model.init()` の部分失敗でワーカースレッドが無限リークする（`d66d4d6c`）

`Model.init()`（`model.py:876-944`）は `self._inited = True` を **最終行 `model.py:944` でのみ**立てる。
一方 `model.py:897-898` で `AudioLifecycleWorker()` を 2 つ生成し、そのコンストラクタ（`model.py:240-246`）は
**daemon スレッドを即 start する**。

```python
# model.py:883
if getattr(self, '_inited', False):
    return
...
# model.py:897-898   ← ここで daemon thread が 2 本起動する
self.mic_lifecycle_worker = AudioLifecycleWorker()
self.speaker_lifecycle_worker = AudioLifecycleWorker()
...
# model.py:941-944   ← ここまで到達して初めてフラグが立つ
self.clipboard = Clipboard()
self.telemetry = Telemetry()
self._inited = True
```

したがって `model.py:902` 以降（`Translator()` / `Overlay()` / `OverlayImage()` / `Watchdog()` /
`OSCHandler()` / `Clipboard()` / `Telemetry()`）のいずれかが例外を投げると:

1. `_inited` は False のまま
2. `_bootstrapModel()` は例外を握りつぶして続行（`controller.py:4228-4230`）
3. 以降**すべての `ensure_initialized()` 呼び出し**（`model.py:946-955`、public メソッドのほぼ全てが冒頭で呼ぶ）が `init()` を先頭から再実行
4. そのたびに `AudioLifecycleWorker` が 2 つ新規生成され、**前回のスレッドは誰からも参照されず永久に生き残る**
5. `Controller.shutdown()`（`controller.py:429-435`）が停止できるのは最新の 1 組だけ

`ensure_initialized()` 自身も例外を握りつぶす（`model.py:952-955`）ため、半初期化状態のまま無限に再試行が続く。

**実害**: 壊れたインストールや SteamVR 異常で `OverlayImage(config.PATH_LOCAL)`（フォント/画像をディスクから読む）や
`Clipboard()`（openvr に触る）が失敗すると、スレッドが際限なく増えプロセスが重くなる。
さらに終了時に古いワーカーが PyAudio 操作の途中でプロセス終了に巻き込まれる経路が残る
（`controller.py:395-404` で ActiveEndpointTracker について既に踏んだ access violation と同種）。

**対応方針**: 「一度失敗したら再試行しない」フラグを入れる。

```python
if getattr(self, '_inited', False) or getattr(self, '_init_failed', False):
    return
try:
    ...本体...
    self._inited = True
except Exception:
    self._init_failed = True
    raise
```

---

### 🟢 P-3 翻訳フォールバックが最大 2 秒を純粋な sleep で捨てる（`5139ece3`）

```python
# model.py:1368-1383
else:
    max_retries = 20  # 0.1s間隔で最大2秒。CTranslate2が使用不可な場合の無限ループを防ぐ
    for _ in range(max_retries):
        translation = self.translator.translate(translator_name="CTranslate2", ...)
        if isinstance(translation, str):
            break
        if translation is None:
            break  # CTranslate2もこの言語ペア未対応。リトライしても変わらない
        sleep(0.1)
```

`translateCTranslate2`（`translation_translator.py:484-507`）はモデル未ロード時に
`is_loaded_ctranslate2_model` が False なので **即座に `False` を返す**。
つまり CTranslate2 が未ロード（モデル切替中・ダウンロード未完了・重みファイル破損など）の場合、
この 20 回のループは **1 回も意味のある処理をせずに 2 秒を sleep で消費する**。

さらにこのフォールバックは `getInputTranslate` のターゲット言語ループ（`model.py:1406-1419`）の**内側**にあるため、
3 言語有効なら最悪 6 秒。その間、パイプラインが単一スレッド構造（後述 PL-1）であるため**文字起こしも止まる**。

**対応方針**: リトライの前に `translator.isLoadedCTranslate2Model()` を確認し、
未ロードなら sleep せず即座に抜ける。「一時的な失敗を待つ」というリトライ本来の意図は、
モデルがロード済みの場合にのみ成立する。

---

### 🟢 P-4 `shutdown()` が watchdog を止めない（`28b836c3` + フォローアップ `42eddde6`）

> **実機検証で最初の修正が不十分と判明した（2026-09-14）**。詳細は下記「フォローアップ」参照。

`Controller.init()` は `controller.py:4255` で `self.startWatchdog()` を呼ぶが、
`Controller.shutdown()`（`controller.py:383-469`）に対応する停止が無い。
`controller.py:453-456` で OSC / OBS / WebSocket / Overlay は明示停止しているが、watchdog だけ漏れている。

結果、`Watchdog` が仕掛けた `faulthandler.dump_traceback_later(interval + 15s)`（`model.py:2201-2212`）の
タイマーが武装したまま残る。フロントエンドは終了操作と同時に feed を止めるため、
プロセスが 35 秒以上生き残ると **正常終了なのに `freeze_trace.log` に偽のフリーズダンプが出る**。

**実害**: フリーズ調査用ログにノイズが混じる。この計装は `model.py:71-82` の長いコメントが示すとおり
調査の一次情報源であり、汚染のコストは低くない。

**対応方針**: `controller.py:456` の直後に 1 行。

```python
self._stopServiceForShutdown(model.stopWatchdog, "watchdog")
```

#### フォローアップ（`42eddde6`）— 最初の修正では目的を達成できていなかった

実機ログに次の行が出て発覚した。

```
shutdown: watchdog の停止が 5.0s でタイムアウトしました(プロセス終了時に破棄されます)
```

原因は `Model.stopWatchdog()` 内の順序:

- `Watchdog.start()` は末尾で `time.sleep(self.interval)` する（既定 20 秒、`watchdog.py:55`）
- `threadFnc.stop()` は `loop` フラグを降ろすだけで、この sleep を中断できない（`model.py` の `threadFnc.stop`）
- よって `join()` は最大 `interval` 秒ブロックする
- `faulthandler.cancel_dump_traceback_later()` は**その `join()` の後ろ**にあった
- `_stopServiceForShutdown` は 5 秒で諦めるため、**解除は一度も実行されなかった**

つまり「偽のフリーズダンプを防ぐ」という当初の目的が達成できておらず、
さらに **P-4 以前には無かった 5 秒の終了遅延を新たに作り込んでいた**。

解除は `faulthandler` に対する操作でスレッドとは独立しているため `join` より前に移し、
`join` には上限（`_WATCHDOG_JOIN_TIMEOUT_SEC = 1.0` 秒）を付けた。
daemon thread なので待ちきれなくてもプロセス終了時に破棄される。

**教訓**: 「停止処理を呼ぶ」だけでは不十分で、**その停止処理自体が制限時間内に完了できるか**まで
確認する必要がある。`_stopServiceForShutdown` のタイムアウトは shutdown を守るが、
包んだ処理の目的が達成されることは保証しない。

---

### 🟢 P-5 複数ターゲット言語が逐次翻訳される — 再導入・実機検証済み（`f5e2e2f3`）

> **2026-09-15 実機検証で効果を確認**。同一セッション内に 1 言語と 3 言語の両方が含まれ、
> 同一エンジン（Google）・同一ネットワーク条件での直接比較ができた。
>
> | 有効言語 | `translate=` | 平均 |
> |---|---|---|
> | 1 言語 | 1622 / 1077 / 730 ms | 約 1143ms |
> | 3 言語 | 1491 / 2019 / 1565 / 1662 / 1379 / 594 / 1347 ms | **約 1437ms** |
>
> **3 言語でも約 26% 増**（逐次なら 3 倍 = 約 3.4 秒。修正前の同条件は `translate=3544ms`）。
> 異常 0 件（フリーズ / `ProtocolError` / スレッド停止いずれも無し）、ASR 成功 11 / 配信 11。

**前提**: フォーク側で `Tse.session` を `threading.local()` へ分離したこと
（misyaguziya/translators `f3697bd`、requirements の pin も追従）。**これ無しでは成立しない。**

#### 1 回目（`73366d0a`）はなぜ失敗したか — 取り消し済み（`afa73518`）

> **実機で明確な回帰**。`ThreadPoolExecutor` による並列化を入れたところ、
> 35 秒フリーズが発生し `freeze_trace.log` に記録された。

**原因（`freeze_trace.log` + `error.log` から確定）**:

- `model.py:1486`（追加した `future.result()`、タイムアウト無し）でスレッドが無期限ブロック
- 同時刻、別スレッドが `translators/server.py:673` の `self.session.post()` で停止
- `error.log` に `urllib3.exceptions.ProtocolError: None`（コネクションプール破壊の典型）

`translators` ライブラリは `self.session`（`requests.Session`）を**モジュールレベルの
シングルトンに 1 本だけ持ち、全呼び出しで使い回している**（`server.py:533` で生成、
548/673 で使用）。**`requests.Session` はスレッドセーフではない**。並列化により 3 スレッドが
同じセッションを同時に叩き、コネクションプールを壊していた。逐次実行なら 1 度に 1 呼び出し
なのでこの問題は起きない。

さらに、パイプラインが単一スレッド（PL-2）であるため、翻訳がハングすると
**文字起こしごと停止**する。実機ログでは ASR 14 件に対し配信 5 件、終了時に
`Mic transcription thread did not terminate within timeout` が出ていた。
ユーザーの「動作したりしなかったり」はこれ。

**Google / Bing / Papago は全て `translators` ライブラリ経由**なので、この方式での並列化は
そもそも採れない。多言語時の高速化をやるなら別の設計が要る:

- エンジンごと・スレッドごとにセッションを分離する（ライブラリの構造上、簡単ではない）
- `translators` を介さず自前で HTTP を叩く
- バッチ API を持つエンジン（CTranslate2 の `translate_batch` に複数 `target_prefix`）を使う

いずれも**実機検証を前提に、単独で切り出して**検討すること。

**教訓**: 「I/O 待ちだから並列化すれば速くなる」は、**その I/O を行うクライアントが
スレッドセーフな場合にのみ成立する**。サードパーティ製ライブラリの内部状態（セッション、
コネクションプール、クッキー、言語マップのキャッシュ）を確認せずに並列化してはいけない。
ユニットテストでは `getTranslate` をスタブしていたため、この問題は一切検出できなかった。

> **実測値（2026-09-15、3 言語 + Google）**: `translate` が **約 3.9 秒**（1 言語あたり約 1.3 秒 × 3）。
> 逐次ループであることが数字でそのまま裏付けられた。翻訳 OFF 時は `translate=0ms` なので、
> この差は純粋に翻訳である。

`ThreadPoolExecutor(max_workers=有効なターゲット言語数)` で並列化した。クラウドエンジン
（Google / DeepL / Bing / Papago / LLM 系）はネットワーク I/O 待ちが支配的なので、概ね 1 言語分の時間で済む。

**実装上の必須条件**:
- 添字はターゲット言語スロットに対応するため、**完了順ではなく投入順で結果を取る**。
- 例外は最初の 1 件をそのまま送出する（`Controller._processMessage` が VRAM 不足エラーを検出する契約）。
- 1 言語のときはスレッドを起こさず直接呼ぶ（既定構成では常にこちら）。

**CTranslate2 は短縮されない**。`_ctranslate2_lock` で直列化されるため。このロックは
`translateCTranslate2()` が共有トークナイザの `src_lang` を書き換えてから使うため外せない
（外すなら言語ごとに別インスタンスを持つか、`translate_batch` に複数 `target_prefix` を
まとめて渡すバッチ化が必要。別途検討）。

---

### 🟢 P-7 文字起こし結果が配信されず埋もれる（`3e8413a3`）

> **M-1 の計装が炙り出した既存バグ**。実機ログで `[ASR-stats][speaker]` が 4 件すべて成功して
> いるのに、ユーザーに届いたメッセージは 1 件だけだった。

push と pop が非対称だった。

- **生成側**: Google の `interim_send()` は**キューから取り出したチャンクごと**に走る
  （`transcription_transcriber.py` の非 VAD ループ）。パイプラインが遅れてキューに複数チャンクが
  溜まっていると、1 回の `transcribeAudioQueue()` で複数件が `transcript_data` に積まれる。
- **配信側**: 呼び出し元（`model.py` の `sendTranscript`）は `_transcribe()` が True を返すたびに
  `getTranscript()` を 1 回しか呼んでおらず、**1 件しか取り出していなかった**。

結果として:

1. 残りは「次に ASR が成功した時」まで配信されず、**発話が止まるといちばん完全なテキストが
   出ないまま埋もれる**
2. `getTranscript()` は `pop(-1)` で最も古い 1 件を返すため、**表示がバックログの分だけ過去にずれる**
3. `transcript_data` は `max_phrases`（既定 10）で頭打ちになり、溢れた分は古い順に**無言で捨てられる**

配信側を「溜まっている分を全て取り出す」ループに変更（`hasTranscript()` を追加）。
`_transcribe()` の戻り値で分岐しないのは、前回の呼び出しが残した分も確実に吐き出すため。

### 🟢 P-8 遅延時の無駄な中間 ASR をドレイン単位で畳む（`942cf224`）

P-7 で全件配信にしたことで、`interim_send` が積んだ**中間結果も全て配信される**ようになった。
これらは同じ発話の育っていく途中経過であり、配信されると 1 件ずつ翻訳まで通る（1 件 1〜3 秒）。
遅れているほど中間結果が増えるため、そのままでは遅延が雪だるま式に悪化する。

`interim_send()` をキューのドレイン単位で 1 回に畳んだ（`audio_queue.empty()` を条件に追加）。
チャンクが 1 個ずつ届く通常時は get 直後にキューが空なので**従来と同じ挙動**になり、
遅れている時だけ「後でより完全なテキストに置き換わるだけの中間結果」への ASR が省かれる。
Google 無料エンドポイントへのリクエスト数が減るため、既知の信頼性問題にも有利に働くはず。

**あわせて `unsent` フラグを追加**。`reset_only()` は「この `last_sample` は直前に
`interim_send` 済み」を前提に送信せずリセットするが、畳み込みでその前提が崩れる。
未送信のまま無音ギャップを跨ぐと**完成したフレーズが無言で消える**ため、
未送信で残っている場合は送ってからリセットする。

> **実機検証が特に必要**。Google の挙動は過去に何度も実機でしか分からない形で裏切られている。

### P-8 / P-9 は当初 VAD 経路に入っていなかった（2026-09-15 に是正）

`transcribeAudioQueue()` には **VAD 経路と エネルギー閾値経路の 2 つの独立したループ**がある。
P-8・P-9 は後者にしか入れておらず、**VAD を有効にすると一切効いていなかった**。

実機ログ（VAD を mic/speaker 両方で有効、翻訳は CTranslate2 / CPU）で次が観測された:

- 2 件の `[latency][speaker]` が**同一ミリ秒**で配信（バースト）
- その直後に `[latency][mic] asr=4039ms translate=30482ms total=34524ms`

VAD 経路にも P-9 と同じ「1 フレーズ確定したら即座に返る」を入れて是正した（`f5e2e2f3`
に P-5 再導入とまとめて入ってしまっている。コミットメッセージには記載漏れ）。

**教訓**: 同じ関数の中に独立した分岐が 2 本ある場合、片方だけ直すと
「設定次第で直っていない」状態になる。`vad_segmented` のような
**モードで分かれる実装は、両方の経路を必ず確認する**こと。

### `translate=30482ms` はロック待ちであって推論時間ではない

このセッションはターゲット言語 1 つ・CTranslate2（CPU）で、**並列化の経路も
`translators` も通っていない**。単発の CTranslate2 推論が 30 秒かかったのではなく、
`_ctranslate2_lock`（`translation_translator.py`）の待ち時間が大半である。

`Translator` はプロセスに 1 つで、mic と speaker が同じロックを奪い合う。このロックは
`translateCTranslate2()` が共有トークナイザの `src_lang` を書き換えてから使うため外せない。
**VAD を両チャンネルで有効にすると、CPU の CTranslate2 では供給が処理能力を超える。**

`[latency]` の `translate=` はロック待ちを含むため、この区別ができない。切り分けたい場合は
ロック取得前後の計測を分けて出す必要がある（未実装）。

### 🟢 M-2 speaker 側が重い真因は「候補言語ごとに ASR を複数回叩く」だった（`d86db2ad`）

実機ログで speaker の `asr=` が mic の約 3 倍（mic 772〜1331ms / speaker 1957〜5897ms）
だった理由を、当初「VAD セグメントが長いから」と**誤読していた**。真因は候補言語のループ。

- **mic** は `SELECTED_YOUR_LANGUAGES`（通常 1 つ）を候補にする → `model.py:806-808`
- **speaker** は `SELECTED_TARGET_LANGUAGES` を候補にする → `model.py:868-870`

`_finalizeAndTranscribe` は候補言語を順にループして `provider.transcribe()` を呼ぶ。
**回数はエンジンによって変わる**:

| エンジン | `is_definitive` | N 候補での実際の呼び出し回数 |
|---|---|---|
| **Google** | **常に False**（「検出された言語」の概念が無い） | **必ず N 回** |
| Whisper（ローカル / API） | 検出言語が要求言語と一致すれば True | 1〜N 回（早期 break） |
| Deepgram | 常に True（1 呼び出しで多言語判定） | 常に 1 回 |

つまり**ターゲット言語を 3 つにすると、mic は翻訳が 3 倍、speaker は ASR が 3 倍**になる。

**ASR の並列化は見送り**。ローカル Whisper はモデルが 1 つで CPU/GPU を奪い合うだけで、
そもそも早期 break で 1 回しか走らないことが多い。必ず N 回叩く Google は並列化の効果が
最も大きいが、**無料エンドポイントの信頼性問題が既知**（同セッションで ASR 失敗 7/22）で、
同時リクエストを 3 倍にするのは悪化方向。翻訳の並列化で一度実機を壊した直後に同じ性質の
賭けをする価値は薄い。`is_definitive` という既存のプロバイダ契約が engine 差を正しく
吸収しているので、**エンジンごとの分岐を足す必要もない**。

代わりに計測の内訳だけ追加した。`[ASR-stats]` / `[ASR-error]` に
`calls=実行回数/候補数` と言語ごとの所要時間（失敗時は `nomatch` / `error`）を出す。
挙動は変えない。これで「早期 break が実際に効いているか」「どの言語が遅いか」
「候補言語を減らす効果」が数字で判断できる。

### `error.log` の `OSError: [Errno 22]` 大量発生は原因ではなく結果

上記の 34 秒スタックの **後** に始まり、ちょうど 50 回で止まっている。
`utils.py` の `_MAX_CONSECUTIVE_STDOUT_FAILURES = 50` に到達し、
「フロントエンド消失」と判定して `os._exit(1)` した設計どおりの動作。
バックエンドが 34 秒応答しなくなった → フロントエンドが落ちた/読まなくなった →
stdout への書き込みが全て失敗、という連鎖。

```python
# model.py:1406-1419
for value in target_languages.values():
    if value["enable"] is True:
        ...
        translation, success_flag = self.getTranslate(...)   # ← 1 言語ずつ直列
```

ターゲット言語は最大 3 スロット（`config.py:1092` の `["1", "2", "3"]`、既定は 1 つだけ有効）。
3 言語を有効にすると、API エンジンならネットワーク往復が 3 回、CTranslate2 なら推論が 3 回、素直に直列で走る。

CTranslate2 側は `translate_batch` がバッチを受け取れる API であるにもかかわらず、1 件しか渡していない:

```python
# translation_translator.py:502
results = self.ctranslate2_translator.translate_batch([source], target_prefix=[target_prefix])
```

**対応方針（2 案、どちらも P-5 として扱う）**:
- API エンジン: `ThreadPoolExecutor` で言語ごとに並列化（I/O 待ちが支配的なので GIL の影響を受けない）
- CTranslate2: 複数の `target_prefix` を 1 回の `translate_batch` にまとめる

**注意**: `_ctranslate2_lock`（`translation_translator.py:141,450,490`）を単純に外してはならない。
`translation_translator.py:493` で `self.ctranslate2_tokenizer.src_lang = source_language` という
**共有可変状態**を書き換えてから使うため、ロックには実在の理由がある。
バッチ化はこの問題を回避する方向（1 回の呼び出しに畳む）なので相性が良い。

---

### ⬜ P-6 `Clipboard` の監視スレッドが停止されない

`Model.init()` の `model.py:941` で `Clipboard()` を生成 → `models/clipboard/clipboard.py:198-199` が daemon スレッドを start。
`_stop_monitoring` フィールド（`clipboard.py:190`）は存在するのに、**それを True にする public メソッドが無く**、
`shutdown()` からも呼ばれない。

**実害**: `shutdown()` が `model.shutdownOverlay()`（`controller.py:456`）で OpenVR を解放しようとした瞬間に、
Clipboard 側が `openvr_session.acquire()` を保持していると参照カウントが 0 にならず、
OpenVR が解放されないままプロセス終了になる。`clipboard.py:217-223` の docstring が自ら警告している状況そのもの。
ただし発生は「終了と SteamVR 起動検出が秒単位で重なる」狭い窓に限られるため優先度は低い。

**対応方針**: `Clipboard.stop()`（`_stop_monitoring = True` のみ）を追加し、
`shutdown()` から `_stopServiceForShutdown` 経由で呼ぶ。

---

## S. 構造 / 保守性

### ⛔ S-1 一度実装したが巻き戻した（2026-09-15）

> **結論: この指摘に従って実装したが、割に合わなかったため `a70f70e6` まで巻き戻した。**
> 破棄した実装は `backup/s1-discarded-20260915`（`5120e5ec`）に退避してある。

#### 何をやったか

下記の指摘どおり、`_TranscriptionEngineSpec` を新設して 4 エンジンの差分を集約し、
`init()` の文字起こし側・翻訳側の match/case もレジストリ走査へ置き換えた。
テストは 737 → 747 件へ増やし、実機検証（保存済みキーでの起動、DeepL/Groq の
`is valid/available` とモデル一覧反映）まで通した。**動くものはできていた。**

#### なぜ巻き戻したか

**1. 見積もりが外れた。** レビュー時点の「−600 行」に対し、実績は **controller.py −103 行**。
差の大半は `OpenAI_Compatible`（165 行分）を畳むのをやめたこと。レビューでは
「差分は `base_url` を渡す 1 点だけ」と書いたが、実際のコードを読むと
**モデル一覧が空の場合の扱いも違い**、汎用側へ入れると動作中の 5 エンジンの挙動が変わる。
無理に共通化できるものではなかった。

**2. 重複を消したつもりが、移しただけだった。** 公開メソッド 16 個を `setattr` で
動的生成したが、生成する側に `_TRANSCRIPTION_ENGINE_METHOD_NAMES` という
**16 個の名前一覧が必要**だった。名前の列挙は消えておらず場所が変わっただけで、
消えたのは本体の重複のみ。その対価として生成機構 52 行と、
`grep "def setGroqWhisperAuthKey"` が引けなくなる可読性の劣化を払っていた。
（指摘を受けて普通の `def` へ戻したところ、行数はほぼ同じ 4798 → 4801 行になった。
つまり**あの機構は払ったコストに対して何も買えていなかった**。）

**3. 不要な間接参照を作り込んでいた。** 巻き戻し前のコードレビューで 4 件検出され、
**全て S-1 の範囲に集中していた**:

| 箇所 | 内容 |
|---|---|
| spec の `fetch_models` | `config` 属性名を文字列で渡して `getattr` していた（隣の行の `authenticate` は直接参照しており、一貫していない） |
| `_fetchOpenAICompatibleTranscriptionModels` | 呼び出し先の既定値が `None` なのに、意味のない条件付き kwargs 展開 |
| `_TranscriptionEngineSpec.engine_key` | 一度も読まれないデッドフィールド |
| `required_config_attrs` | 1 エンジン・1 属性のためだけの汎用機構 + 文字列間接参照 |

バグ修正（P-1〜P-9）と計測（M-1/M-2）では過剰な抽象化をしていないのに、
**「リファクタ」と称した作業でだけこれが起きた**。目的が「重複を消す」になると、
手段が目的化する。

#### 教訓

- **行数削減を目的に、動いているコードへ間接参照を足さない。** 減った行数より、
  増えた間接参照のほうが高くつく。
- **「重複を消した」つもりが「重複を移した」だけになっていないか確認する。**
  名前・文字列・テーブルのどこかに同じ列挙が残るなら、消えていない。
- **着手条件を「将来エンジンが増えたら困る」ではなく「実際に事故が起きた」に置く。**
  今回は「エンジン追加時にコピペ差分が入るかもしれない」という想定で動いた。
  4 エンジンが逐語コピペである事実は変わらないので、**実際にコピペ起因の不具合が
  出た時点で、その具体的な壊れ方に合わせて直すほうが良い。**
- ただし **`init()` 側の match/case 撤去（`f5109748` / `3a83521e` / 適用ループ）は
  筋が良かった**。テーブルを引くだけで動的生成もラッパーも無く、
  「同じロジックがエンドポイントと `init()` の 2 箇所にある」という実在の重複を消していた。
  再挑戦するならこちらだけを切り出すこと。

---

#### 元の指摘（参考）

### ⬜ S-1 [最大の残り重複] 文字起こし API 4 エンジンが逐語コピペ、翻訳レジストリからも 1 エンジンが漏れている

`setGroqWhisperAuthKey`（`controller.py:1520-1566`）と `setOpenAIWhisperAuthKey`（`controller.py:1599-1645`）を
diff で突き合わせた結果、**47 行中の差分はエンジン名に由来する文字列だけ**であった。

```
$ diff <(sed -n '1520,1566p' controller.py) <(sed -n '1599,1645p' controller.py)
<     def setGroqWhisperAuthKey(...)          >     def setOpenAIWhisperAuthKey(...)
<         engine = "Groq_Whisper"             >         engine = "OpenAI_Whisper"
<         ... config.GROQ_WHISPER_BASE_URL    >         ... config.OPENAI_WHISPER_BASE_URL
<         ... SELECTABLE_GROQ_WHISPER_...     >         ... SELECTABLE_OPENAI_WHISPER_...
<         self.delGroqWhisperAuthKey()        >         self.delOpenAIWhisperAuthKey()
```

これが Groq / OpenAI / Custom / Deepgram の 4 本ある（`controller.py:1516-1898`、計 383 行）。
`del*`（`controller.py:1568-1579` 他）と `set*Model`（`controller.py:1584-1593` 他）も同様。
差分は「config 属性名 / base_url の取得元 / `keyword_filter` の有無 / `run_mapping` キー / Deepgram のみ言語一覧追加」の 5 点。

さらに **`init()` が同じ 4 エンジンの分岐を match/case でもう一度書いている**
（`check_transcription_engine` = `controller.py:4591-4674`、適用ループ = `controller.py:4688-4732`、計 150 行）。
翻訳側も `TRANSLATION_PROVIDER_REGISTRY` を持っているのに、`init()` の
`check_translation_engine`（`controller.py:4385-4488`）と適用ループ（`controller.py:4502-4577`）は
**レジストリを使わず match/case を再実装している**（180 行）。

加えて **`OpenAI_Compatible` だけが翻訳レジストリから漏れている**。
`controller.py:2892-3052`（165 行）は `_setTranslationEngineAuthKey`（`controller.py:2532-2578`）と論理的に同一で、
差分は「`authenticate` に `base_url` を追加で渡す」だけ。
`CONNECTION_PROVIDER_REGISTRY` 側は既に `connect_kwargs` という同種の逃げ道を持っている（`controller.py:2629`）。

**実害**: 文字起こしエンジンを 1 つ追加するたびに **約 130 行のコピペ + `init()` の 2 箇所に match/case 追加**が必要。
プロジェクトの状況として **Groq/OpenAI/Custom/Deepgram のフロントエンド UI は別の実装者がこれから着手予定**であり、
そこで差分（認証失敗時の `del*` 呼び出し漏れ、`updateTranscriptionEngine()` 呼び忘れ等）が入ると、
**4 本のうち 1 本だけ挙動が違う**という最も発見しにくいバグになる。

**対応方針**:
1. `models/transcription/` に `TRANSCRIPTION_PROVIDER_REGISTRY` を新設（`translation_providers.py` と同じ dataclass 形式）
2. `Controller._setTranscriptionEngineAuthKey` 等の共通実装を追加
3. `init()` の 2 つの match/case をレジストリ走査に置換
4. `OpenAI_Compatible` を `TRANSLATION_PROVIDER_REGISTRY` に `auth_kwargs` フィールド付きで編入

**規模**: controller.py 約 −650 行 / 新レジストリ +100 行。影響 3〜4 ファイル、テスト 4〜5 本。

**必須の制約 — grep 可視性を壊さないこと**:
`_SIMPLE_CONFIG_GETTERS` 方式でテーブル化したメソッドは `grep "def getUiLanguage"` ではヒットしない
（ヒットするのは `controller.py:194` のテーブル行だけ）。この開発は grep ベースで行われるため、
**メソッド名は動的生成（`setattr(Controller, name, ...)`）で必ず残し、本体だけを共通化する**こと。
メソッド名自体が消える形のレジストリ化は採用しない。

---

### ⬜ S-2 フロント / バックエンドのエンドポイント契約を検証するものが何も無い

両側とも既にテーブル駆動である:

- バックエンド: `mainloop.py:154-561` の `mapping`（エンドポイント文字列 → ハンドラ）
- フロントエンド: `src-ui/logics/configs/config_page_setter/ui_config_setter.js` の `SETTINGS_ARRAY`（**101 エントリ**、`base_endpoint_name` フィールド）
- URL 組み立て: `src-ui/logics/configs/config_page_setter/useSettingsLogics.js:74,81,88,94,152,154,202` が `/get/data/${base_endpoint_name}` 等を機械的に生成

しかし **バックエンド側に `src-ui/` を参照するテストは 1 本も無い**
（`src-python` 全体を grep して `ui_config_setter` / `src-ui` のヒットは docs 3 件のみ）。

**実害**: `base_endpoint_name` の綴り違いや `mapping` への追加忘れは **UI を手で触るまで検出されず 404 になる**。
101 項目の手動 UI 確認は現実的に行われないため、設定項目の片側追加が CI を通過し、リリース後に「その設定だけ動かない」形で発覚する。

**対応方針**: `src-python/test/test_ui_contract.py` を 1 本追加。
`ui_config_setter.js` を正規表現で読み、`logics_template_id`（`get_set` / `toggle_enable_disable` / …）から
期待エンドポイント集合を導出し、`mainloop.mapping` のキー集合に含まれることを assert する。
**本番コードの変更はゼロ。** 型生成器やビルドステップは追加しない（後述 ⛔ 参照）。

---

### ⬜ S-3 機械的に集約できるパターンが 3 系統残っている

前回の純粋 getter テーブル化（94 個）と同種のパターン。

**(a) enable/disable トグル 23 メソッド ≈ 138 行**
`controller.py:1360, 1366, 1372, 1946, 1952, 2015, 2021, 2170, 2176, 2353, 2359, 2500, 2506, 3113, 3119, 3126, 3132, 3189, 3195, 3202, 3208, 3215, 3221, 4134, 4140`
がいずれも `if config.X is False: config.X = True` / `return {"status":200,"result":config.X}` の完全同一形。

実害: トグルを 1 つ追加するたびに 12 行のコピペ。実際 `setEnableTranslation`（`controller.py:1318`、副作用あり）と
`setDisableTranslation`（`controller.py:1360`、純粋）のように**ペアが非対称に育っており**、
コピペ元を間違えると副作用が片側だけ落ちる。

**(b) 数値強制 setter 12 メソッド ≈ 168 行**
`controller.py:1959, 1973, 1987, 2246, 2260, 2429, 2443, 4038, 4052, 4066, 4080, 4106`
が `try: value = int/float(data) except: return VRCTError.create_error_response(...)` の同一形。
差分は「属性名 / int か float / ErrorCode / メッセージ / 後処理コールバック」の 5 つだけ。

実害: OBS 系 7 個は `_pushObsBrowserSourceSettings()` の呼び忘れが即
「設定変更が既存の OBS ページに反映されない」バグになる。現状その保証はコピペ精度のみ。

**(c) 翻訳レジストリへの 3 行委譲 35 メソッド ≈ 107 行**
`controller.py:2728-2817` の 30 メソッドは `return self._getTranslationEngineAuthKey("Plamo_API")` のような
厳密に 3 行の委譲で、5 エンジン × 6 種の直積。`TRANSLATION_PROVIDER_REGISTRY` から機械生成できる。

実害: エンジン追加時に「レジストリ 1 エントリ + `_ENGINE_MODEL_BINDINGS` 4 行 + 委譲 6 メソッド + `mainloop.mapping` 6 行」の
4 箇所同期が必要。委譲の書き忘れは 404 になるまで気付かない。

**規模**: 合計約 −300 行。
分割（ミックスイン / サブコントローラ化）は依然として不要。

> **着手前に S-1 の顛末（上記）を必ず読むこと。** 特に **(c)「委譲 35 メソッドの機械生成」は
> S-1 で失敗したのと同じ形**になる可能性が高い。生成する側にメソッド名の一覧テーブルが必要なら、
> **名前の列挙は消えず場所が移るだけ**で、grep 可読性だけを失う。
>
> 着手するなら、まず「生成後に名前の列挙がどこにも残らないか」を確認する。残るなら (c) はやらない。
> (a) トグルと (b) 数値 setter は**本体のロジックが完全に同一**で、テーブルの値が属性名と
> エラーコードだけなので (c) とは性質が違う（列挙が実際に消える）。
>
> なお既存の `_SIMPLE_CONFIG_GETTERS`（純粋 getter 94 個）は、テーブルが
> `{メソッド名: 属性名}` で**メソッド名がテーブルの値として意味を持つ**ため列挙は残っている。
> ただし `grep setEnableClipboard` でテーブル行に当たるので実害は小さい、というのが当時の判断。
> (c) も同じ形になるなら、同じ基準で「実害が小さいか」を測ること。

---

### ⬜ S-4 `models/obs` だけが config を直接 import している

`models/` 配下から `config` を import しているのは 1 ファイルのみ（grep で確認）:

```
src-python/models/obs/obs_browser_source_server.py:6:from config import config
```

使用箇所は同ファイル `:30,38,41,44,47,49,52,55` の 8 箇所で、すべて `getattr(config, "OBS_...", default)` 形式。
他の `models/` 配下は `Overlay(overlay_settings)`（`model.py:913`）、
`Watchdog(config.WATCHDOG_TIMEOUT, config.WATCHDOG_INTERVAL)`（`model.py:925`）のように
**すべて model.py 側から値を注入されており、設計意図どおりに完成している**。

**実害**: `models/` 配下で「config を import してよい」という前例が 1 つ残り続け、次に OBS 周りを触る人が踏襲する。
また `models/obs` の単体テストを書くとき config シングルトンを巻き込む（= `config.json` への書き込み、後述 S-5 関連）。

**対応方針**: 設定 8 項目を起動時に `model.startObsBrowserSourceServer(host, port, settings)` で渡す形に変更。
`controller.py:4014-4035` の `_pushObsBrowserSourceSettings()` が既に同じ 7 項目を dict に詰めて WebSocket 送信しているので、その dict を再利用できる。

**規模**: 約 30 行、3 ファイル（`models/obs/obs_browser_source_server.py` / `model.py:2307-2331` / `controller.py`）。

---

### ⬜ S-5 `device_manager.py` のコメントが現在のコードと矛盾している

```python
# device_manager.py:1011-1013
# Provide a module-level singleton. ... This avoids side-effects during simple imports.
device_manager = DeviceManager()
```

しかし `DeviceManager.__new__`（`device_manager.py:111-129`）は `init()` を呼び、
`init()` は `device_manager.py:237-248` で PyAudio が利用可能なら `self.update()` を実行する。
つまり **`import config` するだけで PyAudio の全デバイス列挙が同期実行される**
（`config.py:13` が `device_manager` を import するため）。コメントの主張は事実と異なる。

**実害**: 「import は副作用なし」と信じて import 順序を変えた開発者が、
PyAudio 未初期化を前提とした変更を入れて実機で壊す。
過去に `_bootstrapModel`（`controller.py:4207-4215`）でタイミング変更の回帰を踏んで一度巻き戻した前例があり、
この領域の誤解はコストが高い。

**対応方針**: コメントを実態に合わせる（「`__new__` が light init + 1 回の `update()` を行う」と明記）。3 行。

**関連（対応不要）**: `config.py:1290` 付近の起動時デバイス検証について、
`_mic_host_validator`（`config.py:600-611`）が未 update の device_manager を参照して
永続化された `SELECTED_MIC_HOST` を握りつぶす経路を疑ったが、
上記のとおり `DeviceManager.init()` が import 時に `update()` を済ませているため **Windows 実機では成立しない**。
PyAudio import 失敗時のみ成立しうるが、その場合はどのみちデバイス機能が全損なので実害の増分は無い。**確認したが問題なし。**

---

## PL. 処理のパイプライン

### PL-1 現状の構造（確認済み・設計として妥当）

1 つの発話が画面に出るまでの経路:

```
[PyAudio コールバックスレッド]  (speech_recognition の listener スレッド)
  audio_callback: raw bytes を audio_queue へ push
                  (putDroppingOldestOnFull、満杯なら最古を破棄)
        ↓ キュー境界 ①  ← ここが唯一のスレッド境界
[_print_transcript スレッド]  (threadFnc のループ、model.py:653)
  sendTranscript() 内で以下をすべて同期直列実行:
    1. transcribeAudioQueue()  : キューを drain し、VAD の reason
                                 (silence / flush / max_duration) で確定判定
    2. _finalizeAndTranscribe(): ASR 呼び出し（ブロッキング I/O）
    3. getTranscript()         : 結果取得
    4. controller.micMessage / speakerMessage を同じスレッド上で同期呼び出し
        ↓ 関数呼び出し（スレッド境界なし）
    5. _processMessage(): 翻訳 → transliteration → OSC 送信 → オーバーレイ画像生成
                          → クリップボード → stdout 配信 → WebSocket → ログ → 履歴
    6. ループ先頭へ戻る
```

**良い点（確認済み）**:
- キュー/スレッド境界は **1 回だけ**。それ以降は全部関数呼び出しで、冗長な中継段・不要な同期点は無い。
- 音声データのコピーは必要最小限。`last_sample` の逐次連結（`transcription_transcriber.py:316,372`）は
  bytes 連結のため理論上 O(n²) だが、VAD 方式では `_MAX_SPEECH_DURATION_MS = 7000`
  （`transcription_recorder.py:481`）、エネルギー閾値方式では `MAX_PHRASE_DURATION_SECONDS = 15`
  （`transcription_transcriber.py:66`）で上限が効くため実害は限定的。
- `MessageDirectionSpec`（`models/message_pipeline.py`）により mic/speaker/chat の 3 重複は解消済み。
  `_processMessage` は 243 行あるが、これは「1 つの手続き的パイプラインを 1 関数で表現している」状態であり、
  過度な抽象化を避ける方針として妥当。**分割は推奨しない。**

### PL-2 head-of-line blocking（構造的制約、現時点では許容）

上記の裏返しとして、**ASR・翻訳・OSC 送信・オーバーレイ生成・stdout 配信がすべて 1 本のスレッドに直列化**される。
翻訳が遅い間は文字起こしも進まない。

ただし `audio_queue` は maxsize=20（`model.py:134`）で、VAD 方式なら 1 チャンク最大 7 秒ぶんであるため、
**音声が失われるリスクは実質無い**。発生するのは表示の遅延（バックログの蓄積）であって取りこぼしではない。

**判定**: 現時点では構造変更を推奨しない。まず M-1 で実測し、
翻訳が支配的だと数字で確認できた場合にのみ「翻訳以降を別スレッドへ逃がす」を検討する。
P-3 / P-5 は同じ問題に対するはるかに安価な緩和策であり、先にそちらを実施すべき。

### PL-3 レイテンシの支配要因（grep で列挙）

| 箇所 | 値 | 実レイテンシへの効き方 |
|---|---|---|
| `audio_vad.py:167` `hangover_frames` | 24 frames ≒ 768 ms | 発話終了の検出そのものの遅延。意図的なヒステリシス |
| `transcription_recorder.py:481` `_MAX_SPEECH_DURATION_MS` | 7000 ms | VAD 方式の強制分割上限 |
| `transcription_transcriber.py:66` `MAX_PHRASE_DURATION_SECONDS` | 15 s | エネルギー閾値方式の強制確定。最悪ケースで 15 秒間 ASR が呼ばれない |
| `transcription_transcriber.py:59` `GOOGLE_RECOGNIZE_TIMEOUT_SECONDS` | 10 s | Google 認識失敗時のブロック上限 |
| `transcription_transcriber.py:351,391` `time.sleep(0.01)` | 10 ms | アイドル時のポーリング間隔。オーバーヘッドは無視できる |
| ASR 呼び出し | **未計測** | 最大の変動要因 |
| 翻訳呼び出し | **未計測** | LLM 系なら数百 ms〜数秒 |
| オーバーレイ画像生成 | **未計測** | フォントは `overlay_image.py:76-81` でキャッシュ済み |

**「未計測」の 3 つが支配的である可能性が高いが、現状それを数字で言えない。** → M-1 へ。

### PL-4 実測結果（2026-09-14、M-1 導入後の実機ログ）

環境: 文字起こし `Google`（無料エンドポイント）、翻訳 `CTranslate2`
`nllb-200-distilled-600M-ct2-int8`、**compute_mode = cpu**、ターゲット言語 **1 つのみ有効**。

翻訳 ON の 8 サンプル:

| | asr | translate | output | total |
|---|---|---|---|---|
| 最小 | 573 ms | 748 ms | 0 ms | 1565 ms |
| 最大 | 1724 ms | 1432 ms | 2 ms | 3157 ms |
| 平均 | **約 920 ms** | **約 1124 ms** | **約 1 ms** | 約 2045 ms |

翻訳 OFF の 5 サンプル: asr 平均 約 1044 ms。

**読み取れること**:

1. **翻訳が ASR より重い**（1124ms 対 920ms、総時間の約 55%）。しかも
   **ターゲット言語は 1 つしか有効になっていない**ので、これは「複数言語の逐次実行」ではなく
   **CTranslate2 の単発推論が CPU で約 1.1 秒かかっている**という意味である。
2. **`output` は 0〜2ms で完全に無視できる**。OSC 送信・オーバーレイ画像生成・
   WebSocket 送信・UI 配信の最適化は**不要**と実測で確定した。
3. `total` は 1.5〜3.2 秒。ここに VAD hangover（約 0.77 秒）が加わるのが体感値。

**P-5 の優先度への影響**（下記 P-5 の項も参照）:

- 「複数ターゲット言語の並列化」は、**1 言語しか使わない構成では効果ゼロ**。
  2〜3 言語を有効にしているユーザーにのみ効く。
- 単発 1.1 秒を縮めたいなら、並列化ではなく **compute_mode（GPU/CUDA）・モデルサイズ・
  量子化**の話になる。これはコード構造の問題ではなく設定・環境の問題。
- したがって **P-5 は「多言語利用時のための改善」として位置づけ直す**のが正しく、
  単発レイテンシの改善策ではない。

---

## 対応不要と判断した項目

### ⛔ 前回項目 33「Config の 3 分割」— クローズ推奨

`config.X` 参照は **本番コードだけで 1115 箇所**（`controller.py` + `model.py` の実測）、テスト込みで約 1781 箇所。
アクセスパスを `config.ui.X` のように変える分割は、**既に却下された Controller 分割（267 箇所）の 4 倍以上**の書き換えになる。

「ファイルだけ 3 分割して `config` ファサードは維持する」変種なら呼び出し元 0 箇所だが、
移せるのは記述子機構（`config.py:47-456`、約 410 行）とバリデータ（`config.py:458-662`、約 205 行）で、
config.py が 1394 → 約 780 行になるだけ。

**やらない場合の実害が挙げられない。** 1394 行のうち約 891 行は「宣言とデフォルト値」であり、
grep で属性名を引けば記述子宣言・`init_config` のデフォルト・バリデータの 2〜3 箇所に確実に当たる。
ファイルが長いこと自体のコストが具体的に発生している証拠を、コード・テスト・conftest のいずれからも見つけられなかった。

### ⛔ 前回項目 34「`controller.init()` の宣言的化」— 独立項目としては不要

632 行（`controller.py:4240-4871`）の内訳を実測すると:

| 内容 | 行数 |
|---|---|
| 翻訳エンジン検査 + 適用の match/case（`:4385-4488`, `:4502-4577`） | 180 |
| 文字起こしエンジン検査 + 適用の match/case（`:4591-4674`, `:4688-4732`） | 150 |
| 重みダウンロードと二重検証の制御フロー（`:4267-4380`） | 110 |
| 残りの「ステップ列」部分（`:4737-4870`） | 約 190 |

**330 行（52%）は S-1 で消える。** 残り 190 行をテーブル化するのは、各ステップの条件・失敗時の振る舞い・
進捗番号がすべて異なる（`:4749` は 2 つの config の OR、`:4832-4841` は WebSocket の可用性判定で config を書き戻す、
`:4845-4855` は OBS が WebSocket に依存）ため、テーブルのスキーマが事実上「任意のクロージャ」になり、
**抽象化して読みにくくするだけ**である。

S-1 の副産物として `init()` は 632 → 約 300 行になる。それで十分。

### ⛔ 前回項目 35「UI 契約の型生成」— 型生成は不要、S-2 で代替

両側とも既にテーブル駆動であり（S-2 参照）、コード生成器 + 生成物 + ビルド統合を挟むと、
grep ベース作業の Windows デスクトップアプリに第 3 の生成物とビルドステップが増える。
検出したい不具合（キーの綴り違い・片側の追加忘れ）は **テスト 1 本で捕まえられる**。

### ⛔ 前回項目 36「models の config 非依存化」— 大仕事ではない、S-4 で完了

実測の結果、残っているのは 1 ファイル・9 行のみ（S-4 参照）。大規模構造変更として構える必要はない。

### ⛔ `Controller` のドメイン分割 — 前回の結論を維持

S-1 + S-3 で controller.py は約 3900 行になる。分割（コンポジション / ミックスイン）は依然として投資対効果が薄い。

---

## 確認したが問題なしと判断した領域

- モジュール間の**循環依存は存在しない**（全 import 文を走査）
- `errors.py:13-31` のフック登録による逆依存は正しく回避されている
- `config.py:800-803` の mutable_tracking による `config.X[k]=v` イディオム
- `_SIMPLE_CONFIG_GETTERS` の動的登録と `mainloop.mapping` の束縛順序（`controller.py:4901` が import 時に完了）
- `mic/speaker_lifecycle_lock` のデッドロック（公開版 / `_Locked` 版の分離が一貫）
- `Model.init()` の二重実行（`_inited` ガード。ただし**失敗時の再実行は P-2 のとおり問題あり**）
- 集約ペイロードの秘匿値マスク（`utils.py:497,514-532,570-573` が `token` / `auth_key` を再帰的にマスク）
- `shutdown()` の停止順序（OBS → WebSocket の依存順）と各タイムアウト設計。**ただし watchdog / Clipboard の漏れは P-4 / P-6**
- `pyaudio_op_lock` の粒度（open/close/stop のみ直列化、読み取りループは絞らない）
- 起動シーケンスの順序前提 2 件（`setWatchdogCallback` による `Model.init()` の先行実行、`startWatchdog()` を init 先頭に置く判断）
- `stdout` 専用書き込みスレッドのログキュー有界化（200 件）とポーリング間隔 0.02 秒（ブロッキング get のため CPU 負荷は実質ゼロ）
