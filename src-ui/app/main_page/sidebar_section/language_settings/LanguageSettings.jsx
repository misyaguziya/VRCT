import { useTranslation } from "react-i18next";

import styles from "./LanguageSettings.module.scss";

import { PresetTabSelector } from "./preset_tab_selector/PresetTabSelector";
import { LanguageSelectorOpenButton } from "./language_selector_open_button/LanguageSelectorOpenButton";
import { LanguageSwapButton } from "./language_swap_button/LanguageSwapButton";
import { TranslatorSelectorOpenButton } from "./translator_selector_open_button/TranslatorSelectorOpenButton";
import { useIsOpenedTranslatorSelector } from "@store";

export const LanguageSettings = () => {
    const { updateIsOpenedTranslatorSelector} = useIsOpenedTranslatorSelector();
    const closeTranslatorSelector = () => updateIsOpenedTranslatorSelector(false);

    return (
        <div className={styles.container} onMouseLeave={closeTranslatorSelector} >
            <p className={styles.title}>Language Settings</p>
            <PresetTabSelector />
            <PresetContainer />
        </div>
    );
};


import MicSvg from "@images/mic.svg?react";
import HeadphonesSvg from "@images/headphones.svg?react";
import { useIsOpenedLanguageSelector } from "@store";
import { useMainFunction } from "@logics/useMainFunction";

const PresetContainer = () => {
    const { t } = useTranslation();
    const { updateIsOpenedLanguageSelector, currentIsOpenedLanguageSelector } = useIsOpenedLanguageSelector();

    const {
        currentTranscriptionSendStatus,
        currentTranscriptionReceiveStatus,
    } = useMainFunction();


    const closeLanguageSelector = () => {
        updateIsOpenedLanguageSelector({
            your_language: false,
            target_language: false,
        });
    };

    const toggleYourLanguageSelector = () => {
        if (currentIsOpenedLanguageSelector.your_language === true) {
            closeLanguageSelector();
        } else {
            updateIsOpenedLanguageSelector({
                your_language: true,
                target_language: false,
            });
        }
    };

    const toggleTargetLanguageSelector = () => {
        if (currentIsOpenedLanguageSelector.target_language === true) {
            closeLanguageSelector();
        } else {
            updateIsOpenedLanguageSelector({
                your_language: false,
                target_language: true,
            });
        }
    };

    const handleLanguageSelectorClick = (selector) => {
        if (selector === "your_language") {
            toggleYourLanguageSelector();
        } else if (selector === "target_language") {
            toggleTargetLanguageSelector();
        }
    };

    const your_language_settings = {
        title: t("main_page.your_language"),
        is_opened: currentIsOpenedLanguageSelector.your_language,
        onClickFunction: () => handleLanguageSelectorClick("your_language"),
        TurnedOnSvgComponent: <MicSvg />,
        is_turned_on: currentTranscriptionSendStatus.data,
    };

    const target_language_settings = {
        title: t("main_page.target_language"),
        is_opened: currentIsOpenedLanguageSelector.target_language,
        onClickFunction: () => handleLanguageSelectorClick("target_language"),
        TurnedOnSvgComponent: <HeadphonesSvg />,
        is_turned_on: currentTranscriptionReceiveStatus.data,
    };

    return (
        <div className={styles.preset_container}>
            <LanguageSelectorOpenButton {...your_language_settings} />
            <LanguageSwapButton />
            <LanguageSelectorOpenButton {...target_language_settings} />
            <TranslatorSelectorOpenButton />
        </div>
    );
};