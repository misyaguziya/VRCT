import styles from "./MainSection.module.scss";

import { TopBar } from "./top_bar/TopBar";
import { MessageContainer } from "./message_container/MessageContainer";
import { LanguageSelector } from "./language_selector/LanguageSelector";

import { useStore_IsOpenedLanguageSelector } from "@store";

export const MainSection = () => {

    return (
        <div className={styles.container}>
            <TopBar />
            <MessageContainer />
            <HandleLanguageSelector />
        </div>
    );
};


import { useLanguageSettings } from "@logics/useLanguageSettings";
const HandleLanguageSelector = () => {
    const { currentIsOpenedLanguageSelector } = useStore_IsOpenedLanguageSelector();
    const {
        currentSelectedYourLanguages,
        setSelectedYourLanguages,
        currentSelectedTargetLanguages,
        setSelectedTargetLanguages,
    } = useLanguageSettings();

    if (currentIsOpenedLanguageSelector.your_language === true) {
        const onclickFunction_YourLanguage = (payload) => setSelectedYourLanguages(payload);
        return <LanguageSelector id="your_language" onClickFunction={onclickFunction_YourLanguage}/>;
    } else if (currentIsOpenedLanguageSelector.target_language === true) {
        const onclickFunction_TargetLanguage = (payload) => setSelectedTargetLanguages(payload);
        return <LanguageSelector id="target_language" onClickFunction={onclickFunction_TargetLanguage}/>;
    } else {
        return null;
    }
};