import clsx from "clsx";
import { useTranslation } from "react-i18next";
import styles from "./Device.module.scss";
import {
    useEnableAutoMicSelect,
    useMicHostList,
    useSelectedMicHost,
    useMicDeviceList,
    useSelectedMicDevice,
    useMicThreshold,
    useEnableAutoSpeakerSelect,
    useSpeakerDeviceList,
    useSelectedSpeakerDevice,
    useSpeakerThreshold,
} from "@logics_configs";
import {
    useOnMouseLeaveDropdownMenu,
} from "../components/useSettingBox";
import { LabelComponent } from "../components/label_component/LabelComponent";
import { DropdownMenu } from "../components/dropdown_menu/DropdownMenu";
import { ThresholdComponent } from "../components/threshold_component/ThresholdComponent";
import { Switchbox } from "../components/switchbox/Switchbox";

export const Device = () => {
    return (
        <>
            <Mic_Container />
            <Speaker_Container />
        </>
    );
};

const Mic_Container = () => {
    const { t } = useTranslation();
    const { currentEnableAutoMicSelect, toggleEnableAutoMicSelect } = useEnableAutoMicSelect();
    const { currentSelectedMicHost, setSelectedMicHost } = useSelectedMicHost();
    const { currentMicHostList } = useMicHostList();
    const { onMouseLeaveFunction } = useOnMouseLeaveDropdownMenu();
    const { currentEnableAutomaticMicThreshold, toggleEnableAutomaticMicThreshold } = useMicThreshold();


    const selectFunction_host = (selected_data) => {
        setSelectedMicHost(selected_data.selected_id);
    };

    const is_disabled_selector = currentEnableAutoMicSelect.data === true || currentEnableAutoMicSelect.data === "pending";

    const { currentSelectedMicDevice, setSelectedMicDevice } = useSelectedMicDevice();
    const { currentMicDeviceList } = useMicDeviceList();

    const selectFunction_device = (selected_data) => {
        setSelectedMicDevice(selected_data.selected_id);
    };

    const getLabels = () => {
        if (currentEnableAutomaticMicThreshold.data === true) {
            return {
                label: t("config_page.mic_dynamic_energy_threshold.label_for_automatic"),
                desc: t("config_page.mic_dynamic_energy_threshold.desc_for_automatic"),
            };
        } else {
            return {
                label: t("config_page.mic_dynamic_energy_threshold.label_for_manual"),
                desc: t("config_page.mic_dynamic_energy_threshold.desc_for_manual"),
            };
        }
    };

    return (
        <div className={styles.mic_container}>
            <div className={styles.device_container} onMouseLeave={onMouseLeaveFunction}>
                <LabelComponent label={t("config_page.mic_host_device.label")} />
                <div className={styles.device_contents}>

                    <div className={styles.device_auto_select_wrapper}>
                        <p className={styles.device_secondary_label}>{t("config_page.mic_host_device.label_auto_select")}</p>
                        <Switchbox
                            variable={currentEnableAutoMicSelect}
                            toggleFunction={toggleEnableAutoMicSelect}
                        />
                    </div>

                    <div className={styles.device_dropdown_wrapper}>
                        <div className={styles.device_dropdown}>
                            <p className={styles.device_secondary_label}>{t("config_page.mic_host_device.label_host")}</p>
                            <DropdownMenu
                                dropdown_id="mic_host"
                                selected_id={currentSelectedMicHost.data}
                                list={currentMicHostList.data}
                                selectFunction={selectFunction_host}
                                state={currentSelectedMicHost.state}
                                style={{ maxWidth: "20rem", minWidth: "10rem" }}
                                is_disabled={is_disabled_selector}
                            />
                        </div>

                        <div className={styles.device_dropdown}>
                            <p className={styles.device_secondary_label}>{t("config_page.mic_host_device.label_device")}</p>
                            <DropdownMenu
                                dropdown_id="mic_device"
                                selected_id={currentSelectedMicDevice.data}
                                list={currentMicDeviceList.data}
                                selectFunction={selectFunction_device}
                                state={currentSelectedMicDevice.state}
                                is_disabled={is_disabled_selector}
                            />
                        </div>
                    </div>
                </div>
            </div>
            <div className={styles.threshold_container}>
                <div className={styles.threshold_switch_section}>
                    <LabelComponent {...getLabels()} />
                    <Switchbox
                        variable={currentEnableAutomaticMicThreshold}
                        toggleFunction={toggleEnableAutomaticMicThreshold}
                    />
                </div>
                <div className={styles.threshold_section}>
                    <ThresholdComponent
                        id="mic_threshold"
                        min="0"
                        max="2000"
                    />
                </div>
            </div>
        </div>
    );
};

