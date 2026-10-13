import styles from "./SliderAndMeter.module.scss";
import {
    useStore_MicVolume,
    useStore_SpeakerVolume,
} from "@store";
import {
    useDevice,
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

const toNumericThreshold = (val, fallback = 0) => {
    const num = Number(val);
    return Number.isFinite(num) ? num : fallback;
};

const ThresholdVolumeMeter_Mic = (props) => {
    const { currentMicVolume } = useStore_MicVolume();

    const { currentEnableAutomaticMicThreshold, currentMicVadFilter } = useDevice();

    const currentVolumeVariable = Math.min(currentMicVolume.data, props.max);
    const volume_width_percentage = (currentVolumeVariable / props.max) * 100;

    const is_slider_hidden = currentEnableAutomaticMicThreshold.data === true || currentMicVadFilter.data === true;
    const slider_value = toNumericThreshold(props.ui_threshold, props.min ?? 0);

    return (
        <>
            <VolumeMeter volume_width_percentage={volume_width_percentage} volume={currentVolumeVariable} threshold={props.ui_threshold}/>
            {is_slider_hidden === false &&
                <input
                    type="range"
                    min={props.min}
                    max={props.max}
                    value={slider_value}
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

    const { currentEnableAutomaticSpeakerThreshold, currentSpeakerVadFilter } = useDevice();

    const currentVolumeVariable = Math.min(currentSpeakerVolume.data, props.max);
    const volume_width_percentage = (currentVolumeVariable / props.max) * 100;

    const is_slider_hidden = currentEnableAutomaticSpeakerThreshold.data === true || currentSpeakerVadFilter.data === true;
    const slider_value = toNumericThreshold(props.ui_threshold, props.min ?? 0);

    return (
        <>
            <VolumeMeter volume_width_percentage={volume_width_percentage} volume={currentVolumeVariable} threshold={props.ui_threshold} />
            {is_slider_hidden === false &&
                <input
                    type="range"
                    min={props.min}
                    max={props.max}
                    value={slider_value}
                    onChange={(e) => props.setUiThresholdFunction(e.target.value)}
                    onMouseUp={(e) => props.setThresholdFunction(e.target.value)}
                    className={styles.threshold_slider}
                />
            }
        </>
    );
};

const VolumeMeter = ({ volume_width_percentage, volume, threshold }) => {
    const numeric_threshold = toNumericThreshold(threshold, 0);

    return (
        <div
            className={styles.volume_meter}
            style={{
                width: `${volume_width_percentage}%`,
                backgroundColor: (volume < numeric_threshold) ? "var(--primary_750_color)" : "var(--primary_400_color)"
            }}
        />
    );
};