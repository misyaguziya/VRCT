import { createAtomWithHook } from "@store";

import {
    ctranslate2_weight_type_status,
    whisper_weight_type_status,
    ui_configs,
} from "@ui_configs";

import {
    useSettingsLogics,
    useConfigFunctions,
} from "./useSettingsLogics";


export const SETTINGS_ARRAY = [
    // Device
    {
        Category: "Device",
        Base_Name: "EnableAutoMicSelect",
        default_value: true,
        ui_template_id: "toggle",
        logics_template_id: "toggle_enable_disable",
        base_endpoint_name: "auto_mic_select",
    },
    {
        Category: "Device",
        Base_Name: "MicHostList",
        default_value: [],
        ui_template_id: "list",
        logics_template_id: "get_set",
        add_endpoint_run_array: ["from_backend"],
        base_endpoint_name: "selectable_mic_host_list",
        response_transform: "arrayToObject",
    },
    {
        Category: "Device",
        Base_Name: "MicDeviceList",
        default_value: [],
        ui_template_id: "list",
        logics_template_id: "get_set",
        add_endpoint_run_array: ["from_backend"],
        base_endpoint_name: "selectable_mic_device_list",
        response_transform: "arrayToObject",
    },
    {
        Category: "Device",
        Base_Name: "SelectedMicHost",
        default_value: "",
        ui_template_id: "select",
        logics_template_id: "get_set",
        add_endpoint_run_array: ["from_backend"],
        base_endpoint_name: "selected_mic_host",
    },
    {
        Category: "Device",
        Base_Name: "SelectedMicDevice",
        default_value: "",
        ui_template_id: "select",
        logics_template_id: "get_set",
        add_endpoint_run_array: ["from_backend"],
        base_endpoint_name: "selected_mic_device",
    },
    {
        Category: "Device",
        Base_Name: "EnableAutomaticMicThreshold",
        default_value: true,
        ui_template_id: "toggle",
        logics_template_id: "toggle_enable_disable",
        base_endpoint_name: "mic_automatic_threshold",
    },
    {
        Category: "Device",
        Base_Name: "MicThreshold",
        default_value: 0,
        ui_template_id: "slider",
        logics_template_id: "get_set",
        base_endpoint_name: "mic_threshold",
    },
    {
        Category: "Device",
        Base_Name: "EnableAutoSpeakerSelect",
        default_value: true,
        ui_template_id: "toggle",
        logics_template_id: "toggle_enable_disable",
        base_endpoint_name: "auto_speaker_select",
    },
    {
        Category: "Device",
        Base_Name: "SpeakerDeviceList",
        default_value: [],
        ui_template_id: "list",
        logics_template_id: "get_set",
        add_endpoint_run_array: ["from_backend"],
        base_endpoint_name: "selectable_speaker_device_list",
        response_transform: "arrayToObject",
    },
    {
        Category: "Device",
        Base_Name: "SelectedSpeakerDevice",
        default_value: "",
        ui_template_id: "select",
        logics_template_id: "get_set",
        add_endpoint_run_array: ["from_backend"],
        base_endpoint_name: "selected_speaker_device",
    },
    {
        Category: "Device",
        Base_Name: "EnableAutomaticSpeakerThreshold",
        default_value: true,
        ui_template_id: "toggle",
        logics_template_id: "toggle_enable_disable",
        base_endpoint_name: "speaker_automatic_threshold",
    },
    {
        Category: "Device",
        Base_Name: "SpeakerThreshold",
        default_value: 0,
        ui_template_id: "slider",
        logics_template_id: "get_set",
        base_endpoint_name: "speaker_threshold",
    },

    // Appearance
    {
        Category: "Appearance",
        Base_Name: "UiLanguage",
        default_value: "en",
        ui_template_id: "select",
        logics_template_id: "get_set",
        base_endpoint_name: "ui_language",
    },
    {
        Category: "Appearance",
        Base_Name: "UiScaling",
        default_value: 100,
        ui_template_id: "slider",
        logics_template_id: "get_set",
        base_endpoint_name: "ui_scaling",
    },
    {
        Category: "Appearance",
        Base_Name: "MessageLogUiScaling",
        default_value: 100,
        ui_template_id: "slider",
        logics_template_id: "get_set",
        base_endpoint_name: "textbox_ui_scaling",
    },
    {
        Category: "Appearance",
        Base_Name: "SendMessageButtonType",
        default_value: "primary",
        ui_template_id: "select",
        logics_template_id: "get_set",
        base_endpoint_name: "send_message_button_type",
    },
    {
        Category: "Appearance",
        Base_Name: "ShowResendButton",
        default_value: true,
        ui_template_id: "toggle",
        logics_template_id: "toggle_enable_disable",
        base_endpoint_name: "show_resend_button",
    },
    {
        Category: "Appearance",
        Base_Name: "SelectedFontFamily",
        default_value: "Yu Gothic UI",
        ui_template_id: "select",
        logics_template_id: "get_set",
        base_endpoint_name: "font_family",
    },
    {
        Category: "Appearance",
        Base_Name: "Transparency",
        default_value: 100,
        ui_template_id: "slider",
        logics_template_id: "get_set",
        base_endpoint_name: "transparency",
    },

    // Translation
    // CTranslate2/Whisper weights
    {
        Category: "Translation",
        Base_Name: "CTranslate2WeightTypeStatus",
        default_value: ctranslate2_weight_type_status,
        ui_template_id: "list",
        logics_template_id: "weight_download_status",
        base_endpoint_name: "ctranslate2_weight",
    },
    {
        Category: "Translation",
        Base_Name: "SelectedCTranslate2WeightType",
        default_value: "",
        ui_template_id: "select",
        logics_template_id: "get_set",
        base_endpoint_name: "selected_ctranslate2_weight_type",
    },
    {
        Category: "Translation",
        Base_Name: "SelectedTranslationComputeType",
        default_value: "",
        ui_template_id: "select",
        logics_template_id: "get_set",
        base_endpoint_name: "selected_translation_compute_type",
    },
    {
        Category: "Translation",
        Base_Name: "SelectableTranslationComputeDeviceList",
        default_value: [],
        ui_template_id: "list",
        logics_template_id: "get_set",
        base_endpoint_name: "selectable_translation_compute_device_list",
        response_transform: "transformToIndexedArray",
    },
    {
        Category: "Translation",
        Base_Name: "SelectedTranslationComputeDevice",
        default_value: "",
        ui_template_id: "select",
        logics_template_id: "get_set",
        base_endpoint_name: "selected_translation_compute_device",
    },
    // DeepL
    {
        Category: "Translation",
        Base_Name: "DeepLAuthKey",
        default_value: "",
        ui_template_id: "input",
        logics_template_id: "get_set_delete",
        base_endpoint_name: "deepl_auth_key",
    },
    // Plamo
    {
        Category: "Translation",
        Base_Name: "PlamoAuthKey",
        default_value: "",
        ui_template_id: "input",
        logics_template_id: "get_set_delete",
        base_endpoint_name: "plamo_auth_key",
    },
    {
        Category: "Translation",
        Base_Name: "SelectablePlamoModelList",
        default_value: [],
        ui_template_id: "list",
        logics_template_id: "get_set",
        add_endpoint_run_array: ["from_backend"],
        base_endpoint_name: "selectable_plamo_model_list",
        response_transform: "arrayToObject",
    },
    {
        Category: "Translation",
        Base_Name: "SelectedPlamoModel",
        default_value: "",
        ui_template_id: "select",
        logics_template_id: "get_set",
        add_endpoint_run_array: ["from_backend"],
        base_endpoint_name: "selected_plamo_model",
    },
    // Gemini
    {
        Category: "Translation",
        Base_Name: "GeminiAuthKey",
        default_value: "",
        ui_template_id: "input",
        logics_template_id: "get_set_delete",
        base_endpoint_name: "gemini_auth_key",
    },
    {
        Category: "Translation",
        Base_Name: "SelectableGeminiModelList",
        default_value: [],
        ui_template_id: "list",
        logics_template_id: "get_set",
        add_endpoint_run_array: ["from_backend"],
        base_endpoint_name: "selectable_gemini_model_list",
        response_transform: "arrayToObject",
    },
    {
        Category: "Translation",
        Base_Name: "SelectedGeminiModel",
        default_value: "",
        ui_template_id: "select",
        logics_template_id: "get_set",
        add_endpoint_run_array: ["from_backend"],
        base_endpoint_name: "selected_gemini_model",
    },
    // OpenAI
    {
        Category: "Translation",
        Base_Name: "OpenAIAuthKey",
        default_value: "",
        ui_template_id: "input",
        logics_template_id: "get_set_delete",
        base_endpoint_name: "openai_auth_key",
    },
    {
        Category: "Translation",
        Base_Name: "SelectableOpenAIModelList",
        default_value: [],
        ui_template_id: "list",
        logics_template_id: "get_set",
        add_endpoint_run_array: ["from_backend"],
        base_endpoint_name: "selectable_openai_model_list",
        response_transform: "arrayToObject",
    },
    {
        Category: "Translation",
        Base_Name: "SelectedOpenAIModel",
        default_value: "",
        ui_template_id: "select",
        logics_template_id: "get_set",
        add_endpoint_run_array: ["from_backend"],
        base_endpoint_name: "selected_openai_model",
    },
    // Groq
    {
        Category: "Translation",
        Base_Name: "GroqAuthKey",
        default_value: "",
        ui_template_id: "input",
        logics_template_id: "get_set_delete",
        base_endpoint_name: "groq_auth_key",
    },
    {
        Category: "Translation",
        Base_Name: "SelectableGroqModelList",
        default_value: [],
        ui_template_id: "list",
        logics_template_id: "get_set",
        add_endpoint_run_array: ["from_backend"],
        base_endpoint_name: "selectable_groq_model_list",
        response_transform: "arrayToObject",
    },
    {
        Category: "Translation",
        Base_Name: "SelectedGroqModel",
        default_value: "",
        ui_template_id: "select",
        logics_template_id: "get_set",
        add_endpoint_run_array: ["from_backend"],
        base_endpoint_name: "selected_groq_model",
    },
    // Open Router
    {
        Category: "Translation",
        Base_Name: "OpenRouterAuthKey",
        default_value: "",
        ui_template_id: "input",
        logics_template_id: "get_set_delete",
        base_endpoint_name: "openrouter_auth_key",
    },
    {
        Category: "Translation",
        Base_Name: "SelectableOpenRouterModelList",
        default_value: [],
        ui_template_id: "list",
        logics_template_id: "get_set",
        add_endpoint_run_array: ["from_backend"],
        base_endpoint_name: "selectable_openrouter_model_list",
        response_transform: "arrayToObject",
    },
    {
        Category: "Translation",
        Base_Name: "SelectedOpenRouterModel",
        default_value: "",
        ui_template_id: "select",
        logics_template_id: "get_set",
        add_endpoint_run_array: ["from_backend"],
        base_endpoint_name: "selected_openrouter_model",
    },
    // LM Studio
    {
        Category: "Translation",
        Base_Name: "LMStudioURL",
        default_value: "",
        ui_template_id: "input",
        logics_template_id: "get_set",
        base_endpoint_name: "lmstudio_url",
    },
    {
        Category: "Translation",
        Base_Name: "SelectableLMStudioModelList",
        default_value: [],
        ui_template_id: "list",
        logics_template_id: "get_set",
        add_endpoint_run_array: ["from_backend"],
        base_endpoint_name: "selectable_lmstudio_model_list",
        response_transform: "arrayToObject",
    },
    {
        Category: "Translation",
        Base_Name: "SelectedLMStudioModel",
        default_value: "",
        ui_template_id: "select",
        logics_template_id: "get_set",
        add_endpoint_run_array: ["from_backend"],
        base_endpoint_name: "selected_lmstudio_model",
    },
    // Ollama
    {
        Category: "Translation",
        Base_Name: "OllamaURL",
        default_value: "",
        ui_template_id: "input",
        logics_template_id: "get_set",
        base_endpoint_name: "ollama_url",
    },
    {
        Category: "Translation",
        Base_Name: "SelectableOllamaModelList",
        default_value: [],
        ui_template_id: "list",
        logics_template_id: "get_set",
        add_endpoint_run_array: ["from_backend"],
        base_endpoint_name: "selectable_ollama_model_list",
        response_transform: "arrayToObject",
    },
    {
        Category: "Translation",
        Base_Name: "SelectedOllamaModel",
        default_value: "",
        ui_template_id: "select",
        logics_template_id: "get_set",
        add_endpoint_run_array: ["from_backend"],
        base_endpoint_name: "selected_ollama_model",
    },

    // Transcription
    // Mic
    {
        Category: "Transcription",
        Base_Name: "MicRecordTimeout",
        default_value: 0,
        ui_template_id: "slider",
        logics_template_id: "get_set",
        base_endpoint_name: "mic_record_timeout",
    },
    {
        Category: "Transcription",
        Base_Name: "MicPhraseTimeout",
        default_value: 0,
        ui_template_id: "slider",
        logics_template_id: "get_set",
        base_endpoint_name: "mic_phrase_timeout",
    },
    {
        Category: "Transcription",
        Base_Name: "MicMaxWords",
        default_value: 0,
        ui_template_id: "slider",
        logics_template_id: "get_set",
        base_endpoint_name: "mic_max_phrases",
    },
    {
        Category: "Transcription",
        Base_Name: "MicWordFilterList",
        default_value: [],
        ui_template_id: "list",
        logics_template_id: "get_set",
        base_endpoint_name: "mic_word_filter",
    },
    // Speaker
    {
        Category: "Transcription",
        Base_Name: "SpeakerRecordTimeout",
        default_value: 0,
        ui_template_id: "slider",
        logics_template_id: "get_set",
        base_endpoint_name: "speaker_record_timeout",
    },
    {
        Category: "Transcription",
        Base_Name: "SpeakerPhraseTimeout",
        default_value: 0,
        ui_template_id: "slider",
        logics_template_id: "get_set",
        base_endpoint_name: "speaker_phrase_timeout",
    },
    {
        Category: "Transcription",
        Base_Name: "SpeakerMaxWords",
        default_value: 0,
        ui_template_id: "slider",
        logics_template_id: "get_set",
        base_endpoint_name: "speaker_max_phrases",
    },
    // Engines
    {
        Category: "Transcription",
        Base_Name: "SelectedTranscriptionEngine",
        default_value: "",
        ui_template_id: "select",
        logics_template_id: "get_set",
        base_endpoint_name: "selected_transcription_engine",
    },
    {
        Category: "Transcription",
        Base_Name: "WhisperWeightTypeStatus",
        default_value: whisper_weight_type_status,
        ui_template_id: "list",
        logics_template_id: "weight_download_status",
        base_endpoint_name: "whisper_weight",
    },
    {
        Category: "Transcription",
        Base_Name: "SelectedWhisperWeightType",
        default_value: "",
        ui_template_id: "select",
        logics_template_id: "get_set",
        base_endpoint_name: "selected_whisper_weight_type",
    },
    {
        Category: "Transcription",
        Base_Name: "SelectedTranscriptionComputeType",
        default_value: "",
        ui_template_id: "select",
        logics_template_id: "get_set",
        base_endpoint_name: "selected_transcription_compute_type",
    },
    {
        Category: "Transcription",
        Base_Name: "SelectableTranscriptionComputeDeviceList",
        default_value: [],
        ui_template_id: "list",
        logics_template_id: "get_set",
        base_endpoint_name: "selectable_transcription_compute_device_list",
        response_transform: "transformToIndexedArray",
    },
    {
        Category: "Transcription",
        Base_Name: "SelectedTranscriptionComputeDevice",
        default_value: "",
        ui_template_id: "select",
        logics_template_id: "get_set",
        base_endpoint_name: "selected_transcription_compute_device",
    },
    // Advanced
    {
        Category: "Transcription",
        Base_Name: "MicAvgLogprob",
        default_value: 0,
        ui_template_id: "slider",
        logics_template_id: "get_set",
        base_endpoint_name: "mic_avg_logprob",
    },
    {
        Category: "Transcription",
        Base_Name: "MicNoSpeechProb",
        default_value: 0,
        ui_template_id: "slider",
        logics_template_id: "get_set",
        base_endpoint_name: "mic_no_speech_prob",
    },
    {
        Category: "Transcription",
        Base_Name: "SpeakerAvgLogprob",
        default_value: 0,
        ui_template_id: "slider",
        logics_template_id: "get_set",
        base_endpoint_name: "speaker_avg_logprob",
    },
    {
        Category: "Transcription",
        Base_Name: "SpeakerNoSpeechProb",
        default_value: 0,
        ui_template_id: "slider",
        logics_template_id: "get_set",
        base_endpoint_name: "speaker_no_speech_prob",
    },

    // Vr
    {
        Category: "Vr",
        Base_Name: "IsEnabledOverlaySmallLog",
        default_value: false,
        ui_template_id: "toggle",
        logics_template_id: "toggle_enable_disable",
        base_endpoint_name: "overlay_small_log",
    },
    {
        Category: "Vr",
        Base_Name: "OverlaySmallLogSettings",
        default_value: ui_configs.overlay_small_log_default_settings,
        ui_template_id: "object",
        logics_template_id: "get_set",
        base_endpoint_name: "overlay_small_log_settings",
    },
    {
        Category: "Vr",
        Base_Name: "IsEnabledOverlayLargeLog",
        default_value: false,
        ui_template_id: "toggle",
        logics_template_id: "toggle_enable_disable",
        base_endpoint_name: "overlay_large_log",
    },
    {
        Category: "Vr",
        Base_Name: "OverlayLargeLogSettings",
        default_value: ui_configs.overlay_large_log_default_settings,
        ui_template_id: "object",
        logics_template_id: "get_set",
        base_endpoint_name: "overlay_large_log_settings",
    },
    {
        Category: "Vr",
        Base_Name: "OverlayShowOnlyTranslatedMessages",
        default_value: false,
        ui_template_id: "toggle",
        logics_template_id: "toggle_enable_disable",
        base_endpoint_name: "overlay_show_only_translated_messages",
    },
    {
        Category: "Vr",
        Base_Name: "VoiceTypingMode",
        default_value: false,
        ui_template_id: "toggle",
        logics_template_id: "toggle_enable_disable",
        base_endpoint_name: "clipboard",
    },

    // Others
    {
        Category: "Others",
        Base_Name: "EnableAutoClearMessageInputBox",
        default_value: false,
        ui_template_id: "toggle",
        logics_template_id: "toggle_enable_disable",
        base_endpoint_name: "auto_clear_message_box",
    },
    {
        Category: "Others",
        Base_Name: "EnableSendOnlyTranslatedMessages",
        default_value: false,
        ui_template_id: "toggle",
        logics_template_id: "toggle_enable_disable",
        base_endpoint_name: "send_only_translated_messages",
    },
    {
        Category: "Others",
        Base_Name: "EnableAutoExportMessageLogs",
        default_value: false,
        ui_template_id: "toggle",
        logics_template_id: "toggle_enable_disable",
        base_endpoint_name: "logger_feature",
    },
    {
        Category: "Others",
        Base_Name: "EnableVrcMicMuteSync",
        default_value: false,
        ui_template_id: "toggle",
        logics_template_id: "toggle_enable_disable",
        base_endpoint_name: "vrc_mic_mute_sync",
    },
    {
        Category: "Others",
        Base_Name: "EnableSendMessageToVrc",
        default_value: false,
        ui_template_id: "toggle",
        logics_template_id: "toggle_enable_disable",
        base_endpoint_name: "send_message_to_vrc",
    },
    {
        Category: "Others",
        Base_Name: "EnableNotificationVrcSfx",
        default_value: false,
        ui_template_id: "toggle",
        logics_template_id: "toggle_enable_disable",
        base_endpoint_name: "notification_vrc_sfx",
    },
    {
        Category: "Others",
        Base_Name: "EnableSendReceivedMessageToVrc",
        default_value: false,
        ui_template_id: "toggle",
        logics_template_id: "toggle_enable_disable",
        base_endpoint_name: "send_received_message_to_vrc",
    },
    {
        Category: "Others",
        Base_Name: "SendMessageFormatParts",
        default_value: [],
        ui_template_id: "list",
        logics_template_id: "get_set",
        base_endpoint_name: "send_message_format_parts",
    },
    {
        Category: "Others",
        Base_Name: "ReceivedMessageFormatParts",
        default_value: [],
        ui_template_id: "list",
        logics_template_id: "get_set",
        base_endpoint_name: "received_message_format_parts",
    },
    {
        Category: "Others",
        Base_Name: "ConvertMessageToRomaji",
        default_value: false,
        ui_template_id: "toggle",
        logics_template_id: "toggle_enable_disable",
        base_endpoint_name: "convert_message_to_romaji",
    },
    {
        Category: "Others",
        Base_Name: "ConvertMessageToHiragana",
        default_value: false,
        ui_template_id: "toggle",
        logics_template_id: "toggle_enable_disable",
        base_endpoint_name: "convert_message_to_hiragana",
    },

    // AdvancedSettings
    {
        Category: "AdvancedSettings",
        Base_Name: "OscIpAddress",
        default_value: "127.0.0.1",
        ui_template_id: "input",
        logics_template_id: "get_set",
        base_endpoint_name: "osc_ip_address",
    },
    {
        Category: "AdvancedSettings",
        Base_Name: "OscPort",
        default_value: 9000,
        ui_template_id: "input",
        logics_template_id: "get_set",
        base_endpoint_name: "osc_port",
    },
    {
        Category: "AdvancedSettings",
        Base_Name: "EnableWebsocket",
        default_value: false,
        ui_template_id: "toggle",
        logics_template_id: "toggle_enable_disable",
        base_endpoint_name: "websocket_server",
    },
    {
        Category: "AdvancedSettings",
        Base_Name: "WebsocketHost",
        default_value: "127.0.0.1",
        ui_template_id: "input",
        logics_template_id: "get_set",
        base_endpoint_name: "websocket_host",
    },
    {
        Category: "AdvancedSettings",
        Base_Name: "WebsocketPort",
        default_value: 9001,
        ui_template_id: "input",
        logics_template_id: "get_set",
        base_endpoint_name: "websocket_port",
    },

];



