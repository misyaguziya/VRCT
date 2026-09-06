# VRCT バックエンド（Python）コードレビュー

- **対象**: `src-python/`（実装 約 15,000 行 / テスト含め 22,144 行、44 モジュール）
  - 中核: `controller.py` (4,267) / `model.py` (1,738) / `config.py` (1,161) / `device_manager.py` (874) / `errors.py` (857) / `mainloop.py` (701)
  - 周辺: `models/` 配下（transcription / translation / overlay / osc / obs / websocket / telemetry / transliteration / clipboard / watchdog）
  - **除外**: `src-python/docs/ref/` 配下（他プロジェクトの参照コピー、875 ファイル）
- **ブランチ**: `feature/beta-release-pipeline`（`89eb4337` 時点）
- **実施日**: 2026-08-27
- **方法**: 3 名のレビュアーが独立した観点でコードを読み、指摘を統合。

> **検証済み（2026-08-27）**: 各レビュアーの Critical 指摘を実コードで再検証しました。
> - ログのマスク判定不一致（P0-1）: `SENSITIVE_ENDPOINT_MARKERS` に対し `"Set DeepL Auth Key".lower()` を実際に評価し `False` を確認。
> - `ValidatedProperty` の生参照（P0-3）: `ManagedProperty.__get__` が `copy.deepcopy` する一方、`ValidatedProperty.__get__` は `getattr` をそのまま返すことを確認。`__set__` も `normalized` を非コピーで格納。
> - Session 起動失敗の固定化（P0-2）: `self.features = new_features` が `_start()` より前、`_recorder` 代入が `recordIntoQueue()` より前、`_stop()` の `resume()/stop()` が無ガードであることを確認。加えて `error.log` に実障害 `OSError: device gone`（`transcription_recorder.py:218 recordIntoQueue`）の記録あり。
>
> **再確認済み（2026-09-01）**: レビュー基点 `89eb4337` から `93c1e438`（ブランチ `backend-code-review`）までの `git diff` を全ファイル走査し、指摘との突き合わせを行いました。
> - **[一部修正] B「初期化ダウンロードのタイムアウト無し」**（`dc2ea952`）: `translation_utils.py` の `downloadCTranslate2Weight`/`downloadFile` と `transcription_whisper.py` の `downloadFile` に `timeout=(10, 60)` + 最大 3 回リトライ + 指数バックオフを追加。4xx（恒久失敗）と 429/5xx（再試行対象）を区別し、失敗時は部分ファイルを削除する丁寧な実装です。ただし `model.py:1105, 1125, 1174`（GitHub releases 取得・setup.exe ダウンロード）と `controller.py:3887, 3891` の `join()`（タイムアウト無しのまま）、`startWatchdog()` の位置（`init()` の最終行のまま）は未修正です。
> - **[一部修正] A「pytest 実行が config.json を削除する」**（`4b96bef5`）: リポジトリ root に `pytest.ini` を追加し `testpaths = src-python` / `norecursedirs` で `docs/ref` 等を除外、210 件の collection error を解消。ただし `test_endpoints.py` / `test_client.py` 冒頭の `os.remove("config.json")` と実アプリ起動（`from mainloop import main_instance`）は**手つかず**で、`src-python` を testpaths に含む以上、素の `pytest` は依然として危険です。
> - **[修正済み] C「telemetry_state.json が .gitignore の対象外」**（`93c1e438`）: `.gitignore` に追加され解消。
> - 上記以外の指摘（CTranslate2 tokenizer のロック、WebSocket 認証、`0.0.0.0` バインド検証、アップデータの署名検証、Tauri CSP、`mainloop` の `sleep(0.2)`、Controller の God Object 化 等）は該当ファイルの diff が存在せず、未着手です。
>
> **Critical 3 件、修正完了（2026-09-01）**:
> - **P0-1**（`c25aa735`）: `_isSensitiveEndpoint` の判定を正規化し、`printResponse` に再帰マスキング（`_maskSensitiveData`）を追加。`controller.py` の 7 箇所から生キーを渡す `printLog` 呼び出しを削除。回帰テスト 14 件、旧コードでの失敗を確認済み。
> - **P0-3**（`a3e3d64f`）: `ValidatedProperty.__get__`/`__set__` を `ManagedProperty` と同じ deepcopy 方式に変更。唯一この生参照バグに依存していた `controller.py: changeToCTranslate2Process()` の直接添字代入を read→変更→再代入に修正。回帰テスト 11 件、旧コードでの失敗を確認済み。
> - **P0-2**（`514d44d7`）: `_AudioDeviceSession._start()` の Recorder 生成/listener 起動を try/except で囲み、失敗時に `_recorder`/`_transcriber`/`_audio_queue`/`_active_device`/`features` を全て巻き戻すよう修正。`already_running` 判定を `_recorder.stop is not None` に強化し、`_stop()`/`pause()`/`resume()` を `callable()` ガード。回帰テスト 6 件、旧コードでの失敗を確認済み。**実機検証済み**（マイク接続中の文字起こし ON 中に USB を物理的に抜き差ししながら OFF→ON を複数回サイクルさせ、いずれも正常復帰することを `process.log` で確認）。
> - 3 件とも既存テストへの回帰なし（138 パス／1 件失敗は今回と無関係の既存問題）。

| レビュアー | 観点 |
|---|---|
| **A** | アーキテクチャ / 責務分離 / 拡張性 / テスト容易性 |
| **B** | 並行処理 / リソース管理 / リアルタイム性 / 障害耐性 |
| **C** | セキュリティ / プライバシー / 外部連携 / 依存関係 |

---

## エグゼクティブサマリ

VRCT のバックエンドは、**「実測に基づいて個別の問題を丁寧に潰してきた層」と「その下で放置されている構造的な穴」が同居している**コードベースです。

良い面は明確です。`pyaudio_op_lock` による PortAudio/COM 操作の全面直列化、中断不能な `PyAudio.open()` を別スレッドに隔離する 8 秒タイムアウト、`_DiscardQueue` による型レベルのリーク封じ、`faulthandler` の恒久計装（実際に `freeze_trace.log` に 35 秒フリーズの全スレッドスタックが取れている）、`errors.py` のフック方式による逆依存回避、config のアトミック書き込み — いずれも「過去に実機で踏んだ問題」への的確な対処であり、コメントに観測日付まで残っています。個人開発のデスクトップアプリとしては相当に規律があります。

一方で、3 名が独立に到達した結論も共通していました。

1. **中核 3 ファイルが構造的に飽和している。** `Controller` は単一クラスに 327 メソッド / 4,267 行、`Config` は 133 ディスクリプタに不変メタデータ・揮発する実行時状態・永続ユーザー設定が同居。両者が全モジュールからグローバルシングルトンとして直接参照され、依存の向きが事実上「全員 → config/model」になっています。

2. **防御機構が実装されているのに、判定条件のズレで機能していない箇所がある。** ログのシークレットマスク機構は正しく設計されているのに、判定キーワード（`auth_key`）と実際に渡す文字列（`"Set OpenRouter Auth Key"`）が一致せず**全 7 エンジンで素通り**します。`ValidatedProperty` のバリデータは「不正値なら旧値に戻す」設計なのに、getter が内部オブジェクトの生参照を返すため**フォールバック先が不正値そのもの**になります。どちらも「機構がある」ことがレビューを素通りさせてきた類の欠陥です。

3. **`mainloop.py` の一律 `time.sleep(0.2)` と 423 再キューを、3 名全員が独立に指摘した。** A は「安定化の根拠がコメントになく、後任が消すことも残すこともできない」、B は「これは本来直すべき競合を隠している疑いが強い」と評価しています。実際 B が挙げた無ロック箇所（OSC ミュート同期、Auto Select、CTranslate2 tokenizer）は、この 200ms によってたまたま時間差で回避されている可能性があります。

4. **リアルタイムパイプラインにバックプレッシャが存在しない。** `audio_queue` は無制限かつ drain 後に `last_sample` へ連結されるため、Whisper が実時間より遅い環境では「溜まる → 音声が長くなる → さらに遅くなる」の正のフィードバックが成立します。「落とす」ポリシーが一つもありません。

5. **翻訳エンジンの追加コストが 8 箇所。** 1 エンジン増やすたびに controller / model / Translator ファサード / クライアント実装 / config / mainloop / `init()` の 2 箇所 / errors に、ほぼ同一のコードを書き写す必要があります。既に `translation_openai_compatible.py` だけ会話履歴機能が欠落しており、**ドリフトは発生済み**です。

---

## 最優先で対処すべき 3 件

> 🟢 **2026-09-01: 3 件とも修正完了・コミット済み**（`c25aa735` / `a3e3d64f` / `514d44d7`）。詳細は冒頭の再確認ノートを参照。

### P0-1 API キーが平文で `process.log` と stdout に書き出される 🟢 修正済み（`c25aa735`）

**観点 C / Critical**・**場所**: `src-python/controller.py:1857, 1902, 1989, 2077, 2165, 2253, 2472` ・判定は `src-python/utils.py:328-356`

マスク機構は存在します。

```python
# utils.py:328
SENSITIVE_ENDPOINT_MARKERS = ("auth_key", "api_key", "password", "token", "secret")
```

しかし呼び出し側が渡すのは第 1 引数の**人間可読なラベル**です。

```python
# controller.py:2253
printLog("Set OpenRouter Auth Key", data)   # data = 生の API キー
```

`"Set OpenRouter Auth Key".lower()` は `"set openrouter auth key"` であり、アンダースコア付きの `auth_key` を含みません。判定は `False` になり、`utils.py:354` で `process.log` に、`utils.py:356` で stdout（Tauri への IPC パイプ）にキーが平文で流れます。**対象は DeepL / Plamo / Gemini / OpenAI / Groq / OpenRouter / OpenAI-Compatible の全 7 エンジン**です。

| 渡される文字列 | マスクされるか |
|---|---|
| `Set OpenRouter Auth Key` | **False** |
| `Set DeepL Auth Key` | **False** |
| `/set/data/openrouter_auth_key` | True |

さらに**より深刻な第 2 経路**があります。`Controller.updateConfigSettings()`（`controller.py:207-217`）は `init_mapping` の全 `/get/data/*` を舐めて 1 つの dict に集約し、`/run/initialization_complete` として送出します。この dict には 7 種の `*_auth_key` の値そのものが入りますが、`printResponse` に渡るエンドポイント名は `/run/initialization_complete` なので判定は当然 `False`。**起動のたびに毎回**全キーがログに落ちます。リポジトリ内の `src-python/process.log:75` に、この集約レスポンスが実際に記録されているのを確認しました（当該環境では全キーが `null` のため実キーの流出はありません）。

`process.log` はインストールディレクトリに平文で残り、10MB までローテーションされません。ユーザーが不具合報告でログを Discord に添付するだけで、全エンジンの API キーが第三者に渡ります。

**対応**:
1. `printLog` の第 1 引数にキー値を渡すのをやめる（`printLog("Set OpenRouter Auth Key")` のみ）。
2. `_isSensitiveEndpoint` を `lower().replace(" ", "_")` で正規化してから判定する。
3. **`printResponse` を、エンドポイント名ではなくペイロードのキー名を再帰的に走査してマスクする方式に変える。** エンドポイント名ベースの判定は、集約レスポンスに対して原理的に機能しません。

### P0-2 Recorder 起動が途中失敗すると Session が壊れた状態で固定化する 🟢 修正済み（`514d44d7`・実機検証済み）

**観点 B / Critical**・**場所**: `src-python/model.py:275-281, 319-322, 383-386`、`src-python/models/transcription/transcription_recorder.py:169-172`

```python
# model.py:277-281
self._stop()
self.features = new_features          # ← _start の前に確定させている
if self.features:
    self._start(device=resolved_device)
```
```python
# model.py:317-322
self._recorder = self._create_recorder(device)          # ← 成功
...
self._recorder.recordIntoQueue(audio_queue, energy_queue)  # ← ここで例外
```
```python
# transcription_recorder.py:170-172  (recordIntoQueue が走る前の初期値)
self.stop = None
self.pause = None
self.resume = None
```

**これは仮説ではありません。** `error.log` に `transcription_recorder.py:218 recordIntoQueue` からの `OSError: device gone` が記録されています。つまり「Recorder は生成できたが listener 起動直前にデバイスが消えた」ケースが実際に起きています。このとき:

1. 例外は `startTranscriptionSendMessage`（`controller.py:3165-3167`）まで伝播し、VRAM エラーでないので `errorLogging()` だけで握り潰される。
2. `self.features = {"transcript"}` は既に確定済み、`self._recorder` は非 None のまま残る。
3. 次の `reconfigure(transcript=True)` は `same_features and same_device and already_running`（`_recorder is not None`）が全て真になり **no-op で早期 return** → ユーザーが OFF→ON しても**永久に復帰しない**。
4. `reconfigure(transcript=False)` すると `_stop()` の `self._recorder.resume()` が `None()` で **TypeError**。捕捉されず 500 が返り、`_recorder` も `features` もクリアされずさらに壊れる。

