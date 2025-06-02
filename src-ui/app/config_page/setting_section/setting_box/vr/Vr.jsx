import React, { useState, useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import clsx from "clsx";
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
    useSendTextToOverlay,
} from "@logics_configs";

import RedoSvg from "@images/redo.svg?react";

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

    const restoreDefaultSettings = () => {
        setOverlaySmallLogSettings(ui_configs.overlay_small_log_default_settings);
        setOverlayLargeLogSettings(ui_configs.overlay_large_log_default_settings);
    };

    return (
        <div className={styles.container}>
            <div className={styles.wrapper}>
                <PageSwitcherContainer
                    toggleFunction={toggleIsOpenedSmallSettings}
                    is_selected={is_opened_small_settings}
                    label_1={t("config_page.vr.single_line")}
                    label_2={t("config_page.vr.multi_lines")}
                />
                {is_opened_small_settings ? (
                    <OverlaySettingsContainer
                        id="overlay_settings_small"
                        ui_configs={ui_configs.overlay_small_log}
                        default_ui_configs={ui_configs.overlay_small_log_default_settings}
                        current_overlay_settings={currentOverlaySmallLogSettings.data}
                        set_overlay_settings={setOverlaySmallLogSettings}
                        current_is_enabled_overlay={currentIsEnabledOverlaySmallLog}
                        toggle_is_enabled_overlay={toggleIsEnabledOverlaySmallLog}
                    />
                ) : (
                    <OverlaySettingsContainer
                        id="overlay_settings_large"
                        ui_configs={ui_configs.overlay_large_log}
                        default_ui_configs={ui_configs.overlay_large_log_default_settings}
                        current_overlay_settings={currentOverlayLargeLogSettings.data}
                        set_overlay_settings={setOverlayLargeLogSettings}
                        current_is_enabled_overlay={currentIsEnabledOverlayLargeLog}
                        toggle_is_enabled_overlay={toggleIsEnabledOverlayLargeLog}
                    />
                )}
            </div>
            <CommonSettingsContainer />
            <button
                className={styles.restore_default_settings_button}
                onClick={restoreDefaultSettings}
            >
                {t("config_page.vr.restore_default_settings")}
            </button>
        </div>
    );
};

