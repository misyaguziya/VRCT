import { useTranslation } from "react-i18next";
import clsx from "clsx";
import styles from "./LanguageSelectorOpenButton.module.scss";
import ArrowLeftSvg from "@images/arrow_left.svg?react";
import { useStore_IsOpenedLanguageSelector } from "@store";
import {
    useLanguageSettings,
} from "@logics_main";

export const LanguageSelectorOpenButton = ({ TurnedOnSvgComponent, is_turned_on, selector_key, target_key }) => {
    const { t } = useTranslation();
    const { updateIsOpenedLanguageSelector, currentIsOpenedLanguageSelector } = useStore_IsOpenedLanguageSelector();

    const {
        currentSelectedPresetTabNumber,
        currentSelectedYourLanguages,
        currentSelectedTargetLanguages,
    } = useLanguageSettings();

    const toggleSelector = () => {
        if (currentIsOpenedLanguageSelector.data[selector_key] === true && currentIsOpenedLanguageSelector.data.target_key === target_key) { // Close Language Selector
            updateIsOpenedLanguageSelector({ your_language: false, target_language: false, target_key: "1" });
        } else { // Open Language Selector
            updateIsOpenedLanguageSelector({
                your_language: selector_key === "your_language",
                target_language: selector_key === "target_language",
                target_key: target_key,
            });
        }
    };

    const arrow_class_names = clsx(styles.arrow_left_svg, {
        [styles.reverse]: (currentIsOpenedLanguageSelector.data[selector_key] === true && currentIsOpenedLanguageSelector.data.target_key === target_key),
    });

    const category_class_names = clsx(styles.category_svg, {
        [styles.is_turned_on]: is_turned_on,
    });

    const getVariable = (target_selector_key) => {
        if (target_selector_key === "your_language") return currentSelectedYourLanguages.data[currentSelectedPresetTabNumber.data];
        if (target_selector_key === "target_language") return currentSelectedTargetLanguages.data[currentSelectedPresetTabNumber.data];
    };

    const getTitle = (target_selector_key) => {
        if (target_selector_key === "your_language") return t("main_page.your_language");
        if (target_selector_key === "target_language") {
            if (currentSelectedTargetLanguages.data[currentSelectedPresetTabNumber.data]["2"].enable === false) return t("main_page.target_language");
            return `${t("main_page.target_language")} ${target_key}`;
        }
    };

    const title = getTitle(selector_key);

    if (getVariable(selector_key)[target_key].enable === false) return null;

    const language_text = getVariable(selector_key)[target_key].language ?? "Loading...";
    const country_text = getVariable(selector_key)[target_key].country ?? "Loading...";

    return (
        <div className={styles.container}>
            <div className={styles.title_container}>
                <TurnedOnSvgComponent className={category_class_names} />
                <p className={styles.title}>{title}</p>
            </div>
            <div className={styles.dropdown_menu_container} onClick={toggleSelector}>
                <p className={styles.selected_language}>{language_text}</p>
                <p className={styles.selected_language}>({country_text})</p>
                <ArrowLeftSvg className={arrow_class_names} />
            </div>
        </div>
    );
};