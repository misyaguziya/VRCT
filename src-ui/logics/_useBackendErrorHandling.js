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
    useOscPort,
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

    const { updateDeepLAuthKey, saveErrorDeepLAuthKey } = useDeepLAuthKey();


    const { saveErrorOscIpAddress } = useOscIpAddress();
    const { saveErrorOscPort } = useOscPort();

    const errorHandling_Backend = ({message, data, endpoint, _result}) => {
        switch (message) {
            case "No mic device detected":
                showNotification_Error(t("common_error.no_device_mic"));
                break;
            case "No speaker device detected":
                showNotification_Error(t("common_error.no_device_speaker"));
                break;

            case "Mic energy threshold value is out of range":
                showNotification_Error(t("common_error.threshold_invalid_value",
                    { min: ui_configs.mic_threshold_min, max: ui_configs.mic_threshold_max },
                ));
                break;
            case "Speaker energy threshold value is out of range":
                showNotification_Error(t("common_error.threshold_invalid_value",
                { min: ui_configs.speaker_threshold_min, max: ui_configs.speaker_threshold_max },
            ));
            break;

            case "CTranslate2 weight download error":
                showNotification_Error(t("common_error.failed_download_weight_ctranslate2"));
                break;
            case "Whisper weight download error":
                showNotification_Error(t("common_error.failed_download_weight_whisper"));
                break;

            case "Translation engine limit error":
                showNotification_Error(t("common_error.translation_limit"));
                break;

            case "DeepL auth key length is not correct":
                updateDeepLAuthKey(data);
                showNotification_Error(t("common_error.deepl_auth_key_invalid_length"));
                break;
            case "Authentication failure of deepL auth key":
                updateDeepLAuthKey(data);
                showNotification_Error(t("common_error.deepl_auth_key_failed_authentication"));
                break;

            case "Mic record timeout value is out of range":
                updateMicRecordTimeout(data);
                showNotification_Error(
                    t("common_error.invalid_value_mic_record_timeout",
                    { mic_phrase_timeout_label: t("config_page.transcription.mic_phrase_timeout.label") }
                ));
                break;
            case "Mic phrase timeout value is out of range":
                updateMicPhraseTimeout(data);
                showNotification_Error(
                    t("common_error.invalid_value_mic_phrase_timeout",
                    { mic_record_timeout_label: t("config_page.transcription.mic_record_timeout.label") }
                ));
                break;
            case "Mic max phrases value is out of range":
                updateMicMaxWords(data);
                showNotification_Error(t("common_error.invalid_value_mic_max_phrase"));
                break;


            case "Speaker record timeout value is out of range":
                updateSpeakerRecordTimeout(data);
                showNotification_Error(
                    t("common_error.invalid_value_speaker_record_timeout",
                    { speaker_phrase_timeout_label: t("config_page.transcription.speaker_phrase_timeout.label") }
                ));
                break;
            case "Speaker phrase timeout value is out of range":
                updateSpeakerPhraseTimeout(data);
                showNotification_Error(
                    t("common_error.invalid_value_speaker_phrase_timeout",
                    { speaker_record_timeout_label: t("config_page.transcription.speaker_record_timeout.label") }
                ));
                break;
            case "Speaker max phrases value is out of range":
                updateSpeakerMaxWords(data);
                showNotification_Error(t("common_error.invalid_value_speaker_max_phrase"));
                break;

            default:
                // determine by endpoint, not message.
                if (endpoint === "/set/data/deepl_auth_key") saveErrorDeepLAuthKey({message, data, endpoint, _result});
                if (endpoint === "/set/data/osc_ip_address") saveErrorOscIpAddress({message, data, endpoint, _result});
                if (endpoint === "/set/data/osc_port") saveErrorOscPort({message, data, endpoint, _result});


                break;
        }

    }

    return {
        errorHandling_Backend,
    }
};