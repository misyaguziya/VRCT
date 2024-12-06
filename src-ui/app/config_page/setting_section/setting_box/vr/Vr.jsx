import React, { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { clsx } from "clsx";
import styles from "./Vr.module.scss";
import { ui_configs } from "@ui_configs";
import { Slider } from "../_components/";
import {
    RadioButtonContainer,
    SwitchBoxContainer,
    CheckboxContainer,
} from "../_templates/Templates";

import {
    SectionLabelComponent,
} from "../_components/";

import {
    useIsEnabledOverlaySmallLog,
    useOverlaySmallLogSettings,
    useIsEnabledOverlayLargeLog,
    useOverlayLargeLogSettings,
    useOverlayShowOnlyTranslatedMessages,
} from "@logics_configs";

export const Vr = () => {
    const { t } = useTranslation();
    const [is_opened_small_settings, setIsOpenedSmallSettings] = useState(true);
    const toggleIsOpenedSmallSettings = () => {
        setIsOpenedSmallSettings(!is_opened_small_settings);
    };

    const { currentOverlaySmallLogSettings, setOverlaySmallLogSettings } = useOverlaySmallLogSettings();
    const { currentIsEnabledOverlaySmallLog, toggleIsEnabledOverlaySmallLog } = useIsEnabledOverlaySmallLog();

    const { currentOverlayLargeLogSettings, setOverlayLargeLogSettings } = useOverlayLargeLogSettings();
    const { currentIsEnabledOverlayLargeLog, toggleIsEnabledOverlayLargeLog } = useIsEnabledOverlayLargeLog();
    return (
        <div className={styles.container}>
            <div className={styles.wrapper}>
                <PageSwitcherContainer
                    toggleFunction={toggleIsOpenedSmallSettings}
                    is_selected={is_opened_small_settings}
                    label_1="Small"
                    label_2="Large"
                    />
                {is_opened_small_settings ? (
                    <OverlaySettingsContainer
                    id="overlay_settings_small"
                    ui_configs={ui_configs.overlay_small_log}
                    current_overlay_settings={currentOverlaySmallLogSettings.data}
                    set_overlay_settings={setOverlaySmallLogSettings}
                    current_is_enabled_overlay={currentIsEnabledOverlaySmallLog}
                    toggle_is_enabled_overlay={toggleIsEnabledOverlaySmallLog}
                    />
                ) : (
                    <OverlaySettingsContainer
                    id="overlay_settings_large"
                    ui_configs={ui_configs.overlay_large_log}
                    current_overlay_settings={currentOverlayLargeLogSettings.data}
                    set_overlay_settings={setOverlayLargeLogSettings}
                    current_is_enabled_overlay={currentIsEnabledOverlayLargeLog}
                    toggle_is_enabled_overlay={toggleIsEnabledOverlayLargeLog}
                    />
                )}
            </div>
            <CommonSettingsContainer />
        </div>
    );
};

const OverlaySettingsContainer = ({
    current_overlay_settings,
    set_overlay_settings,
    current_is_enabled_overlay,
    toggle_is_enabled_overlay,
    ui_configs,
    id
}) => {

    const { t } = useTranslation();
    useEffect(() => {
        setSettings(current_overlay_settings);
    }, [current_overlay_settings]);

    const [settings, setSettings] = useState(current_overlay_settings);
    const [timeout_id, setTimeoutId] = useState(null);

    const [is_opened_position_controller, setIsOpenedPositionController] = useState(true);
    const togglePositionRotationController = () => {
        setIsOpenedPositionController(!is_opened_position_controller);
    };

    const onchangeFunction = (key, value) => {
        setSettings((prev) => ({ ...prev, [key]: value }));

        if (timeout_id) clearTimeout(timeout_id);

        const newTimeoutId = setTimeout(() => {
            const new_data = { ...settings, [key]: value };
            set_overlay_settings(new_data);
        }, 50);

        setTimeoutId(newTimeoutId);
    };

    const selectTrackerFunction = (value) => {
        const new_data = { ...settings, tracker: value };
        set_overlay_settings(new_data);
    };


    return (
        <>
            <SwitchBoxContainer
                label={t("overlay_settings.enable")}
                variable={current_is_enabled_overlay}
                toggleFunction={toggle_is_enabled_overlay}
            />
            <PageSwitcherContainer
                toggleFunction={togglePositionRotationController}
                is_selected={is_opened_position_controller}
                label_1={t("overlay_settings.position")}
                label_2={t("overlay_settings.rotation")}
            />

            <div className={styles.position_rotation_controls_box}>
                {is_opened_position_controller ? (
                    <PositionControls settings={settings} onchangeFunction={onchangeFunction} ui_configs={ui_configs} />
                ) : (
                    <RotationControls settings={settings} onchangeFunction={onchangeFunction} ui_configs={ui_configs} />
                )}
            </div>
            <OtherControls settings={settings} onchangeFunction={onchangeFunction} ui_configs={ui_configs} />
            <RadioButtonContainer
                label={t("overlay_settings.tracker")}
                selectFunction={selectTrackerFunction}
                name={id}
                options={[
                    { id: "HMD", label: "HMD" },
                    { id: "LeftHand", label: "LeftHand" },
                    { id: "RightHand", label: "RightHand" },
                ]}
                checked_variable={{data: settings.tracker}}
                column={true}
            />
        </>
    );
};


const PageSwitcherContainer = (props) => {
    const toggle_button_class_names__position = clsx(styles.controller_type_switcher, {
        [styles.is_selected]: props.is_selected,
    });
    const toggle_button_class_names__rotation = clsx(styles.controller_type_switcher, {
        [styles.is_selected]: !props.is_selected,
    });

    return (
        <div className={styles.controller_type_switch} onClick={() => props.toggleFunction()}>
            <div className={toggle_button_class_names__position}>
                <p className={styles.controller_switcher_label}>{props.label_1}</p>
            </div>
            <div className={toggle_button_class_names__rotation}>
                <p className={styles.controller_switcher_label}>{props.label_2}</p>
            </div>
        </div>
    );
};

const PositionControls = ({settings, onchangeFunction, ui_configs}) => {
    const { t } = useTranslation();

    return (
        <div className={styles.position_controls}>
            <div className={styles.position_wrapper}>
                <label className={clsx(styles.slider_label, styles.x_position_label)}>{t("overlay_settings.x_position")}</label>
                <Slider
                    className={styles.x_position_slider}
                    variable={settings.x_pos}
                    step={ui_configs.x_pos.step}
                    min={ui_configs.x_pos.min}
                    max={ui_configs.x_pos.max}
                    onchangeFunction={(value) => onchangeFunction("x_pos", value)}
                />
            </div>
            <div className={styles.position_wrapper}>
                <label className={clsx(styles.slider_label, styles.y_position_label)}>{t("overlay_settings.y_position")}</label>
                <Slider
                    className={styles.y_position_slider}
                    variable={settings.y_pos}
                    step={ui_configs.y_pos.step}
                    min={ui_configs.y_pos.min}
                    max={ui_configs.y_pos.max}
                    onchangeFunction={(value) => onchangeFunction("y_pos", value)}
                    orientation="vertical"
                />
            </div>
            <div className={styles.position_wrapper}>
                <label className={clsx(styles.slider_label, styles.z_position_label)}>{t("overlay_settings.z_position")}</label>
                <Slider
                    className={styles.z_position_slider}
                    variable={settings.z_pos}
                    step={ui_configs.z_pos.step}
                    min={ui_configs.z_pos.min}
                    max={ui_configs.z_pos.max}
                    onchangeFunction={(value) => onchangeFunction("z_pos", value)}
                    orientation="vertical"
                />
            </div>
        </div>
    );
};

const RotationControls = ({settings, onchangeFunction}) => {
    const { t } = useTranslation();

    return (
        <div className={styles.rotation_controls}>
            <div className={styles.rotation_wrapper}>
                <label className={clsx(styles.slider_label, styles.x_rotation_label)}>{t("overlay_settings.x_rotation")}</label>
                <Slider
                    className={styles.x_rotation_slider}
                    variable={-settings.x_rotation}
                    valueLabelFormat={settings.x_rotation}
                    step={5}
                    min={-180}
                    max={180}
                    onchangeFunction={(value) => onchangeFunction("x_rotation", -value)}
                    orientation="vertical"
                />
            </div>
            <div className={styles.rotation_wrapper}>
                <label className={clsx(styles.slider_label, styles.y_rotation_label)}>{t("overlay_settings.y_rotation")}</label>
                <Slider
                    className={styles.y_rotation_slider}
                    variable={settings.y_rotation}
                    step={5}
                    min={-180}
                    max={180}
                    onchangeFunction={(value) => onchangeFunction("y_rotation", value)}
                />
            </div>
            <div className={styles.rotation_wrapper}>
                <label className={clsx(styles.slider_label, styles.z_rotation_label)}>{t("overlay_settings.z_rotation")}</label>
                <Slider
                    className={styles.z_rotation_slider}
                    variable={settings.z_rotation}
                    step={5}
                    min={-180}
                    max={180}
                    onchangeFunction={(value) => onchangeFunction("z_rotation", value)}
                    orientation="vertical"
                />
            </div>
        </div>
    );
};

const OtherControls = ({settings, onchangeFunction, ui_configs}) => {
    const { t } = useTranslation();

    const ui_variable_opacity = (settings.opacity * 100).toFixed(0);
    const ui_variable_ui_scaling = (settings.ui_scaling * 100).toFixed(0);

    return(
        <div className={styles.other_controls}>
            <div className={styles.other_controls_wrapper}>
                <label className={clsx(styles.other_controls_slider_label, styles.opacity_label)}>
                    {t("overlay_settings.opacity")}
                </label>
                <Slider
                    className={clsx(styles.other_controls_slider, styles.opacity_slider)}
                    variable={settings.opacity * 100}
                    valueLabelFormat={`${ui_variable_opacity}%`}
                    step={5}
                    min={10}
                    max={100}
                    onchangeFunction={(value) => onchangeFunction("opacity", value / 100)}
                />
            </div>
            <div className={styles.other_controls_wrapper}>
                <label className={clsx(styles.other_controls_slider_label, styles.ui_scaling_label)}>
                    {t("overlay_settings.ui_scaling")}
                </label>
                <Slider
                    className={clsx(styles.other_controls_slider, styles.ui_scaling_slider)}
                    variable={settings.ui_scaling * 100}
                    valueLabelFormat={`${ui_variable_ui_scaling}%`}
                    step={ui_configs.ui_scaling.step}
                    min={ui_configs.ui_scaling.min}
                    max={ui_configs.ui_scaling.max}
                    onchangeFunction={(value) => onchangeFunction("ui_scaling", value / 100)}
                />
            </div>
            <div className={styles.other_controls_wrapper}>
                <label className={clsx(styles.other_controls_slider_label, styles.display_duration_label)}>{t("overlay_settings.display_duration")}</label>
                <Slider
                    className={clsx(styles.other_controls_slider, styles.display_duration_slider)}
                    variable={settings.display_duration}
                    valueLabelFormat={`${settings.display_duration} second(s)`}
                    step={1}
                    min={1}
                    max={60}
                    onchangeFunction={(value) => onchangeFunction("display_duration", value)}
                />
            </div>
            <div className={styles.other_controls_wrapper}>
                <label className={clsx(styles.other_controls_slider_label, styles.fadeout_duration_label)}>{t("overlay_settings.fadeout_duration")}</label>
                <Slider
                    className={clsx(styles.other_controls_slider, styles.fadeout_duration_slider)}
                    variable={settings.fadeout_duration}
                    valueLabelFormat={`${settings.fadeout_duration} second(s)`}
                    step={1}
                    min={0}
                    max={5}
                    onchangeFunction={(value) => onchangeFunction("fadeout_duration", value)}
                />
            </div>
        </div>
    );
};


const CommonSettingsContainer = () => {
    const { t } = useTranslation();
    const { currentOverlayShowOnlyTranslatedMessages, toggleOverlayShowOnlyTranslatedMessages } = useOverlayShowOnlyTranslatedMessages();

    return (
        <div className={styles.common_container}>
            <SectionLabelComponent label="Common Settings" />
            <CheckboxContainer
                label={t("overlay_settings.overlay_show_only_translated_messages.label")}
                variable={currentOverlayShowOnlyTranslatedMessages}
                toggleFunction={toggleOverlayShowOnlyTranslatedMessages}
            />
        </div>
    );
};