import { useTranslation } from "react-i18next";
import { useSettingBox } from "../components/useSettingBox";
import {
    useMicHostList,
    useSelectedMicHost,
    useSelectedMicDevice,
    useMicDeviceList,
    useSelectedSpeakerDevice,
    useSpeakerDeviceList,
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

    const { currentSpeakerDeviceList } = useSpeakerDeviceList();
    const { currentSelectedSpeakerDevice } = useSelectedSpeakerDevice();

    const {
        setSelectedMicHost,
        setSelectedMicDevice,
        getMicHostList,
        getMicDeviceList,
        setSelectedSpeakerDevice,
        getSpeakerDeviceList,
    } = useConfig();

    const selectFunction = (selected_data) => {
        switch (selected_data.dropdown_id) {
            case "mic_host":
                setSelectedMicHost(selected_data.selected_id);
                break;

            case "mic_device":
                setSelectedMicDevice(selected_data.selected_id);
                break;

            case "speaker_device":
                setSelectedSpeakerDevice(selected_data.selected_id);
                break;

            default:
                break;
        }
    };

    // const volumeCheckStartFunction_Mic = () => {
    //     volumeCheckStart_Mic();
    // };
    // const volumeCheckStopFunction_Mic = () => {
    //     volumeCheckStop_Mic();
    // };


    return (
        <>
            <DropdownMenuContainer
                dropdown_id="mic_host"
                label={t("config_page.mic_host.label")}
                selected_id={currentSelectedMicHost.data}
                list={currentMicHostList.data}
                selectFunction={selectFunction}
                openListFunction={getMicHostList}
                state={currentSelectedMicHost.state}
            />

            <DropdownMenuContainer
                dropdown_id="mic_device"
                label={t("config_page.mic_device.label")}
                selected_id={currentSelectedMicDevice.data}
                list={currentMicDeviceList.data}
                selectFunction={selectFunction}
                openListFunction={getMicDeviceList}
                state={currentSelectedMicDevice.state}
            />

            <ThresholdContainer
                label={t("config_page.mic_dynamic_energy_threshold.label_for_manual")}
                desc={t("config_page.mic_dynamic_energy_threshold.desc_for_manual")}
                id="mic_threshold"
                min="0"
                max="2000"
                // volumeCheckStartFunction={volumeCheckStartFunction_Mic}
                // volumeCheckStopFunction={volumeCheckStopFunction_Mic}
            />


            <DropdownMenuContainer
                dropdown_id="speaker_device"
                label={t("config_page.speaker_device.label")}
                selected_id={currentSelectedSpeakerDevice.data}
                list={currentSpeakerDeviceList.data}
                selectFunction={selectFunction}
                openListFunction={getSpeakerDeviceList}
                state={currentSelectedSpeakerDevice.state}
            />

            <ThresholdContainer
                label={t("config_page.speaker_dynamic_energy_threshold.label_for_manual")}
                desc={t("config_page.speaker_dynamic_energy_threshold.desc_for_manual")}
                id="speaker_threshold"
                min="0"
                max="4000"
            />
        </>
    );
};