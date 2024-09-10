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

const HandleLanguageSelector = () => {
    const { currentIsOpenedLanguageSelector } = useStore_IsOpenedLanguageSelector();

    if (currentIsOpenedLanguageSelector.your_language === true) {
        return <LanguageSelector id="your_language"/>;
    } else if (currentIsOpenedLanguageSelector.target_language === true) {
        return <LanguageSelector id="target_language"/>;
    } else {
        return null;
    }
};