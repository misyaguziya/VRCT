import clsx from "clsx";
import { useEffect, useState } from "react";
import { useI18n } from "@useI18n";
import styles from "./Appearance.module.scss";
import { ui_configs } from "@ui_configs";
import { useStore_SelectableFontFamilyList } from "@store";

import {
    useWindow,
} from "@logics_common";

import {
    useAppearance,
} from "@logics_configs";

import {
    SliderContainer,
    DropdownMenuContainer,
    RadioButtonContainer,
    CheckboxContainer,
} from "../_templates/Templates";

export const Appearance = () => {
    return (
        <>
            <UiLanguageContainer />
            <UiScalingContainer />
            <MessageLogUiScalingContainer />
            <SendMessageButtonTypeContainer />
            <ShowResendButtonContainer />
            <FontFamilyContainer />
            <TransparencyContainer />
        </>
    );
};

const UiLanguageContainer = () => {
    const { t } = useI18n();
    const { currentUiLanguage, setUiLanguage } = useAppearance();

    const is_not_en_lang = currentUiLanguage.data !== "en" && currentUiLanguage.data !== undefined;
    return (
        <RadioButtonContainer
            label={is_not_en_lang ? "UI Language" : t("config_page.appearance.ui_language.label")}
            desc={is_not_en_lang ? t("config_page.appearance.ui_language.label") : false}
            selectFunction={setUiLanguage}
            name="ui_language"
            options={ui_configs.selectable_ui_languages}
            checked_variable={currentUiLanguage}
        />
    );
};

const UiScalingContainer = () => {
    const { t } = useI18n();
    const { currentUiScaling, setUiScaling } = useAppearance();
    const { asyncUpdateBreakPoint } = useWindow();

    const [ui_ui_scaling, setUiUiScaling] = useState(currentUiScaling.data);

    const onchangeFunction = (value) => {
        setUiUiScaling(value);
    };
    const onchangeCommittedFunction = (value) => {
        setUiScaling(value);
    };
    useEffect(() => {
        setUiUiScaling(currentUiScaling.data);
        asyncUpdateBreakPoint();
    }, [currentUiScaling.data]);

    // [Duplicated]
    const createMarks = (min, max) => {
        const marks = [];
        for (let value = min; value <= max; value += 10) {
            const label = ([50,70,90,110,130,150,170,190].includes(value)) ? "" : value;
            marks.push({ value, label: `${label}` });
        }
        return marks;
    };

    const marks = createMarks(40, 200);

    return (
        <SliderContainer
            label={t("config_page.appearance.ui_size.label") + " (%)"}
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


export const MessageLogUiScalingContainer = () => {
    const { t } = useI18n();
    const { currentMessageLogUiScaling, setMessageLogUiScaling } = useAppearance();
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

    // [Duplicated]
    const createMarks = (min, max) => {
        const marks = [];
        for (let value = min; value <= max; value += 10) {
            const label = ([50,70,90,110,130,150,170,190].includes(value)) ? "" : value;
            marks.push({ value, label: `${label}` });
        }
        return marks;
    };

    const marks = createMarks(40, 200);

    return (
        <SliderContainer
            label={t("config_page.appearance.textbox_ui_size.label") + " (%)"}
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
    const { t } = useI18n();
    const { currentSendMessageButtonType, setSendMessageButtonType } = useAppearance();

    return (
        <RadioButtonContainer
            label={t("config_page.appearance.send_message_button_type.label")}
            selectFunction={setSendMessageButtonType}
            name="send_message_button_type"
            options={[
                { id: "hide", label: t("config_page.appearance.send_message_button_type.hide") },
                { id: "show", label: t("config_page.appearance.send_message_button_type.show") },
                { id: "show_and_disable_enter_key", label: t("config_page.appearance.send_message_button_type.show_and_disable_enter_key") },
            ]}
            checked_variable={currentSendMessageButtonType}
            column={true}
        />
    );
};

const ShowResendButtonContainer = () => {
    const { t } = useI18n();
    const { currentShowResendButton, toggleShowResendButton } = useAppearance();

    return (
        <CheckboxContainer
            label={t("config_page.appearance.show_resend_button.label")}
            desc={t("config_page.appearance.show_resend_button.desc")}
            variable={currentShowResendButton}
            toggleFunction={toggleShowResendButton}
        />
    );
};

const FontFamilyContainer = () => {
    const { t } = useI18n();
    const { currentSelectedFontFamily, setSelectedFontFamily } = useAppearance();

    const selectFunction = (selected_data) => {
        setSelectedFontFamily(selected_data.selected_id);
    };
    const { currentSelectableFontFamilyList } = useStore_SelectableFontFamilyList();

    return (
        <DropdownMenuContainer
            dropdown_id="font_family"
            label={t("config_page.appearance.font_family.label")}
            selected_id={currentSelectedFontFamily.data}
            list={currentSelectableFontFamilyList.data}
            selectFunction={selectFunction}
            state={currentSelectedFontFamily.state}
        />
    );
};

const TransparencyContainer = () => {
    const { t } = useI18n();
    const { currentTransparency, setTransparency } = useAppearance();
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

    // [Duplicated]
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
            label={t("config_page.appearance.transparency.label") + " (%)"}
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