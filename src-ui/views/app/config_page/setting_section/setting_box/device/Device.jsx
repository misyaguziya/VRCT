import { useI18n } from "@useI18n";
import styles from "./Device.module.scss";
import clsx from "clsx";
import { useStore_IsBreakPoint } from "@store";
import { ui_configs } from "@ui_configs";
import {
    useDevice,
} from "@logics_configs";

import {
    MultiDropdownMenuContainer,
} from "../_templates/Templates";

import {
    SectionLabelComponent,
    LabelComponent,
    DropdownMenu,
    ThresholdComponent,
    SwitchBox,
    RadioButton,
} from "../_components";

export const Device = () => {
    return (
        <div className={styles.container}>
            <MicContainer />
            <SpeakerContainer />
        </div>
    );
};

const MicContainer = () => {
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

        currentMicVadFilter,
        toggleMicVadFilter,
        currentEnableAutomaticMicThreshold,
        toggleEnableAutomaticMicThreshold,
    } = useDevice();

    const selectFunction_host = (selected_data) => {
        setSelectedMicHost(selected_data.selected_id);
    };

    const selectFunction_device = (selected_data) => {
        setSelectedMicDevice(selected_data.selected_id);
    };

    const is_disabled_selector = currentEnableAutoMicSelect.data === true || currentEnableAutoMicSelect.state === "pending";

    const getMicSensitivityMode = () => {
        if (currentMicVadFilter.data === true) return "vad";
        if (currentEnableAutomaticMicThreshold.data === true) return "auto";
        return "manual";
    };

    const setMicSensitivityMode = (id) => {
        if (id === "vad") {
            if (!currentMicVadFilter.data) toggleMicVadFilter();
            return;
        }
        if (currentMicVadFilter.data) toggleMicVadFilter();
        if (currentEnableAutomaticMicThreshold.data !== (id === "auto")) {
            toggleEnableAutomaticMicThreshold();
        }
    };

    const mic_sensitivity_mode = getMicSensitivityMode();
    const mic_sensitivity_variable = {
        data: mic_sensitivity_mode,
        state: currentMicVadFilter.state === "pending" || currentEnableAutomaticMicThreshold.state === "pending" ? "pending" : currentMicVadFilter.state,
    };

    return (
        <div className={styles.mic_container}>
            <SectionLabelComponent label={t("config_page.device.section_label_mic")} />
            <MultiDropdownMenuContainer
                setting_id="mic_host_device"
                label={t("config_page.device.mic_host_device.label")}
                dropdown_settings={[
                    {
                        insert_component: SwitchBox,
                        insert_component_props: {
                            secondary_label: t("config_page.device.label_auto_select"),
                            variable: currentEnableAutoMicSelect,
                            toggleFunction: toggleEnableAutoMicSelect,
                        },
                        insert_to: "before",
                    },
                    {
                        dropdown_id: "mic_host",
                        secondary_label: t("config_page.device.label_host"),
                        selected_id: currentSelectedMicHost.data,
                        list: currentMicHostList.data,
                        selectFunction: selectFunction_host,
                        state: currentSelectedMicHost.state,
                        is_disabled: is_disabled_selector,
                    },
                    {
                        dropdown_id: "mic_device",
                        secondary_label: t("config_page.device.label_device"),
                        selected_id: currentSelectedMicDevice.data,
                        list: currentMicDeviceList.data,
                        selectFunction: selectFunction_device,
                        state: currentSelectedMicDevice.state,
                        is_disabled: is_disabled_selector,
                    }
                ]}
            />
            <div className={styles.threshold_container} data-setting-id="mic_dynamic_energy_threshold">
                <div className={styles.threshold_switch_section}>
                    <LabelComponent label={t("config_page.device.mic_dynamic_energy_threshold.label")} />
                    <RadioButton
                        name="mic_sensitivity_mode"
                        checked_variable={mic_sensitivity_variable}
                        selectFunction={setMicSensitivityMode}
                        options={[
                            {
                                id: "vad",
                                label: t("config_page.device.mic_dynamic_energy_threshold.option_vad"),
                                desc: t("config_page.device.mic_dynamic_energy_threshold.desc_for_vad"),
                            },
                            {
                                id: "auto",
                                label: t("config_page.device.mic_dynamic_energy_threshold.option_auto"),
                                desc: t("config_page.device.mic_dynamic_energy_threshold.desc_for_automatic"),
                            },
                            {
                                id: "manual",
                                label: t("config_page.device.mic_dynamic_energy_threshold.option_manual"),
                                desc: t("config_page.device.mic_dynamic_energy_threshold.desc_for_manual"),
                            },
                        ]}
                    />
                </div>
                <div className={styles.threshold_section}>
                    <ThresholdComponent
                        id="mic_threshold"
                        min={ui_configs.mic_threshold_min}
                        max={ui_configs.mic_threshold_max}
                        is_vad_active={currentMicVadFilter.data === true}
                    />
                </div>
            </div>
        </div>
    );
};

