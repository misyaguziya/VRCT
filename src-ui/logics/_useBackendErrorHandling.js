import { useI18n } from "@useI18n";

import {
    useNotificationStatus,
    useLLMConnection,
} from "@logics_common";

import {
    useMainFunction,
} from "@logics_main";

import {
    useTranscription,

    useTranslation,

    useOthers,

    useAdvancedSettings,
} from "@logics_configs";
import { ui_configs } from "./ui_configs";

export const _useBackendErrorHandling = () => {
    const { t } = useI18n();
    const { showNotification_Error } = useNotificationStatus();

    const {
        updateMicRecordTimeout,
        updateMicPhraseTimeout,
        updateMicMaxWords,

        updateSpeakerRecordTimeout,
        updateSpeakerPhraseTimeout,
        updateSpeakerMaxWords,
    } = useTranscription();

    const { updateTranslationStatus, updateTranscriptionSendStatus, updateTranscriptionReceiveStatus } = useMainFunction();

    const {
        updateDeepLAuthKey,

        updatePlamoAuthKey,
        updateSelectedPlamoModel,

        updateGeminiAuthKey,
        updateSelectedGeminiModel,

        updateOpenAIAuthKey,
        updateSelectedOpenAIModel,

        updateGroqAuthKey,
        updateSelectedGroqModel,

        updateOpenRouterAuthKey,
        updateSelectedOpenRouterModel,

        updateLMStudioURL,
        updateSelectedLMStudioModel,

        updateSelectedOllamaModel,
    } = useTranslation();

    const { updateEnableVrcMicMuteSync } = useOthers();

    const {
        updateOscIpAddress,
        updateEnableWebsocket,
        updateWebsocketHost,
        updateWebsocketPort,
        updateEnableObsBrowserSource,
        updateObsBrowserSourcePort,
        updateObsBrowserSourceFontColor,
        updateObsBrowserSourceFontOutlineColor,
    } = useAdvancedSettings();

    const {
        updateIsOllamaConnected,
        updateIsLMStudioConnected,
    } = useLLMConnection();

    const errorHandling_Backend = ({error_code, message, data, endpoint, result}) => {
        switch (error_code) {
            // ============================================================================
            // デバイス関連エラー (DEVICE_*)
            // ============================================================================
            case "DEVICE_NO_MIC":
                showNotification_Error(t("common_error.no_device_mic"), { category_id: error_code });
                return;
            case "DEVICE_NO_SPEAKER":
                showNotification_Error(t("common_error.no_device_speaker"), { category_id: error_code });
                return;

            // ============================================================================
            // 翻訳関連エラー (TRANSLATION_*)
            // ============================================================================
            case "TRANSLATION_ENGINE_LIMIT":
                showNotification_Error(t("common_error.translation_limit"), { category_id: error_code });
                return;
            case "TRANSLATION_VRAM_CHAT":
            case "TRANSLATION_VRAM_MIC":
            case "TRANSLATION_VRAM_SPEAKER":
            case "TRANSLATION_VRAM_ENABLE":
                showNotification_Error(message, { category_id: error_code });
                return;
            case "TRANSLATION_DISABLED_VRAM":
                updateTranslationStatus(data);
                showNotification_Error(message, { category_id: error_code });
                return;

            // ============================================================================
            // 音声認識関連エラー (TRANSCRIPTION_*)
            // ============================================================================
            case "TRANSCRIPTION_VRAM_MIC":
            case "TRANSCRIPTION_VRAM_SPEAKER":
                showNotification_Error(message, { category_id: error_code });
                return;
            case "TRANSCRIPTION_SEND_DISABLED_VRAM":
                updateTranscriptionSendStatus(data);
                showNotification_Error(message, { category_id: error_code });
                return;
            case "TRANSCRIPTION_RECEIVE_DISABLED_VRAM":
                updateTranscriptionReceiveStatus(data);
                showNotification_Error(message, { category_id: error_code });
                return;

            // ============================================================================
            // ウェイトダウンロード関連エラー (WEIGHT_*)
            // ============================================================================
            case "WEIGHT_CTRANSLATE2_DOWNLOAD":
                showNotification_Error(t("common_error.failed_download_weight_ctranslate2"), { category_id: error_code });
                return;
            case "WEIGHT_WHISPER_DOWNLOAD":
                showNotification_Error(t("common_error.failed_download_weight_whisper"), { category_id: error_code });
                return;

            // ============================================================================
            // バリデーションエラー (VALIDATION_*)
            // ============================================================================
            case "VALIDATION_MIC_THRESHOLD":
                showNotification_Error(t("common_error.threshold_invalid_value", { min: ui_configs.mic_threshold_min, max: ui_configs.mic_threshold_max }), { category_id: error_code });
                return;
            case "VALIDATION_SPEAKER_THRESHOLD":
                showNotification_Error(t("common_error.threshold_invalid_value", { min: ui_configs.speaker_threshold_min, max: ui_configs.speaker_threshold_max }), { category_id: error_code });
                return;
            case "VALIDATION_MIC_RECORD_TIMEOUT":
                updateMicRecordTimeout(data);
                showNotification_Error(t("common_error.invalid_value_mic_record_timeout", { mic_phrase_timeout_label: t("config_page.transcription.mic_phrase_timeout.label") }), { category_id: error_code });
                return;
            case "VALIDATION_MIC_PHRASE_TIMEOUT":
                updateMicPhraseTimeout(data);
                showNotification_Error(t("common_error.invalid_value_mic_phrase_timeout", { mic_record_timeout_label: t("config_page.transcription.mic_record_timeout.label") }), { category_id: error_code });
                return;
            case "VALIDATION_MIC_MAX_PHRASES":
                updateMicMaxWords(data);
                showNotification_Error(t("common_error.invalid_value_mic_max_phrase"), { category_id: error_code });
                return;
            case "VALIDATION_SPEAKER_RECORD_TIMEOUT":
                updateSpeakerRecordTimeout(data);
                showNotification_Error(t("common_error.invalid_value_speaker_record_timeout", { speaker_phrase_timeout_label: t("config_page.transcription.speaker_phrase_timeout.label") }), { category_id: error_code });
                return;
            case "VALIDATION_SPEAKER_PHRASE_TIMEOUT":
                updateSpeakerPhraseTimeout(data);
                showNotification_Error(t("common_error.invalid_value_speaker_phrase_timeout", { speaker_record_timeout_label: t("config_page.transcription.speaker_record_timeout.label") }), { category_id: error_code });
                return;
            case "VALIDATION_SPEAKER_MAX_PHRASES":
                updateSpeakerMaxWords(data);
                showNotification_Error(t("common_error.invalid_value_speaker_max_phrase"), { category_id: error_code });
                return;
            case "VALIDATION_INVALID_IP":
            case "VALIDATION_CANNOT_SET_IP":
                if (endpoint === "/set/data/websocket_host") {
                    updateWebsocketHost(data);
                } else {
                    updateOscIpAddress(data);
                }
                showNotification_Error(message, { category_id: error_code });
                return;

            // ============================================================================
            // 認証エラー (AUTH_*)
            // ============================================================================
            case "AUTH_DEEPL_LENGTH":
                updateDeepLAuthKey(data);
                showNotification_Error(t("common_error.deepl_auth_key_invalid_length"), { category_id: error_code });
                return;
            case "AUTH_DEEPL_FAILED":
                updateDeepLAuthKey(data);
                showNotification_Error(t("common_error.deepl_auth_key_failed_authentication"), { category_id: error_code });
                return;
            case "AUTH_PLAMO_LENGTH":
            case "AUTH_PLAMO_FAILED":
                updatePlamoAuthKey(data);
                showNotification_Error(message, { category_id: error_code });
                return;
            case "AUTH_GEMINI_LENGTH":
            case "AUTH_GEMINI_FAILED":
                updateGeminiAuthKey(data);
                showNotification_Error(message, { category_id: error_code });
                return;
            case "AUTH_OPENAI_INVALID":
            case "AUTH_OPENAI_FAILED":
                updateOpenAIAuthKey(data);
                showNotification_Error(message, { category_id: error_code });
                return;
            case "AUTH_GROQ_INVALID":
            case "AUTH_GROQ_FAILED":
                updateGroqAuthKey(data);
                showNotification_Error(message, { category_id: error_code });
                return;
            case "AUTH_OPENROUTER_INVALID":
            case "AUTH_OPENROUTER_FAILED":
                updateOpenRouterAuthKey(data);
                showNotification_Error(message, { category_id: error_code });
                return;

            // ============================================================================
            // モデル選択エラー (MODEL_*)
            // ============================================================================
            case "MODEL_PLAMO_INVALID":
                updateSelectedPlamoModel(data);
                showNotification_Error(message, { category_id: error_code });
                return;
            case "MODEL_GEMINI_INVALID":
                updateSelectedGeminiModel(data);
                showNotification_Error(message, { category_id: error_code });
                return;
            case "MODEL_OPENAI_INVALID":
                updateSelectedOpenAIModel(data);
                showNotification_Error(message, { category_id: error_code });
                return;
            case "MODEL_GROQ_INVALID":
                updateSelectedGroqModel(data);
                showNotification_Error(message, { category_id: error_code });
                return;
            case "MODEL_OPENROUTER_INVALID":
                updateSelectedOpenRouterModel(data);
                showNotification_Error(message, { category_id: error_code });
                return;
            case "MODEL_LMSTUDIO_INVALID":
                updateSelectedLMStudioModel(data);
                showNotification_Error(message, { category_id: error_code });
                return;
            case "MODEL_OLLAMA_INVALID":
                updateSelectedOllamaModel(data);
                showNotification_Error(message, { category_id: error_code });
                return;

            // ============================================================================
            // 接続エラー (CONNECTION_*)
            // ============================================================================
            case "CONNECTION_LMSTUDIO_FAILED":
                updateIsLMStudioConnected(data);
                showNotification_Error(message, { category_id: error_code });
                return;
            case "CONNECTION_OLLAMA_FAILED":
                updateIsOllamaConnected(data);
                showNotification_Error(message, { category_id: error_code });
                return;
            case "CONNECTION_LMSTUDIO_URL_INVALID":
                updateLMStudioURL(data);
                showNotification_Error(message, { category_id: error_code });
                return;

            // ============================================================================
            // WebSocketエラー (WEBSOCKET_*)
            // ============================================================================
            case "WEBSOCKET_HOST_INVALID":
                updateWebsocketHost(data);
                showNotification_Error(message, { category_id: error_code });
                return;
            case "WEBSOCKET_PORT_UNAVAILABLE":
                updateWebsocketPort(data);
                showNotification_Error(message, { category_id: error_code });
                return;
            case "WEBSOCKET_SERVER_UNAVAILABLE":
                updateEnableWebsocket(data);
                showNotification_Error(message, { category_id: error_code });
                return;

            // ============================================================================
            // OBS Browser Sourceエラー (OBS_BROWSER_SOURCE_*)
            // ============================================================================
            case "OBS_BROWSER_SOURCE_HOST_UNAVAILABLE":
                updateWebsocketHost(data);
                showNotification_Error(message, { category_id: error_code });
                return;
            case "OBS_BROWSER_SOURCE_PORT_UNAVAILABLE":
                updateObsBrowserSourcePort(data);
                showNotification_Error(message, { category_id: error_code });
                return;
            case "OBS_BROWSER_SOURCE_SERVER_UNAVAILABLE":
                updateEnableObsBrowserSource(data);
                showNotification_Error(message, { category_id: error_code });
                return;
            case "OBS_BROWSER_SOURCE_FONT_COLOR_INVALID":
                updateObsBrowserSourceFontColor(data);
                showNotification_Error(message, { category_id: error_code });
                return;
            case "OBS_BROWSER_SOURCE_FONT_OUTLINE_COLOR_INVALID":
                updateObsBrowserSourceFontOutlineColor(data);
                showNotification_Error(message, { category_id: error_code });
                return;

            // ============================================================================
            // VRC連携エラー (VRC_*)
            // ============================================================================
            case "VRC_MIC_MUTE_SYNC_OSC_DISABLED":
                updateEnableVrcMicMuteSync(data);
                showNotification_Error(message, { category_id: error_code });
                return;

            // ============================================================================
            // 汎用エラー (GENERAL_*)
            // ============================================================================
            case "GENERAL_EXCEPTION":
            case "GENERAL_UNKNOWN":
                console.error(`Error occurred at endpoint: ${endpoint}\nerror_code: ${error_code}\nmessage: ${message}\nresult: ${JSON.stringify(result)}`);
                showNotification_Error(message, { category_id: error_code });
                showNotification_Error(`An error occurred. Please contact the developers and restart VRCT. Error: ${error_code} - ${message || JSON.stringify(result)}`, { hide_duration: null, category_id: error_code });
                return;

            default:
                console.error(`Invalid error_code or message: ${error_code}\nendpoint: ${endpoint}\nmessage: ${message}\nresult: ${JSON.stringify(result)}`);
                showNotification_Error(`An error occurred. Please contact the developers and restart VRCT. Error: ${error_code} - ${message || JSON.stringify(result)}`, { hide_duration: null, category_id: error_code });
                return;
        }

    }

    return {
        errorHandling_Backend,
    }
};
