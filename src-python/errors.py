# src-python/errors.py
"""
統一エラー管理システム

すべてのエラーを一元管理し、エンドポイントとエラーコードの対応を明確にする。
"""

from typing import Any, Optional, Dict
from enum import Enum


class ErrorCode(str, Enum):
    """エラーコード定数
    
    命名規則: カテゴリ_具体的な内容
    """
    # ============================================================================
    # デバイス関連エラー (DEVICE_*)
    # ============================================================================
    DEVICE_NO_MIC = "DEVICE_NO_MIC"
    DEVICE_NO_SPEAKER = "DEVICE_NO_SPEAKER"
    
    # ============================================================================
    # 翻訳関連エラー (TRANSLATION_*)
    # ============================================================================
    TRANSLATION_ENGINE_LIMIT = "TRANSLATION_ENGINE_LIMIT"
    TRANSLATION_VRAM_CHAT = "TRANSLATION_VRAM_CHAT"
    TRANSLATION_VRAM_MIC = "TRANSLATION_VRAM_MIC"
    TRANSLATION_VRAM_SPEAKER = "TRANSLATION_VRAM_SPEAKER"
    TRANSLATION_VRAM_ENABLE = "TRANSLATION_VRAM_ENABLE"
    TRANSLATION_DISABLED_VRAM = "TRANSLATION_DISABLED_VRAM"
    
    # ============================================================================
    # 音声認識関連エラー (TRANSCRIPTION_*)
    # ============================================================================
    TRANSCRIPTION_VRAM_MIC = "TRANSCRIPTION_VRAM_MIC"
    TRANSCRIPTION_VRAM_SPEAKER = "TRANSCRIPTION_VRAM_SPEAKER"
    TRANSCRIPTION_SEND_DISABLED_VRAM = "TRANSCRIPTION_SEND_DISABLED_VRAM"
    TRANSCRIPTION_RECEIVE_DISABLED_VRAM = "TRANSCRIPTION_RECEIVE_DISABLED_VRAM"
    
    # ============================================================================
    # ウェイトダウンロード関連エラー (WEIGHT_*)
    # ============================================================================
    WEIGHT_CTRANSLATE2_DOWNLOAD = "WEIGHT_CTRANSLATE2_DOWNLOAD"
    WEIGHT_WHISPER_DOWNLOAD = "WEIGHT_WHISPER_DOWNLOAD"
    
    # ============================================================================
    # バリデーションエラー (VALIDATION_*)
    # ============================================================================
    VALIDATION_MIC_THRESHOLD = "VALIDATION_MIC_THRESHOLD"
    VALIDATION_SPEAKER_THRESHOLD = "VALIDATION_SPEAKER_THRESHOLD"
    VALIDATION_MIC_RECORD_TIMEOUT = "VALIDATION_MIC_RECORD_TIMEOUT"
    VALIDATION_MIC_PHRASE_TIMEOUT = "VALIDATION_MIC_PHRASE_TIMEOUT"
    VALIDATION_MIC_MAX_PHRASES = "VALIDATION_MIC_MAX_PHRASES"
    VALIDATION_SPEAKER_RECORD_TIMEOUT = "VALIDATION_SPEAKER_RECORD_TIMEOUT"
    VALIDATION_SPEAKER_PHRASE_TIMEOUT = "VALIDATION_SPEAKER_PHRASE_TIMEOUT"
    VALIDATION_SPEAKER_MAX_PHRASES = "VALIDATION_SPEAKER_MAX_PHRASES"
    VALIDATION_INVALID_IP = "VALIDATION_INVALID_IP"
    VALIDATION_CANNOT_SET_IP = "VALIDATION_CANNOT_SET_IP"
    
    # ============================================================================
    # 認証エラー (AUTH_*)
    # ============================================================================
    AUTH_DEEPL_LENGTH = "AUTH_DEEPL_LENGTH"
    AUTH_DEEPL_FAILED = "AUTH_DEEPL_FAILED"
    AUTH_PLAMO_LENGTH = "AUTH_PLAMO_LENGTH"
    AUTH_PLAMO_FAILED = "AUTH_PLAMO_FAILED"
    AUTH_GEMINI_LENGTH = "AUTH_GEMINI_LENGTH"
    AUTH_GEMINI_FAILED = "AUTH_GEMINI_FAILED"
    AUTH_OPENAI_INVALID = "AUTH_OPENAI_INVALID"
    AUTH_OPENAI_FAILED = "AUTH_OPENAI_FAILED"
    AUTH_GROQ_INVALID = "AUTH_GROQ_INVALID"
    AUTH_GROQ_FAILED = "AUTH_GROQ_FAILED"
    AUTH_OPENROUTER_INVALID = "AUTH_OPENROUTER_INVALID"
    AUTH_OPENROUTER_FAILED = "AUTH_OPENROUTER_FAILED"
    
    # ============================================================================
    # モデル選択エラー (MODEL_*)
    # ============================================================================
    MODEL_PLAMO_INVALID = "MODEL_PLAMO_INVALID"
    MODEL_GEMINI_INVALID = "MODEL_GEMINI_INVALID"
    MODEL_OPENAI_INVALID = "MODEL_OPENAI_INVALID"
    MODEL_GROQ_INVALID = "MODEL_GROQ_INVALID"
    MODEL_OPENROUTER_INVALID = "MODEL_OPENROUTER_INVALID"
    MODEL_LMSTUDIO_INVALID = "MODEL_LMSTUDIO_INVALID"
    MODEL_OLLAMA_INVALID = "MODEL_OLLAMA_INVALID"
    
    # ============================================================================
    # 接続エラー (CONNECTION_*)
    # ============================================================================
    CONNECTION_LMSTUDIO_FAILED = "CONNECTION_LMSTUDIO_FAILED"
    CONNECTION_OLLAMA_FAILED = "CONNECTION_OLLAMA_FAILED"
    CONNECTION_LMSTUDIO_URL_INVALID = "CONNECTION_LMSTUDIO_URL_INVALID"
    
    # ============================================================================
    # WebSocketエラー (WEBSOCKET_*)
    # ============================================================================
    WEBSOCKET_HOST_INVALID = "WEBSOCKET_HOST_INVALID"
    WEBSOCKET_PORT_UNAVAILABLE = "WEBSOCKET_PORT_UNAVAILABLE"
    WEBSOCKET_SERVER_UNAVAILABLE = "WEBSOCKET_SERVER_UNAVAILABLE"
    
    # ============================================================================
    # VRC連携エラー (VRC_*)
    # ============================================================================
    VRC_MIC_MUTE_SYNC_OSC_DISABLED = "VRC_MIC_MUTE_SYNC_OSC_DISABLED"
    
    # ============================================================================
    # 汎用エラー (GENERAL_*)
    # ============================================================================
    GENERAL_EXCEPTION = "GENERAL_EXCEPTION"
    GENERAL_UNKNOWN = "GENERAL_UNKNOWN"


