import { useTranslation } from "react-i18next";
import styles from "./MainSection.module.scss";

import { TopBar } from "./top_bar/TopBar";
import { MessageContainer } from "./message_container/MessageContainer";
import { LanguageSelector } from "./language_selector/LanguageSelector";

import { useStore_IsOpenedLanguageSelector } from "@store";
import { useLanguageSettings } from "@logics_main";
import { useEffect } from "react";
import { SubtitleSystemContainer } from "./subtitle_system_container/SubtitleSystemContainer";

import { PluginHost } from "./PluginHost";

import { usePlugins } from "@logics_configs";

export const MainSection = () => {
    const { currentPluginsData } = usePlugins();

    const render_plugins = currentPluginsData.data.filter((plugin) => plugin.is_enabled && plugin.location === "main_section");

    return (
        <div className={styles.container}>
            <TopBar />
            {render_plugins.length
                ? <PluginHost render_components={render_plugins}/>
                : <MessageContainer />
            }
            <HandleLanguageSelector />
        </div>
    );
};


const HandleLanguageSelector = () => {
    const { t } = useTranslation();
    const { currentIsOpenedLanguageSelector, updateIsOpenedLanguageSelector } = useStore_IsOpenedLanguageSelector();
    const {
        currentSelectedPresetTabNumber,
        currentSelectedYourLanguages,
        setSelectedYourLanguages,
        currentSelectedTargetLanguages,
        setSelectedTargetLanguages,
    } = useLanguageSettings();

    useEffect(() => {
        updateIsOpenedLanguageSelector({
            your_language: false,
            target_language: false,
            target_key: "1"
        });

    }, [currentSelectedPresetTabNumber.data, currentSelectedYourLanguages.data, currentSelectedTargetLanguages.data]);

    const getTitle = (target_selector_key) => {
        if (target_selector_key === "your_language") return t("main_page.language_selector.title_your_language");
        if (target_selector_key === "target_language") {
            if (currentSelectedTargetLanguages.data[currentSelectedPresetTabNumber.data]["2"].enable === false) return t("main_page.language_selector.title_target_language");
            return `${t("main_page.language_selector.title_target_language")} (${currentIsOpenedLanguageSelector.data.target_key})`;
        }
    };



    if (currentIsOpenedLanguageSelector.data.your_language === true) {
        const onclickFunction_YourLanguage = (payload) => {
            updateIsOpenedLanguageSelector({ your_language: false, target_language: false, target_key: currentIsOpenedLanguageSelector.data.target_key });
            setSelectedYourLanguages({
                ...payload,
                target_key: currentIsOpenedLanguageSelector.data.target_key,
            });
        };
        const title = getTitle("your_language");
        return (
            <LanguageSelector
                title={title}
                onClickFunction={onclickFunction_YourLanguage}
            />
        );
    } else if (currentIsOpenedLanguageSelector.data.target_language === true) {
        const onclickFunction_TargetLanguage = (payload) => {
            updateIsOpenedLanguageSelector({ your_language: false, target_language: false, target_key: currentIsOpenedLanguageSelector.data.target_key });
            setSelectedTargetLanguages({
                ...payload,
                target_key: currentIsOpenedLanguageSelector.data.target_key,
            });
        };
        const title = getTitle("target_language");
        return (
            <LanguageSelector
                title={title}
                onClickFunction={onclickFunction_TargetLanguage}
            />
        );
    } else {
        return null;
    }
};