const Speaker_Container = () => {
    const { t } = useTranslation();
    const { currentEnableAutoSpeakerSelect, toggleEnableAutoSpeakerSelect } = useEnableAutoSpeakerSelect();
    const { currentSelectedSpeakerDevice, setSelectedSpeakerDevice } = useSelectedSpeakerDevice();
    const { currentSpeakerDeviceList } = useSpeakerDeviceList();
    const { onMouseLeaveFunction } = useOnMouseLeaveDropdownMenu();
    const { currentEnableAutomaticSpeakerThreshold, toggleEnableAutomaticSpeakerThreshold } = useSpeakerThreshold();

    const selectFunction = (selected_data) => {
        setSelectedSpeakerDevice(selected_data.selected_id);
    };

    const is_disabled_selector = currentEnableAutoSpeakerSelect.data === true || currentEnableAutoSpeakerSelect.data === "pending";

    const getLabels = () => {
        if (currentEnableAutomaticSpeakerThreshold.data === true) {
            return {
                label: t("config_page.speaker_dynamic_energy_threshold.label_for_automatic"),
                desc: t("config_page.speaker_dynamic_energy_threshold.desc_for_automatic"),
            };
        } else {
            return {
                label: t("config_page.speaker_dynamic_energy_threshold.label_for_manual"),
                desc: t("config_page.speaker_dynamic_energy_threshold.desc_for_manual"),
            };
        }

    };

    return (
        <div className={styles.speaker_container}>
            <div className={styles.device_container} onMouseLeave={onMouseLeaveFunction}>
                <LabelComponent label={t("config_page.speaker_device.label")} />
                <div className={styles.device_contents}>

                    <div className={styles.device_auto_select_wrapper}>
                        <p className={styles.device_secondary_label}>{t("config_page.speaker_device.label_auto_select")}</p>
                        <Switchbox
                            variable={currentEnableAutoSpeakerSelect}
                            toggleFunction={toggleEnableAutoSpeakerSelect}
                        />
                    </div>

                    <div className={styles.device_dropdown}>
                        <p className={styles.device_secondary_label}>{t("config_page.mic_host_device.label_device")}</p>
                        <DropdownMenu
                            dropdown_id="speaker_device"
                            label={t("config_page.speaker_device.label")}
                            selected_id={currentSelectedSpeakerDevice.data}
                            list={currentSpeakerDeviceList.data}
                            selectFunction={selectFunction}
                            state={currentSelectedSpeakerDevice.state}
                            is_disabled={is_disabled_selector}
                        />
                    </div>
                </div>
            </div>
            <div className={styles.threshold_container}>
                <div className={styles.threshold_switch_section}>
                    <LabelComponent {...getLabels()}/>
                    <Switchbox
                        variable={currentEnableAutomaticSpeakerThreshold}
                        toggleFunction={toggleEnableAutomaticSpeakerThreshold}
                    />
                </div>
                <div className={styles.threshold_section}>
                    <ThresholdComponent
                        id="speaker_threshold"
                        min="0"
                        max="4000"
                    />
                </div>
            </div>
        </div>
    );
};