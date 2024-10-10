import { useTranslation } from "react-i18next";
import styles from "./LanguageSettings.module.scss";
import { PresetTabSelector } from "./preset_tab_selector/PresetTabSelector";
import { LanguageSelectorOpenButton } from "./language_selector_open_button/LanguageSelectorOpenButton";
import { LanguageSwapButton } from "./language_swap_button/LanguageSwapButton";
import { TranslatorSelectorOpenButton } from "./translator_selector_open_button/TranslatorSelectorOpenButton";
import { useStore_IsOpenedTranslatorSelector } from "@store";

export const LanguageSettings = () => {
    const { t } = useTranslation();
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
import { useStore_IsOpenedLanguageSelector } from "@store";
import {
    useMainFunction,
    useLanguageSettings,
} from "@logics_main";

// 言語セレクターをトグルする処理を関数化
const toggleSelector = (selector, currentStatus, updateSelector) => {
    if (currentStatus) {
        updateSelector({ your_language: false, target_language: false });
    } else {
        updateSelector({
            your_language: selector === "your_language",
            target_language: selector === "target_language",
        });
    }
};

// 選択された言語データの取得を関数化
const getSelectedLanguageData = (presetTabData, languageData) => {
    return (presetTabData !== undefined && languageData !== undefined)
        ? languageData[Number(presetTabData)]
        : undefined;
};

const PresetContainer = () => {
    const { t } = useTranslation();
    const { updateIsOpenedLanguageSelector, currentIsOpenedLanguageSelector } = useStore_IsOpenedLanguageSelector();

    const { currentTranscriptionSendStatus, currentTranscriptionReceiveStatus } = useMainFunction();
    const {
        currentSelectedPresetTabNumber,
        currentSelectedYourLanguages,
        currentSelectedTargetLanguages,
    } = useLanguageSettings();

    const your_language_data = getSelectedLanguageData(currentSelectedPresetTabNumber.data, currentSelectedYourLanguages.data);
    const target_language_data = getSelectedLanguageData(currentSelectedPresetTabNumber.data, currentSelectedTargetLanguages.data);


    const yourLanguageSettings = {
        title: t("main_page.your_language"),
        is_opened: currentIsOpenedLanguageSelector.data.your_language,
        onClickFunction: () => toggleSelector("your_language", currentIsOpenedLanguageSelector.data.your_language, updateIsOpenedLanguageSelector),
        TurnedOnSvgComponent: <MicSvg />,
        is_turned_on: currentTranscriptionSendStatus.data,
        variable: your_language_data?.primary,
    };

    const targetLanguageSettings = {
        title: t("main_page.target_language"),
        is_opened: currentIsOpenedLanguageSelector.data.target_language,
        onClickFunction: () => toggleSelector("target_language", currentIsOpenedLanguageSelector.data.target_language, updateIsOpenedLanguageSelector),
        TurnedOnSvgComponent: <HeadphonesSvg />,
        is_turned_on: currentTranscriptionReceiveStatus.data,
        variable: target_language_data?.primary,
    };

    return (
        <div className={styles.preset_container}>
            <LanguageSelectorOpenButton {...yourLanguageSettings} />
            <LanguageSwapButton />
            <LanguageSelectorOpenButton {...targetLanguageSettings} />
            <TranslatorSelectorOpenButton />
        </div>
    );
};