「文字起こしが二度と ON にならない」というユーザー体験に直結する、最も可能性の高い経路です。

**対応**: `_start()` 全体を try/except で包み、失敗時は `_recorder = None` / `features = set()` / `_active_device = None` に巻き戻してから再送出する。`_stop()` の `resume`/`stop` を `callable()` ガードする。`already_running` 判定を `_recorder is not None` ではなく `_recorder.stop is not None`（listener が実際に走っているか）に変える。

> **音声デバイス領域のため、この 1 件だけを単独でリリースし、実機検証してください。** 手順案: USB マイク接続 → 文字起こし ON → **ON 処理中に USB を物理的に抜く** → `error.log` に `device gone` を確認 → 再接続 → OFF→ON で復帰するか確認（修正前は復帰しないはず）。他の音声系修正を同時に入れないこと。

### P0-3 `ValidatedProperty` の生参照でバリデーションが構造的に迂回される 🟢 修正済み（`a3e3d64f`）

**観点 A / Critical**・**場所**: `src-python/config.py:323-326, 328-339, 438-449`、呼び出し側 `src-python/controller.py:1865` ほか 14 箇所

`ManagedProperty.__get__` は mutable を deepcopy して返します（`config.py:270-272`）。一方 `ValidatedProperty.__get__` は生参照を返し、`__set__` も `normalized` を非コピーで格納します。

```python
# config.py:323-326
def __get__(self, instance, owner):
    if instance is None: return self
    return getattr(instance, self.private_name)   # 生参照
```

そしてコードベース全体がこのイディオムを使っています。

```python
auth_keys = config.AUTH_KEYS        # 内部 dict そのもの
auth_keys[translator_name] = key    # ← この時点で既に config の内部状態が変わっている
config.AUTH_KEYS = auth_keys        # バリデータへ渡す
```

結果として、バリデータの防御が無効になります。

```python
# config.py:438-449
def _selected_translation_engines_validator(val, inst):
    old_value = inst.SELECTED_TRANSLATION_ENGINES   # ← val と同一オブジェクト
    ...
        else:
            new[k] = old_value.get(k)               # ← 「新しい不正値」を返す
```

対象は `AUTH_KEYS` / `SELECTED_YOUR_LANGUAGES` / `SELECTED_TARGET_LANGUAGES` / `SELECTED_TRANSLATION_ENGINES` / `HOTKEYS` / `OVERLAY_*_SETTINGS` / `PLUGINS_STATUS`。なお `controller.py:3350` だけは `copy.deepcopy()` を明示しており、作者がこの罠を一箇所では認識していたことが分かります。

**対応**: `ValidatedProperty.__get__` を `ManagedProperty` と同じく deepcopy に揃える（両者の `__get__` を共通基底へ抽出するのが望ましい）。同時に `config.AUTH_KEYS["X"] = v` 型の部分更新を `config.setAuthKey(name, value)` のような明示 API に置き換え、read-modify-write イディオムを撲滅する。

**修正は 1 行ですが、他の全リファクタの前提**です。これを直さずに構造改善を進めると、バリデータが効いていない前提のコードが増え続けます。

---

## A. アーキテクチャ / 保守性

### 良い点

- **`_AudioDeviceSession` による録音ライフサイクルの抽象化**（`model.py:178-390`）。features（transcript/energy）の和集合で単一 Recorder を保持し、`_device_key()` で差分検知して無駄な stop/start を防ぐ。Mic/Speaker 差分をサブクラスのフック 4 つに閉じ込めており、**本レビュー対象内で最も良く設計された部分**。
- **`errors.py` の逆依存回避**（`errors.py:12-28`）。テレメトリ通知をフック登録方式にして `errors → model` の依存を作らず、`model.py:1737` から登録している。層の向きを意識した明確な判断。
- **config 永続化のアトミック書き込み**（`config.py:589-606`）。tmp + `fsync` + `os_replace`。シャットダウン時に debounce 中の変更を flush する処理も入っている。
- **設定検証のディスクリプタ化**（`config.py:234-357`）と `_auto_register_descriptors()` によるボイラープレート排除。load 時に未知キーを破棄（`config.py:1094`）するため、改竄された config.json による属性注入ができない。
- **設計判断のコメント品質**。`config.py:41-45`（ADR-0004 での VAD 撤退）、`controller.py:17-25`（DL 進捗の間引き根拠と観測日）など、「なぜそうしたか」が実測日付付きで残っている。

### 指摘

#### [Critical] Controller の God Object 化（327 メソッド / 4,267 行）

`controller.py:45`。UI エンドポイントハンドラ（get/set/del × 約 130 設定項目）、翻訳プロバイダ認証、デバイスライフサイクル、ウェイト DL 進捗クラス（`DownloadCTranslate2` / `DownloadWhisper` を**ネストクラスとして**内包）、サーバ起動、メッセージ整形、初期化まで全て同一クラス。変更のたびに 4,267 行を触ることになり、テストが `Controller.__new__(Controller)` を使わざるを得ない原因にもなっている。

**提案**: 機能ドメイン単位のミックスイン/サブコントローラへ分割（`controllers/translation_engines.py`, `audio_devices.py`, `servers.py`, `appearance.py`）。まず「単純 get/set しかしない約 80 メソッド」を config ディスクリプタからのテーブル駆動に置き換えるだけで 1,000 行以上減る。

#### [High] 翻訳プロバイダの知識が 4 層に重複し、1 エンジン追加のコストが 8 箇所

`controller.py:1898-2720`（約 820 行）、`model.py:626-772`、`translation_translator.py:96-420`、`controller.py:3924-4110`。Groq と Gemini の `setXAuthKey`/`delXAuthKey`/`setXModel` は変数名以外ほぼ完全一致。`Translator.translate()` に 13 分岐の `match`、`controller.init()` 内に**さらに 2 箇所**同じプロバイダ列挙。

新エンジン追加時の変更点は ①クライアント実装 ②`Translator` の 4 メソッド + `translate` 分岐 ③`Model` の 5 委譲 ④`Controller` の 6 ハンドラ ⑤`config` の 2 ディスクリプタ ⑥`mainloop` の 6 エンドポイント ⑦`init()` の 2 箇所 ⑧`errors.py` の 3 ErrorCode。**抜けても静的には検出されず、実行時に静かに壊れます。**

**提案**: `TranslationProvider` プロトコル（`authenticate` / `list_models` / `set_model` / `translate` / `key_validator`）と `PROVIDERS: dict[str, TranslationProvider]` レジストリに統合。Controller のハンドラは `provider_name` を取る 6 つの汎用メソッドに畳み、mainloop のマッピングはレジストリからループ生成する。**本プロジェクトで最も投資対効果が高い項目**（約 1,500 行削減、追加コスト 8 箇所 → 1 箇所）。

#### [High] LLM クライアント実装が 7 ファイルで逐語コピー

`translation_groq.py` / `openrouter.py` / `gemini.py` / `openai.py` / `lmstudio.py` / `ollama.py` / `plamo.py`。`# Inject recent conversation history if enabled by YAML config` から始まる約 35 行が、bare except と関数内 import まで含めて完全同一。`_get_available_text_models` の除外キーワード配列も同一。

**既にドリフト済み**: `translation_openai_compatible.py` は 117 行しかなく、履歴機能が欠落しています（`grep -c` の結果 0）。

**提案**: `OpenAICompatibleChatClient` 基底クラスを `translation_utils.py` に置き、Groq / OpenRouter / OpenAI / OpenAI_Compatible / LMStudio を薄いサブクラスにする。履歴整形は `build_history_prompt()` の単一関数へ抽出。約 800 行が 250 行程度になる。

#### [High] Config が実行時状態とユーザー設定を同居させている（133 ディスクリプタ）

`config.py:558` 以降。同一クラスに ①不変メタデータ（`VERSION`, `PATH_LOGS`）②**揮発する実行時状態**（`ENABLE_TRANSLATION`, `SELECTABLE_TRANSLATION_ENGINE_STATUS`, `SELECTABLE_GROQ_MODEL_LIST`）③永続ユーザー設定（`MIC_THRESHOLD`, `OVERLAY_*`）が混在。区別は `serialize` フラグ 1 個だけ。

結果として「`config.X = y` はディスクに残るのか」が読んで分からず、テストが `config` グローバルを setUp/tearDown で手動退避する羽目になっています（`test_controller_audio.py:20-30`）。

**提案**: `AppMetadata`（frozen dataclass）/ `UserSettings` / `RuntimeState`（オブザーバ付き）の 3 分割。`serialize=False` かつ `readonly=False` のディスクリプタを機械的に移すだけで大半が済む。

#### [High] micMessage / speakerMessage / chatMessage の構造重複と挙動ドリフト

`controller.py:369-554`（184 行）/ `554-751`（197 行）/ `752-923`（172 行）。「翻訳 → transliteration → OSC 送信 → Overlay 描画 → WebSocket 送信 → Logger」という同一パイプラインを 3 回書き下している。正規化 diff で mic/speaker 間の実質差分は 169 行分。その中に**意図的か不明な差異**が混ざる:

```python
# micMessage: 全ターゲット言語をループ
for i, no in enumerate(config.SELECTED_TAB_TARGET_LANGUAGES_NO_LIST):
# speakerMessage: 常に translation[0] のみ
transliteration_translation.append(model.convertMessageToTransliteration(translation[0], ...))
```

transliteration の判定条件も、mic は「自分の設定言語が日本語か」、speaker は「受信メッセージ自体の言語が日本語か」と非対称。**どちらが仕様でどちらがバグか、コードからは判定できません。**

**提案**: `MessagePipeline(direction)` に共通化し、方向差分を設定オブジェクトで注入。統合の過程で上記の非対称を仕様として決着させる。

#### [High] エラー返却契約が統一されていない（バリデーション失敗が 200 で返る）

`controller.py:1296-1316` vs `controller.py:1211-1220`。

```python
@staticmethod
def setUiLanguage(data, *args, **kwargs) -> dict:
    config.UI_LANGUAGE = data                          # 不正値なら descriptor が黙って return
    return {"status":200, "result":config.UI_LANGUAGE}  # 旧値を 200 で返す
```

`ManagedProperty.__set__`（`config.py:274-290`）は型不一致・allowed 外を `return` で握りつぶすため、UI は「成功したが値が変わっていない」レスポンスを受け取ります。一方 `setTransparency` は `VRCTError.create_error_response` を返す。同じ `/set/data/*` 系でエンドポイントごとに契約が違うため、UI 側にも同じ数の分岐が必要になります。

**提案**: ディスクリプタの `__set__` を「拒否時に `ConfigValidationError` を送出」に変更し、Controller に共通デコレータ（例外 → `VRCTError` 変換）を被せる。

#### [Medium] `errors.py` の約 3 割が完全な未使用コード

`errors.py:717-820`（`ENDPOINT_ERROR_MAPPING`）、`822`, `834`, `847`。`ENDPOINT_ERROR_MAPPING` / `get_error_metadata` / `is_critical_error` / `requires_user_action` は `errors.py` の外から一度も参照されていません。`ERROR_METADATA` の `severity` / `user_action_required` / `auto_fallback` も、`create_error_response` が `severity` を詰めるだけで `status` は常に 400 固定（`errors.py:634`）。

857 行のうち相当部分が「将来使うつもりだった構造」として残り、読み手に「severity に応じた分岐がどこかにある」と誤解させています。

**提案**: 実使用分に絞って削除。エンドポイント↔エラーコード対応表が UI 契約として必要なら、Python の dict ではなく生成物（JSON schema / TypeScript 型）として書き出し、UI 側から実際に import させる。

#### [Medium] mainloop に本番用と（実質）テスト専用の 2 つのディスパッチ経路が並存

`mainloop.py:575`（`handleRequest`）と `mainloop.py:599`（`_call_handler`）はほぼ同一（差は `response.get("status")` vs `response.get("status", 500)` のみ）。`handleRequest` の呼び出し元は `test_endpoints.py` の 40 箇所のみで、本番の `handler()` は `_call_handler` を使います。

**つまりテストは本番が通らない経路を検証しています。** エンドポイントロック・再キュー・レスポンス送出という、実際に不具合が出やすい部分がテストで一切カバーされていません。

#### [Medium] エンドポイント定義の `status` フィールドが「HTTP ステータス」と誤読される可変フラグ

`mainloop.py:127-505`。`{"status": False, ...}` の `status` は実際には「初期化完了まで受け付けない」ロックフラグで、423 を返す判定に使われ `init()` 完了後に全て `True` へ書き換わります。加えて初期値が不整合 — `/delete/data/deepl_auth_key` と `/delete/data/plamo_auth_key` は `False`、`/delete/data/gemini_auth_key` 以下 5 つは `True`。同種の操作で扱いが違う理由がコードから読めません。さらに `updateConfigSettings()` は `init_mapping` のハンドラを**このフラグを見ずに**直接呼ぶため、ロックは一部経路にしか効いていません。

