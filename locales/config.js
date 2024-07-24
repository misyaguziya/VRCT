import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import translation_en from "./en.json";
import translation_ja from "./ja.json";
import translation_ko from "./ko.json";
import translation_zh_Hant from "./zh-Hant.json";


const resources = {
    en: { translation: translation_en },
    ja: { translation: translation_ja },
    ko: { translation: translation_ko },
    zh_Hant: { translation: translation_zh_Hant },
};

i18n
    .use(initReactI18next) // passes i18n down to react-i18next
    .init({
        resources,
        lng: "en",
        fallbackLng: "en",
        debug: true,
        interpolation: {
            escapeValue: false // react already safes from xss
        }
    });

export default i18n;
