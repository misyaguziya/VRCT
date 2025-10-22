export const ui_configs = {
    mic_threshold_min: 0,
    mic_threshold_max: 2000,
    speaker_threshold_min: 0,
    speaker_threshold_max: 4000,
    overlay_small_log: {
        x_pos: { step: 0.05, min: -0.5, max: 0.5 },
        y_pos: { step: 0.05, min: -0.8, max: 0.8 },
        z_pos: { step: 0.05, min: -0.5, max: 1.5 },
        x_rotation: { min: -180, max: 180, step: 5 },
        y_rotation: { min: -180, max: 180, step: 5 },
        z_rotation: { min: -180, max: 180, step: 5 },
        ui_scaling: { step: 10, min: 40, max: 200 },
    },
    overlay_large_log: {
        x_pos: { step: 0.05, min: -0.5, max: 0.5 },
        y_pos: { step: 0.05, min: -0.8, max: 0.8 },
        z_pos: { step: 0.05, min: -0.5, max: 1.5 },
        x_rotation: { min: -180, max: 180, step: 5 },
        y_rotation: { min: -180, max: 180, step: 5 },
        z_rotation: { min: -180, max: 180, step: 5 },
        ui_scaling: { step: 10, min: 40, max: 200 },
    },

    overlay_small_log_default_settings: {
        x_pos: 0.0,
        y_pos: 0.0,
        z_pos: 0.0,
        x_rotation: 0.0,
        y_rotation: 0.0,
        z_rotation: 0.0,
        display_duration: 5,
        fadeout_duration: 2,
        opacity: 1.0,
        ui_scaling: 1.0,
        tracker: "HMD",
    },
    overlay_large_log_default_settings: {
        x_pos: 0.0,
        y_pos: 0.0,
        z_pos: 0.0,
        x_rotation: 0.0,
        y_rotation: 0.0,
        z_rotation: 0.0,
        display_duration: 5,
        fadeout_duration: 2,
        opacity: 1.0,
        ui_scaling: 1.0,
        tracker: "LeftHand",
    },

    send_message_format_parts: {
        message: {
            prefix: "",
            suffix: ""
        },
        separator: "\n",
        translation: {
            prefix: "",
            separator: "\n",
            suffix: ""
        },
        translation_first: false,
    },
    received_message_format_parts: {
        message: {
            prefix: "",
            suffix: ""
        },
        separator: "\n",
        translation: {
            prefix: "",
            separator: "\n",
            suffix: ""
        },
        translation_first: false,
    },

    selectable_ui_languages: [
        {id: "en", label: "English"},
        {id: "ja", label: "日本語"},
        {id: "ko", label: "한국어"},
        {id: "zh-Hant", label: "繁體中文"},
        {id: "zh-Hans", label: "简体中文"},
    ]
};

// true: src-ui\plugins false: src-tauri\target\debug\plugins
export const IS_PLUGIN_PATH_DEV_MODE = false;

// true: dev_vrct_plugins_list.json false: vrct_plugins_list.json
export const IS_PLUGIN_LIST_URL_DEV_MODE = false;

export const getPluginsList = () => {
    const base_url = "https://raw.githubusercontent.com/ShiinaSakamoto/vrct_plugins_list/main/";
    const plugins_list_url = (IS_PLUGIN_LIST_URL_DEV_MODE)
    ? base_url + "dev_vrct_plugins_list.json"
    : base_url + "vrct_plugins_list.json";
    return plugins_list_url;
};
if (IS_PLUGIN_PATH_DEV_MODE || IS_PLUGIN_LIST_URL_DEV_MODE) console.warn("ui_configs IS_PLUGIN_PATH_DEV_MODE or IS_PLUGIN_LIST_URL_DEV_MODE is true. Turn to 'false' when it's production environment.");

export const translator_status = [
    { id: "DeepL", label: "DeepL", is_available: false },
    { id: "DeepL_API", label: `DeepL API`, is_available: false },
    { id: "Google", label: "Google", is_available: false },
    { id: "Bing", label: "Bing", is_available: false },
    { id: "Papago", label: "Papago", is_available: false },
    { id: "CTranslate2", label: `AI\nCTranslate2`, is_available: false, is_default: true },
];

export const ctranslate2_weight_type_status = [
    { id: "m2m100_418M-ct2-int8", capacity: "418MB"},
    { id: "m2m100_1.2B-ct2-int8", capacity: "1.2GB"},
    { id: "nllb-200-distilled-1.3B-ct2-int8", capacity: "1.3GB"},
    { id: "nllb-200-3.3B-ct2-int8", capacity: "3.3GB"},
].map(item => ({ ...item, is_downloaded: false, progress: null }));

export const whisper_weight_type_status = [
    { id: "tiny", capacity: "74.5MB"},
    { id: "base", capacity: "141MB"},
    { id: "small", capacity: "463MB"},
    { id: "medium", capacity: "1.42GB"},
    { id: "large-v1", capacity: "2.87GB"},
    { id: "large-v2", capacity: "2.87GB"},
    { id: "large-v3", capacity: "2.87GB"},
    { id: "large-v3-turbo-int8", capacity: "794MB"},
    { id: "large-v3-turbo", capacity: "1.58GB"},
].map(item => ({ ...item, is_downloaded: false, progress: null }));

export const supporters_data_url = "https://shiinasakamoto.github.io/vrct_supporters/assets/supporters/data.json";
export const supporters_images_url = "https://ShiinaSakamoto.github.io/vrct_supporters/assets/supporters";