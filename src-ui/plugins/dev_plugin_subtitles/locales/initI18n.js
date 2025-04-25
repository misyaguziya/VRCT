import en from "./en.yml";
import ja from "./ja.yml";
import plugin_info from "../plugin_info.json";

export const initI18n = (i18n) => {
    const ns = plugin_info.plugin_id;

    // addResourceBundle will merge into i18n’s store
    i18n.addResourceBundle("en", ns, en, /* deep = */ true, /* overwrite = */ true);
    i18n.addResourceBundle("ja", ns, ja, /* deep = */ true, /* overwrite = */ true);
};