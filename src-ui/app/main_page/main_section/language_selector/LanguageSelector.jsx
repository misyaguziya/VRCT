import { useTranslation } from "react-i18next";

import { useSelectableLanguageList } from "@logics_main";
import styles from "./LanguageSelector.module.scss";

import { LanguageSelectorTopBar } from "./language_selector_top_bar/LanguageSelectorTopBar";
export const LanguageSelector = ({ id, onClickFunction }) => {
    const { t } = useTranslation();
    const { currentSelectableLanguageList } = useSelectableLanguageList();

    const languageTitles = {
        your_language: t("main_page.language_selector.title_your_language"),
        target_language: t("main_page.language_selector.title_target_language")
    };

    const language_selector_title = languageTitles[id] || "";

    const groupLanguagesByFirstLetter = (languages) => {
        return languages.reduce((acc, { language, country }) => {
            const firstLetter = language[0].toUpperCase();
            if (!acc[firstLetter]) {
                acc[firstLetter] = [];
            }
            acc[firstLetter].push({ language, country });
            return acc;
        }, {});
    };

    const groupedLanguages = groupLanguagesByFirstLetter(currentSelectableLanguageList.data);

    return (
        <div className={styles.container}>
            <LanguageSelectorTopBar title={language_selector_title}/>
            <div className={styles.language_list_scroll_wrapper}>
                <div className={styles.language_list}>
                    {Object.entries(groupedLanguages).map(([letter, languages]) => (
                        <LanguageGroup key={letter} onClickFunction={onClickFunction} letter={letter} languages={languages} />
                    ))}
                </div>
            </div>
        </div>
    );
};

const LanguageGroup = ({ onClickFunction, letter, languages }) => {
    return (
        <div className={styles.language_each_letter_box}>
            <p className={styles.language_latter}>{letter}</p>
            {languages.map((languageData, index) => (
                <LanguageButton key={index} onClickFunction={onClickFunction} languageData={languageData} />
            ))}
        </div>
    );
};

const LanguageButton = ({ onClickFunction, languageData }) => {

    const adjustedOnClickFunction = () => {
        onClickFunction({
            language: languageData.language,
            country: languageData.country
        });
    };

    return (
        <div className={styles.language_button} onClick={adjustedOnClickFunction}>
            <p className={styles.language_label}>{languageData.language} ({languageData.country})</p>
        </div>
    );
};