**提案**: `available_before_init: bool` などに改名。初期値は「初期化前に呼ばれると壊れるか」という一つの基準で 267 エンドポイントを棚卸しする。

#### [Medium] 末端モジュールがグローバル config を直接参照し、設定の source of truth が二重化

`obs_browser_source_server.py:6, 29-52` と `controller.py:3667-3688`。`models/` 配下で `from config import config` するのはこのファイルのみ（他は全て引数受け取り）。`_build_overlay_html()` が直接 config を読む一方、既に開いているページには `_pushObsBrowserSourceSettings()` が WebSocket で同じ値を送る。同じ設定に 2 経路があります。`_HEX_COLOR_RE` と色検証ロジックも `controller.py:14, 3762` と `obs_browser_source_server.py:9-26` に重複しており、片方だけ変更すると HTML と WebSocket で違う値が出ます。

#### [Medium] `SELECTABLE_*_LIST` が list ではなく `dict_keys` のライブビュー

`config.py:834-841`。`ManagedProperty.__get__` の deepcopy 分岐は `(dict, list)` しか見ないため生ビューが返ります。`readonly=True` なのに中身は共有可変で、元の dict を書き換えると黙って変化します。`SELECTABLE_TRANSCRIPTION_ENGINE_LIST` に至っては「最初の言語の最初の国のエンジン dict のキー」という、言語データの並び順に依存する極めて壊れやすい導出。

#### 🟢 [Medium] pytest 実行が開発者の config.json を削除し、アプリ全体を起動する（`7a22b89a`）

`test_endpoints.py:1-8`, `test_client.py:19-21`。両ファイルとも**モジュールトップレベル**で `os.remove("config.json")` を実行し、続けて `from mainloop import main_instance`（= Controller 生成 → `model.init()` → 実デバイス・実ネットワークアクセス）を行います。`test_client.py` はさらに別プロセスを `Popen` します。ファイル名が `test_*.py` なので、`src-python` で素の `pytest` を打つと**収集時点で**実行されます（pytest 設定ファイルは存在しません）。

**CI でも開発機でも安全に全テストを回せない状態です。** これを直さないと、以降の変更を安全に検証できません。

**対応内容（`7a22b89a`）**: レビュー原案の「`test_` 名前空間から追い出す（リネーム）」は採用せず、両ファイルの危険なコードを直接実行時のみ通る経路（`test_endpoints.py` は `if __name__ == "__main__":` ブロック先頭、`test_client.py` は `main()` 関数先頭）に移動する根本修正を行った。`docs/test_endpoints.md`/`docs/test_client.md`/`docs/mainloop.md` からファイル名で明示的に参照されているドキュメント済みツールであり、リネームは 3 ドキュメントの更新と使い慣れた実行コマンドの変更を招くため見送った。補助的に `conftest.py`（`collect_ignore`）も追加したが、これは `pytest test_endpoints.py` のようにファイルを直接指定された場合には効かないことを検証済み（実際、この調査中に `pytest --collect-only test_endpoints.py test_client.py` を実行して実環境の `config.json` を削除する事故を起こした）。安全性の実体は根本修正側にある。

#### [Medium] DI の接合点がなく、テストが `__new__` とグローバル差し替えに依存

`Controller.__init__`（`controller.py:46-70`）が無条件に `model.init()` を呼ぶため、単体テストは `Controller.__new__(Controller)` で `__init__` をバイパスしています。この方式は「`__init__` で初期化される属性」を全てテスト側が知っている必要があり、**既にドリフト済み**です — `test_controller_audio.py:15` が設定する `_pending_partial_transcripts` は、現在 `controller.py` のどこからも参照されていません（VAD 撤退時の消し残し）。

**提案**: `Controller.__init__(self, config=None, model=None)` のデフォルト引数注入（既存呼び出しは無変更）。`model.init()` は `Controller.init()` へ移動。

#### [Medium] config の debounce タイマーが単一で、連続変更時に書き込みが無限に先送りされる

`config.py:607-622`。タイマーはクラス変数で 1 本のみ。**どの設定を変えても既存タイマーがキャンセルされ 2 秒が再スタート**するため、スライダーのドラッグなど 2 秒未満間隔の変更が続く限り**全設定**の書き込みが先送りされます。正常終了時は `shutdown()` で救われますが、クラッシュ時（本コードベースが `faulthandler` で追跡中のネイティブフォルトを含む）は全て失われます。また 1 行目の `self._config_data[key] = value` はデッドコードです（`saveConfigToFile` が `json_serializable_vars` から再構築して丸ごと上書きするため）。

**提案**: 「最初の変更から N 秒」の上限付きスロットリングに変更。

#### [Medium] `controller.init()` が 424 行の単一メソッド

`controller.py:3844-4267`。ネットワーク判定 → ウェイト DL（生 `Thread` + `join`）→ `ThreadPoolExecutor` 疎通確認 → 12 分岐の翻訳エンジン検証 → 9 分岐の結果適用 → 文字起こし → transliteration → word filter → 更新チェック → logger → OSC → device manager → overlay → WebSocket → OBS → telemetry。並行実行モデルも `Thread` / `ThreadPoolExecutor` / デーモンスレッドが混在。初期化順序の制約（`disableOscQuery` は `startReceiveOSC` の後、OBS は WebSocket の後）が**コードの並び順にのみ**表現されています。

#### [Low] `models/ocr/` が `__pycache__` のみ残存

`.py` ソースは 1 つも無く、`ocr_bubble_detector` / `ocr_capture_hwnd` / `ocr_pipeline` / `scan_winsow`（typo 込み）など 11 個の `.pyc` が残っています（最終更新 2025-09〜2026-08）。コードベース全体で `ocr` を参照する箇所は 0。PyInstaller が `models/` を丸ごと含めている場合、削除済み機能のバイトコードが成果物に混入し得ます。

#### [Low] 命名の非一貫性とデッドな属性

`getTranslatorLStudioModelList`（`LMStudio` の M 欠落、`mainloop.py:277` のマッピングもこの綴りで固定）、`getDeepLAuthKey`（L 大文字）と `setDeeplAuthKey`（l 小文字）の混在、`_pending_partial_transcripts` の消し残し。`Controller` が 327 メソッドあるため、命名から機能を推測できることの価値が相対的に高い。

#### [Low] バージョン番号が 3 ファイルに独立して存在

`config.py:811`（`_VERSION = "3.4.3"`）、`src-tauri/tauri.conf.json:4`、`package.json:4`。直近コミット `d4257250` で CI 側の不一致検出が入っているのは良い緩和ですが、根治は `package.json` を単一の真実としてビルド時に注入することです。

---

## B. 並行処理 / 信頼性

### 良い点

- **PortAudio/WASAPI 操作の全面直列化**（`device_manager.py:45` の `pyaudio_op_lock`）。デバイス列挙、`Microphone()` コンストラクタ内の列挙を含む生成〜疎通確認、本番ストリームの open/close、tracker の COM 呼び出しで共有。過去のハングの実測に基づいた良い設計。
- **PyAudio `open()` のタイムアウト隔離**（`transcription_recorder.py:118-140`）。中断不能な `open()` を別スレッドに逃がし 8s で制御を返す。mainloop のワーカー枯渇を防いでいる。
- **`stop()` の無限ブロック回避**（`transcription_recorder.py:231-259`）。`speech_recognition` 側のタイムアウト無し join に入る前に `Pa_StopStream` で `read()` を強制的に返させる。
- **`_DiscardQueue`**（`model.py:88-99`）。energy-only 時に誰も drain しない audio チャンクが溜まるリークを型で潰している。
- **`threadFnc` の例外耐性**（`model.py:126-138`）。ワーカー関数の例外でスレッドが無言死しない。
- **`_notify_event` の再利用**（`device_manager.py:403-408`）。start/stop 並行時に古い Event を set してしまう race を、インスタンス再利用で正しく潰している。
- **恒久計装**（`mainloop.py:27-28`, `model.py:1533-1545`）。実際に `freeze_trace.log` に 35s フリーズの全スレッドスタックが取得できており、調査の一次情報源として機能している。

### 指摘

#### [High] `Controller.shutdown()` が mic/speaker_lifecycle_lock を取らずに停止処理を呼ぶ

`controller.py:127-142`。他の全経路（`stopTranscriptionSendMessage`, `_reconfigureMicDeviceLocked`）は必ずロックを取るのに、shutdown だけが直接 Model を叩きます。終了時に `Main.stop()` が走る一方で `AudioLifecycleWorker` がまだ `restartAccessMicDevices` 実行中（ロック保持、PyAudio open 中）というケースが成立し、`_stop()` と `_start()` が同一 Session に対して並行実行されます。最悪ケースは、`_start` が代入した新 Recorder を `_stop` が知らずに捨て、listener スレッドと PyAudio ストリームが宙に浮いたままプロセスが終了する — **まさに shutdown のコメントが防ごうとしているハンドルリーク**です。

**提案**: `with self.mic_lifecycle_lock:` で囲む（ただし `acquire(timeout=...)` にして終了処理をハングさせない）。`AudioLifecycleWorker` に「新規タスクを受け付けない」フラグを立ててから停止処理に入る。
**検証**: 実機。Auto Mic Select ON + 文字起こし ON でマイクを抜き差ししてデバイス切替中にアプリを終了。プロセスが残らないこと、直後に再起動してマイクが開けることを確認。

#### 🟢 [High] Clipboard スレッドの `openvr.shutdown()` が Overlay の OpenVR コンテキストをプロセスごと破棄する（`3c7b8477`）

`clipboard.py:187-211` と `overlay.py:104-134`。`Clipboard` は `Model.init()`（`model.py:565`）で**設定に関係なく無条件に**インスタンス化され、VR monitor スレッドが 10s 周期で SteamVR を待ちます。`Overlay.main()` も同様に 10s 周期。**SteamVR 起動の瞬間、両スレッドがほぼ同時に目を覚まします。** Clipboard 側が Overlay の `init()` 直後に `openvr.shutdown()`（プロセス全体の `VR_Shutdown`）を呼ぶと、Overlay の `self.system` / `self.overlay` / `handle` が全て無効になり、`initialized=True` のまま `setOverlayRaw` が失敗し続けます。下記の無限ループ指摘と組み合わさると文字起こしスレッドが固まります。

**提案**: OpenVR の init/shutdown をプロセス内で 1 箇所（`Overlay`）に集約。難しければ専用 Lock + 参照カウントを導入。最低でも Clipboard は `ENABLE_CLIPBOARD` が有効な場合だけスレッドを起こす。

**対応内容（`3c7b8477`）**: ユーザーとの協議で「OpenVRへのアクセスを複数箇所からすべきでない」との方針となり、専用 Lock + 参照カウント案を採用。新規 `models/openvr_session.py` にプロセス全体で共有する参照カウント付き OpenVR セッションを実装し、`Clipboard._setup_vr_app_name()` と `Overlay.init()`/`shutdownOverlay()` の両方をこれ経由に統一（`ENABLE_CLIPBOARD` によるスレッド起動ガードは採用せず、根本の共有化のみで対応）。実機（SteamVR、オーバーレイ表示 ON）で動作確認済み。

**このコミットに合わせて発見・修正した別バグ**: 実機検証中、VRChat のウィンドウが非アクティブだとクリップボードへのコピー・貼り付けが一切行われないことが判明した。原因は `focus_window()` の `SetForegroundWindow()` が、Windows のフォーカス奪取防止機構により VRChat が既にフォアグラウンドでない限り OS に無視され失敗すること、かつ `copy_and_paste()` がこの失敗時に即座に `return` しクリップボードへのコピーすら行っていなかったこと。`AttachThreadInput` で自スレッドの入力状態を現フォアグラウンドウィンドウのスレッドに一時的に結び付けてから `SetForegroundWindow` を呼ぶ既知の Win32 ワークアラウンドを導入し、またフォーカスの成否に関わらずコピー自体は常に行うよう修正（自動貼り付けはフォーカス成功時のみ、無関係なウィンドウへの誤入力を避けるため）。実機で確認済み。

#### [High] CTranslate2 の tokenizer / translator が無ロックで複数スレッドから変更される

`translation_translator.py:475, 442`。

```python
self.ctranslate2_tokenizer.src_lang = source_language   # 共有オブジェクトの状態を書き換える
```

`Translator` は `Model.init()` で 1 個だけ生成されるシングルトン相当で、**(1) mic の `_print_transcript` スレッド、(2) speaker の `_print_transcript` スレッド、(3) チャット送信を処理する mainloop ワーカー**が同時に呼びます。

- **競合 A**: mic が `src_lang = "ja"` を代入した直後に speaker が `"en"` で上書きし、mic の `encode()` が英語トークナイザ設定で走る → **クラッシュしないので気付きにくい翻訳品質の劣化**。
- **競合 B**: `changeCTranslate2Model()` が無ロックで `is_loaded = False` → 再生成 → tokenizer 差し替えを行うため、破棄途中のオブジェクトに `translate_batch` が入り得る。`model.py:923-937` のフォールバック（最大 20 回リトライ）がこの窓を 2 秒間叩き続けます。

