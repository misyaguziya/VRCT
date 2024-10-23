import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import styles from "./Vr.module.scss";
import { Slider } from "../_components/";
import { clsx } from "clsx";

export const Vr = () => {
    const { t } = useTranslation();
    const [is_opened_position_controller, setIsOpenedPositionController] = useState(true);

    const toggleController = () => {
        setIsOpenedPositionController(!is_opened_position_controller);
    };

    const toggle_button_class_names__position = clsx(styles.controller_type_switcher, {
        [styles.is_selected]: is_opened_position_controller
    });
    const toggle_button_class_names__rotation = clsx(styles.controller_type_switcher, {
        [styles.is_selected]: !is_opened_position_controller
    });

    return (
        <div className={styles.container}>
            <div className={styles.controller_type_switch} onClick={toggleController}>
                <div className={toggle_button_class_names__position}>
                    <p className={styles.controller_switcher_label}>Position</p>
                </div>
                <div className={toggle_button_class_names__rotation}>
                    <p className={styles.controller_switcher_label}>Rotation</p>
                </div>
            </div>
            <div className={styles.position_rotation_controls_box}>
                {is_opened_position_controller
                ? <PositionControls />
                : <RotationControls />
            }
            </div>
            <OtherControls />

        </div>
    );
};

const PositionControls = () => {
    const { t } = useTranslation();
    const [position, setPosition] = useState({ x: 0, y: 0, z: 0 });

    const handlePositionChange = (axis, value) => {
        setPosition((prev) => ({ ...prev, [axis]: value }));
    };

    return (
        <div className={styles.position_controls}>
            <div className={styles.position_wrapper}>
                <label className={clsx(styles.slider_label, styles.x_position_label)}>{t("overlay_settings.x_position")}</label>
                <Slider
                    className={styles.x_position_slider}
                    variable={position.x}
                    step={1}
                    min={-100}
                    max={100}
                    onchangeFunction={(value) => handlePositionChange("x", value)}
                />
            </div>
            <div className={styles.position_wrapper}>
                <label className={clsx(styles.slider_label, styles.y_position_label)}>{t("overlay_settings.y_position")}</label>
                <Slider
                    className={styles.y_position_slider}
                    variable={position.y}
                    step={1}
                    min={-100}
                    max={100}
                    onchangeFunction={(value) => handlePositionChange("y", value)}
                    orientation="vertical"
                />
            </div>
            <div className={styles.position_wrapper}>
                <label className={clsx(styles.slider_label, styles.z_position_label)}>{t("overlay_settings.z_position")}</label>
                <Slider
                    className={styles.z_position_slider}
                    variable={position.z}
                    step={1}
                    min={-100}
                    max={100}
                    onchangeFunction={(value) => handlePositionChange("z", value)}
                    orientation="vertical"
                />
            </div>
        </div>
    );
};
const RotationControls = () => {
    const { t } = useTranslation();
    const [rotation, setRotation] = useState({ rotate_x: 0, rotate_y: 0, rotate_z: 0 });

    const handleRotationChange = (axis, value) => {
        setRotation((prev) => ({ ...prev, [axis]: value }));
    };


    return (
        <div className={styles.rotation_controls}>
            <div className={styles.rotation_wrapper}>
                <label className={clsx(styles.slider_label, styles.x_rotation_label)}>{t("overlay_settings.x_rotation")}</label>
                <Slider
                    className={styles.x_rotation_slider}
                    variable={-rotation.rotate_x}
                    valueLabelFormat={rotation.rotate_x}
                    step={10}
                    min={-180}
                    max={180}
                    onchangeFunction={(value) => handleRotationChange("rotate_x", -value)}
                    orientation="vertical"
                />
            </div>
            <div className={styles.rotation_wrapper}>
                <label className={clsx(styles.slider_label, styles.y_rotation_label)}>{t("overlay_settings.y_rotation")}</label>
                <Slider
                    className={styles.y_rotation_slider}
                    variable={rotation.rotate_y}
                    step={10}
                    min={-180}
                    max={180}
                    onchangeFunction={(value) => handleRotationChange("rotate_y", value)}
                />
            </div>
            <div className={styles.rotation_wrapper}>
                <label className={clsx(styles.slider_label, styles.z_rotation_label)}>{t("overlay_settings.z_rotation")}</label>
                <Slider
                    className={styles.z_rotation_slider}
                    variable={rotation.rotate_z}
                    step={15}
                    min={-180}
                    max={180}
                    onchangeFunction={(value) => handleRotationChange("rotate_z", value)}
                    orientation="vertical"
                />
            </div>
        </div>
    );
};


const OtherControls = () => {
    const { t } = useTranslation();
    const [opacity, setOpacity] = useState(1);
    const [ui_scaling, setUiScaling] = useState(100);

    const handleOpacityChange = (value) => {
        setOpacity(value / 100);
    };

    const handleUiScalingChange = (value) => {
        setUiScaling(value);
    };

    const ui_variable_opacity = (opacity * 100).toFixed(0);

    const [display_duration, setDisplayDuration] = useState(5);
    const [fadeout_duration, setFadeoutDuration] = useState(2);

    const handleDisplayDurationChange = (value) => {
        setDisplayDuration(value);
    };

    const handleFadeoutDurationChange = (value) => {
        setFadeoutDuration(value);
    };


    return(
        <div className={styles.other_controls}>
            <div className={styles.other_controls_wrapper}>
                <label className={clsx(styles.other_controls_slider_label, styles.opacity_label)}>{t("overlay_settings.opacity")}</label>
                <Slider
                    className={clsx(styles.other_controls_slider, styles.opacity_slider)}
                    variable={(opacity * 100)}
                    valueLabelFormat={`${ui_variable_opacity}%`}
                    step={5}
                    min={10}
                    max={100}
                    onchangeFunction={handleOpacityChange}
                />
            </div>
            <div className={styles.other_controls_wrapper}>
                <label className={clsx(styles.other_controls_slider_label, styles.ui_scaling_label)}>{t("overlay_settings.ui_scaling")}</label>
                <Slider
                    className={clsx(styles.other_controls_slider, styles.ui_scaling_slider)}
                    variable={ui_scaling}
                    valueLabelFormat={`${ui_scaling}%`}
                    step={10}
                    min={40}
                    max={200}
                    onchangeFunction={handleUiScalingChange}
                />
            </div>
            <div className={styles.other_controls_wrapper}>
                <label className={clsx(styles.other_controls_slider_label, styles.display_duration_label)}>{t("overlay_settings.display_duration")}</label>
                <Slider
                    className={clsx(styles.other_controls_slider, styles.display_duration_slider)}
                    variable={display_duration}
                    valueLabelFormat={`${display_duration} second(s)`}
                    step={1}
                    min={1}
                    max={60}
                    onchangeFunction={handleDisplayDurationChange}
                />
            </div>
            <div className={styles.other_controls_wrapper}>
                <label className={clsx(styles.other_controls_slider_label, styles.fadeout_duration_label)}>{t("overlay_settings.fadeout_duration")}</label>
                <Slider
                    className={clsx(styles.other_controls_slider, styles.fadeout_duration_slider)}
                    variable={fadeout_duration}
                    valueLabelFormat={`${fadeout_duration} second(s)`}
                    step={1}
                    min={0}
                    max={5}
                    onchangeFunction={handleFadeoutDurationChange}
                />
            </div>
        </div>
    );
};