class ErrorCategory(str, Enum):
    """エラーカテゴリ"""
    DEVICE = "device"
    TRANSLATION = "translation"
    TRANSCRIPTION = "transcription"
    WEIGHT = "weight"
    VALIDATION = "validation"
    AUTH = "auth"
    MODEL = "model"
    CONNECTION = "connection"
    WEBSOCKET = "websocket"
    VRC = "vrc"
    GENERAL = "general"


# エラーコードのメタデータ定義
ERROR_METADATA: Dict[ErrorCode, Dict[str, Any]] = {
    # デバイスエラー
    ErrorCode.DEVICE_NO_MIC: {
        "category": ErrorCategory.DEVICE,
        "message": "No mic device detected",
        "severity": "error",
        "user_action_required": True,
    },
    ErrorCode.DEVICE_NO_SPEAKER: {
        "category": ErrorCategory.DEVICE,
        "message": "No speaker device detected",
        "severity": "error",
        "user_action_required": True,
    },
    
    # 翻訳エラー
    ErrorCode.TRANSLATION_ENGINE_LIMIT: {
        "category": ErrorCategory.TRANSLATION,
        "message": "Translation engine limit error",
        "severity": "warning",
        "user_action_required": False,
        "auto_fallback": True,
    },
    ErrorCode.TRANSLATION_VRAM_CHAT: {
        "category": ErrorCategory.TRANSLATION,
        "message": "VRAM out of memory during translation of chat",
        "severity": "critical",
        "user_action_required": True,
    },
    ErrorCode.TRANSLATION_VRAM_MIC: {
        "category": ErrorCategory.TRANSLATION,
        "message": "VRAM out of memory during translation of mic",
        "severity": "critical",
        "user_action_required": True,
    },
    ErrorCode.TRANSLATION_VRAM_SPEAKER: {
        "category": ErrorCategory.TRANSLATION,
        "message": "VRAM out of memory during translation of speaker",
        "severity": "critical",
        "user_action_required": True,
    },
    ErrorCode.TRANSLATION_VRAM_ENABLE: {
        "category": ErrorCategory.TRANSLATION,
        "message": "VRAM out of memory enabling translation",
        "severity": "critical",
        "user_action_required": True,
    },
    ErrorCode.TRANSLATION_DISABLED_VRAM: {
        "category": ErrorCategory.TRANSLATION,
        "message": "Translation disabled due to VRAM overflow",
        "severity": "critical",
        "user_action_required": True,
    },
    
    # 音声認識エラー
    ErrorCode.TRANSCRIPTION_VRAM_MIC: {
        "category": ErrorCategory.TRANSCRIPTION,
        "message": "VRAM out of memory during mic transcription",
        "severity": "critical",
        "user_action_required": True,
    },
    ErrorCode.TRANSCRIPTION_VRAM_SPEAKER: {
        "category": ErrorCategory.TRANSCRIPTION,
        "message": "VRAM out of memory during speaker transcription",
        "severity": "critical",
        "user_action_required": True,
    },
    ErrorCode.TRANSCRIPTION_SEND_DISABLED_VRAM: {
        "category": ErrorCategory.TRANSCRIPTION,
        "message": "Transcription send disabled due to VRAM overflow",
        "severity": "critical",
        "user_action_required": True,
    },
    ErrorCode.TRANSCRIPTION_RECEIVE_DISABLED_VRAM: {
        "category": ErrorCategory.TRANSCRIPTION,
        "message": "Transcription receive disabled due to VRAM overflow",
        "severity": "critical",
        "user_action_required": True,
    },
    
    # ウェイトダウンロードエラー
    ErrorCode.WEIGHT_CTRANSLATE2_DOWNLOAD: {
        "category": ErrorCategory.WEIGHT,
        "message": "CTranslate2 weight download error",
        "severity": "error",
        "user_action_required": True,
    },
    ErrorCode.WEIGHT_WHISPER_DOWNLOAD: {
        "category": ErrorCategory.WEIGHT,
        "message": "Whisper weight download error",
        "severity": "error",
        "user_action_required": True,
    },
    
    # バリデーションエラー
    ErrorCode.VALIDATION_MIC_THRESHOLD: {
        "category": ErrorCategory.VALIDATION,
        "message": "Mic energy threshold value is out of range",
        "severity": "warning",
        "user_action_required": True,
    },
    ErrorCode.VALIDATION_SPEAKER_THRESHOLD: {
        "category": ErrorCategory.VALIDATION,
        "message": "Speaker energy threshold value is out of range",
        "severity": "warning",
        "user_action_required": True,
    },
    ErrorCode.VALIDATION_MIC_RECORD_TIMEOUT: {
        "category": ErrorCategory.VALIDATION,
        "message": "Mic record timeout value is out of range",
        "severity": "warning",
        "user_action_required": True,
    },
    ErrorCode.VALIDATION_MIC_PHRASE_TIMEOUT: {
        "category": ErrorCategory.VALIDATION,
        "message": "Mic phrase timeout value is out of range",
        "severity": "warning",
        "user_action_required": True,
    },
    ErrorCode.VALIDATION_MIC_MAX_PHRASES: {
        "category": ErrorCategory.VALIDATION,
        "message": "Mic max phrases value is out of range",
        "severity": "warning",
        "user_action_required": True,
    },
    ErrorCode.VALIDATION_SPEAKER_RECORD_TIMEOUT: {
        "category": ErrorCategory.VALIDATION,
        "message": "Speaker record timeout value is out of range",
        "severity": "warning",
        "user_action_required": True,
    },
    ErrorCode.VALIDATION_SPEAKER_PHRASE_TIMEOUT: {
        "category": ErrorCategory.VALIDATION,
        "message": "Speaker phrase timeout value is out of range",
        "severity": "warning",
        "user_action_required": True,
    },
    ErrorCode.VALIDATION_SPEAKER_MAX_PHRASES: {
        "category": ErrorCategory.VALIDATION,
        "message": "Speaker max phrases value is out of range",
        "severity": "warning",
        "user_action_required": True,
    },
    ErrorCode.VALIDATION_INVALID_IP: {
        "category": ErrorCategory.VALIDATION,
        "message": "Invalid IP address",
        "severity": "warning",
        "user_action_required": True,
    },
    ErrorCode.VALIDATION_CANNOT_SET_IP: {
        "category": ErrorCategory.VALIDATION,
        "message": "Cannot set IP address",
        "severity": "error",
        "user_action_required": True,
    },
    
    # 認証エラー
    ErrorCode.AUTH_DEEPL_LENGTH: {
        "category": ErrorCategory.AUTH,
        "message": "DeepL auth key length is not correct",
        "severity": "warning",
        "user_action_required": True,
    },
    ErrorCode.AUTH_DEEPL_FAILED: {
        "category": ErrorCategory.AUTH,
        "message": "Authentication failure of deepL auth key",
        "severity": "error",
        "user_action_required": True,
    },
    ErrorCode.AUTH_PLAMO_LENGTH: {
        "category": ErrorCategory.AUTH,
        "message": "Plamo auth key length is not correct",
        "severity": "warning",
        "user_action_required": True,
    },
    ErrorCode.AUTH_PLAMO_FAILED: {
        "category": ErrorCategory.AUTH,
        "message": "Authentication failure of plamo auth key",
        "severity": "error",
        "user_action_required": True,
    },
    ErrorCode.AUTH_GEMINI_LENGTH: {
        "category": ErrorCategory.AUTH,
        "message": "Gemini auth key length is not correct",
        "severity": "warning",
        "user_action_required": True,
    },
    ErrorCode.AUTH_GEMINI_FAILED: {
        "category": ErrorCategory.AUTH,
        "message": "Authentication failure of gemini auth key",
        "severity": "error",
        "user_action_required": True,
    },
    ErrorCode.AUTH_OPENAI_INVALID: {
        "category": ErrorCategory.AUTH,
        "message": "OpenAI auth key is not valid",
        "severity": "warning",
        "user_action_required": True,
    },
    ErrorCode.AUTH_OPENAI_FAILED: {
        "category": ErrorCategory.AUTH,
        "message": "Authentication failure of OpenAI auth key",
        "severity": "error",
        "user_action_required": True,
    },
    ErrorCode.AUTH_GROQ_INVALID: {
        "category": ErrorCategory.AUTH,
        "message": "Groq auth key is not valid",
        "severity": "warning",
        "user_action_required": True,
    },
    ErrorCode.AUTH_GROQ_FAILED: {
        "category": ErrorCategory.AUTH,
        "message": "Authentication failure of Groq auth key",
        "severity": "error",
        "user_action_required": True,
    },
    ErrorCode.AUTH_OPENROUTER_INVALID: {
        "category": ErrorCategory.AUTH,
        "message": "OpenRouter auth key is not valid",
        "severity": "warning",
        "user_action_required": True,
    },
    ErrorCode.AUTH_OPENROUTER_FAILED: {
        "category": ErrorCategory.AUTH,
        "message": "Authentication failure of OpenRouter auth key",
        "severity": "error",
        "user_action_required": True,
    },
    
    # モデル選択エラー
    ErrorCode.MODEL_PLAMO_INVALID: {
        "category": ErrorCategory.MODEL,
        "message": "Plamo model is not valid",
        "severity": "warning",
        "user_action_required": True,
    },
    ErrorCode.MODEL_GEMINI_INVALID: {
        "category": ErrorCategory.MODEL,
        "message": "Gemini model is not valid",
        "severity": "warning",
        "user_action_required": True,
    },
    ErrorCode.MODEL_OPENAI_INVALID: {
        "category": ErrorCategory.MODEL,
        "message": "OpenAI model is not valid",
        "severity": "warning",
        "user_action_required": True,
    },
    ErrorCode.MODEL_GROQ_INVALID: {
        "category": ErrorCategory.MODEL,
        "message": "Groq model is not valid",
        "severity": "warning",
        "user_action_required": True,
    },
    ErrorCode.MODEL_OPENROUTER_INVALID: {
        "category": ErrorCategory.MODEL,
        "message": "OpenRouter model is not valid",
        "severity": "warning",
        "user_action_required": True,
    },
    ErrorCode.MODEL_LMSTUDIO_INVALID: {
        "category": ErrorCategory.MODEL,
        "message": "LMStudio model is not valid",
        "severity": "warning",
        "user_action_required": True,
    },
    ErrorCode.MODEL_OLLAMA_INVALID: {
        "category": ErrorCategory.MODEL,
        "message": "ollama model is not valid",
        "severity": "warning",
        "user_action_required": True,
    },
    
    # 接続エラー
    ErrorCode.CONNECTION_LMSTUDIO_FAILED: {
        "category": ErrorCategory.CONNECTION,
        "message": "Cannot connect to LMStudio server",
        "severity": "error",
        "user_action_required": True,
    },
    ErrorCode.CONNECTION_OLLAMA_FAILED: {
        "category": ErrorCategory.CONNECTION,
        "message": "Cannot connect to ollama server",
        "severity": "error",
        "user_action_required": True,
    },
    ErrorCode.CONNECTION_LMSTUDIO_URL_INVALID: {
        "category": ErrorCategory.CONNECTION,
        "message": "LMStudio URL is not valid",
        "severity": "warning",
        "user_action_required": True,
    },
    
    # WebSocketエラー
    ErrorCode.WEBSOCKET_HOST_INVALID: {
        "category": ErrorCategory.WEBSOCKET,
        "message": "WebSocket server host is not available",
        "severity": "error",
        "user_action_required": True,
    },
    ErrorCode.WEBSOCKET_PORT_UNAVAILABLE: {
        "category": ErrorCategory.WEBSOCKET,
        "message": "WebSocket server port is not available",
        "severity": "error",
        "user_action_required": True,
    },
    ErrorCode.WEBSOCKET_SERVER_UNAVAILABLE: {
        "category": ErrorCategory.WEBSOCKET,
        "message": "WebSocket server host or port is not available",
        "severity": "error",
        "user_action_required": True,
    },
    
    # VRC連携エラー
    ErrorCode.VRC_MIC_MUTE_SYNC_OSC_DISABLED: {
        "category": ErrorCategory.VRC,
        "message": "Cannot enable VRC mic mute sync while OSC query is disabled",
        "severity": "warning",
        "user_action_required": True,
    },
    
    # 汎用エラー
    ErrorCode.GENERAL_EXCEPTION: {
        "category": ErrorCategory.GENERAL,
        "message": "An error occurred",
        "severity": "error",
        "user_action_required": False,
    },
    ErrorCode.GENERAL_UNKNOWN: {
        "category": ErrorCategory.GENERAL,
        "message": "Unknown error",
        "severity": "error",
        "user_action_required": False,
    },
}


