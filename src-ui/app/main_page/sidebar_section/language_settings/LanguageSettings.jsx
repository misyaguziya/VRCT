import { useI18n } from "@useI18n";
import styles from "./LanguageSettings.module.scss";
import { PresetTabSelector } from "./preset_tab_selector/PresetTabSelector";
import { LanguageSelectorOpenButton } from "./language_selector_open_button/LanguageSelectorOpenButton";
import { LanguageSwapButton } from "./language_swap_button/LanguageSwapButton";
import { TranslatorSelectorOpenButton } from "./translator_selector_open_button/TranslatorSelectorOpenButton";
import { AddRemoveTargetLanguageButtons } from "./add_remove_target_language_buttons/AddRemoveTargetLanguageButtons";
import { useStore_IsOpenedTranslatorSelector } from "@store";

export const LanguageSettings = () => {
    const { t } = useI18n();
    const { updateIsOpenedTranslatorSelector } = useStore_IsOpenedTranslatorSelector();
    const closeTranslatorSelector = () => updateIsOpenedTranslatorSelector(false);

    return (
        <div className={styles.container} onMouseLeave={closeTranslatorSelector}>
            <p className={styles.title}>{t("main_page.language_settings")}</p>
            <PresetTabSelector />
            <PresetContainer />
        </div>
    );
};

import MicSvg from "@images/mic.svg?react";
import HeadphonesSvg from "@images/headphones.svg?react";
import { useMainFunction } from "@logics_main";

const PresetContainer = () => {
    const { t } = useI18n();
    const { currentTranscriptionSendStatus, currentTranscriptionReceiveStatus } = useMainFunction();

    const yourLanguageSettings = {
        TurnedOnSvgComponent: MicSvg,
        is_turned_on: currentTranscriptionSendStatus.data,
    };

    const targetLanguageSettings = {
        TurnedOnSvgComponent: HeadphonesSvg,
        is_turned_on: currentTranscriptionReceiveStatus.data,
    };

    return (
        <div className={styles.preset_container}>
            <LanguageSelectorOpenButton {...yourLanguageSettings} selector_key="your_language" target_key="1"/>
            <LanguageSwapButton />
            <div className={styles.target_language_containers}>
                <LanguageSelectorOpenButton {...targetLanguageSettings} selector_key="target_language" target_key="1" />
                <LanguageSelectorOpenButton {...targetLanguageSettings} selector_key="target_language" target_key="2" />
                <LanguageSelectorOpenButton {...targetLanguageSettings} selector_key="target_language" target_key="3" />
            </div>
            <AddRemoveTargetLanguageButtons />
            <TranslatorSelectorOpenButton />
        </div>
    );
};
