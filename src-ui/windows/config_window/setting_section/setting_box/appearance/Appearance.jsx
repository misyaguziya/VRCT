import { useTranslation } from "react-i18next";

import { useSettingBox } from "../components/useSettingBox";
import { useSelectedMicDeviceStatus, useMicDeviceListStatus } from "@store";
export const Appearance = () => {
    const { t } = useTranslation();
    const { currentSelectedMicDeviceStatus, updateSelectedMicDeviceStatus } = useSelectedMicDeviceStatus();
    const { currentMicDeviceListStatus } = useMicDeviceListStatus();
    const {
        DropdownMenuContainer,
        SliderContainer,
        CheckboxContainer,
        SwitchboxContainer,
        EntryContainer,
        ThresholdContainer,
        RadioButtonContainer,
        DeeplAuthKeyContainer,
        MessageFormatContainer,
    } = useSettingBox();

    const selectFunction = (selected_data) => {
        const asyncFunction = () => {
            return new Promise((resolve) => {
                setTimeout(() => {
                    resolve(selected_data.selected_id);
                }, 3000);
            });
        };
        updateSelectedMicDeviceStatus(asyncFunction);
    };

    return (
        <>
            <DropdownMenuContainer dropdown_id="mic_host" label="Mic Host/Driver" desc="description" selected_id="b" list={{a: "A", b: "B", c: "C"}} />
            <DropdownMenuContainer dropdown_id="mic_device" label="Mic Device" desc="description" selected_id={currentSelectedMicDeviceStatus.data} list={currentMicDeviceListStatus} selectFunction={selectFunction} state={currentSelectedMicDeviceStatus.state} />

            <SliderContainer label="Transparent" desc="description" min="0" max="3000"/>
            <CheckboxContainer label="Transparent" desc="description" checkbox_id="checkbox_id_1"/>
            <SwitchboxContainer label="Transparent" desc="description" switchbox_id="switchbox_id_1"/>

            <RadioButtonContainer label="Transparent" desc="description" switchbox_id="radiobutton_id_1"/>

            <EntryContainer width="20rem" label="Transparent" desc="description" switchbox_id="entry_id_1"/>

            <ThresholdContainer label="Transparent" desc="description" id="mic_threshold"  min="0" max="3000"/>

            <DeeplAuthKeyContainer label={t(`config_window.deepl_auth_key.label`)} desc={t(`config_window.deepl_auth_key.desc`)}/>


            <MessageFormatContainer label={t(`config_window.send_message_format.label`)} desc={t(`config_window.send_message_format.desc`)} id="send"/>

            <MessageFormatContainer label={t(`config_window.send_message_format_with_t.label`)} desc={t(`config_window.send_message_format_with_t.desc`)} id="send_with_t"/>


            <MessageFormatContainer label={t(`config_window.send_message_format.label`)} desc={t(`config_window.send_message_format.desc`)} id="received"/>

            <MessageFormatContainer label={t(`config_window.send_message_format_with_t.label`)} desc={t(`config_window.send_message_format_with_t.desc`)} id="received_with_t"/>

        </>
    );
};