import { useState, useEffect } from "react";
import styles from "./SliderAndMeter.module.scss";

export const SliderAndMeter = (props) => {
    const [volume, setVolume] = useState(0);
    const [threshold, setThreshold] = useState(props.max / 2);

    const updateVolume = () => {
        setVolume(Math.random());
    };

    // useEffect(() => {
    //     const intervalId = setInterval(updateVolume, 200);
    //     return () => clearInterval(intervalId);
    // }, []);

    return (
        <div className={styles.container}>
            <div className={styles.meter_container}>
                <div
                    className={styles.volume_meter}
                    style={{
                        width: `${(volume * 100)}%`,
                        backgroundColor: volume < (threshold / props.max) ? "var(--primary_750_color)" : "var(--primary_400_color)"
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
                <button onClick={updateVolume}>Update Volume</button>
                <div className={styles.volume_info}>
                    <span>Current Volume: {(volume * props.max).toFixed(2)}</span>
                </div>
                <div className={styles.threshold_info}>
                    <span>Threshold: {threshold}</span>
                </div>
            </div>
        </div>
    );
};
