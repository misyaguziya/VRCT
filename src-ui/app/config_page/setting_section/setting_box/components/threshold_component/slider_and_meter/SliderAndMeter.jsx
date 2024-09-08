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
                    ? <ThresholdVolumeMeter_Mic min={props.min} max={props.max}/>
                    : <ThresholdVolumeMeter_Speaker min={props.min} max={props.max}/>
                }
            </div>
            <DevSection {...props}/>
        </div>
    );
};


const ThresholdVolumeMeter_Mic = ({min, max}) => {
    const [threshold, setThreshold] = useState(max / 2);

    const { currentMicVolume } = useMicVolume();

    const currentVolumeVariable = Math.min(currentMicVolume.data, max);
    const volume_width_percentage = (currentVolumeVariable / max) * 100;

    return (
        <>
            <VolumeMeter volume_width_percentage={volume_width_percentage} volume={currentVolumeVariable} threshold={threshold}/>
            <input
                type="range"
                min={min}
                max={max}
                value={threshold}
                onChange={(e) => setThreshold(e.target.value)}
                className={styles.threshold_slider}
            />
        </>
    );
};


const ThresholdVolumeMeter_Speaker = ({min, max}) => {
    const [threshold, setThreshold] = useState(max / 2);

    const { currentSpeakerVolume } = useSpeakerVolume();

    const currentVolumeVariable = Math.min(currentSpeakerVolume.data, max);
    const volume_width_percentage = (currentVolumeVariable / max) * 100;

    return (
        <>
            <VolumeMeter volume_width_percentage={volume_width_percentage} volume={currentSpeakerVolume} threshold={threshold}/>
                <input
                type="range"
                min={min}
                max={max}
                value={threshold}
                onChange={(e) => setThreshold(e.target.value)}
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