import { useTranslation } from "react-i18next";
import { useSettingBox } from "../components/useSettingBox";
import { useConfig } from "@logics/useConfig";

export const Others = () => {
    const { t } = useTranslation();
    const {
        CheckboxContainer,
        RadioButtonContainer,
    } = useSettingBox();

    const { currentEnableAutoClearMessageBox, toggleEnableAutoClearMessageBox } = useConfig();
    const { currentSendMessageButtonType, setSendMessageButtonType } = useConfig();


    return (
        <>
            <CheckboxContainer
                label={t("config_page.auto_clear_the_message_box.label")}
                variable={currentEnableAutoClearMessageBox}
                toggleFunction={toggleEnableAutoClearMessageBox}
            />

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
        </>
    );
};