class VRCTError:
    """VRCTエラーハンドリングクラス"""
    
    @staticmethod
    def create_error_response(
        error_code: ErrorCode,
        data: Any = None,
        details: Optional[Dict[str, Any]] = None,
        custom_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """統一されたエラーレスポンスを生成
        
        Args:
            error_code: エラーコード
            data: エラー時に戻す値（通常は元の値）
            details: 追加の詳細情報
            custom_message: カスタムメッセージ（指定しない場合はデフォルトメッセージ）
        
        Returns:
            エラーレスポンス辞書
        """
        metadata = ERROR_METADATA.get(error_code, ERROR_METADATA[ErrorCode.GENERAL_UNKNOWN])
        
        return {
            "status": 400,
            "result": {
                "error_code": error_code.value,
                "message": custom_message or metadata["message"],
                "data": data,
                "details": details or {},
                "category": metadata["category"].value,
                "severity": metadata["severity"],
            }
        }
    
    @staticmethod
    def create_exception_error_response(
        exception: Exception,
        data: Any = None,
        error_code: ErrorCode = ErrorCode.GENERAL_EXCEPTION
    ) -> Dict[str, Any]:
        """例外からエラーレスポンスを生成
        
        Args:
            exception: 発生した例外
            data: エラー時に戻す値
            error_code: エラーコード
        
        Returns:
            エラーレスポンス辞書
        """
        return VRCTError.create_error_response(
            error_code=error_code,
            data=data,
            custom_message=f"Error: {str(exception)}",
            details={"exception_type": type(exception).__name__}
        )


# エンドポイントとエラーコードのマッピング
# UIがエラーハンドリングする際の参照として使用
ENDPOINT_ERROR_MAPPING: Dict[str, Dict[str, ErrorCode]] = {
    # run_mapping経由のエラー通知
    "/run/error_device": {
        "NO_MIC": ErrorCode.DEVICE_NO_MIC,
        "NO_SPEAKER": ErrorCode.DEVICE_NO_SPEAKER,
    },
    "/run/error_translation_engine": {
        "LIMIT": ErrorCode.TRANSLATION_ENGINE_LIMIT,
    },
    "/run/error_translation_chat_vram_overflow": {
        "VRAM": ErrorCode.TRANSLATION_VRAM_CHAT,
    },
    "/run/error_translation_mic_vram_overflow": {
        "VRAM": ErrorCode.TRANSLATION_VRAM_MIC,
    },
    "/run/error_translation_speaker_vram_overflow": {
        "VRAM": ErrorCode.TRANSLATION_VRAM_SPEAKER,
    },
    "/run/error_transcription_mic_vram_overflow": {
        "VRAM": ErrorCode.TRANSCRIPTION_VRAM_MIC,
    },
    "/run/error_transcription_speaker_vram_overflow": {
        "VRAM": ErrorCode.TRANSCRIPTION_VRAM_SPEAKER,
    },
    "/run/error_ctranslate2_weight": {
        "DOWNLOAD": ErrorCode.WEIGHT_CTRANSLATE2_DOWNLOAD,
    },
    "/run/error_whisper_weight": {
        "DOWNLOAD": ErrorCode.WEIGHT_WHISPER_DOWNLOAD,
    },
    
    # エンドポイント直接のエラーレスポンス
    "/set/data/mic_threshold": {
        "OUT_OF_RANGE": ErrorCode.VALIDATION_MIC_THRESHOLD,
    },
    "/set/data/speaker_threshold": {
        "OUT_OF_RANGE": ErrorCode.VALIDATION_SPEAKER_THRESHOLD,
    },
    "/set/data/mic_record_timeout": {
        "OUT_OF_RANGE": ErrorCode.VALIDATION_MIC_RECORD_TIMEOUT,
    },
    "/set/data/mic_phrase_timeout": {
        "OUT_OF_RANGE": ErrorCode.VALIDATION_MIC_PHRASE_TIMEOUT,
    },
    "/set/data/mic_max_phrases": {
        "OUT_OF_RANGE": ErrorCode.VALIDATION_MIC_MAX_PHRASES,
    },
    "/set/data/speaker_record_timeout": {
        "OUT_OF_RANGE": ErrorCode.VALIDATION_SPEAKER_RECORD_TIMEOUT,
    },
    "/set/data/speaker_phrase_timeout": {
        "OUT_OF_RANGE": ErrorCode.VALIDATION_SPEAKER_PHRASE_TIMEOUT,
    },
    "/set/data/speaker_max_phrases": {
        "OUT_OF_RANGE": ErrorCode.VALIDATION_SPEAKER_MAX_PHRASES,
    },
    "/set/data/osc_ip_address": {
        "INVALID": ErrorCode.VALIDATION_INVALID_IP,
        "CANNOT_SET": ErrorCode.VALIDATION_CANNOT_SET_IP,
    },
    "/set/data/deepl_auth_key": {
        "LENGTH": ErrorCode.AUTH_DEEPL_LENGTH,
        "FAILED": ErrorCode.AUTH_DEEPL_FAILED,
    },
    "/set/data/plamo_auth_key": {
        "LENGTH": ErrorCode.AUTH_PLAMO_LENGTH,
        "FAILED": ErrorCode.AUTH_PLAMO_FAILED,
    },
    "/set/data/selected_plamo_model": {
        "INVALID": ErrorCode.MODEL_PLAMO_INVALID,
    },
    "/set/data/gemini_auth_key": {
        "LENGTH": ErrorCode.AUTH_GEMINI_LENGTH,
        "FAILED": ErrorCode.AUTH_GEMINI_FAILED,
    },
    "/set/data/selected_gemini_model": {
        "INVALID": ErrorCode.MODEL_GEMINI_INVALID,
    },
    "/set/data/openai_auth_key": {
        "INVALID": ErrorCode.AUTH_OPENAI_INVALID,
        "FAILED": ErrorCode.AUTH_OPENAI_FAILED,
    },
    "/set/data/selected_openai_model": {
        "INVALID": ErrorCode.MODEL_OPENAI_INVALID,
    },
    "/set/data/groq_auth_key": {
        "INVALID": ErrorCode.AUTH_GROQ_INVALID,
        "FAILED": ErrorCode.AUTH_GROQ_FAILED,
    },
    "/set/data/selected_groq_model": {
        "INVALID": ErrorCode.MODEL_GROQ_INVALID,
    },
    "/set/data/openrouter_auth_key": {
        "INVALID": ErrorCode.AUTH_OPENROUTER_INVALID,
        "FAILED": ErrorCode.AUTH_OPENROUTER_FAILED,
    },
    "/set/data/selected_openrouter_model": {
        "INVALID": ErrorCode.MODEL_OPENROUTER_INVALID,
    },
    "/run/lmstudio_connection": {
        "FAILED": ErrorCode.CONNECTION_LMSTUDIO_FAILED,
    },
    "/set/data/lmstudio_url": {
        "INVALID": ErrorCode.CONNECTION_LMSTUDIO_URL_INVALID,
    },
    "/set/data/selected_lmstudio_model": {
        "INVALID": ErrorCode.MODEL_LMSTUDIO_INVALID,
    },
    "/run/ollama_connection": {
        "FAILED": ErrorCode.CONNECTION_OLLAMA_FAILED,
    },
    "/set/data/selected_ollama_model": {
        "INVALID": ErrorCode.MODEL_OLLAMA_INVALID,
    },
    "/set/data/websocket_host": {
        "INVALID_IP": ErrorCode.VALIDATION_INVALID_IP,
        "UNAVAILABLE": ErrorCode.WEBSOCKET_HOST_INVALID,
    },
    "/set/data/websocket_port": {
        "UNAVAILABLE": ErrorCode.WEBSOCKET_PORT_UNAVAILABLE,
    },
    "/set/enable/websocket_server": {
        "UNAVAILABLE": ErrorCode.WEBSOCKET_SERVER_UNAVAILABLE,
    },
    "/set/enable/vrc_mic_mute_sync": {
        "OSC_DISABLED": ErrorCode.VRC_MIC_MUTE_SYNC_OSC_DISABLED,
    },
}


def get_error_metadata(error_code: ErrorCode) -> Dict[str, Any]:
    """エラーコードのメタデータを取得
    
    Args:
        error_code: エラーコード
    
    Returns:
        メタデータ辞書
    """
    return ERROR_METADATA.get(error_code, ERROR_METADATA[ErrorCode.GENERAL_UNKNOWN])


def is_critical_error(error_code: ErrorCode) -> bool:
    """クリティカルエラーかどうかを判定
    
    Args:
        error_code: エラーコード
    
    Returns:
        クリティカルエラーの場合True
    """
    metadata = get_error_metadata(error_code)
    return metadata.get("severity") == "critical"


def requires_user_action(error_code: ErrorCode) -> bool:
    """ユーザーアクションが必要なエラーかどうかを判定
    
    Args:
        error_code: エラーコード
    
    Returns:
        ユーザーアクションが必要な場合True
    """
    metadata = get_error_metadata(error_code)
    return metadata.get("user_action_required", False)