const OverlaySettingsContainer = ({
    current_overlay_settings,
    set_overlay_settings,
    current_is_enabled_overlay,
    toggle_is_enabled_overlay,
    ui_configs,
    default_ui_configs,
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

    const selectFunction = (key, value) => {
        const new_data = { ...settings, [key]: value };
        set_overlay_settings(new_data);
    };


    return (
        <>
            <SwitchBoxContainer
                label={t("config_page.vr.overlay_enable")}
                variable={current_is_enabled_overlay}
                toggleFunction={toggle_is_enabled_overlay}
            />
            <PageSwitcherContainer
                toggleFunction={togglePositionRotationController}
                is_selected={is_opened_position_controller}
                label_1={t("config_page.vr.position")}
                label_2={t("config_page.vr.rotation")}
            />

            <div className={styles.position_rotation_controls_box}>
                {is_opened_position_controller ? (
                    <PositionControls settings={settings} onchangeFunction={onchangeFunction} ui_configs={ui_configs} default_ui_configs={default_ui_configs} selectFunction={selectFunction}/>
                ) : (
                    <RotationControls settings={settings} onchangeFunction={onchangeFunction} ui_configs={ui_configs} default_ui_configs={default_ui_configs} selectFunction={selectFunction}/>
                )}
            <SendSampleTextToggleButton />
            </div>
            <OtherControls settings={settings} onchangeFunction={onchangeFunction} ui_configs={ui_configs} />
            <RadioButtonContainer
                label={t("config_page.vr.tracker")}
                selectFunction={(value) => selectFunction("tracker", value)}
                name={id}
                options={[
                    { id: "HMD", label: t("config_page.vr.hmd") },
                    { id: "LeftHand", label: t("config_page.vr.left_hand") },
                    { id: "RightHand", label: t("config_page.vr.right_hand") },
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


/**
 * PositionControls:
 * - x_pos, y_pos, z_pos 用のスライダーとリセットボタン、上下ボタンを表示
 * - useVariableControl を使って、is_max/is_min/variable_display/countUp/countDown を共通化
 */
const PositionControls = ({ settings, onchangeFunction, selectFunction, ui_configs, default_ui_configs }) => {
    const { t } = useTranslation();

    // x_pos 用のフック呼び出し
    const {
        variable_display: x_variable_display,
        is_max: is_max_position_x,
        is_min: is_min_position_x,
        countUp: countUpPositionX,
        countDown: countDownPositionX,
    } = useVariableControl("x_pos", settings, onchangeFunction, ui_configs);

    // y_pos 用のフック呼び出し
    const {
        variable_display: y_variable_display,
        is_max: is_max_position_y,
        is_min: is_min_position_y,
        countUp: countUpPositionY,
        countDown: countDownPositionY,
    } = useVariableControl("y_pos", settings, onchangeFunction, ui_configs);

    // z_pos 用のフック呼び出し
    const {
        variable_display: z_variable_display,
        is_max: is_max_position_z,
        is_min: is_min_position_z,
        countUp: countUpPositionZ,
        countDown: countDownPositionZ,
    } = useVariableControl("z_pos", settings, onchangeFunction, ui_configs);

    // 各ボタンの className を生成
    const x_position_button_up_classname = clsx(styles.x_position_button_up, { [styles.is_disabled]: is_max_position_x });
    const x_position_button_down_classname = clsx(styles.x_position_button_down, { [styles.is_disabled]: is_min_position_x });

    const y_position_button_up_classname = clsx(styles.y_position_button_up, { [styles.is_disabled]: is_max_position_y });
    const y_position_button_down_classname = clsx(styles.y_position_button_down, { [styles.is_disabled]: is_min_position_y });

    const z_position_button_up_classname = clsx(styles.z_position_button_up, { [styles.is_disabled]: is_max_position_z });
    const z_position_button_down_classname = clsx(styles.z_position_button_down, { [styles.is_disabled]: is_min_position_z });

    return (
        <div className={styles.position_controls}>
            {/* X Position */}
            <div className={styles.position_wrapper}>
                <p className={clsx(styles.slider_label, styles.x_position_label)}>
                    {t("config_page.vr.x_position")}
                    <ResetButton onClickFunction={() => selectFunction("x_pos", default_ui_configs.x_pos)} />
                </p>
                <Slider
                    className={styles.x_position_slider}
                    no_padding={true}
                    variable={settings.x_pos}
                    step={ui_configs.x_pos.step}
                    min={ui_configs.x_pos.min}
                    max={ui_configs.x_pos.max}
                    onchangeFunction={(value) => onchangeFunction("x_pos", value)}
                    valueLabelDisplay={x_variable_display}
                    valueLabelDisplayLocation="top"
                />
                <div className={styles.x_position_button_wrapper}>
                    <div className={x_position_button_up_classname} onClick={countUpPositionX}>△</div>
                    <div className={x_position_button_down_classname} onClick={countDownPositionX}>▽</div>
                </div>
            </div>

            {/* Y Position */}
            <div className={styles.position_wrapper}>
                <p className={clsx(styles.slider_label, styles.y_position_label)}>
                    {t("config_page.vr.y_position")}
                    <ResetButton onClickFunction={() => selectFunction("y_pos", default_ui_configs.y_pos)} />
                </p>
                <Slider
                    className={styles.y_position_slider}
                    no_padding={true}
                    variable={settings.y_pos}
                    step={ui_configs.y_pos.step}
                    min={ui_configs.y_pos.min}
                    max={ui_configs.y_pos.max}
                    onchangeFunction={(value) => onchangeFunction("y_pos", value)}
                    orientation="vertical"
                    valueLabelDisplay={y_variable_display}
                    valueLabelDisplayLocation="right"
                />
                <div className={styles.y_position_button_wrapper}>
                    <div className={y_position_button_up_classname} onClick={countUpPositionY}>△</div>
                    <div className={y_position_button_down_classname} onClick={countDownPositionY}>▽</div>
                </div>
            </div>

            {/* Z Position */}
            <div className={styles.position_wrapper}>
                <p className={clsx(styles.slider_label, styles.z_position_label)}>
                    {t("config_page.vr.z_position")}
                    <ResetButton onClickFunction={() => selectFunction("z_pos", default_ui_configs.z_pos)} />
                </p>
                <Slider
                    className={styles.z_position_slider}
                    no_padding={true}
                    variable={settings.z_pos}
                    step={ui_configs.z_pos.step}
                    min={ui_configs.z_pos.min}
                    max={ui_configs.z_pos.max}
                    onchangeFunction={(value) => onchangeFunction("z_pos", value)}
                    orientation="vertical"
                    valueLabelDisplay={z_variable_display}
                    valueLabelDisplayLocation="left"
                />
                <div className={styles.z_position_button_wrapper}>
                    <div className={z_position_button_up_classname} onClick={countUpPositionZ}>△</div>
                    <div className={z_position_button_down_classname} onClick={countDownPositionZ}>▽</div>
                </div>
            </div>
        </div>
    );
};

const RotationControls = ({settings, onchangeFunction, selectFunction, ui_configs, default_ui_configs}) => {
    const { t } = useTranslation();

    const {
        variable_display: x_variable_display,
        is_max: is_max_rotation_x,
        is_min: is_min_rotation_x,
        countUp: countUpRotationX,
        countDown: countDownRotationX,
    } = useVariableControl("x_rotation", settings, onchangeFunction, ui_configs);

    const {
        variable_display: y_variable_display,
        is_max: is_max_rotation_y,
        is_min: is_min_rotation_y,
        countUp: countUpRotationY,
        countDown: countDownRotationY,
    } = useVariableControl("y_rotation", settings, onchangeFunction, ui_configs);

    const {
        variable_display: z_variable_display,
        is_max: is_max_rotation_z,
        is_min: is_min_rotation_z,
        countUp: countUpRotationZ,
        countDown: countDownRotationZ,
    } = useVariableControl("z_rotation", settings, onchangeFunction, ui_configs);

    const x_rotation_button_up_classname = clsx(styles.x_rotation_button_up, { [styles.is_disabled]: is_min_rotation_x });
    const x_rotation_button_down_classname = clsx(styles.x_rotation_button_down, { [styles.is_disabled]: is_max_rotation_x });

    const y_rotation_button_up_classname = clsx(styles.y_rotation_button_up, { [styles.is_disabled]: is_max_rotation_y });
    const y_rotation_button_down_classname = clsx(styles.y_rotation_button_down, { [styles.is_disabled]: is_min_rotation_y });

    const z_rotation_button_up_classname = clsx(styles.z_rotation_button_up, { [styles.is_disabled]: is_max_rotation_z });
    const z_rotation_button_down_classname = clsx(styles.z_rotation_button_down, { [styles.is_disabled]: is_min_rotation_z });

    return (
        <div className={styles.rotation_controls}>
            <div className={styles.rotation_wrapper}>
                <p className={clsx(styles.slider_label, styles.x_rotation_label)}>
                    {t("config_page.vr.x_rotation")}
                    <ResetButton onClickFunction={() => selectFunction("x_rotation", default_ui_configs.x_rotation)} />
                </p>
                <Slider
                    className={styles.x_rotation_slider}
                    no_padding={true}
                    variable={-settings.x_rotation}
                    valueLabelFormat={settings.x_rotation}
                    step={ui_configs.x_rotation.step}
                    min={ui_configs.x_rotation.min}
                    max={ui_configs.x_rotation.max}
                    onchangeFunction={(value) => onchangeFunction("x_rotation", -value)}
                    orientation="vertical"
                    valueLabelDisplay={x_variable_display}
                    valueLabelDisplayLocation="right"
                />
                <div className={styles.x_rotation_button_wrapper}>
                    <div className={x_rotation_button_up_classname} onClick={countDownRotationX}>△</div>
                    <div className={x_rotation_button_down_classname} onClick={countUpRotationX}>▽</div>
                </div>
            </div>
            <div className={styles.rotation_wrapper}>
                <p className={clsx(styles.slider_label, styles.y_rotation_label)}>
                    {t("config_page.vr.y_rotation")}
                    <ResetButton onClickFunction={() => selectFunction("y_rotation", default_ui_configs.y_rotation)} />
                </p>
                <Slider
                    className={styles.y_rotation_slider}
                    no_padding={true}
                    variable={settings.y_rotation}
                    step={ui_configs.y_rotation.step}
                    min={ui_configs.y_rotation.min}
                    max={ui_configs.y_rotation.max}
                    onchangeFunction={(value) => onchangeFunction("y_rotation", value)}
                    valueLabelDisplay={y_variable_display}
                    valueLabelDisplayLocation="top"
                />
                <div className={styles.y_rotation_button_wrapper}>
                    <div className={y_rotation_button_up_classname} onClick={countUpRotationY}>△</div>
                    <div className={y_rotation_button_down_classname} onClick={countDownRotationY}>▽</div>
                </div>
            </div>
            <div className={styles.rotation_wrapper}>
                <p className={clsx(styles.slider_label, styles.z_rotation_label)}>
                    {t("config_page.vr.z_rotation")}
                    <ResetButton onClickFunction={() => selectFunction("z_rotation", default_ui_configs.z_rotation)} />
                </p>
                <Slider
                    className={styles.z_rotation_slider}
                    no_padding={true}
                    variable={settings.z_rotation}
                    step={ui_configs.z_rotation.step}
                    min={ui_configs.z_rotation.min}
                    max={ui_configs.z_rotation.max}
                    onchangeFunction={(value) => onchangeFunction("z_rotation", value)}
                    orientation="vertical"
                    valueLabelDisplay={z_variable_display}
                    valueLabelDisplayLocation="left"
                />
                <div className={styles.z_rotation_button_wrapper}>
                    <div className={z_rotation_button_up_classname} onClick={countUpRotationZ}>△</div>
                    <div className={z_rotation_button_down_classname} onClick={countDownRotationZ}>▽</div>
                </div>
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
                <p className={clsx(styles.other_controls_slider_label, styles.opacity_label)}>
                    {t("config_page.vr.opacity")}
                </p>
                <Slider
                    className={clsx(styles.other_controls_slider, styles.opacity_slider)}
                    no_padding={true}
                    variable={settings.opacity * 100}
                    valueLabelFormat={`${ui_variable_opacity}%`}
                    step={5}
                    min={10}
                    max={100}
                    onchangeFunction={(value) => onchangeFunction("opacity", value / 100)}
                />
            </div>
            <div className={styles.other_controls_wrapper}>
                <p className={clsx(styles.other_controls_slider_label, styles.ui_scaling_label)}>
                    {t("config_page.vr.ui_scaling")}
                </p>
                <Slider
                    className={clsx(styles.other_controls_slider, styles.ui_scaling_slider)}
                    no_padding={true}
                    variable={settings.ui_scaling * 100}
                    valueLabelFormat={`${ui_variable_ui_scaling}%`}
                    step={ui_configs.ui_scaling.step}
                    min={ui_configs.ui_scaling.min}
                    max={ui_configs.ui_scaling.max}
                    onchangeFunction={(value) => onchangeFunction("ui_scaling", value / 100)}
                />
            </div>
            <div className={styles.other_controls_wrapper}>
                <p className={clsx(styles.other_controls_slider_label, styles.display_duration_label)}>{t("config_page.vr.display_duration")}</p>
                <Slider
                    className={clsx(styles.other_controls_slider, styles.display_duration_slider)}
                    no_padding={true}
                    variable={settings.display_duration}
                    valueLabelFormat={`${settings.display_duration} second(s)`}
                    step={1}
                    min={1}
                    max={60}
                    onchangeFunction={(value) => onchangeFunction("display_duration", value)}
                />
            </div>
            <div className={styles.other_controls_wrapper}>
                <p className={clsx(styles.other_controls_slider_label, styles.fadeout_duration_label)}>{t("config_page.vr.fadeout_duration")}</p>
                <Slider
                    className={clsx(styles.other_controls_slider, styles.fadeout_duration_slider)}
                    no_padding={true}
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
            <SectionLabelComponent label={t("config_page.vr.common_settings")} />
            <CheckboxContainer
                label={t("config_page.vr.overlay_show_only_translated_messages.label")}
                variable={currentOverlayShowOnlyTranslatedMessages}
                toggleFunction={toggleOverlayShowOnlyTranslatedMessages}
            />
        </div>
    );
};

const ResetButton = ({onClickFunction}) => {
    return (
        <button className={styles.slider_reset_button} onClick={onClickFunction}>
            <RedoSvg className={styles.slider_reset_svg}/>
        </button>
    );
};

import SquareSvg from "@images/square.svg?react";
import TriangleSvg from "@images/triangle.svg?react";
import { randomIntMinMax } from "@utils";

const SendSampleTextToggleButton = () => {
    const { t } = useTranslation();
    const { sendTextToOverlay } = useSendTextToOverlay();
    const [is_started, setIsStarted] = useState(false);

    useEffect(() => {
        let interval_id;

        if (is_started) {
            interval_id = setInterval(() => {
                const text_data = Array.from(
                    { length: randomIntMinMax(1, 5) },
                    () => t("config_page.vr.sample_text_button.sample_text")
                ).join(" ");
                sendTextToOverlay(text_data);
            }, 1000);
        };

        return () => {
            if (interval_id) {
                clearInterval(interval_id);
            }
        };
    }, [is_started]);

    const toggleFunction = () => {
        setIsStarted(!is_started);
    };

    const label = is_started
        ? t("config_page.vr.sample_text_button.stop")
        : t("config_page.vr.sample_text_button.start");

    return (
        <div className={styles.sample_text_button_wrapper}>
            <button
                className={clsx(styles.sample_text_button, { [styles.is_started]: is_started })}
                onClick={toggleFunction}
            >
                {is_started ? (
                    <SquareSvg className={styles.sample_text_button_square_svg} />
                ) : (
                    <TriangleSvg className={styles.sample_text_button_triangle_svg} />
                )}
            </button>
            <p className={styles.sample_text_button_label}>{label}</p>
        </div>
    );
};



const useVariableControl = (key, settings, onchangeFunction, ui_configs) => {
    const [variable_display, setVariableDisplay] = useState("auto");

    const [is_max, setIsMax] = useState(settings[key] >= ui_configs[key].max);
    const [is_min, setIsMin] = useState(settings[key] <= ui_configs[key].min);

    const timerRef = useRef();

        // アンマウント時にタイマーをクリアする
    useEffect(() => {
        return () => {
            clearTimeout(timerRef.current);
        };
    }, []);

    const triggerDisplay = () => {
        setVariableDisplay("on");
        clearTimeout(timerRef.current);
        timerRef.current = setTimeout(() => {
            setVariableDisplay("auto");
        }, 2000);
    };

    useEffect(() => {
        setIsMax(settings[key] >= ui_configs[key].max);
        setIsMin(settings[key] <= ui_configs[key].min);
    }, [settings[key]]);

    const countUp = () => {
        if (is_max) return;
        const step = ui_configs[key].step;
        const new_value = parseFloat((settings[key] + step).toFixed(2));
        onchangeFunction(key, new_value);
        triggerDisplay();
    };

    const countDown = () => {
        if (is_min) return;
        const step = ui_configs[key].step;
        const new_value = parseFloat((settings[key] - step).toFixed(2));
        onchangeFunction(key, new_value);
        triggerDisplay();
    };

    return {
        variable_display,
        is_max,
        is_min,
        countUp,
        countDown,
    };
};