**提案**: `Translator` に `RLock` を 1 本持たせ、`translateCTranslate2()` と `changeCTranslate2Model()` を保護。あるいは `src_lang` をインスタンス状態として持たない書き方に変更する。CTranslate2 の `Translator` 自体はスレッドセーフですが、**tokenizer の保護にはなりません**。

#### [High] 初期化時のダウンロードが `join()` タイムアウト無し + HTTP タイムアウト無しで、watchdog 発動前に永久ハングし得る

`controller.py:3886-3891, 4267`、`transcription_whisper.py:63`、`translation_utils.py:121`、`model.py:1105, 1125, 1174`。

```python
th_download_ctranslate2.join()      # ← タイムアウト無し
res = requests_get(url, stream=True) # ← timeout 引数無し
self.startWatchdog()                 # ← init() の最終行
```

HF への接続が「確立はするが応答が来ない」状態（キャプティブポータル、プロキシ、パケットロスの多いモバイル回線）になると、`requests` は無期限に待ちます。`init()` が返らない → `mapping[key]["status"] = True` に到達しない → **22 個のエンドポイントが永久ロック** → さらに `startWatchdog()` にも到達しないので**自動復旧も効きません**。UI は「初期化中」のまま無限に固まります。

**提案**: 全ダウンロード系に `timeout=(10, 60)` を付与。`join()` に上限（例 30 分）。**`startWatchdog()` を `init()` の先頭に移す**（初期化中は feed が来ないので初期化専用の長いタイムアウトを用意）。
**検証**: `weights/` を空にし、`huggingface.co` 宛を REJECT ではなく **DROP** に設定して起動。

#### [High] 423 (Locked endpoint) の再キューがビジーループになり、ハンドラワーカーを食い潰す

`mainloop.py:646-648`。

```python
if status == 423:
    time.sleep(0.1)
    self.queue.put((endpoint, data))    # ← 応答を返さず無限に再投入
```

UI が初期化完了前にロック中エンドポイントを叩くと、そのリクエストは応答を返さないまま 0.1s 周期で永久に再キューされます。**ワーカーは 3 本しかないので、3 件溜まった時点で他の全リクエストが処理されなくなります。** 上記の初期化ハングと重なると恒久的な無応答です。同じロジックは `_endpoint_locks` 取得失敗時の再キュー（`mainloop.py:634-637`）にもあり、こちらは 0.05s 周期でさらに激しい。

**提案**: 試行回数上限を設けて超えたら 423 を返す。より根本的には「保留リスト」に退避し、ロック解除イベントで起こす。同一エンドポイントの重複キューは潰す。

#### [High] OSC 受信スレッドから Session の pause/resume を無ロックで呼ぶ TOCTOU

`model.py:283-292, 1069-1078`。`ThreadingOSCUDPServer` はリクエストごとにスレッドを起こすため、`changeHandlerMute` は**ロックを一切持たない任意のスレッド**で走ります。VRChat でミュートを連打しながらデバイス切替が走ると:

- `_stop()` が `_recorder = None` にした直後に `AttributeError: 'NoneType' object has no attribute 'pause'`
- `recordIntoQueue` 前の Recorder に当たると `TypeError: 'NoneType' object is not callable`
- `resume()` が `_start()` 途中の新しい `_audio_queue` を drain して録音済み音声を取りこぼす

例外は OSC の per-request スレッドで出るため、ユーザーからは「ミュート同期がたまに効かない」としか見えません。

**提案**: OSC ハンドラも `model.audio_lifecycle_worker.enqueue(...)` に投げて他のデバイス操作と直列化する（既存設計と一貫）。
**検証**: 実機。ミュートを 1 秒周期で連打しながらマイクデバイスを切り替える操作を 1 分間。

#### [High] Auto Select フラグと monitoring / tracker のライフサイクルが無ロック

`device_manager.py:398-452`。`setMicAutoActive` と `setSpeakerAutoActive` は**別々のエンドポイントロック**配下で処理されるため並行実行できます。

- **競合 A（二重起動）**: 両方が同時に `startMonitoring()` に入り `is_alive()` が両方 False → **monitoring スレッドが 2 本**。COM 通知ごとに callback が二重発火し、Recorder が二重に close/open される。
- **競合 B（誤停止）**: mic 側が `_mic_auto_active = True` を書く**前**に speaker 側が `any_active = False` と判定して `stopMonitoring()` → Auto Select が有効なのに監視スレッドが居ない。
- `_startMicEndpointTracker` の check-then-act も同様で、tracker が 2 本走ると 250ms 周期の COM ポーリングが倍になる。

**提案**: `_lifecycle_lock` を追加し、`pyaudio_op_lock` とは別にしてネスト順序（lifecycle → pyaudio）を明文化。
**検証**: 実機。Auto Mic/Speaker Select を交互に高速 ON/OFF し、`threading.enumerate()` でスレッドが 1 本ずつを超えないことを確認。

#### [Medium] `Overlay.updateImage()` の `while self.initialized is False` が無限ループになる

`overlay.py:145-148`。`reStartOverlay()` が起こす `main()` は最初に `while checkSteamvrRunning() is False: sleep(10)` で待つため、**SteamVR が落ちた状態で `setOverlayRaw` が失敗すると `initialized` は永久に False**、`updateImage` を呼んだスレッドが無限に回り続けます。このスレッドは mic/speaker の `_print_transcript` なので、**文字起こしパイプラインが完全停止**します。さらに `_stop()` の `join(timeout=15)` はタイムアウトし Recorder が残ります。

**検証**: オーバーレイ有効で文字起こし ON → **SteamVR を強制終了** → その後喋る。修正前は `freeze_trace.log` に `overlay.py:148` を含むスタックが出るはず。

#### [Medium] `Model._quitApp()` の `os._exit(0)` が config フラッシュとデバイス解放を全てスキップする

`model.py:1222-1230`。アップデート実行時に `os._exit(0)` を呼ぶため、2 秒デバウンス中の設定変更が**失われ**、PyAudio ストリームが open のまま強制終了し、`atexit` の `_cleanupFreezeTraceIfEmpty` も走らず 0 バイトのゴミログが残ります。

**提案**: 最低でも `config.saveConfigToFile()` と停止処理を短いタイムアウト付きで実行してから `os._exit(0)`。

#### [Medium] watchdog の復旧戦略が「重い停止処理を呼ぶ」だけで、フリーズ元が音声系なら watchdog 自身も固まる

`mainloop.py:688, 671-685`、`watchdog.py:44-57`。callback は `Main.stop()` → `controller.shutdown()`（最大 15s × 4 の join + `Pa_StopStream` の `pyaudio_op_lock` 取得）。**フリーズの原因が WASAPI 側で `pyaudio_op_lock` が握られたままの場合、watchdog スレッド自身がロック待ちで固まり、プロセスは一切終了しません** — watchdog の存在意義が失われます。加えて `last_feed_time` は callback 後も更新されないため、20 秒ごとに `shutdown()` が繰り返し呼ばれます。

**提案**: (1) callback を one-shot 化。(2) 「グレースフル停止を別スレッドで試み、N 秒以内に落ちなければ `os._exit(1)`」というエスカレーション。VRCT はフロントエンドが再起動を担うので、強制終了のほうが無応答継続より望ましい。

#### [Medium] `AudioLifecycleWorker` が単一スレッド・無制限キュー・停止手段なし

`model.py:158-176`。`while True` で抜ける手段がなく、`Queue()` に maxsize もありません。mic/speaker の Before/After callback と tracker reconfigure の**計 6 系統**が投入されます。1 件の処理は最悪 20 秒超（15s join + 8s open タイムアウト）で、その間**speaker 側の切替も待たされます**（mic と speaker でロックを分けた意味が消える）。`ActiveEndpointTracker` は 250ms 周期なので、音量が拮抗すると同じ `_reconfigureMicDeviceLocked` が積み上がり、実デバイス状態から乖離した古い reconfigure が延々と実行されます。

**提案**: mic/speaker でワーカーを分ける、重複投入を dedup する（「最新のみ保持」）、`stop()` と「シャットダウン中は enqueue を無視」フラグを追加。

#### [Medium] リアルタイムパイプラインにバックプレッシャが無く、遅延が累積する

`model.py:319-322`、`transcription_transcriber.py:96-115, 170-181`。

```python
audio_queue = Queue() if "transcript" in self.features else _DiscardQueue()   # maxsize 無し
...
while True:                       # 溜まっている分を全部 drain して
    audio, time_spoken = audio_queue.get_nowait()
    self.updateLastSampleAndPhraseStatus(audio, time_spoken)
...
source_info["last_sample"] += data    # drain した分は全部連結される
```

Whisper large-v3 を CPU で回す構成では、1 フレーズの推論が実時間を超えることがあります。フレーズ間隔が `phrase_timeout` 未満で続く限り `last_sample` はリセットされないため、**「溜まる → 音声が長くなる → 推論がさらに遅くなる → さらに溜まる」の正のフィードバック**が成立します。結果は「喋ってから字幕が出るまで数十秒」「メモリ使用量が増え続ける」。

**提案**: `audio_queue` に `maxsize`（例 50 チャンク ≒ 数秒分）を設定し、`Full` 時は**古いチャンクを捨てる**。あるいは `last_sample` の長さ上限を設ける。どちらにせよ**「落とす」ポリシーを明示的に持つべき**で、現状は無制限に溜める一択です。
**検証**: CPU + large-v3 で 5 分間連続発話し、字幕遅延と RSS を計測。`audio_queue.qsize()` が単調増加しないことを確認。

#### [Medium] mainloop の一律 `time.sleep(0.2)` がスループット上限を 15 req/s に固定する

`mainloop.py:614`。この sleep は**エンドポイントロックを保持したまま**行われるため、ワーカー 3 本 × 5 req/s = 最大 15 req/s が全体の上限になります。起動時の `updateConfigSettings()` は 100 個近い `/get/data/*` を舐めるため無視できない遅延です。

**A・B 両名が指摘**: 「安定化」の根拠がコメントになく、**本来直すべき競合を隠している可能性が高い**（本レビューで挙げた無ロック箇所を、たまたま時間差で回避しているだけの疑い）。ロック整理の完了後に削除すべきです。

#### [Medium] OSC サーバの `serve_forever(10)` により `shutdown()` が最大 10 秒ブロックし、かつ終了時に停止されない

`osc.py:191-204`、`controller.py:97-155`。`socketserver.BaseServer.shutdown()` は `poll_interval`（ここでは 10 秒）単位で停止要求を確認するまで**呼び出し側をブロック**します。OSC の IP/ポートを変更するだけで **UI が最大 10 秒無応答**になり、その間 3 本中 1 本のワーカーが塞がります。さらに `Controller.shutdown()` は `model.stopReceiveOSC()` を**呼んでいない**ため、OSC / OSCQuery HTTP / zeroconf スレッド（`freeze_trace.log` に実在を確認）は停止されずプロセス終了任せです。zeroconf はサービス広告を出しているので、明示的な `close()` なしの終了は他アプリ側に無効なレコードを残します。

**提案**: `serve_forever(0.5)` に短縮（selector 待ちなので CPU 使用率はほぼ変わらない。コメントの「CPU 削減のため 2s→10s」は根拠が薄い）。`shutdown()` に OSC / WebSocket / OBS / Overlay の明示停止を追加。

#### [Medium] stdout 書き込みの破断・ブロッキングが全スレッドに波及する

`utils.py:39-51`。**実障害の記録あり** — `error.log` に `OSError: [Errno 22] Invalid argument` が `utils.py:48` で連発（2026-08-27 07:08）。同時刻の `freeze_trace.log` は「全スレッド idle、feed が 35 秒来ない」状態を示しており、**フロントエンド側の stdout パイプが壊れた後もバックエンドがゾンビとして生き続けている**構図と整合します。

- パイプが壊れても検知・自己終了の仕組みがなく、`errorLogging()` が呼ばれるたびに `error.log` へ書き込むため I/O バーストになる。
- パイプが「壊れる」のではなく「読まれずに埋まる」場合、`sys.stdout.write` は**ブロック**します。その間 `_stdout_write_lock` を握ったままなので、`printLog` / `printResponse` / `run()` を呼ぶ**全スレッド**が芋づる式に停止します。energy メーターは毎秒 15 回程度 `run()` を叩くので真っ先に詰まります。
- `controller.py:20-42` のダウンロード進捗スロットルは、まさにこの経路の輻輳（35s 遅延）を実測して入れられた対策で、**根本原因は未解決**です。

**提案**: (1) 連続 N 回の書き込み失敗で「フロントエンド消失」とみなし自己終了。(2) stdout 書き込みを専用 1 スレッド + 有界キューに移し、溢れたら `printLog`（status 348 のログ）から捨てる。`printResponse`（実応答）は捨てない、という優先度を付ける。

#### [Low] その他

