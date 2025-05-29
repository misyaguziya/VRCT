import { useTranslation } from "react-i18next";

import {
    useNotificationStatus,
} from "@logics_common";

import {
    useMicRecordTimeout,
    useMicPhraseTimeout,
    useMicMaxWords,

    useSpeakerRecordTimeout,
    useSpeakerPhraseTimeout,
    useSpeakerMaxWords,

    useDeepLAuthKey,

    useOscIpAddress,
    useWebsocket,
} from "@logics_configs";
import { ui_configs } from "../ui_configs";

export const _useBackendErrorHandling = () => {
    const { t } = useTranslation();
    const { showNotification_Error } = useNotificationStatus();

    const { updateMicRecordTimeout } = useMicRecordTimeout();
    const { updateMicPhraseTimeout } = useMicPhraseTimeout();
    const { updateMicMaxWords } = useMicMaxWords();

    const { updateSpeakerRecordTimeout } = useSpeakerRecordTimeout();
    const { updateSpeakerPhraseTimeout } = useSpeakerPhraseTimeout();
    const { updateSpeakerMaxWords } = useSpeakerMaxWords();

    const { updateDeepLAuthKey } = useDeepLAuthKey();

    const { updateOscIpAddress } = useOscIpAddress();
    const { updateEnableWebsocket, updateWebsocketHost, updateWebsocketPort } = useWebsocket();

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

            case "/set/data/deepl_auth_key":
                if (message === "DeepL auth key length is not correct") {
                    updateDeepLAuthKey(data);
                    showNotification_Error(t("common_error.deepl_auth_key_invalid_length"));
                } else if (message === "Authentication failure of deepL auth key") {
                    updateDeepLAuthKey(data);
                    showNotification_Error(t("common_error.deepl_auth_key_failed_authentication"));
                } else { // Exception
                    updateDeepLAuthKey(data);
                    showNotification_Error(message);
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

            default:
                console.error(`Invalid endpoint or message: ${endpoint}\nmessage: ${message}\nresult: ${JSON.stringify(result)}`);
                return;
        }

    }

    return {
        errorHandling_Backend,
    }
};