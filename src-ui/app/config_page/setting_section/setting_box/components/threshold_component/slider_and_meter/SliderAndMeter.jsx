import { useState } from "react";
import styles from "./SliderAndMeter.module.scss";
import {
    useMicVolume,
} from "@store";

import { useVolume } from "@logics/useVolume";

export const SliderAndMeter = (props) => {
    const [threshold, setThreshold] = useState(props.max / 2);
    const { currentMicVolume, updateMicVolume } = useMicVolume();

    const updateVolume = () => {
        updateMicVolume(Math.random());
    };

    const {
        volumeCheckStart_Mic,
        volumeCheckStop_Mic,
    } = useVolume();

    let currentVolumeVariable = null;
    let volume_width_percentage = 0;

    if (props.id === "mic_threshold") {
        currentVolumeVariable = Math.min(currentMicVolume.data, props.max);

        volume_width_percentage = (currentVolumeVariable / props.max) * 100;
    } else if (props.id === "speaker_threshold") {
    }

    return (
        <div className={styles.container}>
            <div className={styles.meter_container}>
                <div
                    className={styles.volume_meter}
                    style={{
                        width: `${volume_width_percentage}%`,
                        backgroundColor: (currentVolumeVariable < threshold) ? "var(--primary_750_color)" : "var(--primary_400_color)"
                    }}
                />
                <input
                    type="range"
                    min={props.min}
                    max={props.max}
                    value={threshold}
                    onChange={(e) => setThreshold(e.target.value)}
                    className={styles.threshold_slider}
                />
            </div>
            <div className={styles.dev_info_box}>
                <p>dev</p>
                <button onClick={() => volumeCheckStart_Mic()}>Start</button>
                <button onClick={() => volumeCheckStop_Mic()}>Stop</button>
                <button onClick={() => updateVolume()}>update volume</button>
                <div className={styles.volume_info}>
                    <span>Current Volume: {(currentVolumeVariable)}</span>
                </div>
                <div className={styles.threshold_info}>
                    <span>Threshold: {threshold}</span>
                </div>
            </div>
        </div>
    );
};
