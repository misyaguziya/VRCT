import yaml from "js-yaml";
import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import en_yml from "./en.yml?raw";
import ja_yml from "./ja.yml?raw";
import ko_yml from "./ko.yml?raw";
import zh_hant_yml from "./zh-Hant.yml?raw";
import zh_hans_yml from "./zh-Hans.yml?raw";

const translation_en = yaml.load(en_yml);
const translation_ja = yaml.load(ja_yml);
const translation_ko = yaml.load(ko_yml);
const translation_zh_Hant = yaml.load(zh_hant_yml);
const translation_zh_Hans = yaml.load(zh_hans_yml);


const resources = {
    en: { translation: translation_en },
    ja: { translation: translation_ja },
    ko: { translation: translation_ko },
    "zh-Hant": { translation: translation_zh_Hant },
    "zh-Hans": { translation: translation_zh_Hans },
};

i18n
    .use(initReactI18next) // passes i18n down to react-i18next
    .init({
        resources,
        lng: "en",
        fallbackLng: "en",
        // debug: true,
        interpolation: {
        escapeValue: false, // react already safes from xss
    },
});

export default i18n;
