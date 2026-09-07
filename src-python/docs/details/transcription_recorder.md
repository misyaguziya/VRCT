# transcription_recorder.py - 音声録音インターフェース

## 概要

音声認識システムの入力となる音声データを録音するレコーダーです。マイクとスピーカー出力
（ループバック）の両方をサポートし、音声データとエネルギーレベルを同じ Recorder インスタンス
から同時にキューへ供給できます。pyaudiowpatch (PyAudio) ライブラリを使用して Windows の
音声システムと統合します。

デバイスライフサイクル整理 (2026-08、本ブランチ) の Step 4 で、PyAudio/WASAPI に触る経路を
`BaseEnergyAndAudioRecorder` 一本に統合しました。以前存在した以下のクラスは削除済みです:

- `BaseRecorder` / `SelectedMicRecorder` / `SelectedSpeakerRecorder`
  (speech_recognition の `listen_in_background` を使う旧経路。未参照のため削除)
- `BaseEnergyRecorder` / `SelectedMicEnergyRecorder` / `SelectedSpeakerEnergyRecorder`
  (エナジー計測専用、speech_recognition の `listen_energy_in_background` を使う旧経路)

**2026-09-06、`config.ENABLE_VAD` (既定 False) でのオプトインとして VAD を再導入**しました
(過去2度、この領域で挑戦して未完了/リバートに終わっている経緯があるため、既定は従来通りの
エネルギー閾値方式のまま)。動機は「文章の途中で切れて意味が繋がらない」「静かな出だしの
音声を取りこぼす」という実機での指摘: エネルギー閾値方式の `phrase_time_limit`
(既定 `record_timeout`=3秒) は無音の有無に関わらず単語の途中でも問答無用で録音チャンクを
打ち切る設計であり、これが主因と判明した。`BaseVadAndAudioRecorder` は
`custom_speech_recognition` フォークの `Recognizer.listen_with_segmenter_in_background`
(区切り判定を一切持たず `segmenter` に完全委任する汎用の差し込み点) 経由で
`models/transcription/audio_vad.py` の `VadSegmenter` (Silero VAD、kikitan-translator と
同じパラメータ、プリロール・anchor方式のヒステリシス・`max_speech_frames` 安全弁を実装) に
発話区間検出を委ねる。詳細は `audio_vad.py` のモジュール docstring 参照。

エナジー計測専用の用途 (Config パネルのマイク/スピーカー音量メーター) も、現在は
`SelectedMic/SpeakerEnergyAndAudioRecorder` を `vad_filter=False` で使い、`audio_queue` 引数に
`model._DiscardQueue`（put を無視するダミー Queue）を渡すことで実現しています。理由は
「関連コード」節を参照してください。

## クラス構造

### BaseEnergyAndAudioRecorder クラス
```python
class BaseEnergyAndAudioRecorder:
    def __init__(
        self,
        source: Any,
        energy_threshold: int,
        dynamic_energy_threshold: bool,
        phrase_time_limit: int,
        phrase_timeout: int,
        record_timeout: int,
        vad_filter: bool = False,
        vad_parameters: Optional[dict[str, Any]] = None,
        enable_stall_watchdog: bool = True,
    )
```

音声録音とエネルギー監視を統合する唯一の Recorder。`vad_filter` の有無や `energy_queue` を
渡すかどうかで、以下の4通りの使われ方をすべて 1 つの listener ループでカバーします:

| vad_filter | energy_queue | 用途 |
|---|---|---|
| True | あり/なし | 文字起こし (VAD ON、デフォルト) |
| False | あり/なし | 文字起こし (VAD OFF) |
| False | あり (audio は `_DiscardQueue`) | エナジーメーターのみ |

### SelectedMicEnergyAndAudioRecorder / SelectedSpeakerEnergyAndAudioRecorder クラス
```python
class SelectedMicEnergyAndAudioRecorder(BaseEnergyAndAudioRecorder):
    def __init__(self, device: dict, energy_threshold: int, dynamic_energy_threshold: bool,
                 phrase_time_limit: int, record_timeout: int = 5)

class SelectedSpeakerEnergyAndAudioRecorder(BaseEnergyAndAudioRecorder):
    def __init__(self, device: dict, energy_threshold: int, dynamic_energy_threshold: bool,
                 phrase_time_limit: int, record_timeout: int = 5)
```

