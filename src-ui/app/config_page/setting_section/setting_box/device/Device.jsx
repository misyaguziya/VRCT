import { useI18n } from "@useI18n";
import styles from "./Device.module.scss";
import clsx from "clsx";
import { useStore_IsBreakPoint } from "@store";
import { ui_configs } from "@ui_configs";
import {
    useDevice,
} from "@logics_configs";

import {
    useOnMouseLeaveDropdownMenu,
} from "../_templates/Templates";

import {
    LabelComponent,
    DropdownMenu,
    ThresholdComponent,
    SwitchBox,
} from "../_components/";

export const Device = () => {
    return (
        <>
            <Mic_Container />
            <Speaker_Container />
        </>
    );
};

const Mic_Container = () => {
    const { t } = useI18n();
    const {
        currentEnableAutoMicSelect,
        toggleEnableAutoMicSelect,
        currentMicDeviceList,
        currentMicHostList,

        currentSelectedMicHost,
        setSelectedMicHost,
        currentSelectedMicDevice,
        setSelectedMicDevice,

        currentEnableAutomaticMicThreshold,
        toggleEnableAutomaticMicThreshold,
    } = useDevice();
    const { onMouseLeaveFunction } = useOnMouseLeaveDropdownMenu();

    const selectFunction_host = (selected_data) => {
        setSelectedMicHost(selected_data.selected_id);
    };

    const selectFunction_device = (selected_data) => {
        setSelectedMicDevice(selected_data.selected_id);
    };

    // [Fix me] currentEnableAutoMicSelect.data === "pending"; ?  not currentEnableAutoMicSelect.state === "pending"; ??(.state)
    const is_disabled_selector = currentEnableAutoMicSelect.data === true || currentEnableAutoMicSelect.data === "pending";

    const getLabels = () => {
        if (currentEnableAutomaticMicThreshold.data === true) {
            return {
                label: t("config_page.device.mic_dynamic_energy_threshold.label_for_automatic"),
                desc: t("config_page.device.mic_dynamic_energy_threshold.desc_for_automatic"),
            };
        } else {
            return {
                label: t("config_page.device.mic_dynamic_energy_threshold.label_for_manual"),
                desc: t("config_page.device.mic_dynamic_energy_threshold.desc_for_manual"),
            };
        }
    };

    const { currentIsBreakPoint } = useStore_IsBreakPoint();
    const device_container_class = clsx(styles.device_container, {
        [styles.is_break_point]: currentIsBreakPoint.data,
    });

    return (
        <div className={styles.mic_container}>
            <div className={device_container_class} onMouseLeave={onMouseLeaveFunction}>
                <LabelComponent label={t("config_page.device.mic_host_device.label")} />
                <div className={styles.device_contents}>

                    <div className={styles.device_auto_select_wrapper}>
                        <p className={styles.device_secondary_label}>{t("config_page.device.label_auto_select")}</p>
                        <SwitchBox
                            variable={currentEnableAutoMicSelect}
                            toggleFunction={toggleEnableAutoMicSelect}
                        />
                    </div>

                    <div className={styles.device_dropdown_wrapper}>
                        <div className={styles.device_dropdown}>
                            <p className={styles.device_secondary_label}>{t("config_page.device.label_host")}</p>
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
                            <p className={styles.device_secondary_label}>{t("config_page.device.label_device")}</p>
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
                    <SwitchBox
                        variable={currentEnableAutomaticMicThreshold}
                        toggleFunction={toggleEnableAutomaticMicThreshold}
                    />
                </div>
                <div className={styles.threshold_section}>
                    <ThresholdComponent
                        id="mic_threshold"
                        min={ui_configs.mic_threshold_min}
                        max={ui_configs.mic_threshold_max}
                    />
                </div>
            </div>
        </div>
    );
};

const Speaker_Container = () => {
    const { t } = useI18n();
    const {
        currentEnableAutoSpeakerSelect,
        toggleEnableAutoSpeakerSelect,
        currentSpeakerDeviceList,
        currentSelectedSpeakerDevice,
        setSelectedSpeakerDevice,
        currentEnableAutomaticSpeakerThreshold,
        toggleEnableAutomaticSpeakerThreshold,
    } = useDevice();
    const { onMouseLeaveFunction } = useOnMouseLeaveDropdownMenu();

    const selectFunction = (selected_data) => {
        setSelectedSpeakerDevice(selected_data.selected_id);
    };

    const is_disabled_selector = currentEnableAutoSpeakerSelect.data === true || currentEnableAutoSpeakerSelect.data === "pending";

    const getLabels = () => {
        if (currentEnableAutomaticSpeakerThreshold.data === true) {
            return {
                label: t("config_page.device.speaker_dynamic_energy_threshold.label_for_automatic"),
                desc: t("config_page.device.speaker_dynamic_energy_threshold.desc_for_automatic"),
            };
        } else {
            return {
                label: t("config_page.device.speaker_dynamic_energy_threshold.label_for_manual"),
                desc: t("config_page.device.speaker_dynamic_energy_threshold.desc_for_manual"),
            };
        }

    };

    const { currentIsBreakPoint } = useStore_IsBreakPoint();
    const device_container_class = clsx(styles.device_container, {
        [styles.is_break_point]: currentIsBreakPoint.data,
    });

    return (
        <div className={styles.speaker_container}>
            <div className={device_container_class} onMouseLeave={onMouseLeaveFunction}>
                <LabelComponent label={t("config_page.device.speaker_device.label")} />
                <div className={styles.device_contents}>

                    <div className={styles.device_auto_select_wrapper}>
                        <p className={styles.device_secondary_label}>{t("config_page.device.label_auto_select")}</p>
                        <SwitchBox
                            variable={currentEnableAutoSpeakerSelect}
                            toggleFunction={toggleEnableAutoSpeakerSelect}
                        />
                    </div>

                    <div className={styles.device_dropdown}>
                        <p className={styles.device_secondary_label}>{t("config_page.device.label_device")}</p>
                        <DropdownMenu
                            dropdown_id="speaker_device"
                            label={t("config_page.device.speaker_device.label")}
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
                    <SwitchBox
                        variable={currentEnableAutomaticSpeakerThreshold}
                        toggleFunction={toggleEnableAutomaticSpeakerThreshold}
                    />
                </div>
                <div className={styles.threshold_section}>
                    <ThresholdComponent
                        id="speaker_threshold"
                        min={ui_configs.speaker_threshold_min}
                        max={ui_configs.speaker_threshold_max}
                    />
                </div>
            </div>
        </div>
    );
};