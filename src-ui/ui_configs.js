export const translator_status = [
    { translator_id: "DeepL", translator_name: "DeepL", is_available: false },
    { translator_id: "DeepL_API", translator_name: `DeepL\nAPI`, is_available: false },
    { translator_id: "Google", translator_name: "Google", is_available: false },
    { translator_id: "Bing", translator_name: "Bing", is_available: false },
    { translator_id: "Papago", translator_name: "Papago", is_available: false },
    { translator_id: "CTranslate2", translator_name: `Internal\n(Default)`, is_available: false },
];

export const ui_configs = {
    mic_threshold_min: 0,
    mic_threshold_max: 2000,
    speaker_threshold_min: 0,
    speaker_threshold_max: 4000,
    selectable_ui_languages: [
        {id: "en", label: "English"},
        {id: "ja", label: "日本語"},
        {id: "ko", label: "한국어"},
        {id: "zh-Hant", label: "繁體中文"},
    ]
};

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
];