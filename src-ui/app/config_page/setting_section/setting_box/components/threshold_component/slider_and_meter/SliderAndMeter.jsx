import { useState } from "react";
import styles from "./SliderAndMeter.module.scss";
import {
    useMicVolume,
    useSpeakerVolume,
} from "@store";

import { useVolume } from "@logics/useVolume";

export const SliderAndMeter = (props) => {
    return (
        <div className={styles.container}>
            <div className={styles.meter_container}>
                {props.id === "mic_threshold"
                    ? <ThresholdVolumeMeter_Mic {...props}/>
                    : <ThresholdVolumeMeter_Speaker {...props}/>
                }
            </div>
            <DevSection {...props}/>
        </div>
    );
};


const ThresholdVolumeMeter_Mic = (props) => {
    const { currentMicVolume } = useMicVolume();

    const currentVolumeVariable = Math.min(currentMicVolume.data, props.max);
    const volume_width_percentage = (currentVolumeVariable / props.max) * 100;

    return (
        <>
            <VolumeMeter volume_width_percentage={volume_width_percentage} volume={currentVolumeVariable} threshold={props.ui_threshold}/>
            <input
                type="range"
                min={props.min}
                max={props.max}
                value={props.ui_threshold}
                onChange={(e) => props.setUiThresholdFunction(e.target.value)}
                onMouseUp={(e) => props.setThresholdFunction(e.target.value)}
                className={styles.threshold_slider}
            />
        </>
    );
};


const ThresholdVolumeMeter_Speaker = (props) => {
    const { currentSpeakerVolume } = useSpeakerVolume();

    const currentVolumeVariable = Math.min(currentSpeakerVolume.data, props.max);
    const volume_width_percentage = (currentVolumeVariable / props.max) * 100;

    return (
        <>
            <VolumeMeter volume_width_percentage={volume_width_percentage} volume={currentVolumeVariable} threshold={props.ui_threshold} />
            <input
                type="range"
                min={props.min}
                max={props.max}
                value={props.ui_threshold}
                onChange={(e) => props.setUiThresholdFunction(e.target.value)}
                onMouseUp={(e) => props.setThresholdFunction(e.target.value)}
                className={styles.threshold_slider}
            />
        </>
    );
};



const VolumeMeter = ({ volume_width_percentage, volume, threshold }) => {

    return (
        <div
            className={styles.volume_meter}
            style={{
                width: `${volume_width_percentage}%`,
                backgroundColor: (volume < threshold) ? "var(--primary_750_color)" : "var(--primary_400_color)"
            }}
        />
    );
};


const DevSection = (props) => {
    const {
        volumeCheckStart_Mic,
        volumeCheckStop_Mic,
        volumeCheckStart_Speaker,
        volumeCheckStop_Speaker,
    } = useVolume();

    const volumeCheckStart = () => {
        if (props.id === "mic_threshold") {
            volumeCheckStart_Mic();
        } else if (props.id === "speaker_threshold") {
            volumeCheckStart_Speaker();
        }
    };

    const volumeCheckStop = () => {
        if (props.id === "mic_threshold") {
            volumeCheckStop_Mic();
        } else if (props.id === "speaker_threshold") {
            volumeCheckStop_Speaker();
        }
    };

    return (
        <div className={styles.dev_info_box}>
            <p>dev</p>
            <button className={styles.volume_check_button} onClick={() => volumeCheckStart()}>Start</button>
            <button className={styles.volume_check_button} onClick={() => volumeCheckStop()}>Stop</button>
            <div className={styles.volume_info}>
                {/* <span>Current Volume: {(currentVolumeVariable)}</span> */}
            </div>
            <div className={styles.threshold_info}>
                {/* <span>Threshold: {props.threshold}</span> */}
            </div>
        </div>
    );
};