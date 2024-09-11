import { useTranslation } from "react-i18next";
import styles from "./Device.module.scss";
import {
    ThresholdContainer,
} from "../components/useSettingBox";
export const Device = () => {
    return (
        <>
            <Mic_Container />
            <Speaker_Container />
        </>
    );
};

import { useMicHostList } from "@logics_configs/useMicHostList";
import { useSelectedMicHost } from "@logics_configs/useSelectedMicHost";

import { useMicDeviceList } from "@logics_configs/useMicDeviceList";
import { useSelectedMicDevice } from "@logics_configs/useSelectedMicDevice";

import { LabelComponent } from "../components/label_component/LabelComponent";
import { DropdownMenu } from "../components/dropdown_menu/DropdownMenu";

const Mic_Container = () => {
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
        <div className={styles.mic_container}>
            <div className={styles.device_container}>
                <LabelComponent label={t("config_page.mic_host_device.label")} />
                <div className={styles.device_contents}>
                    <div className={styles.device_dropdown_wrapper}>
                        <p className={styles.device_dropdown_label}>{t("config_page.mic_host_device.label_host")}</p>
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
                        <p className={styles.device_dropdown_label}>{t("config_page.mic_host_device.label_device")}</p>
                        <DropdownMenu
                            dropdown_id="mic_device"
                            selected_id={currentSelectedMicDevice.data}
                            list={currentMicDeviceList.data}
                            selectFunction={selectFunction_device}
                            openListFunction={getMicDeviceList}
                            state={currentSelectedMicDevice.state}
                        />
                    </div>
                </div>
            </div>
            <div className={styles.threshold_container}>
                <ThresholdContainer
                    label={t("config_page.mic_dynamic_energy_threshold.label_for_manual")}
                    desc={t("config_page.mic_dynamic_energy_threshold.desc_for_manual")}
                    id="mic_threshold"
                    min="0"
                    max="2000"
                />
            </div>
        </div>
    );
};

import { useSpeakerDeviceList } from "@logics_configs/useSpeakerDeviceList";
import { useSelectedSpeakerDevice } from "@logics_configs/useSelectedSpeakerDevice";
const Speaker_Container = () => {
    const { t } = useTranslation();
    const { currentSelectedSpeakerDevice, setSelectedSpeakerDevice } = useSelectedSpeakerDevice();
    const { currentSpeakerDeviceList, getSpeakerDeviceList } = useSpeakerDeviceList();

    const selectFunction = (selected_data) => {
        setSelectedSpeakerDevice(selected_data.selected_id);
    };


    return (
        <div className={styles.speaker_container}>
            <div className={styles.device_container}>
                <LabelComponent label={t("config_page.speaker_device.label")} />
                <div className={styles.device_contents}>
                    <div className={styles.device_dropdown_wrapper}>
                        <DropdownMenu
                            dropdown_id="speaker_device"
                            label={t("config_page.speaker_device.label")}
                            selected_id={currentSelectedSpeakerDevice.data}
                            list={currentSpeakerDeviceList.data}
                            selectFunction={selectFunction}
                            openListFunction={getSpeakerDeviceList}
                            state={currentSelectedSpeakerDevice.state}
                        />
                    </div>
                </div>
            </div>
            <div className={styles.threshold_container}>
                <ThresholdContainer
                    label={t("config_page.speaker_dynamic_energy_threshold.label_for_manual")}
                    desc={t("config_page.speaker_dynamic_energy_threshold.desc_for_manual")}
                    id="speaker_threshold"
                    min="0"
                    max="4000"
                />
            </div>
        </div>
    );
};