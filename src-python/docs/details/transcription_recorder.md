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
                 phrase_time_limit: int, phrase_timeout: int = 1, record_timeout: int = 5,
                 vad_filter: bool = False, vad_parameters: Optional[dict] = None)

class SelectedSpeakerEnergyAndAudioRecorder(BaseEnergyAndAudioRecorder):
    def __init__(self, device: dict, energy_threshold: int, dynamic_energy_threshold: bool,
                 phrase_time_limit: int, phrase_timeout: int = 1, record_timeout: int = 5,
                 vad_filter: bool = False, vad_parameters: Optional[dict] = None)
```

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
  `phrase_timeout` ロジック (`updateLastSampleAndPhraseStatus`) に委ねる。
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

> **2026-08-15 訂正**: 以下は ADR-0004 (ストリーミング/VAD 独自実装の撤退) 直後時点の
> 記述で、現状と食い違います。実際には `recordIntoQueue` は
> `misyaguziya/custom_speech_recognition` フォークが提供する
> `Recognizer.listen_energy_and_audio_in_background`（`listen_in_background` 相当に
> `callback_energy` フックを足したもの）を使っています。`callback_energy` はフレーズ確定を
> 待たず生チャンク読み取りのたびに呼ばれ、Config パネルの音量メーターをリアルタイム更新する
> ために必須です（`listen_in_background` だけではフレーズ確定時にしかエナジー値が取れず、
> 音量メーターが動かなくなるデグレードが発生していました）。listener スレッド内の
> `pyaudio_op_lock` の扱いは変わらず、`recordIntoQueue` を呼ぶ側 (Model層) から見た
> インターフェースにも変更はありません。この節以降の VAD/`StreamingVadSegmenter` に関する
> 記述は撤退済みの旧設計のままなので、参照時は注意してください（別途ドキュメント刷新予定）。

## 設定パラメータ

### しきい値設定
- **energy_threshold**: `Recognizer` に設定されるが、現行の自作 listener ループでは
  フレーズ検出に使われない（`speech_recognition` の built-in energy-based phrase detection
  を使っていた旧経路の名残）。将来 `Recognizer` を使う経路を復活させる場合のために保持。
- **dynamic_energy_threshold**: 同上。

### タイムアウト設定
- **phrase_time_limit**: VAD partial スナップショットを送出する間隔の基準
  (`max(250ms, phrase_time_limit * 1000ms)`)。VAD 無効時は未使用。
- **phrase_timeout** / **record_timeout**: `AudioTranscriber` 側のフレーズ区切り判定に渡される
  (Recorder 自体は保持するのみ)。

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

- `transcription_transcriber.py` (`AudioTranscriber`): `AudioQueueItem` とタプル両方の
  キューアイテムを受け取り、フレーズを組み立てて認識エンジンに渡す。
- `device_manager.py`: `pyaudio_op_lock` の定義元、デバイス列挙・監視。
- `model.py`: `MicSession`/`SpeakerSession` (`_AudioDeviceSession`) が
  この Recorder のライフサイクルを features (`transcript`/`energy`) 単位で
  統合管理する。`Model.startMic/SpeakerTranscript`・`startCheckMic/
  SpeakerEnergy` は Session への薄いラッパー。`_DiscardQueue` の定義元でも
  ある。詳細は `model.md` を参照。
- `config.py`: 録音設定管理 (`MIC_THRESHOLD`, `MIC_VAD_FILTER` 等)。
