import { useTranslation } from "react-i18next";
import FolderOpenSvg from "@images/folder_open.svg?react";

import { useSettingBox } from "../components/useSettingBox";
import { useStore_SelectedMicDevice, useStore_MicDeviceList } from "@store";
export const Appearance = () => {
    const { t } = useTranslation();
    const { currentSelectedMicDevice, updateSelectedMicDevice } = useStore_SelectedMicDevice();
    const { currentMicDeviceList } = useStore_MicDeviceList();
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
        WordFilterContainer,
        ActionButtonContainer,
    } = useSettingBox();

    const selectFunction = (selected_data) => {
        const asyncFunction = () => {
            return new Promise((resolve) => {
                setTimeout(() => {
                    resolve(selected_data.selected_id);
                }, 3000);
            });
        };
        updateSelectedMicDevice(asyncFunction);
    };

    return (
        <>
            <DropdownMenuContainer dropdown_id="mic_host" label="Mic Host/Driver" desc="description" selected_id="b" list={{a: "A", b: "B", c: "C"}} />
            <DropdownMenuContainer dropdown_id="mic_device" label="Mic Device" desc="description" selected_id={currentSelectedMicDevice.data} list={currentMicDeviceList} selectFunction={selectFunction} state={currentSelectedMicDevice.state} />

            <SliderContainer label="Transparent" desc="description" min="0" max="3000"/>
            <CheckboxContainer label="Transparent" desc="description" checkbox_id="checkbox_id_1"/>
            <SwitchboxContainer label="Transparent" desc="description" switchbox_id="switchbox_id_1"/>

            <RadioButtonContainer label="Transparent" desc="description" switchbox_id="radiobutton_id_1"/>

            <EntryContainer width="20rem" label="Transparent" desc="description" switchbox_id="entry_id_1"/>

            <ThresholdContainer label="Transparent" desc="description" id="mic_threshold"  min="0" max="3000"/>

            <DeeplAuthKeyContainer label={t(`config_page.deepl_auth_key.label`)} desc={t(`config_page.deepl_auth_key.desc`)}/>


            <MessageFormatContainer label={t(`config_page.send_message_format.label`)} desc={t(`config_page.send_message_format.desc`)} id="send"/>

            <MessageFormatContainer label={t(`config_page.send_message_format_with_t.label`)} desc={t(`config_page.send_message_format_with_t.desc`)} id="send_with_t"/>


            <MessageFormatContainer label={t(`config_page.send_message_format.label`)} desc={t(`config_page.send_message_format.desc`)} id="received"/>

            <MessageFormatContainer label={t(`config_page.send_message_format_with_t.label`)} desc={t(`config_page.send_message_format_with_t.desc`)} id="received_with_t"/>

            <WordFilterContainer label={t(`config_page.mic_word_filter.label`)} desc={t(`config_page.mic_word_filter.desc`)}/>

            <ActionButtonContainer label={t(`config_page.open_config_filepath.label`)} IconComponent={FolderOpenSvg} OnclickFunction={()=>{}}/>

        </>
    );
};