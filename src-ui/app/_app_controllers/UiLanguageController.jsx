import { useEffect } from "react";

import { useTranslation } from "react-i18next";
import { useUiLanguage } from "@logics_configs";

export const UiLanguageController = () => {
    const { currentUiLanguage } = useUiLanguage();
    const { i18n } = useTranslation();

    useEffect(() => {
        i18n.changeLanguage(currentUiLanguage.data);
    }, [currentUiLanguage.data]);
    return null;
};