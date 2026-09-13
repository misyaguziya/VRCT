"""Runtime transcriber that wraps Google SpeechRecognition and faster-whisper.

This class focuses on converting incoming raw audio buffers into text using
either the Google web recognizer (online) or a local Whisper model (offline).

キューには常に (raw_bytes, recorded_at) タプルが積まれる。エネルギー
閾値方式 (既定) では、フレーズ境界は
`speech_recognition.listen_energy_and_audio_in_background` の
phrase_time_limit と AudioTranscriber.transcribeAudioQueue の
phrase_timeout/MAX_PHRASE_DURATION_SECONDS で決まる。VAD方式
(config.MIC_ENABLE_VAD/SPEAKER_ENABLE_VAD、2026-09-06にオプトインとして再導入) では、
キューの各アイテムは既に `audio_vad.VadSegmenter` が区切り終えた
1フレーズであり、蓄積せず即座に確定・文字起こしする
(`self.vad_segmented`、詳細は transcribeAudioQueue 参照)。
partial (発話中の暫定結果) 通知は行わない。

フレーズが「完成した」と判断できるまでは文字起こしを実行しない
(2026-09-06のコードレビュー議論で「確定してから送る」方式に変更)。
以前は溜まっているチャンクがあれば毎回その時点の last_sample 全体を
再送信していたため、無音ギャップが来ない継続発話 (大人数の会話など) で
送るたびに音声が長くなり推論がさらに遅くなる、という雪だるま式の遅延が
生じていた。詳細は transcribeAudioQueue の docstring 参照。
"""

import time
from io import BytesIO
from queue import Empty
from threading import Event
import wave
from typing import Any, Dict, List, Optional
from speech_recognition import Recognizer, AudioData, AudioFile
from speech_recognition.exceptions import UnknownValueError
from datetime import datetime, timedelta
from pyaudiowpatch import get_sample_size, paInt16
from .transcription_whisper import getWhisperModel, checkWhisperWeight
from .transcription_providers import (
    GoogleProvider,
    LocalWhisperProvider,
    OpenAICompatibleTranscriptionProvider,
    DeepgramProvider,
    TranscriptionApiError,
)
from .transcription_openai_compatible import TRANSCRIPTION_API_ENGINES as _API_TRANSCRIPTION_ENGINES

# OpenAI互換系 (base_url/model差し替え) に加えて、独自プロトコルの
# Deepgramも「APIキー/モデルを持つクラウドエンジン」として同列に扱う箇所
# (last_recognition_errorのリセット対象等) で使う。
_CLOUD_TRANSCRIPTION_ENGINES = _API_TRANSCRIPTION_ENGINES + ("Deepgram",)

from pydub import AudioSegment
from errors import AudioPipelineError, AudioPipelineFailure, ERROR_METADATA, ErrorCode
from utils import errorLogging, printLog

import warnings
warnings.simplefilter('ignore', RuntimeWarning)

PHRASE_TIMEOUT = 3
MAX_PHRASES = 10
GOOGLE_RECOGNIZE_TIMEOUT_SECONDS = 10

# 無音ギャップが来ない継続発話でも、一定時間ごとに強制的にフレーズを
# 区切って確定させる安全弁 (フェーズ3項目20の代替。2026-09-06の
# コードレビューで「確定してから送る」方式に変更した際に導入)。
# kikitan/PuriPuly-heart (他ツールのVAD実装、docs/ref/ 参照) を参考に、
# self.phrase_timeout とは独立した固定値にしている。
MAX_PHRASE_DURATION_SECONDS = 15

# VAD方式 (config.MIC_ENABLE_VAD/SPEAKER_ENABLE_VAD) で確定したクリップの前後に付与する無音
# (ゼロバイト) パディング。2026-09-07: Google (無料/非公式エンドポイント)
# で「ネットワークエラーは無いのに認識結果が0件で返る」
# (UnknownValueError) ケースを実機で確認した。当初は Google だけの
# 特別扱い (GoogleProvider内でのパディング、育っていくバッファを都度
# 再送信する方式等) として対策していたが、実機検証で「クリップの前後に
# 無音パディングを付与する」だけで無応答/内容欠落が解消することを確認した
# ため、VADが確定するクリップ全体 (エンジンを問わない) にこの対策を
# 一本化した。kikitan-translator・PuriPuly-heart (docs/ref/ 参照) を参考に
# した値。エネルギー閾値方式 (vad_segmented=False) は対象外 (v3.5.0から
# 変わらない挙動のままで問題が確認されていないため)。
VAD_PRE_PAD_MS = 300
VAD_POST_PAD_MS = 500