- **telemetry のイベントループ起動がビジースピン**（`telemetry/__init__.py:64-76`）。`while self._loop is None: pass` に sleep もタイムアウトもなく、`asyncio.new_event_loop()` が失敗すると **CPU 1 コアを 100% 使って無限スピン**。`threading.Event` + `wait(timeout=5.0)` にすべき。
- **WebSocket サーバの起動判定と送信経路に TOCTOU**（`model.py:1590-1592, 1611-1628`）。check-then-set により 2 本のワーカーが同ポートで bind を試み得る。`self.logger` は `LOGGER_FEATURE` 無効時に `None` なので、警告パスで `AttributeError` になり本来のタイムアウト警告が記録されない。
- **`threadFnc.pause()` / `resume()` はデッドコードで、かつ `stop()` で抜けられない**（`model.py:120-138`）。`while self._pause` が `self.loop` を見ていないため、将来使うとスレッドリークのバグになる。未使用なら削除。
- **`device_manager.update()` の結果代入がロック外**（`device_manager.py:219-297`）。列挙は `pyaudio_op_lock` 配下だが、その後の 4 属性の代入は無保護。「新しい `mic_devices` + 古い `default_mic_device`」が観測され得る。1 つの dataclass にまとめて原子的にスワップすべき。

---

## C. セキュリティ / プライバシー

### 良い点

- **`verify=False` が全コードベースにゼロ**。TLS 検証を潰している箇所は一つもない。
- **HF 由来のリモートファイル名にパストラバーサル対策が実装済み**（`translation_utils.py:140-147`）。`normpath` → `base_dir` 配下チェックで、外れたら書き込みをスキップ。
- **config.json 読み込み時に未知キーを破棄**（`config.py:1090-1103`）。改竄された config.json による属性注入ができない。
- **テレメトリに会話内容が含まれない**。`telemetry/core.py:39-43` と `telemetry/__init__.py:174` が送るのは `error_code` のみ。SDK 側も OS 情報とセッション UUID だけで、ロケール文字列すら固定 `"en-US"`。**UI 文言（`locales/en.yml:337`）の「No personal info or conversation content is ever sent」は実装と一致しています。**
- **YAML は `safe_load`**。`pickle` / `eval` / `exec` の使用箇所は皆無。
- **WebSocket の受信ハンドラが no-op**（`model.py:1566-1568`）。外部クライアントから VRChat チャットボックスへの書き込み注入はできない。
- **API キーが SDK 内部で `SecretStr` にラップされている**（`translation_openai.py:114` ほか）。LangChain の例外文字列にキーが混入しにくい。
- **既定バインドアドレスがすべて `127.0.0.1`**。`0.0.0.0` はどこにもハードコードされていない。

### 指摘

> **Critical 2 件（API キーのログ漏洩）は「最優先で対処すべき 3 件」の P0-1 に統合しました。**

#### [High] API キーが config.json に平文保存され、OS の資格情報ストアを使っていない

`config.py:719-727, 976-984, 589-606`。`AUTH_KEYS` は単純な dict で、バリデータは `isinstance(val[k], (str, type(None)))` を見るだけ。`json_dump` でそのまま平文 JSON に書かれ、ファイル権限の設定もありません。NSIS が `installMode: "currentUser"` のためインストール先はユーザー権限領域で、**同一ユーザーで動く任意のプロセス（マルウェア、他のゲーム MOD、悪意ある VRCT プラグイン）が無条件に全 API キーを読めます。**

**提案**: Windows DPAPI（`CryptProtectData`）でユーザー紐付け暗号化。最低限 config.json に ACL 制限をかける。

#### [High] WebSocket サーバに認証も Origin 検証もなく、任意の Web ページから文字起こしを傍受できる

`websocket_server.py:39-62, 130`。

```python
async def _handler(self, websocket):
    self.clients.add(websocket)   # 無条件に受け入れ
```

`websockets.serve()` に `origins=` / `process_request=` の指定がありません。**WebSocket は同一オリジンポリシーの対象外**なので、VRCT 使用中のユーザーが任意の Web ページを開くと、そのページの JS が `new WebSocket("ws://127.0.0.1:2231")` を実行するだけで、**マイク音声とスピーカーループバック（＝VRChat で同席している他人の発話）の文字起こしをリアルタイムに窃取できます。** 127.0.0.1 バインドは防御になりません。ポートは既定 2231 固定で総当たりも不要です。

**提案**: `origins=[None]` で Origin ヘッダ付きの接続を拒否（OBS/ローカルツール由来の非ブラウザ接続のみ許可）。加えて起動時にランダムトークンを生成し `ws://127.0.0.1:2231/?token=...` での照合を必須化する（トークンは OBS 用 URL に埋め込んで UI からコピーさせる）。

#### [High] `WEBSOCKET_HOST` に `0.0.0.0` / LAN アドレスを設定でき、LAN 上の第三者に露出する

`controller.py:3479-3508`、`utils.py:165-171`。検証は `ipaddress.ip_address()` で parse できるかだけなので、`0.0.0.0` も `192.168.x.x` も通ります。さらに `controller.py:3499-3501` で OBS の HTTP サーバも同じホストに追随します。

ネットカフェ・シェアハウス・大学 LAN・カンファレンス Wi-Fi で、**同一セグメントの全端末が無認証接続して会話の文字起こしを読めます。** OBS 配信者が「配信 PC から見えるように」と 0.0.0.0 にするのは十分あり得る操作です。

**提案**: 上記トークン認証の導入を前提に、ループバック以外を選ぶ場合は UI で明示警告と確認を挟む。少なくとも `0.0.0.0` / `::` は拒否する。

#### 🟢 [High] アップデータがダウンロードした EXE を署名・ハッシュ検証なしで実行する（`3e944a18`）

`model.py:1162-1222`、`config.py:571-574`。完全性チェックは「1MB 以上か」のみで、SHA-256 照合も Authenticode 検証もありません。ダウンロード元は GitHub Releases ではなく **Hugging Face のモデルリポジトリ**（`ms-software/VRCT` / `ms-software/VRCT-beta`）の `resolve/main/VRCT_setup.exe` で、`main` ブランチは可変です。

**バージョン確認は GitHub API、実体ダウンロードは HF と信頼の起点が二重化しており**、両者の対応を保証する仕組みがありません。HF アカウントが侵害されれば任意コードがユーザー権限で実行されます。

**提案**: GitHub Releases のリリースノート（または署名済みマニフェスト）に SHA-256 を掲載し、`_downloadSetup` で照合してから実行する。`resolve/main` ではなくバージョン固定のリビジョン URL を使う。可能なら `WinVerifyTrust` による署名検証も。

**対応内容（`3e944a18`）**: 提案どおり GitHub Release 側に SHA-256 を掲載する方式を採用。CI（`release.yml`）がビルド直後に `Get-FileHash` でインストーラのハッシュを計算し、`VRCT_{VERSION}_x64-setup.exe.sha256` として GitHub Release アセットに追加公開する。`model.py` の `_downloadSetup()` は HF からのダウンロード中にストリーミングで SHA-256 を計算し、GitHub 側の値と比較。不一致はリトライせず即座に失敗として扱い、ファイルを削除してインストーラを起動しない。`.sha256` アセットが無い（本対応以前の古いリリース等）場合はサイズチェックのみへフォールバックし、旧バージョンの再インストール/ダウングレードを壊さないようにした。`resolve/main` のバージョン固定・`WinVerifyTrust` 署名検証は見送り（ユーザーとの協議の結果、GitHub 側を独立した信頼元として使う整合性チェックのみを「最低限のブロック機能」として採用。GitHub/CI 自体の侵害やコード署名の代替にはならない点は明示的に合意済み）。

#### [High] 既定の文字起こしがスピーカーループバック音声を含めて Google に送信される

`transcription_transcriber.py:120-126`、既定値は `SELECTED_TRANSCRIPTION_ENGINE="Google"`。`recognize_google` は SpeechRecognition の**非公式・無認証の Google Web API** に生音声を POST します。VRCT はマイクだけでなくスピーカーのループバックも文字起こし対象にするため、送信される音声には **VRChat で同席している他人の発話**が含まれます。

本人の同意なく第三者の音声がクラウドに送信される構造であり、GDPR / 個人情報保護法の観点で送信主体（ユーザー）が第三者データの取扱者になってしまいます。また非公式エンドポイントのため、Google 側のデータ取扱いに規約上の保証がありません。

**提案**: Speaker 文字起こし有効化時に「同席者の発話を含む音声がクラウドに送信される」旨を明示する。既定エンジンをローカル完結の Whisper に寄せるか、少なくとも Speaker 側だけはローカル処理を既定にすることを検討する。

#### [Medium] テレメトリが既定 ON で、初回起動時の同意フローがない

`config.py:1077`（`self._ENABLE_TELEMETRY = True`）、`controller.py:4257-4260`。設定画面にトグルとプライバシーポリシーへのリンクはありますが、**初回起動時に同意を求める画面がなく**、config.json が無い状態では既定 True のまま送信が始まります。送信内容自体は最小限で会話内容を含まないことを実装・SDK 双方で確認済みですが、EU 圏ユーザーに対する解析目的のデフォルト ON は GDPR の同意要件上グレーです。

#### [Medium] OpenAI-Compatible / LM Studio の URL に `http://` や任意ホストを許可している

`controller.py:2539-2560`、`translation_openai_compatible.py:84-86`。スキーム検証がないため、`http://evil.example/v1` を設定すると `OpenAI(api_key=..., base_url=...)` がそのキーを `Authorization: Bearer` ヘッダで**平文 HTTP** で送信します。設定ミスや SNS で拾った設定例の貼り付けで、中間者に容易に窃取されます。

**提案**: `https://` を必須にし、ループバック／プライベート IP のみ `http://` を例外的に許可する。

#### [Medium] `/run/download_whisper_weight` の `weight_type` が未検証で、任意ディレクトリを作成できる

`controller.py:3114-3115`、`transcription_whisper.py:126-129`。

```python
path = os_path.join(root, "weights", "whisper", weight_type)
os_makedirs(path, exist_ok=True)          # ← 先にディレクトリを作る
if not checkWhisperWeight(root, weight_type):
    repo_id = _MODELS[weight_type]        # ← KeyError はこの後
```

ディレクトリ作成が `_MODELS` の存在チェックより**前**にあります。対照的に `/set/data/selected_whisper_weight_type` は `config.py:779` の `allowed=` で正しく検証されており、**`/run/` 系だけが素通し**です。次項の CSP 無効化と組み合わさると、UI 側の XSS からこのエンドポイントを叩けます。

#### [Medium] Tauri の CSP が無効化され、sidecar への stdin 書き込みと任意引数の spawn が許可されている

`src-tauri/tauri.conf.json:31`（`"csp": null`）、`src-tauri/capabilities/vrct_capability.json`（`shell:allow-stdin-write`, `shell:allow-spawn` with `"args": true`）。

CSP が無効なので WebView 内で任意スクリプトが実行され得ます。プラグイン一覧を `raw.githubusercontent.com/ShiinaSakamoto/vrct_plugins_list` という**第三者リポジトリ**から取得して描画する設計と組み合わさると影響が大きく、XSS が成立すれば `shell:allow-stdin-write` 経由で Python バックエンドの**全エンドポイント**を任意に呼べます（= API キー取得、WS サーバの 0.0.0.0 起動、上記ディレクトリ作成すべて）。

**提案**: `default-src 'self'` ベースの明示的ポリシーを設定。プラグイン一覧の取得元をベンダー管理下に移すか、スキーマ検証したうえで**テキストとしてのみ**描画する。

#### [Medium] OSC 送信先に任意の IP を指定でき、文字起こしが平文 UDP で外部に出る

`controller.py:1790-1799`、`osc.py:74-101`。IP としてパースできれば LAN でも WAN でも通ります。`is_osc_query_enabled` のループバック判定は OSCQuery の可否を分けるだけで**送信自体は止めません**。UDP のため接続失敗のフィードバックもなく、**低ノイズな常時型データ漏洩チャネル**になり得ます。

#### [Medium] モデル重みの完全性検証がハッシュではなくサイズ + mtime のマーカーファイル

`utils.py:56-104`。`.weight_verified.json` にサイズと mtime を記録し、一致すれば重い再ロード検証をスキップします。ダウンロード時にも HF の SHA との照合はしていません。**サイズと mtime は同一ユーザー権限の任意プロセスが自由に偽装できます。** 改竄した `model.bin` を仕込みつつマーカーを整合させれば、検証ロードを回避して CTranslate2 / faster-whisper にロードさせられます。ネイティブライブラリへの細工済みバイナリ入力は、パーサ由来のメモリ破壊を狙う攻撃面です。

#### [Medium] 外部 HTTP リクエストの多くにタイムアウトがない

`model.py:1104, 1124, 1174`、`translation_utils.py:120`、`transcription_whisper.py:63`、`translation_ollama.py:33`。一方で `translation_lmstudio.py:20`、`translation_openrouter.py:26`、`utils.py:149` には指定があり、扱いが不統一です。**B の「初期化ハング」指摘と同じ根です。**

#### [Low] その他

