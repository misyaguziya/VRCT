export const ui_configs = {
    mic_threshold_min: 0,
    mic_threshold_max: 2000,
    speaker_threshold_min: 0,
    speaker_threshold_max: 4000,
    overlay_small_log: {
        x_pos: { step: 0.05, min: -0.5, max: 0.5 },
        y_pos: { step: 0.05, min: -0.8, max: 0.8 },
        z_pos: { step: 0.05, min: -0.5, max: 1.5 },
        ui_scaling: { step: 10, min: 40, max: 200 },
    },
    overlay_large_log: {
        x_pos: { step: 0.05, min: -0.5, max: 0.5 },
        y_pos: { step: 0.05, min: -0.8, max: 0.8 },
        z_pos: { step: 0.05, min: -0.5, max: 1.5 },
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

    selectable_ui_languages: [
        {id: "en", label: "English"},
        {id: "ja", label: "日本語"},
        {id: "ko", label: "한국어"},
        {id: "zh-Hant", label: "繁體中文"},
        {id: "zh-Hans", label: "简体中文"},
    ]
};

export const translator_status = [
    { id: "DeepL", label: "DeepL", is_available: false },
    { id: "DeepL_API", label: `DeepL API`, is_available: false },
    { id: "Google", label: "Google", is_available: false },
    { id: "Bing", label: "Bing", is_available: false },
    { id: "Papago", label: "Papago", is_available: false },
    { id: "CTranslate2", label: `AI\nCTranslate2`, is_available: false, is_default: true },
];

export const ctranslate2_weight_type_status = [
    { id: "small", label: "small", is_downloaded: false, progress: null },
    { id: "large", label: "large", is_downloaded: false, progress: null },
];

export const whisper_weight_type_status = [
    { id: "tiny", label: "tiny", is_downloaded: false, progress: null },
    { id: "base", label: "base", is_downloaded: false, progress: null },
    { id: "small", label: "small", is_downloaded: false, progress: null },
    { id: "medium", label: "medium", is_downloaded: false, progress: null },
    { id: "large-v1", label: "large-v1", is_downloaded: false, progress: null },
    { id: "large-v2", label: "large-v2", is_downloaded: false, progress: null },
    { id: "large-v3", label: "large-v3", is_downloaded: false, progress: null },
    { id: "large-v3-turbo-int8", label: "large-v3-turbo-int8", is_downloaded: false, progress: null },
    { id: "large-v3-turbo", label: "large-v3-turbo", is_downloaded: false, progress: null },
];

export const supporters_data_url = "https://shiinasakamoto.github.io/vrct_supporters/assets/supporters/data.json";
export const supporters_images_url = "https://ShiinaSakamoto.github.io/vrct_supporters/assets/supporters";