### BaseVadAndAudioRecorder クラス (`config.ENABLE_VAD` オプトイン)
```python
class BaseVadAndAudioRecorder:
    def __init__(self, source: Any, record_timeout: int, label: str = "vad")
```
`BaseEnergyAndAudioRecorder` と同じ open/close・停止/一時停止の仕組みを共有し、フレーズ
区切りの判定方法だけが異なる。`VadSegmenter` の `max_speech_frames` は `record_timeout`
(ユーザー設定、既定3秒) に連動させて、エネルギー閾値方式より1発話あたりの区間が
大幅に長くなって体感が遅くなることを防いでいる。`self.SAMPLE_RATE`/`SAMPLE_WIDTH`/
`channels` は常に VAD 正規化後の 16kHz/16bit/mono を公開する (ネイティブなデバイス
フォーマットではない点に注意 — `AudioTranscriber` が `last_sample` を再生/認識する際の
形式として直接使うため)。

### SelectedMicVadRecorder / SelectedSpeakerVadRecorder クラス
```python
class SelectedMicVadRecorder(BaseVadAndAudioRecorder):
    def __init__(self, device: dict, record_timeout: int = 5)

class SelectedSpeakerVadRecorder(BaseVadAndAudioRecorder):
    def __init__(self, device: dict, record_timeout: int = 5)
```
`model.py` の `MicSession._create_recorder`/`SpeakerSession._create_recorder` が
`config.ENABLE_VAD is True` の場合にこちらを選ぶ。`AudioTranscriber` 側も
`vad_segmented=True` で構築される。

audio_queue に積まれるアイテムの形はエネルギー閾値方式と異なり
`(raw_bytes, recorded_at, reason)` の3要素タプル。`reason` は
`"silence"`/`"flush"` (自然な区切り) または `"max_duration"`
(`VadSegmenter.max_speech_frames` の安全弁、無音を挟まない強制打ち切り)
のいずれか (`audio_vad.SpeechSegment.reason` が `custom_speech_recognition`
フォークの `AudioData.segment_reason` として伝播されたもの)。

**2026-09-06、実機検証で「長い連続発話ほど内容が丸ごと抜け落ちる」
regressionが判明し、reason に応じた挙動の分岐を追加した**: 当初は reason を
区別せず、キューの各アイテムを毎回単独で確定・文字起こししていた。しかし
`reason="max_duration"` の断片は単語の途中で始まり/終わる不自然な音声に
なりがちで、これを単独でエンジンに送ると、境界の不自然さでエンジン側の
信頼度フィルタ (Whisper の `avg_logprob`/`no_speech_prob`、Google の
`recognize_google` が返す `UnknownValueError`) に断片ごと棄却されやすい。
PuriPuly-heart (`docs/ref/PuriPuly-heart`) を参考に、`AudioTranscriber` 側で
`reason=="max_duration"` の断片は単独送信せず蓄積し、次に自然な区切り
(silence/flush) が来た時点でまとめて確定・送信するよう変更した (詳細は
`transcription_transcriber.py` の `transcribeAudioQueue` docstring 参照)。
あわせて `max_speech_frames` も `record_timeout` 連動から
PuriPuly-heart の `PEER_MAX_SEGMENT_MS` (7秒) を参考にした固定値に戻した
(record_timeout 連動だと既定3秒ごとに強制打ち切りが頻発し、上記
regressionの発生頻度を上げていたため)。

**2026-09-07、Google (無料/非公式エンドポイント) で「ネットワークエラーは
無いのに認識結果が0件で返る」問題が見つかり、複数の対策を試した経緯が
ある。** 一時期 `max_speech_seconds` 引数を追加して Google だけこの7秒を
3秒に短縮する対策を試したが、実機検証で「呼び出し頻度が上がり過ぎて
処理が悪化する」regressionが確認され撤回した (この引数自体は削除済み、
`max_speech_frames` は常にエンジンを問わず固定7秒)。一方、
`AudioTranscriber` 側の「確定したクリップの前後に無音パディングを付与する」
(`VAD_PRE_PAD_MS`/`VAD_POST_PAD_MS`、エンジンを問わず一律に適用) と
「Google だけ育っていくバッファを都度再送信する」(`interim_send`) は
どちらも有効な対策と判断し、両方を維持している (パディング単体では実機の
再検証で無応答が再発したため、2つを併用する形に落ち着いた)。この
Recorder 自体には Google固有の分岐は無く、上記2つの対策は
`transcription_transcriber.py` 側で完結している。

