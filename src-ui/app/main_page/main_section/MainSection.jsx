import styles from "./MainSection.module.scss";

import { TopBar } from "./top_bar/TopBar";
import { MessageContainer } from "./message_container/MessageContainer";
import { LanguageSelector } from "./language_selector/LanguageSelector";

import { useStore_IsOpenedLanguageSelector } from "@store";
import { useLanguageSettings } from "@logics_main";

export const MainSection = () => {

    return (
        <div className={styles.container}>
            <TopBar />
            <MessageContainer />
            <HandleLanguageSelector />
        </div>
    );
};


const HandleLanguageSelector = () => {
    const { currentIsOpenedLanguageSelector, updateIsOpenedLanguageSelector } = useStore_IsOpenedLanguageSelector();
    const {
        currentSelectedYourLanguages,
        setSelectedYourLanguages,
        currentSelectedTargetLanguages,
        setSelectedTargetLanguages,
    } = useLanguageSettings();

    if (currentIsOpenedLanguageSelector.data.your_language === true) {
        const onclickFunction_YourLanguage = (payload) => {
            updateIsOpenedLanguageSelector({ your_language: false, target_language: false });
            setSelectedYourLanguages(payload);
        };
        return (
            <LanguageSelector
                id="your_language"
                onClickFunction={onclickFunction_YourLanguage}
            />
        );
    } else if (currentIsOpenedLanguageSelector.data.target_language === true) {
        const onclickFunction_TargetLanguage = (payload) => {
            updateIsOpenedLanguageSelector({ your_language: false, target_language: false });
            setSelectedTargetLanguages(payload);
        };
        return (
            <LanguageSelector
                id="target_language"
                onClickFunction={onclickFunction_TargetLanguage}
            />
        );
    } else {
        return null;
    }
};