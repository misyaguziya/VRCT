import { useTranslation } from "react-i18next";
import styles from "./Device.module.scss";
import {
    DropdownMenuContainer,
    ThresholdContainer,
} from "../components/useSettingBox";
export const Device = () => {

    return (
        <>
            <DropdownMenuContainer_MicHost />
            {/* <DropdownMenuContainer_MicDevice /> */}
            <ThresholdContainer_Mic />
            <DropdownMenuContainer_SpeakerDevice />
            <ThresholdContainer_Speaker />
        </>
    );
};

import { useMicHostList } from "@logics_configs/useMicHostList";
import { useSelectedMicHost } from "@logics_configs/useSelectedMicHost";

import { useMicDeviceList } from "@logics_configs/useMicDeviceList";
import { useSelectedMicDevice } from "@logics_configs/useSelectedMicDevice";

import { LabelComponent } from "../components/label_component/LabelComponent";
import { DropdownMenu } from "../components/dropdown_menu/DropdownMenu";

const DropdownMenuContainer_MicHost = () => {
    const { t } = useTranslation();
    const { currentSelectedMicHost, setSelectedMicHost } = useSelectedMicHost();
    const { currentMicHostList, getMicHostList } = useMicHostList();

    const selectFunction_host = (selected_data) => {
        setSelectedMicHost(selected_data.selected_id);
    };

    const { currentSelectedMicDevice, setSelectedMicDevice } = useSelectedMicDevice();
    const { currentMicDeviceList, getMicDeviceList } = useMicDeviceList();

    const selectFunction_device = (selected_data) => {
        setSelectedMicDevice(selected_data.selected_id);
    };


    return (
        <div className={styles.device_container}>
            <LabelComponent label={t("config_page.mic_host.label")} />

            <div className={styles.device_contents}>
                <div className={styles.device_dropdown_wrapper}>
                    <p className={styles.device_dropdown_label}>Host/Driver</p>
                    <DropdownMenu
                        dropdown_id="mic_host"
                        selected_id={currentSelectedMicHost.data}
                        list={currentMicHostList.data}
                        selectFunction={selectFunction_host}
                        openListFunction={getMicHostList}
                        state={currentSelectedMicHost.state}
                        style={{ maxWidth: "20rem", minWidth: "10rem" }}
                    />
                </div>

                <div className={styles.device_dropdown_wrapper}>
                    <p className={styles.device_dropdown_label}>Device</p>
                    <DropdownMenu
                        dropdown_id="mic_device"
                        label={t("config_page.mic_device.label")}
                        selected_id={currentSelectedMicDevice.data}
                        list={currentMicDeviceList.data}
                        selectFunction={selectFunction_device}
                        openListFunction={getMicDeviceList}
                        state={currentSelectedMicDevice.state}
                    />
                </div>
            </div>
        </div>
    );
};

// import { useMicDeviceList } from "@logics_configs/useMicDeviceList";
// import { useSelectedMicDevice } from "@logics_configs/useSelectedMicDevice";
// const DropdownMenuContainer_MicDevice = () => {
//     const { t } = useTranslation();
//     const { currentSelectedMicDevice, setSelectedMicDevice } = useSelectedMicDevice();
//     const { currentMicDeviceList, getMicDeviceList } = useMicDeviceList();

//     const selectFunction = (selected_data) => {
//         setSelectedMicDevice(selected_data.selected_id);
//     };


//     return (
//         <DropdownMenuContainer
//             dropdown_id="mic_device"
//             label={t("config_page.mic_device.label")}
//             selected_id={currentSelectedMicDevice.data}
//             list={currentMicDeviceList.data}
//             selectFunction={selectFunction}
//             openListFunction={getMicDeviceList}
//             state={currentSelectedMicDevice.state}
//         />
//     );
// };

import { useSpeakerDeviceList } from "@logics_configs/useSpeakerDeviceList";
import { useSelectedSpeakerDevice } from "@logics_configs/useSelectedSpeakerDevice";
const DropdownMenuContainer_SpeakerDevice = () => {
    const { t } = useTranslation();
    const { currentSelectedSpeakerDevice, setSelectedSpeakerDevice } = useSelectedSpeakerDevice();
    const { currentSpeakerDeviceList, getSpeakerDeviceList } = useSpeakerDeviceList();

    const selectFunction = (selected_data) => {
        setSelectedSpeakerDevice(selected_data.selected_id);
    };


    return (
        <DropdownMenuContainer
            dropdown_id="speaker_device"
            label={t("config_page.speaker_device.label")}
            selected_id={currentSelectedSpeakerDevice.data}
            list={currentSpeakerDeviceList.data}
            selectFunction={selectFunction}
            openListFunction={getSpeakerDeviceList}
            state={currentSelectedSpeakerDevice.state}
        />
    );
};

const ThresholdContainer_Mic = () => {
    const { t } = useTranslation();

    return (
        <ThresholdContainer
            label={t("config_page.mic_dynamic_energy_threshold.label_for_manual")}
            desc={t("config_page.mic_dynamic_energy_threshold.desc_for_manual")}
            id="mic_threshold"
            min="0"
            max="2000"
        />
    );
};

const ThresholdContainer_Speaker = () => {
    const { t } = useTranslation();

    return (
        <ThresholdContainer
            label={t("config_page.speaker_dynamic_energy_threshold.label_for_manual")}
            desc={t("config_page.speaker_dynamic_energy_threshold.desc_for_manual")}
            id="speaker_threshold"
            min="0"
            max="4000"
        />
    );
};