- **`Popen([...], shell=True)` でエクスプローラを起動**（`controller.py:2982, 2987`）。Windows では `list2cmdline` 後に `cmd.exe /c` へ渡るためパス文字列がシェル解釈を受けます。インストール先パスに `&`, `^`, `|` が含まれると意図しないコマンドが走り得る（`currentUser` インストールではユーザー名がパスに入る）。`os.startfile(path)` にすべき。
- **ログファイルが CWD 相対パスで作られ `PATH_LOGS` 設定が無視される**（`utils.py:273, 346, 365, 405`）。実際 `src-tauri/process.log`（275KB）と `src-python/process.log` の両方にログが散在しています。**P0-1 のキー漏洩と組み合わさると、機微情報を含むログの出力先が起動元によって変わり、削除・ローテーションの対象から漏れます。**
- **例外文字列がそのまま UI レスポンスとログに載る**（`errors.py:641-663`）。`custom_message=f"Error: {str(exception)}"`。エンドポイント名に `auth_key` を含まない場合マスクされません。
- **依存関係の鮮度とピン留めの不備**（`requirements.txt`）。**Pillow 10.0.0** は CVE-2023-50447（`ImageMath.eval` の任意コード実行、10.2.0 で修正）および CVE-2024-28219（10.3.0 で修正）より前のバージョンで、VRCT はオーバーレイ描画で Pillow を多用しています。**transformers 4.40.2** も 2024 年 5 月頃のリリース。`requests` / `urllib3` / `certifi` / `pyperclip` は requirements に**一切記載がなく**、`pyperclip` は `clipboard.py:23` で直接 import しているのに宣言されていません。git 依存 3 件は**タグ参照**で、タグは付け替え可能です。
- ~~**`telemetry_state.json` が .gitignore の対象外**。~~ 🟢 **2026-09-01 修正済み**（`93c1e438`）。内容に機微情報はありませんが、誤って `git add -A` するとローカルの起動日とエラーコード履歴がコミットされる懸念があり、`.gitignore` に追加されました。
- **ポート番号のレンジ検証がない**（`controller.py:1823-1834, 3515-3543, 3632-3644`）。負値や 65535 超が config.json に永続化され、次回起動時に該当機能が起動不能になり得ます。`OBS_BROWSER_SOURCE_PORT` は HTML 側だけ `_clamp_int(..., 1, 65535)` でクランプしており扱いが不統一。

---

## 統合ロードマップ

### フェーズ 0 — 情報漏洩の即時封じ込め（数時間）

| # | 項目 | 観点 | 根拠 |
|---|---|---|---|
| 1 | `printLog` にキー値を渡すのをやめる + `_isSensitiveEndpoint` の正規化 | C | P0-1 |
| 2 | `printResponse` をペイロードのキー名走査によるマスクに変更 | C | P0-1（`initialization_complete` 経路） |
| 3 | ログ出力先を `config.PATH_LOGS` に統一 | C | 1・2 の効果を確実にするため |

**1・2 は他の変更と独立していて回帰リスクがほぼゼロです。最初に入れてください。**

### フェーズ 1 — 音声デバイス系（1 件ずつ単独リリース + 実機検証）

> **この領域は既存方針どおり、未検証の修正を積まず 1 件ずつ実機検証してください。** 各項目の検証手順は B セクションに記載。
>
> 🟢 **2026-09-01: 4 件とも修正・テスト・コミット完了**。

| # | 項目 | 根拠 | 状態 |
|---|---|---|---|
| 4 | `_AudioDeviceSession._start()` の失敗時ロールバック | P0-2。`error.log` に実例あり | 🟢 `514d44d7`（実機検証済み） |
| 5 | `Controller.shutdown()` のロック取得 | 4 と同じ Session 周辺。4 の検証完了後 | 🟢 `69fcfbc3` |
| 6 | OSC ミュート同期の pause/resume を `AudioLifecycleWorker` 経由に | 同上 | 🟢 `4838a437`（`AudioLifecycleWorker`経由の直列化に加え、`mic_lifecycle_lock`による完全排他制御まで実施。詳細は下記） |
| 7 | `DeviceManager` に `_lifecycle_lock` を導入 | Auto Select の ON/OFF 競合 | 🟢 `79613e8b`（併せて`monitoring()`のCOM登録パターンも是正） |

**項目6の補足**: 当初のレビュー提案（`audio_lifecycle_worker.enqueue()`経由での直列化）に加え、ユーザーとの協議の結果、`Model`に`mic_mute_status_change_callback`フックを追加し`Controller`が`mic_lifecycle_lock`付きラッパーを登録する設計まで踏み込んだ。これにより、mainloopワーカーが直接呼ぶ`startTranscriptionSendMessage`等、ロックを直接取得する経路とも完全に排他制御されるようになった。

**項目7の補足**: 実装前にユーザーの要望で`device_manager.py`のデバイス検出方式そのものをレビューした。COM通知（`IMMNotificationClient`）・`pyaudiowpatch`によるループバック録音・ポーリングベースのアクティブエンドポイント追跡という設計判断自体は妥当と確認。ただし`monitoring()`が通知を受けるたびに`CoInitialize`→登録→1回待機→登録解除→`CoUninitialize`を繰り返すパターンが、同ファイル内の`ActiveEndpointTracker._run()`（スレッド開始時に1回だけ登録する正しい作法）と矛盾していたため、これも本コミットで是正した。デバイス名文字列によるマッチング（`pyaudiowpatch`と`pycaw`の識別モデルの違いに起因）は、ライブラリ構成に構造的に付随する制約と判断し、対応を見送った。

### フェーズ 2 — 音声デバイス以外の確実な修正（まとめて可）

