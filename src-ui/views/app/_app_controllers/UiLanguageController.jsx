import { useEffect } from "react";

import { useI18n } from "@useI18n";
import { useAppearance } from "@logics_configs";

export const UiLanguageController = () => {
    const { currentUiLanguage } = useAppearance();
    const { i18n } = useI18n();

    useEffect(() => {
        i18n.changeLanguage(currentUiLanguage.data);
    }, [currentUiLanguage.data]);
    return null;
};