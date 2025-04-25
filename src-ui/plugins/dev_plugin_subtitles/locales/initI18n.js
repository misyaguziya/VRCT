import en from "./en.yml";
import ja from "./ja.yml";
import plugin_info from "../plugin_info.json";

export const initI18n = (i18n) => {
    const ns = plugin_info.plugin_id;
    // parse once
    const en_res = en;
    const ja_res = ja;

    // addResourceBundle will merge into i18n’s store
    i18n.addResourceBundle("en", ns, en_res, /* deep = */ true, /* overwrite = */ true);
    i18n.addResourceBundle("ja", ns, ja_res, /* deep = */ true, /* overwrite = */ true);
};