> 🟢 **2026-09-01: 項目8〜16、全て完了。**（項目14は実機検証済み、コミット`3c7b8477`。フェーズ2完了。）
>
> **項目9の補足**: `_HTTP_TIMEOUT = (10, 60)` を model.py の GitHub API 呼び出し・setup.exe ダウンロードにも展開し、`th_download_ctranslate2/whisper.join()` に30分の上限を追加。`startWatchdog()` を `init()` 先頭に移動（フロントエンドはプロセス起動直後から20秒間隔で `/run/feed_watchdog` を送り続けており、このエンドポイントは初期化中でも処理可能なため安全と確認済み）。
>
> **項目12の補足（重要な設計変更）**: 当初のレビュー提案（`origins=[None]`）は実装しなかった。VRCT の OBS Browser Source 自体が OBS 内蔵 Chromium から Origin ヘッダー付きで接続するため、素直に適用すると OBS 連携機能自体を壊すことが実装前の調査で判明したため。トークン認証を主防御として採用。さらに実装中、ユーザーから外部連携ツール [misyaguziya/VRCT-TTS](https://github.com/misyaguziya/VRCT-TTS) の存在が判明した。このツールは VRCT の WebSocket に URL を手動入力する方式で接続するため、当初案（プロセス起動ごとにトークン再生成）だと再起動のたびに再設定が必要になり実用的でなかった。設計を見直し、`config.WEBSOCKET_AUTH_TOKEN` として config.json に永続化する方式に変更。`src-ui` に「WebSocket URL (click to copy)」ボタンを追加し、既存の OBS URL コピー機能と同じパターンでユーザーが `ws://host:port/?token=...` を取得できるようにした。
>
> **項目13の補足**: 当初のレビュー提案（`resolve/main` のバージョン固定 URL 化・`WinVerifyTrust` 署名検証）は見送り、GitHub Release にハッシュを掲載して照合する部分のみ実装した。CI（`release.yml`）がビルド直後に `Get-FileHash` でインストーラの SHA-256 を計算し、`VRCT_{VERSION}_x64-setup.exe.sha256` として GitHub Release アセットに追加公開（HF 側のアップロード内容は変更なし）。`_downloadSetup()` はダウンロード中にストリーミングでハッシュを計算し、GitHub 側の値と比較。不一致はリトライせず即座に失敗として扱いファイルを削除、`.sha256` アセットが無い（本対応以前の古いリリース）場合はサイズチェックのみへフォールバックする。ユーザーとの協議で、この仕組みは「HF 配布物と GitHub 正規ビルドの整合性チェック」であり、GitHub/CI 自体の侵害には無力でコード署名の代替でもない「最低限のブロック機能」であることを明示的に合意した上で採用。

| # | 項目 | 観点 |
|---|---|---|
| 8 | `ValidatedProperty.__get__` の deepcopy 化 🟢 `a3e3d64f` | A（P0-3。**以降の全リファクタの前提**） |
| 9 | HTTP タイムアウトの全面付与 + 初期化 `join()` の上限 + `startWatchdog()` の前倒し 🟢 `6e8e6a67` | B / C |
| 10 | CTranslate2 translator/tokenizer のロック導入 🟢 `80d71794` | B |
| 11 | 423 再キューの上限化と応答返却 🟢 `311c3969` | B |
| 12 | WebSocket の `origins=[None]` + トークン認証、`0.0.0.0` 拒否 🟢 `cc5d9227`（詳細は下記補足） | C |
| 13 | アップデータの SHA-256 照合 🟢 `3e944a18`（詳細は下記補足） | C |
| 14 | Clipboard の `openvr.shutdown()` 撤去 / 参照カウント化 🟢 `3c7b8477`（実機検証済み。ウィンドウフォーカス失敗時のクリップボード無反応バグも同コミットで修正） | B |
| 15 | `test_endpoints.py` / `test_client.py` の危険な副作用対策 🟢 `7a22b89a`（リネームではなく `__main__` ガード化、詳細は上記該当Findingを参照） | A（**これをやらないと以降の変更を安全に検証できない**） |
| 16 | デッドコード削除（`models/ocr/`、`errors.py` の未使用 4 シンボル、`mainloop.handleRequest`、`_config_data[key] = value`、`_pending_partial_transcripts`） 🟢 `e45d4ef9` | A（265 行削除 / 50 行追加） |

### フェーズ 3 — 構造改善（1〜2 ヶ月）

> 🟢 **2026-09-04: 項目17、完了**（`0fb43755`〜`286525c8`。詳細は下記補足）。

| # | 項目 | 観点 |
|---|---|---|
| 17 | **`TranslationProvider` レジストリの導入** 🟢 `286525c8`（詳細は下記補足） | A（**最も投資対効果が高い**。約 1,500 行削減、追加コスト 8 箇所 → 1 箇所） |
| 18 | stdout 出力を専用スレッド + 有界キューに移行、フロントエンド消失時の自己終了 🟢 `c9ff7bd4`（詳細は下記補足） | B（35 秒フリーズ + `Errno 22` の根本対策） |
| 19 | watchdog のエスカレーション（グレースフル → タイムアウト後 `os._exit`）と one-shot 化 🟢 `853bc8ca`（詳細は下記補足） | B（18 と組み合わせて初めて「フリーズしたら確実に落ちる」が成立） |
| 20 | `audio_queue` の有界化と `last_sample` 長の上限 🟢 `88b1c1d2`（詳細は下記補足） | B（バックプレッシャの明示） |
| 21 | `AudioLifecycleWorker` の mic/speaker 分割・重複除去・停止 API | B |
| 22 | `Controller.__init__` への DI 導入 + `model.init()` を `Controller.init()` へ移動 🟢 `c2b61fa5`（詳細は下記補足） | A |
| 23 | `Controller` のドメイン分割（17 完了後、単純 get/set のテーブル駆動化を先に） 🟡 `d6c67fae`（テーブル駆動化のみ完了、ドメイン分割は見送り、詳細は下記補足） | A |
| 24 | エラー契約の統一（ディスクリプタから例外 → 共通デコレータで `VRCTError` 化） 🟢 `4ab9b521`（詳細は下記補足） | A |
| 25 | `MessagePipeline` への 3 メソッド統合（過程で mic/speaker の非対称を仕様として決着） | A |
| 26 | API キーの DPAPI 暗号化保存 ⬜ 見送り（詳細は下記補足） | C |
| 27 | Tauri CSP の明示的ポリシー設定 ⬜ 見送り（詳細は下記補足） | C |
| 28 | 依存関係の更新（Pillow / transformers）、直接 import の宣言、git 依存の SHA 固定、`pip-audit` の CI 組み込み 🟡 `fbc8b09b`（一部完了、詳細は下記補足） | C |

> **項目18の補足(2026-09-05, `c9ff7bd4`)**: `printLog`/`printResponse`を呼んだスレッドが`sys.stdout.write()`をロック付きで直接実行する方式をやめ、専用デーモンスレッド(`StdoutWriter`)1本に書き込みを閉じ込めた。呼び出し元は2種類のキューに積むだけになる — 応答キュー(`printResponse`用、無制限、取りこぼさない)とログキュー(`printLog`用、有界200件、あふれたら古いものから破棄)。書き込みスレッドは応答キューを優先(`get_nowait()`)し、無ければログキューを短いタイムアウト付きで待つ(`queue.Queue.get(timeout=...)`は条件変数によるブロッキング待ちでビジーループではないため、待機自体はCPU負荷にならない)。このタイムアウトは初め0.2秒だったが、ユーザーからの指摘で「ログが一切無い間は応答の検知・`stopStdoutWriter()`の反映が最大0.2秒遅れる」ことを説明した上で0.02秒に短縮した。連続50回書き込みに失敗した場合は「フロントエンド消失」とみなし登録済みコールバック(既定は`os._exit(1)`、テストは差し替え可能)を呼ぶ。
>
> 設計レビュー時に2件のバグを事前に発見・修正: (1) 書き込みスレッドの起動チェックにTOCTOUレースがあり2本同時に起動しうる問題(起動処理をロックで直列化)。(2) 実装当初は応答キューを毎回`get(timeout=...)`で待つ順序だったため、ログだけが流れている状況(energyメーターが秒15回程度`printLog`を呼ぶ)で1件処理するごとにタイムアウト分の遅延が入りログのスループットが不必要に制限される問題(テストで検出、応答キューの`get_nowait()`優先に順序を変更して解決)。
>
> スコープ外として明示的に見送った項目: 「例外を出さずに書き込みが永久にブロックし続ける」ケース(パイプが読まれずに埋まる場合)の検知。連続失敗カウンタは書き込みが実際に失敗して初めて進むため、ブロックしたまま失敗しない書き込みは検知できない。これを検知するには書き込みスレッドの進捗を外部から監視する別の仕組みが必要なため、別項目として切り出す方針とした。`Controller.shutdown()`への`stopStdoutWriter()`の組み込みも見送った — シャットダウン応答自体は`Controller.shutdown()`が戻った後にキューへ積まれるため、`shutdown()`内で書き込みスレッドを止めるとその応答自体が届かなくなるリスクがあり、デーモンスレッドのためプロセス終了時に自然に終わることから無理に組み込む必要はないと判断した。
>
> 新規テスト9件(`test_utils_stdout_writer.py`)を追加、既存の`test_utils_log_masking.py`のパッチ対象を新しいキュー投入関数に更新。全体479件を3回連続実行して安定を確認済み。
>
> **項目19の補足(2026-09-05, `853bc8ca`)**: 調査の結果、以前は watchdog のコールバックとして `Main.stop()`(→`controller.shutdown()`)を直接登録しており、`controller.shutdown()`が何らかのロック(例: `pyaudio_op_lock`)を握ったまま永久にブロックすると、`Main.stop()`内の`_stop_event.set()`に一生到達せず、watchdogのバックグラウンドスレッド自身もこの呼び出しの中で永久にブロックされることを確認した(レビューの懸念通り、フリーズを検知したいまさにその状況で検知の仕組み自体が道連れで固まる)。加えて、フロントエンド側の`feed_watchdog`送信自体が`StartPythonController.jsx`の`setInterval`(20秒間隔)によるものであり、バックエンドの健全性ではなく「フロントエンドのJSイベントループが回っているか」を見ている構造であることも判明した。ユーザーからの明確な要求「フロントエンドからfeedが来なくなったら必ず終了するようにしたい。それができないのであれば、この機能はあまり意味がない」を受け、確実性を最優先する設計とした。
>
> `Main.escalateShutdown()`を新設し、watchdogのコールバックをこちらに差し替えた。グレースフルな`self.stop()`は別スレッドで試みつつ、他のロックに一切触れない`threading.Timer(30, os._exit, args=(1,))`を独立したハードデッドラインとして仕掛ける。グレースフル処理が何に詰まっていても(例外が出ても)、30秒後には必ず`os._exit()`でプロセスを終了させる。猶予30秒は`controller.shutdown()`の理論上の最大所要時間(mic/speaker停止×2 + energy停止×2、各最大15秒)を踏まえてユーザーと合意して決定した。feedが来ない限りwatchdogは20秒おきにコールバックを呼び続けるため、二重に停止処理・タイマーを積み上げないようone-shot化(ロック付きフラグ)した。`self.stop()`自体はグレースフル処理の実体として、またCtrl+C(`KeyboardInterrupt`)時の経路として引き続き使用しており、削除していない。
>
> 新規テスト4件(`test_mainloop_watchdog_escalation.py`: 二重発火防止、グレースフル処理が永久ブロックしてもハードデッドラインで強制終了、グレースフル完了時はタイマーが正しくキャンセルされる、グレースフル処理内で例外が出ても`os._exit`に到達する)を追加。全体483件を3回連続実行して安定を確認済み。
>
> **項目20の補足(2026-09-06, `88b1c1d2`)**: `audio_queue`(`model.py`)を`maxsize=20`で有界化し、満杯時はブロックせず最も古いチャンクを1つ捨てて追いつく方を優先するようにした。`last_sample`(`transcription_transcriber.py`)は無音ギャップが`phrase_timeout`秒を超えるまでリセットされない設計のため、発話・環境音が途切れないまま続くと無制限に伸び続け「溜まる→音声が長くなる→推論がさらに遅くなる→さらに溜まる」という正のフィードバックループになりうる問題に、長さの実効上限(古い方から切り捨て)を設けて対処した。
>
> 実装後に`/code-review`(xhigh、10角度×検証×スイープ)を実行し、10件の指摘のうち8件を修正・1件は現状維持・1件は変更不要と確認した:
> - **`_AudioDeviceSession.resume()`のTOCTOUハング(既存バグ)を修正**: 以前は`while not empty(): get()`という非アトミックなcheck-then-actで、`_print_transcript`スレッドが同時にキューをdrainしていると`resume()`の後続の無限待ち`get()`が永久にブロックし、`self._recorder.resume()`が一生呼ばれずマイクが停止したまま戻らなくなる(VRChatの素早いミュート/アンミュート切り替えで再現しうる)。`get_nowait()`のみを使うdrainに変更し、原理的にブロックし得なくした。
> - **チャンク破棄・`last_sample`切り詰めが完全にサイレントだった**問題に`printLog`を追加。
> - `MAX_LAST_SAMPLE_SECONDS`(60秒)が「UI側の設定可能上限(30秒)」とコメントだけで結びついておりPython側に強制力が無かった問題を、`_effectiveMaxLastSampleSeconds() = max(60, self.phrase_timeout * 2)`として実際のユーザー設定値から動的に算出する方式に変更。
> - `audio_callback`/`energy_callback`の「非ブロッキングput、満杯なら最古を1つ捨てて再put」ロジックが`utils.py`の`_enqueueLogLine`(項目18)と重複していたため、`putDroppingOldestOnFull()`として共通ヘルパーへ切り出した。
> - `energy_queue`も同じ理由で無制限だったため`maxsize=1`(最新値のみ保持)で有界化。
> - `_capLastSampleLength`をチャンク単位ではなくdrainループ全体の後に1回だけ呼ぶよう変更し(最終結果は数学的に同一)、backlog時の無駄な大きいバイト列コピーを削減。
> - 常に無意味だった`max_bytes -= max_bytes % frame_size`(丸めのつもりが数式上絶対に0にしかならない死んだコード)を削除。
>
> 一方、`_AUDIO_QUEUE_MAXSIZE`(20チャンク、理論上最悪600秒分バッファしうる = last_sample側の60秒上限よりかなり大きい)はレビューで指摘されたが、到達には単発のWhisper推論呼び出しが10分近く返らない必要があり非現実的と判断しそのまま維持(コメントのみ実態を正直に修正)。内側の`except Full: pass`(現状の単一プロデューサ設計では到達不能)も、`utils.py`の既存パターンと完全に一致しており逸脱ではないため変更不要と判断。
>
> 新規/更新テスト13件を追加。全体500件を3回連続実行して安定を確認済み。
>
> **項目22の補足**: `Controller.__init__(self, config_override=None, model_override=None)` を追加し、既存の全呼び出し・`@patch("controller.model")` ベースのテストとの互換性を保ったままDIの足場を用意した(`self._config`/`self._model` として保持、現時点で実際に使っているのは `_bootstrapModel()` のみ — このクラスの残り数千行はまだ裸のモジュールレベル `config`/`model` を直接参照しており、項目23の対象)。
>
> `model.init()` を `Controller.init()` 側へ移動する変更は、一度実機検証で「VRCTをVRChatより先に起動するとOSCQueryが繋がらずミュート同期が壊れる」回帰が見つかり保守的に撤回したが、調査の結果この回帰は今回の変更と無関係な既存バグ(起動時1回きりの `setMuteSelfStatus()` がVRChat未起動時に失敗すると `mic_mute_status` が `None` のまま二度と回復しない構造的な問題)と判明し、`_VrchatOscQueryFoundListener`(zeroconfのイベント駆動監視、`models/osc/osc.py`)を追加して別途修正・実機検証済み。無関係と確認できたため改めて `model.init()` の移動を実装し、実機検証(通常起動・ミュート同期とも正常動作)を経て完了。
>
> **項目23の補足**: 「単純get/setのテーブル駆動化」(`d6c67fae`)は完了。`config.X`をそのまま返すだけの純粋なgetter94個を`_SIMPLE_CONFIG_GETTERS`(メソッド名→config属性名の対応表)+動的生成へ集約し、controller.pyを275行削除/133行追加(純減142行)。生成したメソッドは元と同じ名前で`Controller`クラスへ登録するため、`mainloop.py`のルーティングや既存テストへの影響は無い。setter側は既存の単純2行構成が項目24で対応済みの12個のみと判明し(全パターン再チェック済み)、少数のため動的生成への追加投資は見送った。
>
> 一方、レビューのもう一つの柱である「機能ドメイン単位のミックスイン/サブコントローラへの分割」は**見送りと結論**。コンポジション方式(`self.audio.setX()`)は`mainloop.py`の267箇所のルーティング参照と既存テスト470件超の大部分を書き換える必要があり、リスクが実装コストに見合わないと判断(VRCTは大人数チームでなく、ドメイン間の境界を言語レベルで強制する価値も薄い上、翻訳・マイク/スピーカー・OSC等のドメインは実際には密結合している)。ミックスイン方式(多重継承で`self`名前空間を共有したままファイルだけ分割)も再検討したが、実質的な価値が乏しいと判明: (1) レビューが問題視した「テストが`Controller.__new__(Controller)`に頼らざるを得ない」という点をミックスインは一切解決しない(解決するにはコンポジション+DIが必要)、(2) grep/検索ベースの開発スタイルでは、ファイルが1つでも273メソッドあっても目的のコードへの到達コストはほぼ変わらない、(3) 行数削減効果は既にgetter統合で実現済みで、ドメイン分割自体は「移動」であり「削減」ではない。将来テストのしやすさが実際に問題になった時点で、改めてコンポジション+DIを検討する方が筋が良いと判断した。
>
> **項目24の補足**: 当初は「controller.py側だけで代入前後の値を比較する」という、config.py自体には触れない縮小版アプローチを検討したが、ユーザーから「今後の設定追加のしやすさ」まで含めて見直すよう指示があり、レビュー本来の提案(ディスクリプタ自体が拒否時に例外を送出する)を採用する方向に再設計した。決め手は2点: (1) `mainloop.py`の`_call_handler`が既に全ハンドラ呼び出しを`try/except Exception`で包んでおり、例外を送出してもアプリがクラッシュしないことを確認できた、(2) `HOTKEYS`等の「キー単位で不正な項目だけ旧値にフォールバックする」設計は意図的な仕様(`test_config_validated_property.py`で検証済み)であり、`ValidatedProperty`がバリデータ**全体の**拒否(`None`返却)時のみ例外を送出するようにすれば、この仕様を一切壊さずに済むと判明した。`ConfigValidationError`(config.py)+`_configValidationErrorResponse`デコレータ(controller.py)を追加し、対象12エンドポイントはデコレータ1行を足すだけで直った(本体は無変更)。今後新しい単純な設定セッターを追加する際も、同じデコレータを1行付けるだけで正しいエラー契約に乗せられる。
>
> **項目26は見送りと結論(2026-09-04)**: 調査の結果、レビューが懸念する脅威(同一ユーザーで動く別プロセスがAPIキーを読める)への対処は、原理的にOS提供の秘匿ストレージ機構(Windows DPAPI等)に頼るしかないと判明した — ファイルACL制限は「別ユーザー」は防げても「同一ユーザーの別プロセス」は防げず、自前の対称鍵暗号も鍵自体を同じファイルシステム上に置く以上、同一ユーザーの別プロセスから見れば鍵も読めてしまい実質的な防御にならない。DPAPI実装(ctypes直呼び、pywin32は不使用の方針)を提案したが、VRCTがWindows専用でありプラットフォーム分岐コードを持ち込む価値への疑問、および最終的に「暗号化自体が不要」「ACL制限による軽量な代替案も不要、config.jsonの保護はユーザー側の責任とする」という判断に至った。将来再検討する場合は、この経緯(特に「同一ユーザー別プロセス」という脅威モデルに対する暗号理論上の制約)を踏まえること。
>
> **項目27は見送りと結論(2026-09-04)**: 調査の結果、VRCTのプラグイン機構(GitHubリリースからZIPを取得→JSXをBabelでその場でトランスパイル→`Blob`+動的`import()`で実行、`usePlugins.js`)が「外部から取得したコードを実行する」ことを意図的な仕様として持っており、単純な`default-src 'self'`では機能ごと壊れることが判明した。Tauri v2は自アプリのバンドル済みスクリプトには自動でnonce/hashを付与するが、動的JSロード(まさにこのプラグイン機構)はその自動化の対象外で、`script-src`に`blob:`を明示的に許可する設計が必要。GitHub等へのHTTP通信は`@tauri-apps/plugin-http`経由(Rust側処理)のためCSPの`connect-src`には影響されない一方、`shell:allow-stdin-write`自体はCSPでは制限できない(CSPはページ読み込み内容の制御であり、Tauri API呼び出し可否とは別レイヤー)。プラグイン機構を壊さない`script-src`設計+実機ビルドでの動作確認が必要な、見た目より手間のかかるタスクと判明し、見送りとした。
>
> **項目28は一部完了(2026-09-04, `fbc8b09b`)**: `requests`(直接import)/`urllib3`・`certifi`(requestsの推移的依存)/`pyperclip`(直接import)をrequirements.txtに明記。git依存3件(translators/custom_speech_recognition/tinyoscquery)をタグからコミットSHA固定に変更。`urllib3`(→2.7.0)・`sentencepiece`(→0.2.1)を実際のCVE修正版に更新し、テスト465件で動作確認済み。一方、`setuptools`の更新(PYSEC-2026-3447修正版83.0.0)は**対応不可能と判明**: setuptoolsは82.0.0で`pkg_resources`モジュールを完全に削除しており、`openvr`/`ctranslate2`が起動時に`import pkg_resources`しているため、更新するとテスト32ファイルが収集不能になることを実際に検証して確認した。`openvr`/`ctranslate2`が上流でこの依存をやめない限り対応不可能。pip-auditのCI組み込み・Pillow/transformersの更新は、上記setuptoolsに加えPillow(既知のCVE多数)・langchain-openai/langchain-core(推移的依存、メジャーバージョン跳躍)・zeroconf(推移的依存)が現状でも脆弱性ありと判定され、導入した瞬間にCIが赤くなる状態だったため、対応方針を決めずに見送った。またrequirements.txtのコメントは意図的にASCII文字のみにしている(pip-auditのrequirements parserがOSロケールのコードページでファイルをデコードするため、日本語コメントがあると環境依存でパースに失敗することを実際に確認した)。

> **項目17の補足**: 当初想定した「翻訳エンジンを1つの型に統一」ではなく、実装を精査した結果、実際に構造が一致するエンジン群ごとに2つのレジストリへ分けた。
> - `TRANSLATION_PROVIDER_REGISTRY`（認証キー + モデル一覧型）: Plamo/Gemini/OpenAI/Groq/OpenRouter の5エンジン。Gemini 1エンジンをパイロットとして通した後、残り4エンジンへ一括展開。
> - `CONNECTION_PROVIDER_REGISTRY`（疎通確認型）: LMStudio/Ollama の2エンジン。最初から2実装が一致することを確認できていたため、パイロット段階を挟まず同時に載せた。
> - `OpenAI_Compatible`（base_url依存・入力strip・「モデル一覧非空」を要求する認証成功判定・URL変更時の順序制御という4点で他と異なる）、`DeepL_API`（モデル一覧を持たない）、`Google`/`Bing`/`Papago`（認証もモデル一覧もない無料Web翻訳）、`CTranslate2`（ローカル重みで別物）は、いずれも「同じ形の2つ目の実装が存在しない」ため対象外と結論。無理に抽象化すると、共通実装に一点物のための特殊分岐を追加することになり、レビューが警告する「不要な抽象化」を新たに生むリスクの方が高いと判断した。
>
> 新規テスト91件を追加し、全体406件を3回連続実行して安定を確認済み。副次的に発見した軽微な既存の命名問題（LMStudioの重複エンドポイント・タイポ）は別タスクへ切り出した。

### フェーズ 4 — クリーンアップ / 長期

| # | 項目 | 観点 |
|---|---|---|
| 29 | mainloop の一律 `sleep(0.2)` 削除（**フェーズ 1〜3 のロック整理完了後**） | A / B |
| 30 | OSC `serve_forever(0.5)` 化 + `shutdown()` での OSC/WebSocket/OBS/Overlay 明示停止 | B |
| 31 | `Overlay.updateImage` の無限ループにタイムアウト、`shutdownOverlay` の join タイムアウト | B |
| 32 | telemetry のビジースピン、WebSocket TOCTOU、`threadFnc.pause` 削除、`update()` の原子的スワップ | B |
| 33 | `Config` の 3 分割（`AppMetadata` / `UserSettings` / `RuntimeState`）— 22・23 完了後 | A |
| 34 | `controller.init()` の宣言的ステップ化 | A |
| 35 | UI 契約の型生成（267 エンドポイントを単一スキーマから Python マッピングと TypeScript 型の両方へ） | A |
| 36 | `models/` の完全な config 非依存化 + CI での import グラフ検査 | A |
| 37 | テレメトリの初回オプトイン、Speaker 文字起こしのクラウド送信告知 | C |

---

## 付録 A. 並行処理マップ

常駐スレッドは 15 本前後。

| # | スレッド / ループ | 生成箇所 | 役割 | データの受け渡し | 停止手段 |
|---|---|---|---|---|---|
| 1 | main | `mainloop.py:697-701` | `while not stop_event: sleep(1)` | — | `_stop_event` |
| 2 | `main_receiver` | `mainloop.py:570-573` | stdin 読み取り → JSON parse | → `Main.queue` | daemon のみ（`readline` 中断不可） |
| 3 | `main_handler_0..2`（3 本） | `mainloop.py:653-658` | エンドポイント処理 | `Main.queue` ← / stdout → | `_stop_event` + `queue.get(timeout=0.5)` |
| 4 | `AudioLifecycleWorker`（1 本） | `model.py:162-164` | device 変化時の stop/start を直列実行 | `Queue[Callable]` | **無し**（`while True`） |
| 5 | device monitoring（1 本） | `device_manager.py:409` | COM 通知待ち → `update()` → callback | `_notify_event` / callbacks | `_stop_event` + `join(0.5)` |
| 6 | COM コールバック (pycaw) | `device_manager.py:64-77` | `_notify_event.set()` | Event | 登録解除 |
| 7 | `ActiveEndpointTracker` ×2 | `active_endpoint_tracker.py:167` | 250ms で peak ポーリング | `on_change` → #4 | `stop()` + `join(2.0)` |
| 8/9 | mic / speaker listener | `transcription_recorder.py:218` | 発話区間検出 | → `audio_queue` / `energy_queue` | `stopper()` |
| 10 | `_print_transcript` ×2 | `model.py:354-356` | `audio_queue` → Whisper/Google → `transcript_fnc` | `audio_queue` ← | `stop()` + `join(15s)` |
| 11 | `_energy_progressbar` ×2 | `model.py:368-370` | `energy_queue` → UI | `energy_queue` ← | `stop()` + `join()`（**無制限**） |
| 12 | `mic-open`（使い捨て） | `transcription_recorder.py:126` | PyAudio open のタイムアウト隔離 | `threading.Event` | join せずリーク許容（設計上の意図） |
| 13 | watchdog | `model.py:1528` | 60s 無 feed で `Main.stop()` | `last_feed_time` | `stop()` + `join()`（**無制限**） |
| 14 | WebSocket server loop | `model.py:1605` | asyncio ループ + `_send_loop` | `asyncio.Queue` | `stop()` + `join(2.0/5.0)` |
| 15 | OBS HTTP server | `obs_browser_source_server.py:321` | `ThreadingHTTPServer.serve_forever` | HTTP | `shutdown()` + `join(2.0)` |
| 16 | OSC UDP server + 毎リクエストスレッド | `osc.py:170` | `/avatar/parameters/MuteSelf` 受信 | → `changeHandlerMute` → session.pause/resume | `shutdown()`（**最大 10s**） |
| 17 | OSCQuery HTTP / zeroconf | tinyoscquery 内 | サービス広告 | — | `http_server.shutdown()`（**shutdown から呼ばれない**） |
| 18 | Clipboard VR monitor | `clipboard.py:171` | SteamVR 検出 → `openvr.init/shutdown` | `self.app_name` | **無し**（`_stop_monitoring` は誰も True にしない） |
| 19 | Overlay main | `overlay.py:279-281` | OpenVR オーバーレイ 16fps 更新 | `self.settings` | `loop=False` + `join()`（**無制限**） |
| 20 | telemetry asyncio loop | `telemetry/__init__.py:73` | Aptabase 送信 | `run_coroutine_threadsafe` | `loop.stop()` + `join(5.0)` |
| 21 | config debounce `Timer` | `config.py:618` | 2s デバウンス保存 | `_file_lock` | `cancel()` |
| 22 | `ThreadPoolExecutor`（init 時 2/4 本） | `controller.py:3908, 4034` | 重み検証・翻訳エンジン疎通 | `Future` | `with` で join |
| 23 | ダウンロード各種 | `controller.py:3873/3882/3444/3450` | 重み DL | 進捗 callback | daemon / `join()`（**無制限**） |

**共有ロック**: `pyaudio_op_lock`（PortAudio/COM 全操作）、`Controller.mic_lifecycle_lock` / `speaker_lifecycle_lock`、`Main._endpoint_locks`（エンドポイント単位）、`config._file_lock`、`utils._stdout_write_lock`、`ActiveEndpointTracker._lock`。

---

## 付録 B. 外部通信インベントリ

| 通信先 | プロトコル | 送信データ | 認証 | 発生条件 |
|---|---|---|---|---|
| Google 音声認識 (`recognize_google`) | HTTPS | **マイク／スピーカーループバックの生音声** | なし（非公式エンドポイント） | **既定**の文字起こし全件 |
| Google / Bing / Papago Web 翻訳 (`translators` + `cloudscraper`) | HTTPS | 文字起こしテキスト | なし（スクレイピング） | 該当エンジン選択時 |
| DeepL API | HTTPS | 文字起こしテキスト | API キー | DeepL 選択時 |
| OpenAI / Gemini / Groq / OpenRouter / Plamo | HTTPS | 文字起こしテキスト + **会話履歴** | API キー | 各エンジン選択時 |
| OpenAI-Compatible | **任意（`http://` 可）** | 同上 | API キー | ユーザー指定 URL |
| LM Studio / Ollama | HTTP（localhost 既定、変更可） | 同上 | なし | 該当エンジン選択時 |
| Aptabase `us.aptabase.com` | HTTPS | `app_started` / `error`(error_code)、OS 名・バージョン・アーキ・locale・app version・セッション UUID | App-Key（埋め込み） | `ENABLE_TELEMETRY=true`（**既定 ON**） |
| GitHub API `api.github.com/repos/misyaguziya/VRCT/releases` | HTTPS | なし | なし | 起動時／更新確認 |
| Hugging Face `ms-software/VRCT/resolve/main/VRCT_setup.exe` | HTTPS | なし | なし | アップデート実行時（**検証なしで実行**） |
| Hugging Face Hub（モデル重み） | HTTPS | なし | なし | 重みダウンロード時 |
| `http://www.google.com`（疎通確認） | **HTTP** | なし | なし | `isConnectedNetwork` |
| VRChat OSC | **UDP 平文** | 文字起こし／翻訳テキスト | なし | `SEND_MESSAGE_TO_VRC` |
| WebSocket サーバ（自前） | ws:// 平文 | 文字起こし・翻訳・言語設定 | **なし** | `WEBSOCKET_SERVER=true` |
| OBS Browser Source HTTP（自前） | http:// | 静的 HTML | **なし** | `OBS_BROWSER_SOURCE=true` |

---

## 付録 C. リポジトリ内の実データによる裏付け

本レビューでは、コード読解に加えてリポジトリ内の実ログを証跡として使用しました。

| ファイル | 内容 | 関連指摘 |
|---|---|---|
| `src-python/error.log` | `OSError: device gone` @ `transcription_recorder.py:218 recordIntoQueue` | **P0-2**（Session 起動失敗が実際に起きている） |
| `src-python/error.log` | `OSError: [Errno 22] Invalid argument` @ `utils.py:48` 連発（2026-08-27 07:08） | B「stdout 破断」 |
| `src-python/freeze_trace.log` | 同時刻、全スレッド idle で feed が 35 秒来ない | 同上（フロントエンド消失後のゾンビ化） |
| `src-python/process.log:75` | `/run/initialization_complete` の集約レスポンスが記録されている（当該環境ではキーは全て `null`） | **P0-1**（第 2 経路の実証） |
| `src-tauri/process.log`（275KB）と `src-python/process.log` | ログが 2 箇所に散在 | C「ログ出力先が CWD 相対」 |

**注記**: リポジトリ内に実際の API キー・トークンの平文値は発見していません。`src-python/config.json` の `AUTH_KEYS` は全て `null` でした。ただし P0-1 により、キーが設定された環境では平文でログに残る構造になっています。

**本レビューではファイルを一切変更していません（読み取りのみ）。**
