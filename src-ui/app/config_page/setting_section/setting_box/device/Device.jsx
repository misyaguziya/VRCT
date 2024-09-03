import { useTranslation } from "react-i18next";
import FolderOpenSvg from "@images/folder_open.svg?react";

import { useSettingBox } from "../components/useSettingBox";
import {
    useMicHostList,
    useSelectedMicHost,
    useSelectedMicDevice,
    useMicDeviceList,
} from "@store";

import { useConfig } from "@logics/useConfig";

export const Device = () => {
    const { t } = useTranslation();
    const {
        DropdownMenuContainer,
        ThresholdContainer,
    } = useSettingBox();


    const { currentMicHostList } = useMicHostList();
    const { currentSelectedMicHost } = useSelectedMicHost();

    const { currentMicDeviceList } = useMicDeviceList();
    const { currentSelectedMicDevice } = useSelectedMicDevice();

    const {
        setSelectedMicHost,
        setSelectedMicDevice,
    } = useConfig();

    const selectFunction = (selected_data) => {
        switch (selected_data.dropdown_id) {
            case "mic_host":
                setSelectedMicHost(selected_data.selected_id);
                break;

            case "mic_device":
                setSelectedMicDevice(selected_data.selected_id);
                break;

            default:
                break;
        }
    };


    return (
        <>
            <DropdownMenuContainer
                dropdown_id="mic_host"
                label={t("config_page.mic_host.label")}
                selected_id={currentSelectedMicHost.data}
                list={currentMicHostList.data}
                selectFunction={selectFunction}
                state={currentSelectedMicHost.state}
            />

            <DropdownMenuContainer
                dropdown_id="mic_device"
                label={t("config_page.mic_device.label")}
                selected_id={currentSelectedMicDevice.data}
                list={currentMicDeviceList.data}
                selectFunction={selectFunction}
                state={currentSelectedMicDevice.state}
            />
{/*
            <ThresholdContainer label={t("config_page.mic_dynamic_energy_threshold.label_for_manual")} desc={t("config_page.mic_dynamic_energy_threshold.desc_for_manual")} id="mic_threshold"  min="0" max="3000"/>


            <DropdownMenuContainer dropdown_id="speaker_device" label={t("config_page.speaker_device.label")}  selected_id={currentSelectedMicDevice.data} list={currentMicDeviceList} selectFunction={selectFunction} state={currentSelectedMicDevice.state} />

            <ThresholdContainer label={t("config_page.speaker_dynamic_energy_threshold.label_for_manual")} desc={t("config_page.speaker_dynamic_energy_threshold.desc_for_manual")} id="speaker_threshold"  min="0" max="3000"/> */}
        </>
    );
};