for (const setting_data of SETTINGS_ARRAY) {
    createAtomWithHook(setting_data.default_value, setting_data.Base_Name);
}

const buildCategoryApiFromSettings = (settings, settingsArray, Category, extraFunctions = {}) => {
    const api = {};
    const filtered = settingsArray.filter((s) => s.Category === Category);
    const COMMON_PROPS = [ "current", "update", "get", "set", "toggle", "setSuccess", "delete", "deleteSuccess", "updateFromBackend" ];

    for (const s of filtered) {
        const base = s.Base_Name;

        COMMON_PROPS.forEach(prop => {
            const key = `${prop}${base}`;
            const settingValue = settings[key];

            if (settingValue !== undefined) {
                api[key] = settingValue;
            }
        });

        if (s.logics_template_id === "weight_download_status") {
            const updateDownloadProgressKey = `updateDownloadProgress${base}`;
            const updateDownloadedKey = `updateDownloaded${base}`;
            const pendingKey = `pending${base}`;
            const downloadedKey = `downloaded${base}`;
            const downloadKey = `download${base}`;

            if (typeof settings[updateDownloadProgressKey] === "function") api[updateDownloadProgressKey] = settings[updateDownloadProgressKey];
            if (typeof settings[updateDownloadedKey] === "function") api[updateDownloadedKey] = settings[updateDownloadedKey];
            if (typeof settings[pendingKey] === "function") api[pendingKey] = settings[pendingKey];
            if (typeof settings[downloadedKey] === "function") api[downloadedKey] = settings[downloadedKey];
            if (typeof settings[downloadKey] === "function") api[downloadKey] = settings[downloadKey];

            const updateFromBackendKey = `updateFromBackend${base}`;
            if (typeof settings[updateFromBackendKey] === "function") api[updateFromBackendKey] = settings[updateFromBackendKey];
        }
    }
    return { ...api, ...extraFunctions };
};

export const createCategoryHook = (Category) => {
    return () => {
        const { settings } = useSettingsLogics(SETTINGS_ARRAY, Category);
        const extraFunctions = useConfigFunctions(Category);
        const autoApi = buildCategoryApiFromSettings(settings, SETTINGS_ARRAY, Category, extraFunctions);
        return { ...autoApi };
    };
};