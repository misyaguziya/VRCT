import { useTranslation } from "react-i18next";

import {
    useEnableAutoClearMessageInputBox,
    useSendMessageButtonType,
} from "@logics_configs";

import {
    CheckboxContainer,
    RadioButtonContainer,
} from "../_templates/Templates";


export const Others = () => {
    return (
        <>
            <AutoClearMessageInputBoxContainer />
            <SendMessageButtonTypeContainer />
        </>
    );
};

const AutoClearMessageInputBoxContainer = () => {
    const { t } = useTranslation();
    const { currentEnableAutoClearMessageInputBox, toggleEnableAutoClearMessageInputBox } = useEnableAutoClearMessageInputBox();

    return (
        <CheckboxContainer
            label={t("config_page.auto_clear_the_message_box.label")}
            variable={currentEnableAutoClearMessageInputBox}
            toggleFunction={toggleEnableAutoClearMessageInputBox}
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
            options={[
                { radio_button_id: "hide", label: t("config_page.send_message_button_type.hide") },
                { radio_button_id: "show", label: t("config_page.send_message_button_type.show") },
                { radio_button_id: "show_and_disable_enter_key", label: t("config_page.send_message_button_type.show_and_disable_enter_key") },
            ]}
            checked_variable={currentSendMessageButtonType}
        />
    );
};