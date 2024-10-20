import React, { useState } from "react";
import styles from "./Vr.module.scss";
import { Slider } from "../_components/";

export const Vr = () => {
    const [position, setPosition] = useState({ x: 0, y: 0, z: 0 });
    const [rotation, setRotation] = useState({ rotate_x: 0, rotate_y: 0, rotate_z: 0 });
    const [opacity, setOpacity] = useState(1);
    const [ui_scaling, setUiScaling] = useState(100);

    const handlePositionChange = (axis, value) => {
        setPosition((prev) => ({ ...prev, [axis]: value }));
    };

    const handleRotationChange = (axis, value) => {
        setRotation((prev) => ({ ...prev, [axis]: value }));
    };

    const handleOpacityChange = (value) => {
        setOpacity(value / 100);
    };

    const handleUiScalingChange = (value) => {
        setUiScaling(value);
    };


    const scale = position.z >= 0
        ? (1 - position.z / 200) * (ui_scaling / 100)
        : (1 + Math.abs(position.z) / 200) * (ui_scaling / 100);


    const x_factor = Math.min(Math.abs(position.x) / 100, 1);
    const y_factor = Math.min(Math.abs(position.y) / 100, 1);

    const translate_x = position.x + (position.z * x_factor * (position.x >= 0 ? -1 : 1));
    const translate_y = -1 * (position.y + (position.z * y_factor * (position.y >= 0 ? -1 : 1)));


    return (
        <div className={styles.app}>
            <div className={styles.canvas_container}>
                <div className={styles.z_position}>
                    <label>Z Position</label>
                    <Slider
                        variable={position.z}
                        step={1}
                        min={-100}
                        max={100}
                        onchangeFunction={(value) => handlePositionChange("z", value)}
                        orientation="vertical"
                    />
                </div>
                <div className={styles.canvas}>
                    <div
                        className={styles.chat_box}
                        style={{
                            transform: `
                                translate(${translate_x}px, ${translate_y}px)
                                scale(${scale})
                                rotateX(${rotation.rotate_x}deg)
                                rotateY(${rotation.rotate_y}deg)
                                rotateZ(${rotation.rotate_z}deg)
                            `,
                            opacity: opacity
                        }}
                    >
                        <p className={styles.chat_text}>
                            実際の表示とは大きく違います。これはただのイメージ図です。
                        </p>
                    </div>
                </div>
                <div className={styles.y_position}>
                    <label>Y Position</label>
                    <Slider
                        variable={position.y}
                        step={1}
                        min={-100}
                        max={100}
                        onchangeFunction={(value) => handlePositionChange("y", value)}
                        orientation="vertical"
                    />
                </div>
                <div className={styles.x_position}>
                    <label>X Position</label>
                    <Slider
                        variable={position.x}
                        step={1}
                        min={-100}
                        max={100}
                        onchangeFunction={(value) => handlePositionChange("x", value)}
                    />
                </div>
            </div>
            <div className={styles.other_controls}>
                <div className={styles.x_rotation}>
                    <label>X Rotation</label>
                    <Slider
                        variable={rotation.rotate_x}
                        step={1}
                        min={-180}
                        max={180}
                        onchangeFunction={(value) => handleRotationChange("rotate_x", value)}
                    />
                </div>
                <div className={styles.y_rotation}>
                    <label>Y Rotation</label>
                    <Slider
                        variable={rotation.rotate_y}
                        step={1}
                        min={-180}
                        max={180}
                        onchangeFunction={(value) => handleRotationChange("rotate_y", value)}
                    />
                </div>
                <div className={styles.z_rotation}>
                    <label>Z Rotation</label>
                    <Slider
                        variable={rotation.rotate_z}
                        step={1}
                        min={-180}
                        max={180}
                        onchangeFunction={(value) => handleRotationChange("rotate_z", value)}
                    />
                </div>
                <div className={styles.opacity}>
                    <label>Opacity</label>
                    <Slider
                        variable={opacity * 100}
                        step={1}
                        min={0}
                        max={100}
                        onchangeFunction={handleOpacityChange}
                    />
                </div>
                <div className={styles.ui_scaling}>
                    <label>UI Scaling</label>
                    <Slider
                        variable={ui_scaling}
                        step={1}
                        min={40}
                        max={200}
                        onchangeFunction={handleUiScalingChange}
                    />
                </div>
            </div>
        </div>
    );
};