マイク/スピーカーそれぞれのデバイスを開いて `BaseEnergyAndAudioRecorder` を構築します。
`SelectedSpeakerEnergyAndAudioRecorder` は `enable_stall_watchdog=False` を固定で渡します。
WASAPI ループバックは再生されていない間ずっと無音でブロックするのが正常な状態であり、これを
「デバイス停滞」として `device_error_event` に上げてしまうと "No speaker device detected" の
誤検知になるためです（マイク側は `enable_stall_watchdog=True` のまま — Virtual Desktop Audio
のような仮想デバイスが実際に停止した場合を検知するため）。

## 主要メソッド

```python
recordIntoQueue(audio_queue: Queue, energy_queue: Optional[Queue] = None) -> None
```
`self.stop` / `self.pause` / `self.resume` に、専用 listener スレッドを操作する関数を割り当てて
録音を開始します。内部実装 (`_recordIntoQueueInternal`) は VAD 有無を問わず単一のループです:

- `vad_filter=True`: `StreamingVadSegmenter` でセグメント化し、`AudioQueueItem`
  (`is_final`/`segment_id`/`speech_ended_at` 付き) を `audio_queue` に積む。
- `vad_filter=False`: 正規化した生チャンクをそのまま `(audio_bytes, recorded_at)` の
  タプルで `audio_queue` に積む。フレーズの区切りは `AudioTranscriber` 側の
  `phrase_timeout` ロジック (`AudioTranscriber.transcribeAudioQueue`) に委ねる。
- `energy_queue` が渡されていれば、チャンクごとに `audioop.rms` で計算したエネルギー値を
  同時に積む。

```python
pause() -> None
resume() -> None
stop(wait_for_stop: bool = True) -> None
```
`recordIntoQueue` 呼び出し後、`self.pause`/`self.resume`/`self.stop` としてこれらの関数が
利用可能になります。`stop()` は `pyaudio_stream.stop_stream()` (Pa_StopStream) を叩いてから
listener スレッドの `join()` を待つことで、無音ループバックで `stream.read()` にブロックした
listener を素早く解放します（詳細はソースのコメント参照）。

```python
adjustForNoise() -> None
```
環境ノイズに合わせたしきい値調整（未使用、将来のために残置）。

## PyAudio 直列化 (pyaudio_op_lock)

`device_manager.py` で定義された module-level の `pyaudio_op_lock` を、この Recorder の
以下の箇所で保持します:

- `_validate_audio_source` (コンストラクタ内、`Microphone.__enter__`/`__exit__` によるデバイス
  疎通確認)
- listener スレッドの `self.source.__enter__()` / `__exit__()` (open/close の瞬間のみ。
  `stream.read()` のブロッキング読み取りループ中はロックを解放し、`device_manager.update()`
  側のデバイス列挙を妨げない)

`device_manager.update()` 側も同じロックを取るため、PyAudio/WASAPI への操作
(デバイス列挙、ストリーム open/close) が同時に走ることはなく、Windows WASAPI 特有の
「並行操作でデッドロック」を防ぎます。

`recordIntoQueue` は `misyaguziya/custom_speech_recognition` フォークが提供する
`Recognizer.listen_energy_and_audio_in_background`（`listen_in_background` 相当に
`callback_energy` フックを足したもの、エネルギー閾値方式）または
`Recognizer.listen_with_segmenter_in_background`（区切り判定を `segmenter` に完全委任する
汎用の差し込み点、`config.ENABLE_VAD` 時）のいずれかを使います。`callback_energy` は
フレーズ確定を待たず生チャンク読み取りのたびに呼ばれ、Config パネルの音量メーターを
リアルタイム更新するために必須です（`listen_in_background` だけではフレーズ確定時にしか
エナジー値が取れず、音量メーターが動かなくなるデグレードが発生していました）。listener
スレッド内の `pyaudio_op_lock` の扱いはどちらの経路でも変わらず、`recordIntoQueue` を
呼ぶ側 (Model層) から見たインターフェースにも変更はありません。

