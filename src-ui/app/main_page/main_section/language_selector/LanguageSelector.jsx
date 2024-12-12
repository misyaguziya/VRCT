import { useTranslation } from "react-i18next";

import { useSelectableLanguageList } from "@logics_main";
import styles from "./LanguageSelector.module.scss";

import { LanguageSelectorTopBar } from "./language_selector_top_bar/LanguageSelectorTopBar";
export const LanguageSelector = ({ title, onClickFunction }) => {
    const { t } = useTranslation();
    const { currentSelectableLanguageList } = useSelectableLanguageList();

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
            <LanguageSelectorTopBar title={title}/>
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
            {languages.map((language_data, index) => (
                <LanguageButton key={index} onClickFunction={onClickFunction} language_data={language_data} />
            ))}
        </div>
    );
};

const LanguageButton = ({ onClickFunction, language_data }) => {

    const adjustedOnClickFunction = () => {
        onClickFunction({
            language: language_data.language,
            country: language_data.country,
        });
    };

    return (
        <div className={styles.language_button} onClick={adjustedOnClickFunction}>
            <p className={styles.language_label}>{language_data.language} ({language_data.country})</p>
        </div>
    );
};