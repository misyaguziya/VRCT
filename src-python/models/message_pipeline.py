"""mic/speaker/chatメッセージパイプラインをプラガブルにするための
スペック抽象化(バックエンドレビュー フェーズ3項目25)。

`controller.py`の`micMessage`/`speakerMessage`/`chatMessage`は「翻訳→
transliteration→OSC送信→オーバーレイ更新→(mic限定)クリップボード→
UI配信→WebSocket送信→ロガー→履歴記録」という同一パイプラインを
ほぼ同じ形で3回書き下していた。このモジュールは「方向ごとに何が
違うか」だけをデータとして`MessageDirectionSpec`に集約し、
`Controller._processMessage`(controller.py)が共通実装として使う。

設計は`models/translation/translation_providers.py`の
`TranslationEngineSpec`/`TRANSLATION_PROVIDER_REGISTRY`(項目17)と
同じパターンを踏襲する: 差分を`@dataclass(frozen=True)`にまとめ、
config属性名は文字列で保持して呼び出し側が`getattr`/`setattr`する。

3方向の相違点のうち、以下はユーザーとの対話で「意図的な仕様」と
確定した(バグではない):

- ワードフィルタ(`checkKeywords`)はmic/speakerのみ。文字起こし由来の
  予期せぬ発言を抑制する目的のため、タイプ入力のchatには不要。
- transliterationの判定基準は mic/chat が「自分の設定言語が日本語か」
  (`own_transliteration_source="your_language"`)、speakerは「受信
  メッセージの検出言語が日本語か」(`"detected_language"`)。mic/chatは
  自分が生成した文章なので自分の設定言語基準、speakerは相手の発言
  なので相手の検出言語基準が理にかなっている。

一方、以下はchatMessageだけに存在した実バグで、統合により解消される
(詳細は`Controller._processMessage`のdocstring参照):

- `self._is_overlay_available()`のガード漏れ。
- 空メッセージ(`message == ""`)での`UnboundLocalError`。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from errors import ErrorCode


@dataclass(frozen=True)
class MessageDirectionSpec:
    """mic/speaker/chatメッセージパイプライン1方向分のメタデータ。"""

    kind: str  # "mic" | "speaker" | "chat" (履歴記録・ログ用)

    # --- 音声認識由来の前処理 (Controller.mic/speakerMessageの薄いラッパー側で使う) ---
    has_word_filter: bool  # checkKeywords を行うか (chatはFalse)
    repeat_detector_attr: Optional[str]  # model.detectRepeatXMessage のメソッド名 (chatはNone)

    # --- 翻訳 ---
    translate_attr: str  # "getInputTranslate" | "getOutputTranslate"
    multi_target: bool  # True=mic/chat (複数ターゲット言語をループ), False=speaker (単一)
    own_transliteration_source: str  # "your_language" | "detected_language"
    vram_error_code: ErrorCode  # TRANSLATION_VRAM_MIC/SPEAKER/CHAT
    vram_run_mapping_key: str  # error_translation_mic/speaker/chat_vram_overflow

    # --- 出力 ---
    feature_gate_attr: Optional[str]  # ENABLE_TRANSCRIPTION_SEND/RECEIVE (chatはNone=常時)
    osc_send_gate_attr: str  # SEND_MESSAGE_TO_VRC | SEND_RECEIVED_MESSAGE_TO_VRC
    osc_format_type: str  # "SEND" | "RECEIVED" (messageFormatterへ渡す)
    overlay_direction: str  # "send" | "receive" (createOverlayImageLargeLogへ渡す)
    overlay_small_log: bool  # speakerのみTrue (受信専用の簡易オーバーレイ)
    clipboard: bool  # micのみTrue
    ws_type: str  # "SENT" | "RECEIVED" | "CHAT"
    ws_src_languages_attr: str
    ws_dst_languages_attr: str
    logger_prefix: str  # "[SENT]" | "[RECEIVED]" | "[CHAT]"

    # --- 配信方式 ---
    delivery: str  # "push" (self.run() で配信、mic/speaker) | "return" (戻り値で返す、chat)
    run_mapping_key: Optional[str]  # delivery="push" のみ使用


MIC_MESSAGE_SPEC = MessageDirectionSpec(
    kind="mic",
    has_word_filter=True,
    repeat_detector_attr="detectRepeatSendMessage",
    translate_attr="getInputTranslate",
    multi_target=True,
    own_transliteration_source="your_language",
    vram_error_code=ErrorCode.TRANSLATION_VRAM_MIC,
    vram_run_mapping_key="error_translation_mic_vram_overflow",
    feature_gate_attr="ENABLE_TRANSCRIPTION_SEND",
    osc_send_gate_attr="SEND_MESSAGE_TO_VRC",
    osc_format_type="SEND",
    overlay_direction="send",
    overlay_small_log=False,
    clipboard=True,
    ws_type="SENT",
    ws_src_languages_attr="SELECTED_YOUR_LANGUAGES",
    ws_dst_languages_attr="SELECTED_TARGET_LANGUAGES",
    logger_prefix="[SENT]",
    delivery="push",
    run_mapping_key="transcription_mic",
)

SPEAKER_MESSAGE_SPEC = MessageDirectionSpec(
    kind="speaker",
    has_word_filter=True,
    repeat_detector_attr="detectRepeatReceiveMessage",
    translate_attr="getOutputTranslate",
    multi_target=False,
    own_transliteration_source="detected_language",
    vram_error_code=ErrorCode.TRANSLATION_VRAM_SPEAKER,
    vram_run_mapping_key="error_translation_speaker_vram_overflow",
    feature_gate_attr="ENABLE_TRANSCRIPTION_RECEIVE",
    osc_send_gate_attr="SEND_RECEIVED_MESSAGE_TO_VRC",
    osc_format_type="RECEIVED",
    overlay_direction="receive",
    overlay_small_log=True,
    clipboard=False,
    ws_type="RECEIVED",
    ws_src_languages_attr="SELECTED_TARGET_LANGUAGES",
    ws_dst_languages_attr="SELECTED_YOUR_LANGUAGES",
    logger_prefix="[RECEIVED]",
    delivery="push",
    run_mapping_key="transcription_speaker",
)

CHAT_MESSAGE_SPEC = MessageDirectionSpec(
    kind="chat",
    has_word_filter=False,
    repeat_detector_attr=None,
    translate_attr="getInputTranslate",
    multi_target=True,
    own_transliteration_source="your_language",
    vram_error_code=ErrorCode.TRANSLATION_VRAM_CHAT,
    vram_run_mapping_key="error_translation_chat_vram_overflow",
    feature_gate_attr=None,
    osc_send_gate_attr="SEND_MESSAGE_TO_VRC",
    osc_format_type="SEND",
    overlay_direction="send",
    overlay_small_log=False,
    clipboard=False,
    ws_type="CHAT",
    ws_src_languages_attr="SELECTED_YOUR_LANGUAGES",
    ws_dst_languages_attr="SELECTED_TARGET_LANGUAGES",
    logger_prefix="[CHAT]",
    delivery="return",
    run_mapping_key=None,
)
