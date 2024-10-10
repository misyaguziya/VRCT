import styles from "./SliderAndMeter.module.scss";
import {
    useStore_MicVolume,
    useStore_SpeakerVolume,
} from "@store";
import {
    useMicThreshold,
    useSpeakerThreshold,
} from "@logics_configs";

export const SliderAndMeter = (props) => {
    return (
        <div className={styles.container}>
            <div className={styles.meter_container}>
                {props.id === "mic_threshold"
                    ? <ThresholdVolumeMeter_Mic {...props}/>
                    : <ThresholdVolumeMeter_Speaker {...props}/>
                }
            </div>
        </div>
    );
};

const ThresholdVolumeMeter_Mic = (props) => {
    const { currentMicVolume } = useStore_MicVolume();

    const { currentEnableAutomaticMicThreshold } = useMicThreshold();

    const currentVolumeVariable = Math.min(currentMicVolume.data, props.max);
    const volume_width_percentage = (currentVolumeVariable / props.max) * 100;

    return (
        <>
            <VolumeMeter volume_width_percentage={volume_width_percentage} volume={currentVolumeVariable} threshold={props.ui_threshold}/>
            {currentEnableAutomaticMicThreshold.data === false &&
                <input
                    type="range"
                    min={props.min}
                    max={props.max}
                    value={props.ui_threshold}
                    onChange={(e) => props.setUiThresholdFunction(e.target.value)}
                    onMouseUp={(e) => props.setThresholdFunction(e.target.value)}
                    className={styles.threshold_slider}
                />
            }
        </>
    );
};

const ThresholdVolumeMeter_Speaker = (props) => {
    const { currentSpeakerVolume } = useStore_SpeakerVolume();

    const { currentEnableAutomaticSpeakerThreshold } = useSpeakerThreshold();

    const currentVolumeVariable = Math.min(currentSpeakerVolume.data, props.max);
    const volume_width_percentage = (currentVolumeVariable / props.max) * 100;

    return (
        <>
            <VolumeMeter volume_width_percentage={volume_width_percentage} volume={currentVolumeVariable} threshold={props.ui_threshold} />
            {currentEnableAutomaticSpeakerThreshold.data === false &&
                <input
                    type="range"
                    min={props.min}
                    max={props.max}
                    value={props.ui_threshold}
                    onChange={(e) => props.setUiThresholdFunction(e.target.value)}
                    onMouseUp={(e) => props.setThresholdFunction(e.target.value)}
                    className={styles.threshold_slider}
                />
            }
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