class AudioTranscriber:
    """Convert queued audio buffers into transcripts.

    Public attributes set by the constructor:
    - speaker: bool
    - phrase_timeout: int
    - max_phrases: int
    """

    def __init__(
        self,
        speaker: bool,
        source: Any,
        phrase_timeout: int,
        max_phrases: int,
        transcription_engine: str,
        root: Optional[str] = None,
        whisper_weight_type: Optional[str] = None,
        device: str = "cpu",
        device_index: int = 0,
        compute_type: str = "auto",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        api_model: Optional[str] = None,
        api_model_languages: Optional[List[str]] = None,
        vad_segmented: bool = False,
        source_label: Optional[str] = None,
    ) -> None:
        self.speaker = speaker
        self.source = source_label or ("speaker" if speaker else "mic")
        self.phrase_timeout = phrase_timeout
        self.max_phrases = max_phrases
        # True の場合、audio_queue に積まれる各アイテムは既に VAD
        # (audio_vad.VadSegmenter) がプリロール・hangover・max_speech_frames
        # で区切り終えた「完成済みの1フレーズ」である。この場合は
        # phrase_timeout/MAX_PHRASE_DURATION_SECONDS による蓄積・再分割を
        # 行わず、キューから取り出した各アイテムをそのまま単独で確定・
        # 文字起こしする (詳細は transcribeAudioQueue の docstring 参照)。
        self.vad_segmented = vad_segmented
        self.transcript_data: List[Dict[str, Any]] = []
        self.transcript_changed_event = Event()
        self.last_recognition_error = False
        self.last_api_error_code: Optional[ErrorCode] = None
        # ASR呼び出しの成功/失敗率の計測 (2026-09-07)。Google無料エンドポ
        # イントの信頼性対策 (無音パディング・interim_send) の効果を、
        # ログの手動突き合わせではなく数値で継続的に確認できるようにする
        # ため。_finalizeAndTranscribe が呼ばれるたびに1回の「試行」として
        # カウントし、テキストが得られた場合のみ「成功」とする。
        self.asr_attempts = 0
        self.asr_successes = 0
        self.audio_recognizer = Recognizer()
        self.audio_recognizer.operation_timeout = GOOGLE_RECOGNIZE_TIMEOUT_SECONDS
        self.transcription_engine = "Google"
        self.whisper_model = None
        self.whisper_weight_type = whisper_weight_type
        self._api_provider: Optional[OpenAICompatibleTranscriptionProvider] = None
        self.audio_sources: Dict[str, Any] = {
            "sample_rate": source.SAMPLE_RATE,
            "sample_width": source.SAMPLE_WIDTH,
            "channels": source.channels,
            "last_sample": bytes(),
            "last_spoken": None,
            "phrase_started_at": None,
            "process_data_func": self.processSpeakerData if speaker else self.processMicData,
        }

        if transcription_engine == "Whisper" and checkWhisperWeight(root, whisper_weight_type) is True:
            self.whisper_model = getWhisperModel(
                root, whisper_weight_type, device=device, device_index=device_index, compute_type=compute_type
            )
            self.transcription_engine = "Whisper"
        elif transcription_engine in _API_TRANSCRIPTION_ENGINES:
            self.transcription_engine = transcription_engine
            try:
                self._api_provider = OpenAICompatibleTranscriptionProvider(
                    api_key=api_key or "",
                    base_url=base_url or "",
                    model=api_model or "",
                    engine_name=transcription_engine,
                )
            except Exception:
                errorLogging()
                raise
        elif transcription_engine == "Deepgram":
            self.transcription_engine = transcription_engine
            try:
                self._api_provider = DeepgramProvider(
                    api_key=api_key or "",
                    model=api_model or "",
                    model_languages=api_model_languages,
                )
            except Exception:
                errorLogging()
                raise

    def _resolve_provider(self):
        """`self.transcription_engine`/`self.whisper_model` の"現在の"値を見て
        対応するプロバイダを返す。既存テストが構築後に直接
        `transcriber.transcription_engine`/`transcriber.whisper_model` を
        書き換える運用になっているため、`__init__` 時点で1回だけ決め打つ
        のではなく、呼び出しの都度その場で解決する。
        """
        if self.transcription_engine == "Whisper":
            if self.whisper_model is None:
                return None
            return LocalWhisperProvider(self.whisper_model)
        if self.transcription_engine in _CLOUD_TRANSCRIPTION_ENGINES:
            return self._api_provider
        return GoogleProvider(self.audio_recognizer)

    def transcribeAudioQueue(
        self,
        audio_queue: Any,
        languages: List[str],
        countries: List[str],
        avg_logprob: float = -0.8,
        no_speech_prob: float = 0.6,
        no_repeat_ngram_size: int = 0,
    ) -> bool:
        """キューを非ブロッキングで drain し、フレーズが完成したと判断
        できた時だけ実際に文字起こしを実行する。

        以前は「キューに何かあれば毎回、その時点の last_sample 全体を
        再送信する」実装だったため、無音ギャップが来ない継続発話
        (大人数の会話など) で、送るたびに音声が長くなり推論がさらに
        遅くなる → もっと溜まる、という雪だるま式の遅延が生じていた
        (コードレビュー2026-09-06)。フレーズが完成するまでは蓄積する
        だけにし、以下いずれかの条件で「完成」とみなして初めて送信する:

          1. 無音ギャップ (self.phrase_timeout 秒) を超えた
          2. 継続時間が MAX_PHRASE_DURATION_SECONDS を超えた
          3. (キューが空になった後) 実時間で self.phrase_timeout 秒
             経過した (発話がそこで終わっていれば、次のチャンクは
             永久に来ないため、次のチャンク到達を待つだけでは検知できない)

        蓄積するだけのラウンドは何も送信せず False を返す。呼び出し元
        (model.py の sendTranscript) は前回表示した内容をそのまま残せば
        よい。

        self.vad_segmented が True の場合 (config.MIC_ENABLE_VAD/SPEAKER_ENABLE_VAD)、キューの各
        アイテムは (raw_bytes, recorded_at, reason) の3要素タプルで、
        reason は "silence"/"flush" (自然な区切り) または "max_duration"
        (無音を挟まない強制打ち切り、audio_vad.VadSegmenter.max_speech_frames
        の安全弁) のいずれか。

        当初は reason を区別せず「VAD が返す各アイテムは常に完成済みの
        1フレーズ」として毎回単独で確定・送信していたが、実機検証で
        「長い連続発話ほど内容が丸ごと抜け落ちる」regressionが判明した
        (2026-09-06)。原因は reason="max_duration" の断片 (単語の途中で
        始まり/終わる不自然な音声) を単独でエンジンに送ると、境界の
        不自然さでエンジン側の信頼度フィルタ (Whisper の avg_logprob/
        no_speech_prob) に断片ごと棄却されやすいこと。PuriPuly-heart
        (docs/ref/PuriPuly-heart) を参考に、reason=="max_duration" の
        断片は単独送信せず蓄積し、次に自然な区切り (silence/flush) が
        来た時点でまとめて確定・送信する。話者が本当にノンストップで
        話し続け自然な区切りが長時間来ない病的なケースの保険として、
        MAX_PHRASE_DURATION_SECONDS 安全弁も維持する。

        2026-09-07、Google (無料/非公式エンドポイント) で「ネットワーク
        エラーは無いのに認識結果が0件で返る」問題が見つかり、対策として
        (1) 確定したクリップの前後に無音パディングを付与する
        (`_padWithSilenceForVad`、VAD_PRE_PAD_MS/VAD_POST_PAD_MS 参照、
        エンジンを問わず一律に適用) を導入した。これ単体で改善は確認できた
        ため、一時は Google 固有の特別扱いを全て撤回しこのパディングのみに
        一本化していたが、実機での再検証でパディング単体でも無応答が
        再発する (完全に無くなるわけではない) ことを確認し、
        (2) **Google エンジンは「育っていくバッファを都度送信する」方式**
        (interim_send) も併用する形に戻した。reason に関わらず新しい
        チャンクが来るたびに「発話の先頭からここまでの累積バッファ」全体を
        都度再送信し (last_sample はリセットしない)、結果が来るたびに
        transcript を更新する。自然な区切り (silence/flush) が来た時点、
        または MAX_PHRASE_DURATION_SECONDS 安全弁に達した時点で最後に
        もう一度送信して確定・リセットする (finalize)。パディングは
        finalize/interim_send のどちらでも同じ (1) の仕組みで適用される
        (呼び出しのたびに last_sample のコピーへ付与し、蓄積用の
        last_sample 自体は無加工のまま保つ)。Whisper 等の他エンジンは
        引き続き「確定してから1回だけ送る」方式のまま変更しない (Google
        ほど個々の呼び出しの信頼性が低くなく、呼び出し回数を増やす必要が
        無いため)。
        """
        source_info = self.audio_sources
        transcribed = False
        is_google = self.transcription_engine == "Google"
        kind = "speaker" if self.speaker else "mic"

        def send_current_buffer() -> bool:
            # VAD確定時は last_sample のコピーにのみパディングを付与して
            # 送信し、蓄積用の last_sample 自体は無加工のまま維持する
            # (interim_send が後続チャンクをそのまま追記できるようにする
            # ため、パディング済みの内容を蓄積側に混ぜてはいけない)。
            original = source_info["last_sample"]
            if not original:
                return False
            if self.vad_segmented:
                source_info["last_sample"] = self._padWithSilenceForVad(original)
            try:
                return self._finalizeAndTranscribe(
                    languages, countries, avg_logprob, no_speech_prob, no_repeat_ngram_size
                )
            finally:
                source_info["last_sample"] = original

        def finalize() -> None:
            nonlocal transcribed
            if send_current_buffer():
                transcribed = True
            source_info["last_sample"] = bytes()
            source_info["phrase_started_at"] = None

        def interim_send() -> None:
            # Google 専用: finalize と異なり last_sample/phrase_started_at を
            # リセットしない。次のチャンクが来たら、今回よりさらに育った
            # 同じ発話の累積バッファを再送信することになる (v3.5.0 と同じ)。
            nonlocal transcribed
            if send_current_buffer():
                transcribed = True

        def reset_only() -> None:
            # Google 専用: interim_send() で直前に送信済みの内容を
            # もう一度 _finalizeAndTranscribe に通すと無駄な二重送信に
            # なるため、次のフレーズのための状態リセットだけ行う。
            source_info["last_sample"] = bytes()
            source_info["phrase_started_at"] = None

        if self.vad_segmented:
            while True:
                try:
                    data, time_spoken, reason = audio_queue.get_nowait()
                except Empty:
                    break

                if source_info["phrase_started_at"] is None:
                    source_info["phrase_started_at"] = time_spoken
                source_info["last_sample"] += data
                source_info["last_spoken"] = time_spoken
                accumulated_sec = (time_spoken - source_info["phrase_started_at"]).total_seconds()

                if reason != "max_duration":
                    # 自然な区切り (silence/flush) → ここまでの蓄積分を
                    # まとめて確定・送信する。
                    printLog(
                        f"[VAD-merge][{kind}] finalize reason={reason!r} "
                        f"accumulated={accumulated_sec:.2f}s bytes={len(source_info['last_sample'])}"
                    )
                    finalize()
                elif accumulated_sec >= MAX_PHRASE_DURATION_SECONDS:
                    # 話者が本当にノンストップで話し続け、VAD 側の
                    # max_speech_frames が silence/flush を伴わず
                    # max_duration を繰り返し返し続ける病的なケースの保険。
                    printLog(
                        f"[VAD-merge][{kind}] safety-net finalize reason={reason!r} "
                        f"accumulated={accumulated_sec:.2f}s bytes={len(source_info['last_sample'])}"
                    )
                    finalize()
                elif is_google:
                    printLog(
                        f"[VAD-merge][{kind}] interim-send (Google) reason={reason!r} "
                        f"accumulated={accumulated_sec:.2f}s bytes={len(source_info['last_sample'])}"
                    )
                    interim_send()
                else:
                    # reason == "max_duration" かつ上記安全弁未到達 →
                    # 単独送信せず蓄積を継続する (次のアイテムへ)。
                    printLog(
                        f"[VAD-merge][{kind}] accumulate reason={reason!r} "
                        f"accumulated={accumulated_sec:.2f}s bytes={len(source_info['last_sample'])}"
                    )
            if not transcribed:
                time.sleep(0.01)
            return transcribed

        while True:
            try:
                data, time_spoken = audio_queue.get_nowait()
            except Empty:
                break

            if (
                source_info["last_spoken"] is not None
                and time_spoken - source_info["last_spoken"] > timedelta(seconds=self.phrase_timeout)
            ):
                # Google の場合、ここに残っている last_sample は直前の
                # ループで既に interim_send() 済みなので、再送信せず
                # リセットだけする (無駄な二重送信を避ける)。
                reset_only() if is_google else finalize()

            if source_info["phrase_started_at"] is None:
                source_info["phrase_started_at"] = time_spoken

            source_info["last_sample"] += data
            source_info["last_spoken"] = time_spoken

            if time_spoken - source_info["phrase_started_at"] >= timedelta(seconds=MAX_PHRASE_DURATION_SECONDS):
                finalize()
            elif is_google:
                interim_send()

        if (
            source_info["last_sample"]
            and source_info["last_spoken"] is not None
            and datetime.now() - source_info["last_spoken"] > timedelta(seconds=self.phrase_timeout)
        ):
            # Google はループ内の interim_send() でこの時点の last_sample を
            # 直前に既に送信済み (末尾のチャンクが来た回のループで送られて
            # いる) なので、再送信せずリセットだけする。
            reset_only() if is_google else finalize()

        if not transcribed:
            time.sleep(0.01)
        return transcribed

    def _padWithSilenceForVad(self, data: bytes) -> bytes:
        """VAD が確定したクリップの前後に無音 (ゼロバイト) を付与する。

        実際の音声を追加でキャプチャするわけではなく、確定直前にのみ
        digital silence を足すだけなので、VAD自体のプリロールや他の
        ロジックには一切影響しない。エンジンを問わず一律に適用する
        (2026-09-07、詳細は VAD_PRE_PAD_MS/VAD_POST_PAD_MS のコメント参照)。
        """
        sample_rate = self.audio_sources["sample_rate"]
        sample_width = self.audio_sources["sample_width"]
        bytes_per_ms = sample_rate * sample_width / 1000
        pre_silence = b"\x00" * int(bytes_per_ms * VAD_PRE_PAD_MS)
        post_silence = b"\x00" * int(bytes_per_ms * VAD_POST_PAD_MS)
        return pre_silence + data + post_silence

    def _finalizeAndTranscribe(
        self,
        languages: List[str],
        countries: List[str],
        avg_logprob: float,
        no_speech_prob: float,
        no_repeat_ngram_size: int,
    ) -> bool:
        """確定した audio_sources['last_sample'] を実際に文字起こしする。
        last_sample のクリアは呼び出し元 (transcribeAudioQueue) が行う。
        """
        # Google/API系はネットワーク経由のためエラーが一時的なことが多く、
        # 呼び出しの都度エラー状態をクリアして UI に古いエラーを残さない。
        # ローカル Whisper は従来からこのリセットを行っておらず、その挙動は
        # 変更しない (エラーが決定的である= リトライしても意味が薄いため)。
        if self.transcription_engine == "Google" or self.transcription_engine in _CLOUD_TRANSCRIPTION_ENGINES:
            self.last_recognition_error = False
            self.last_api_error_code = None

        best: Dict[str, Any] = {"confidence": 0, "text": "", "language": None}
        provider_error: Optional[Exception] = None
        try:
            audio_data = self.audio_sources["process_data_func"]()
            provider = self._resolve_provider()
            if provider is None:
                provider_error = RuntimeError("transcription provider is unavailable")
            else:
                force_language = len(languages) == 1
                for language, country in zip(languages, countries):
                    try:
                        text, confidence, is_definitive = provider.transcribe(
                            audio_data,
                            language,
                            country,
                            avg_logprob=avg_logprob,
                            no_speech_prob=no_speech_prob,
                            no_repeat_ngram_size=no_repeat_ngram_size,
                            force_language=force_language,
                        )
                    except UnknownValueError:
                        continue
                    except TranscriptionApiError as exc:
                        self.last_recognition_error = True
                        self.last_api_error_code = exc.error_code
                        provider_error = provider_error or exc
                        errorLogging()
                        continue
                    except Exception as exc:  # noqa: BLE001 - convert to pipeline failure
                        self.last_recognition_error = True
                        provider_error = provider_error or exc
                        errorLogging()
                        continue

                    if confidence > best["confidence"]:
                        best = {"confidence": confidence, "text": text, "language": language}
                    if is_definitive:
                        break

        except UnknownValueError:
            pass
        except AudioPipelineError:
            raise
        except Exception as exc:  # noqa: BLE001 - convert to pipeline failure
            errorLogging()
            provider_error = provider_error or exc

        self.asr_attempts += 1
        succeeded = best["text"] != ""
        if provider_error is not None and not succeeded:
            failure = AudioPipelineFailure(
                error_code=ErrorCode.ASR_ERROR,
                stage="asr",
                source=self.source,
                message=ERROR_METADATA[ErrorCode.ASR_ERROR]["message"],
                exception_type=type(provider_error).__name__,
            )
            printLog(
                f"[ASR-error][{self.source}][{self.transcription_engine}] "
                f"error_type={type(provider_error).__name__}"
            )
            raise AudioPipelineError(failure) from provider_error
        if succeeded:
            self.last_recognition_error = False
            self.asr_successes += 1
            self.updateTranscript(best)
        success_rate = (self.asr_successes / self.asr_attempts) * 100
        printLog(
            f"[ASR-stats][{'speaker' if self.speaker else 'mic'}][{self.transcription_engine}] "
            f"this_call={'success' if succeeded else 'failure'} "
            f"attempts={self.asr_attempts} successes={self.asr_successes} rate={success_rate:.1f}%"
        )
        return True

    def processMicData(self) -> AudioData:
        audio_data = AudioData(
            self.audio_sources["last_sample"], self.audio_sources["sample_rate"], self.audio_sources["sample_width"]
        )
        return audio_data

    def processSpeakerData(self) -> AudioData:
        temp_file = BytesIO()
        with wave.open(temp_file, 'wb') as wf:
            wf.setnchannels(self.audio_sources["channels"])
            wf.setsampwidth(get_sample_size(paInt16))
            wf.setframerate(self.audio_sources["sample_rate"])
            wf.writeframes(self.audio_sources["last_sample"])
        temp_file.seek(0)

        if self.audio_sources["channels"] > 2:
            audio = AudioSegment.from_file(temp_file, format="wav")
            mono_audio = audio.set_channels(1)
            temp_file = BytesIO()
            mono_audio.export(temp_file, format="wav")
            temp_file.seek(0)

        with AudioFile(temp_file) as source:
            audio = self.audio_recognizer.record(source)
        return audio

    def updateTranscript(self, result: dict) -> None:
        """呼び出し元 (_finalizeAndTranscribe) は完成したフレーズ1件に
        つき1回だけ呼ぶため、常に新しいエントリとして挿入する
        (「まだ確定していない同一フレーズを上書きする」という概念は
        「確定してから送る」設計では発生しない)。
        """
        transcript = self.transcript_data
        if len(transcript) > self.max_phrases:
            transcript.pop(-1)
        transcript.insert(0, result)

    def getTranscript(self) -> dict:
        if len(self.transcript_data) > 0:
            result = self.transcript_data.pop(-1)
        else:
            result = {"confidence": 0, "text": "", "language": None}
        return result

    def clearTranscriptData(self) -> None:
        self.transcript_data.clear()
        self.audio_sources["last_sample"] = bytes()
        self.audio_sources["last_spoken"] = None
        self.audio_sources["phrase_started_at"] = None