const SpeakerContainer = () => {
    const { t } = useI18n();
    const {
        currentEnableAutoSpeakerSelect,
        toggleEnableAutoSpeakerSelect,
        currentSpeakerDeviceList,
        currentSelectedSpeakerDevice,
        setSelectedSpeakerDevice,
        currentSpeakerVadFilter,
        toggleSpeakerVadFilter,
        currentEnableAutomaticSpeakerThreshold,
        toggleEnableAutomaticSpeakerThreshold,
    } = useDevice();

    const selectFunction = (selected_data) => {
        setSelectedSpeakerDevice(selected_data.selected_id);
    };

    const is_disabled_selector = currentEnableAutoSpeakerSelect.data === true || currentEnableAutoSpeakerSelect.state === "pending";

    const getSpeakerSensitivityMode = () => {
        if (currentSpeakerVadFilter.data === true) return "vad";
        if (currentEnableAutomaticSpeakerThreshold.data === true) return "auto";
        return "manual";
    };

    const setSpeakerSensitivityMode = (id) => {
        if (id === "vad") {
            if (!currentSpeakerVadFilter.data) toggleSpeakerVadFilter();
            return;
        }
        if (currentSpeakerVadFilter.data) toggleSpeakerVadFilter();
        if (currentEnableAutomaticSpeakerThreshold.data !== (id === "auto")) {
            toggleEnableAutomaticSpeakerThreshold();
        }
    };

    const { currentIsBreakPoint } = useStore_IsBreakPoint();
    const device_container_class = clsx(styles.device_container, {
        [styles.is_break_point]: currentIsBreakPoint.data,
    });

    const speaker_sensitivity_mode = getSpeakerSensitivityMode();
    const speaker_sensitivity_variable = {
        data: speaker_sensitivity_mode,
        state: currentSpeakerVadFilter.state === "pending" || currentEnableAutomaticSpeakerThreshold.state === "pending" ? "pending" : currentSpeakerVadFilter.state,
    };

    return (
        <div className={styles.speaker_container}>
            <SectionLabelComponent label={t("config_page.device.section_label_speaker")} />
            <div className={device_container_class} data-setting-id="speaker_device">
                <LabelComponent label={t("config_page.device.speaker_device.label")} />
                <div className={styles.device_contents}>
                    <SwitchBox
                        secondary_label={t("config_page.device.label_auto_select")}
                        variable={currentEnableAutoSpeakerSelect}
                        toggleFunction={toggleEnableAutoSpeakerSelect}
                    />
                    <DropdownMenu
                        dropdown_id="speaker_device"
                        secondary_label={t("config_page.device.label_device")}
                        label={t("config_page.device.speaker_device.label")}
                        selected_id={currentSelectedSpeakerDevice.data}
                        list={currentSpeakerDeviceList.data}
                        selectFunction={selectFunction}
                        state={currentSelectedSpeakerDevice.state}
                        is_disabled={is_disabled_selector}
                    />
                </div>
            </div>
            <div className={styles.threshold_container} data-setting-id="speaker_dynamic_energy_threshold">
                <div className={styles.threshold_switch_section}>
                    <LabelComponent label={t("config_page.device.speaker_dynamic_energy_threshold.label")} />
                    <RadioButton
                        name="speaker_sensitivity_mode"
                        checked_variable={speaker_sensitivity_variable}
                        selectFunction={setSpeakerSensitivityMode}
                        options={[
                            {
                                id: "vad",
                                label: t("config_page.device.speaker_dynamic_energy_threshold.option_vad"),
                                desc: t("config_page.device.speaker_dynamic_energy_threshold.desc_for_vad"),
                            },
                            {
                                id: "auto",
                                label: t("config_page.device.speaker_dynamic_energy_threshold.option_auto"),
                                desc: t("config_page.device.speaker_dynamic_energy_threshold.desc_for_automatic"),
                            },
                            {
                                id: "manual",
                                label: t("config_page.device.speaker_dynamic_energy_threshold.option_manual"),
                                desc: t("config_page.device.speaker_dynamic_energy_threshold.desc_for_manual"),
                            },
                        ]}
                    />
                </div>
                <div className={styles.threshold_section}>
                    <ThresholdComponent
                        id="speaker_threshold"
                        min={ui_configs.speaker_threshold_min}
                        max={ui_configs.speaker_threshold_max}
                        is_vad_active={currentSpeakerVadFilter.data === true}
                    />
                </div>
            </div>
        </div>
    );
};