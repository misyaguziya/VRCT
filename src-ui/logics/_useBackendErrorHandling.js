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

    const { updateDeepLAuthKey } = useTranslation();

    const { updateEnableVrcMicMuteSync } = useOthers();

    const {
        updateOscIpAddress,
        updateEnableWebsocket,
        updateWebsocketHost,
        updateWebsocketPort,
    } = useAdvancedSettings();

    const {
        updateIsOllamaConnected,
        updateIsLMStudioConnected,
    } = useLLMConnection();

    const errorHandling_Backend = ({message, data, endpoint, result}) => {
        switch (endpoint) {
            case "/run/error_device":
                if (message === "No mic device detected") showNotification_Error(t("common_error.no_device_mic"));
                if (message === "No speaker device detected") showNotification_Error(t("common_error.no_device_speaker"));
                return;

            case "/set/data/mic_threshold":
                if (message === "Mic energy threshold value is out of range") {
                    showNotification_Error(t("common_error.threshold_invalid_value",
                        { min: ui_configs.mic_threshold_min, max: ui_configs.mic_threshold_max },
                    ));
                };
                return;
            case "/set/data/speaker_threshold":
                if (message === "Speaker energy threshold value is out of range") {
                    showNotification_Error(t("common_error.threshold_invalid_value",
                        { min: ui_configs.speaker_threshold_min, max: ui_configs.speaker_threshold_max },
                    ));
                }
                return;

            case "/run/error_ctranslate2_weight":
                if (message === "CTranslate2 weight download error") showNotification_Error(t("common_error.failed_download_weight_ctranslate2"));
                return;
            case "/run/error_whisper_weight":
                if (message === "Whisper weight download error") showNotification_Error(t("common_error.failed_download_weight_whisper"));
                return;

            case "/run/error_translation_engine":
                if (message === "Translation engine limit error") showNotification_Error(t("common_error.translation_limit"));
                return;

            case "/run/enable_translation":
                if (message === "Translation disabled due to VRAM overflow") {
                    updateTranslationStatus(data);
                    showNotification_Error("Translation disabled due to VRAM overflow");
                }
                return;

            case "/run/enable_transcription_send":
                if (message === "Transcription send disabled due to VRAM overflow") {
                    updateTranscriptionSendStatus(data);
                    showNotification_Error("Transcription send disabled due to VRAM overflow");
                }
                return;

            case "/run/enable_transcription_send":
                if (message === "Transcription receive disabled due to VRAM overflow") {
                    updateTranscriptionReceiveStatus(data);
                    showNotification_Error("Transcription receive disabled due to VRAM overflow");
                }
                return;

            case "/run/error_translation_chat_vram_overflow":
                if (message === "VRAM out of memory during translation of chat") showNotification_Error("VRAM out of memory during translation of chat");
                return;
            case "/run/error_translation_mic_vram_overflow":
                if (message === "VRAM out of memory during translation of mic") showNotification_Error("VRAM out of memory during translation of mic");
                return;
            case "/run/error_translation_speaker_vram_overflow":
                if (message === "VRAM out of memory during translation of speaker") showNotification_Error("VRAM out of memory during translation of speaker");
                return;
            case "/run/error_transcription_mic_vram_overflow":
                if (message === "VRAM out of memory during mic transcription") showNotification_Error("VRAM out of memory during mic transcription");
                return;
            case "/run/error_transcription_speaker_vram_overflow":
                if (message === "VRAM out of memory during speaker transcription") showNotification_Error("VRAM out of memory during speaker transcription");
                return;

            case "/set/data/deepl_auth_key":
                if (message === "DeepL auth key length is not correct") {
                    updateDeepLAuthKey(data);
                    showNotification_Error(t("common_error.deepl_auth_key_invalid_length"), { category_id: "deepl_auth_key" });
                } else if (message === "Authentication failure of deepL auth key") {
                    updateDeepLAuthKey(data);
                    showNotification_Error(t("common_error.deepl_auth_key_failed_authentication"), { category_id: "deepl_auth_key" });
                } else { // Exception
                    updateDeepLAuthKey(data);
                    showNotification_Error(message, { category_id: "deepl_auth_key" });
                }
                return;

            case "/set/data/mic_record_timeout":
                if (message === "Mic record timeout value is out of range") {
                    updateMicRecordTimeout(data);
                    showNotification_Error(t("common_error.invalid_value_mic_record_timeout", {
                        mic_phrase_timeout_label: t("config_page.transcription.mic_phrase_timeout.label")
                    }));
                }
                return;
            case "/set/data/mic_phrase_timeout":
                if (message === "Mic phrase timeout value is out of range") {
                    updateMicPhraseTimeout(data);
                    showNotification_Error(t("common_error.invalid_value_mic_phrase_timeout", {
                        mic_record_timeout_label: t("config_page.transcription.mic_record_timeout.label")
                    }));
                }
                return;
            case "/set/data/mic_max_phrases":
                if (message === "Mic max phrases value is out of range") {
                    updateMicMaxWords(data);
                    showNotification_Error(t("common_error.invalid_value_mic_max_phrase"));
                }
                return;


            case "/set/data/speaker_record_timeout":
                if (message === "Speaker record timeout value is out of range") {
                    updateSpeakerRecordTimeout(data);
                    showNotification_Error(t("common_error.invalid_value_speaker_record_timeout", {
                        speaker_phrase_timeout_label: t("config_page.transcription.speaker_phrase_timeout.label")
                    }));
                }
                return;
            case "/set/data/speaker_phrase_timeout":
                if (message === "Speaker phrase timeout value is out of range") {
                    updateSpeakerPhraseTimeout(data);
                    showNotification_Error(t("common_error.invalid_value_speaker_phrase_timeout", {
                        speaker_record_timeout_label: t("config_page.transcription.speaker_record_timeout.label")
                    }));
                }
                return;
            case "/set/data/speaker_max_phrases":
                if (message === "Speaker max phrases value is out of range") {
                    updateSpeakerMaxWords(data);
                    showNotification_Error(t("common_error.invalid_value_speaker_max_phrase"));
                }
                return;

            case "/set/enable/vrc_mic_mute_sync":
                // Normally, this path shouldn't happen because VRC Mic Mute Sync is disabled and can't be turned on from the UI.
                if (message === "Cannot enable VRC mic mute sync while OSC query is disabled") {
                    updateEnableVrcMicMuteSync(data);
                    showNotification_Error("Cannot enable VRC Mic Mute Sync while OSC query is disabled");
                }
                return;


            // Advanced Settings, error messages are set by Backend (EN only)
            case "/set/data/osc_ip_address":
                if (message === "Invalid IP address") {
                    updateOscIpAddress(data);
                    showNotification_Error(message);
                } else if (message === "Cannot set IP address") {
                    updateOscIpAddress(data);
                    showNotification_Error(message);
                } // else? (Backend will send the message "Cannot set IP address" when throw Exception)
                return;


            case "/set/enable/websocket_server":
                if (message === "WebSocket server host or port is not available") {
                    updateEnableWebsocket(data);
                    showNotification_Error(message);
                }
                return;

            case "/set/data/websocket_host":
                if (message === "Invalid IP address") {
                    updateWebsocketHost(data);
                    showNotification_Error(message);
                } else if (message === "WebSocket server host is not available") {
                    updateWebsocketHost(data);
                    showNotification_Error(message);
                }
                return;

            case "/set/data/websocket_port":
                if (message === "WebSocket server port is not available") {
                    updateWebsocketPort(data);
                    showNotification_Error(message);
                }
                return;

            case "/run/lmstudio_connection":
                updateIsLMStudioConnected(data);
                showNotification_Error(message);
                console.error(message);
                return;

            case "/run/ollama_connection":
                updateIsOllamaConnected(data);
                showNotification_Error(message);
                console.error(message);
                return;

            default:
                console.error(`Invalid endpoint or message: ${endpoint}\nmessage: ${message}\nresult: ${JSON.stringify(result)}`);
                showNotification_Error(
                    `An error occurred. Please contact the developers and restart VRCT. Error: Invalid endpoint or message: ${endpoint}\nmessage: ${message}\nresult: ${JSON.stringify(result)}`, { hide_duration: null }
                );
                return;
        }

    }

    return {
        errorHandling_Backend,
    }
};