import clsx from "clsx";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import styles from "./Appearance.module.scss";
import { useStore_SelectableFontFamilyList } from "@store";
import {
    useUiLanguage,
    useUiScaling,
    useMessageLogUiScaling,
    useSendMessageButtonType,
    useSelectedFontFamily,
    useTransparency,
} from "@logics_configs";

import {
    LabelComponent
} from "../_components/";

import {
    SliderContainer,
    DropdownMenuContainer,
    RadioButtonContainer,
} from "../_templates/Templates";

export const Appearance = () => {
    return (
        <>
            <UiLanguageContainer />
            <UiScalingContainer />
            <MessageLogUiScalingContainer />
            <SendMessageButtonTypeContainer />
            <FontFamilyContainer />
            <TransparencyContainer />
        </>
    );
};

const UiLanguageContainer = () => {
    const { t } = useTranslation();
    const { currentUiLanguage, setUiLanguage } = useUiLanguage();
    const SELECTABLE_UI_LANGUAGES_DICT = {
        en: "English",
        ja: "日本語",
        ko: "한국어",
        "zh-Hant": "繁體中文",
    };

    const is_not_en_lang = currentUiLanguage.data !== "en" && currentUiLanguage.data !== undefined;
    return (
        <div className={styles.ui_language_container}>
            <div className={styles.ui_language_label_wrapper}>
                {is_not_en_lang
                ?
                    <>
                        <LabelComponent label="UI Language" desc={t("config_page.ui_language.label")}/>
                    </>
                :
                    <LabelComponent label={t("config_page.ui_language.label")}/>
                }
            </div>
            <div className={styles.ui_language_selector_container}>
                {currentUiLanguage.state === "pending" && <span className={styles.loader}></span>}
                {Object.entries(SELECTABLE_UI_LANGUAGES_DICT).map(([key, value]) => (
                    <label key={key} className={clsx(styles.radio_button_wrapper, { [styles.is_selected]: currentUiLanguage.data === key } )}>
                        <input
                            className={styles.radio_button_input}
                            type="radio"
                            name="ui_language"
                            value={key}
                            onChange={() => setUiLanguage(key)}
                            checked={currentUiLanguage.data === key}
                        />
                        <p className={styles.radio_button_label}>{value}</p>
                    </label>
                ))}
            </div>
        </div>
    );
};

const UiScalingContainer = () => {
    const { t } = useTranslation();
    const { currentUiScaling, setUiScaling } = useUiScaling();
    const [ui_ui_scaling, setUiUiScaling] = useState(currentUiScaling.data);

    const onchangeFunction = (value) => {
        setUiUiScaling(value);
    };
    const onchangeCommittedFunction = (value) => {
        setUiScaling(value);
    };
    useEffect(() => {
        setUiUiScaling(currentUiScaling.data);
    }, [currentUiScaling.data]);

    const createMarks = (min, max) => {
        const marks = [];
        for (let value = min; value <= max; value += 10) {
            const label = ([50,70,130,140,160,170,190].includes(value)) ? "" : value;
            marks.push({ value, label: `${label}` });
        }
        return marks;
    };

    const marks = createMarks(40, 200);

    return (
        <SliderContainer
            label={t("config_page.ui_size.label") + " (%)"}
            min="40"
            max="200"
            onchangeCommittedFunction={onchangeCommittedFunction}
            onchangeFunction={onchangeFunction}
            variable={ui_ui_scaling}
            marks={marks}
            step={null}
            track={false}
        />
    );
};


const MessageLogUiScalingContainer = () => {
    const { t } = useTranslation();
    const { currentMessageLogUiScaling, setMessageLogUiScaling } = useMessageLogUiScaling();
    const [ui_message_log_ui_scaling, setUiMessageLogUiScaling] = useState(currentMessageLogUiScaling.data);

    const onchangeFunction = (value) => {
        setUiMessageLogUiScaling(value);
    };
    const onchangeCommittedFunction = (value) => {
        setMessageLogUiScaling(value);
    };
    useEffect(() => {
        setUiMessageLogUiScaling(currentMessageLogUiScaling.data);
    }, [currentMessageLogUiScaling.data]);

    const createMarks = (min, max) => {
        const marks = [];
        for (let value = min; value <= max; value += 10) {
            const label = ([50,70,130,140,160,170,190].includes(value)) ? "" : value;
            marks.push({ value, label: `${label}` });
        }
        return marks;
    };

    const marks = createMarks(40, 200);

    return (
        <SliderContainer
            label={t("config_page.textbox_ui_size.label") + " (%)"}
            min="40"
            max="200"
            onchangeCommittedFunction={onchangeCommittedFunction}
            onchangeFunction={onchangeFunction}
            variable={ui_message_log_ui_scaling}
            marks={marks}
            step={null}
            track={false}
        />
    );
};

const SendMessageButtonTypeContainer = () => {
    const { t } = useTranslation();
    const { currentSendMessageButtonType, setSendMessageButtonType } = useSendMessageButtonType();

    return (
        <RadioButtonContainer
            label={t("config_page.send_message_button_type.label")}
            selectFunction={setSendMessageButtonType}
            name="send_message_button_type"
            options={[
                { radio_button_id: "hide", label: t("config_page.send_message_button_type.hide") },
                { radio_button_id: "show", label: t("config_page.send_message_button_type.show") },
                { radio_button_id: "show_and_disable_enter_key", label: t("config_page.send_message_button_type.show_and_disable_enter_key") },
            ]}
            checked_variable={currentSendMessageButtonType}
        />
    );
};

const FontFamilyContainer = () => {
    const { t } = useTranslation();
    const { currentSelectedFontFamily, setSelectedFontFamily } = useSelectedFontFamily();

    const selectFunction = (selected_data) => {
        setSelectedFontFamily(selected_data.selected_id);
    };
    const { currentSelectableFontFamilyList } = useStore_SelectableFontFamilyList();

    return (
        <DropdownMenuContainer
            dropdown_id="font_family"
            label={t("config_page.font_family.label")}
            desc={t("config_page.font_family.label")}
            selected_id={currentSelectedFontFamily.data}
            list={currentSelectableFontFamilyList.data}
            selectFunction={selectFunction}
            state={currentSelectedFontFamily.state}
        />
    );
};

const TransparencyContainer = () => {
    const { t } = useTranslation();
    const { currentTransparency, setTransparency } = useTransparency();
    const [ui_message_log_ui_scaling, setUiTransparency] = useState(currentTransparency.data);

    const onchangeFunction = (value) => {
        setUiTransparency(value);
    };
    const onchangeCommittedFunction = (value) => {
        setTransparency(value);
    };
    useEffect(() => {
        setUiTransparency(currentTransparency.data);
    }, [currentTransparency.data]);

    const createMarks = (min, max) => {
        const marks = [];
        for (let value = min; value <= max; value += 10) {
            marks.push({ value, label: `${value}` });
        }
        return marks;
    };

    const marks = createMarks(40, 100);

    return (
        <SliderContainer
            label={t("config_page.transparency.label") + " (%)"}
            min="40"
            max="100"
            onchangeCommittedFunction={onchangeCommittedFunction}
            onchangeFunction={onchangeFunction}
            variable={ui_message_log_ui_scaling}
            marks={marks}
            step={null}
            track={false}
        />
    );
};