## 設定パラメータ

### しきい値設定
- **energy_threshold**: `Recognizer` に設定されるが、現行の自作 listener ループでは
  フレーズ検出に使われない（`speech_recognition` の built-in energy-based phrase detection
  を使っていた旧経路の名残）。将来 `Recognizer` を使う経路を復活させる場合のために保持。
- **dynamic_energy_threshold**: 同上。

### タイムアウト設定
- **phrase_time_limit**: エネルギー閾値方式のみで使用。`record_timeout` と同値
  (`model.py` の `_create_recorder` で `min(RECORD_TIMEOUT, PHRASE_TIMEOUT)` に丸めてから
  両方に渡す)。無音の有無に関わらず、この秒数を超えたら単語の途中でも録音チャンクを
  問答無用で打ち切る (`listen_energy_and_audio_in_background` の仕様)。
- **record_timeout**: エネルギー閾値方式では `phrase_time_limit` と同値として渡される他、
  「無音待ちのまま音声が全く来ない」場合のタイムアウトとしても使う。VAD 方式では
  `VadSegmenter.max_speech_frames` (発話区間の安全弁上限) の算出元として使う。
- **phrase_timeout**: `AudioTranscriber` 側のフレーズ区切り判定に渡される (Recorder 自体は
  保持するのみ)。VAD 方式では `AudioTranscriber.vad_segmented=True` によりこの値ベースの
  蓄積ロジック自体がバイパスされる (VAD が既に区切り済みのため)。

### デバイス設定
- **name**: デバイス名
- **index**: デバイスインデックス
- **channels**: チャンネル数（1=モノラル、2=ステレオ）
- **defaultSampleRate**: サンプリングレート（Hz）

## エラーハンドリング

### デバイスエラー
- `device_error_event` (threading.Event): listener スレッド内の例外、または stall watchdog
  発火時にセットされる。呼び出し側 (`model.py` の `sendMicTranscript`/`sendSpeakerTranscript`)
  がこれをポーリングし、`{"text": False, "language": None}` を返してデバイスエラーとして
  UI に通知する。

### ストリーム停滞 (stall watchdog)
- `stream.read()` に組み込みタイムアウトが無いため、仮想/ループバックデバイスがデータを
  止めても例外が発生しない。`_STREAM_STALL_TIMEOUT_SEC` (10秒) 読み取りが無ければ
  `device_error_event` をセットして listener を終了させる。
- watchdog は **stream を別スレッドから close しない**。Windows WASAPI では read/close の
  同時実行がデッドロックの原因になるため。

## 関連モジュール

- `transcription_transcriber.py` (`AudioTranscriber`): `(raw_bytes, recorded_at)` タプルを
  受け取り、フレーズを組み立てて認識エンジンに渡す。`vad_segmented=True` (config.ENABLE_VAD)
  では蓄積せず各アイテムを単独で確定・文字起こしする。
- `models/transcription/audio_vad.py` (`VadSegmenter`/`VadRecognizerAdapter`):
  `config.ENABLE_VAD` 時の発話区間検出本体。Silero VAD (faster-whisper 同梱 ONNX) による
  プリロール・anchor方式ヒステリシス・`max_speech_frames` 安全弁の実装。
- `device_manager.py`: `pyaudio_op_lock` の定義元、デバイス列挙・監視。
- `model.py`: `MicSession`/`SpeakerSession` (`_AudioDeviceSession`) が
  この Recorder のライフサイクルを features (`transcript`/`energy`) 単位で
  統合管理する。`Model.startMic/SpeakerTranscript`・`startCheckMic/
  SpeakerEnergy` は Session への薄いラッパー。`_DiscardQueue` の定義元でも
  ある。詳細は `model.md` を参照。
- `config.py`: 録音設定管理 (`MIC_THRESHOLD` 等) と `ENABLE_VAD` (既定 False、オプトイン)。
