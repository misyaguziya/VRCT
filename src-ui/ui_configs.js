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
    selectable_ui_languages: {
        en: "English",
        ja: "日本語",
        ko: "한국어",
        "zh-Hant": "繁體中文",
    }
};