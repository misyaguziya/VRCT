import { useEffect, useState } from "react";
import styles from "./ThresholdComponent.module.scss";
import { SliderAndMeter } from "./slider_and_meter/SliderAndMeter";
import { ThresholdEntry } from "./threshold_entry/ThresholdEntry";
import { VolumeCheckButton } from "./volume_check_button/VolumeCheckButton";
import { useVolume } from "@logics/useVolume";
export const ThresholdComponent = (props) => {
    return (
        <div className={styles.container}>
            {props.id === "mic_threshold"
                ? <MicComponent {...props} />
                : <SpeakerComponent {...props} />
            }
        </div>
    );
};
import MicSvg from "@images/mic.svg?react";
import { useMicThreshold } from "@logics_configs/useMicThreshold";
const MicComponent = (props) => {
    const { currentMicThreshold, setMicThreshold } = useMicThreshold();
    const [ui_threshold, setUiThreshold] = useState(currentMicThreshold);
    const {volumeCheckStart_Mic, volumeCheckStop_Mic, currentMicThresholdCheckStatus } = useVolume();


    useEffect(() => {
        setUiThreshold(currentMicThreshold);
    }, [currentMicThreshold]);

    const setUiThresholdFunction = (payload_ui_threshold) => {
        setUiThreshold(payload_ui_threshold);
    };
    const setThresholdFunction = (payload_threshold) => {
        setMicThreshold(payload_threshold);
    };

    return (
        <>
            <VolumeCheckButton
                {...props}
                SvgComponent={MicSvg}
                startFunction={volumeCheckStart_Mic}
                stopFunction={volumeCheckStop_Mic}
                isChecking={currentMicThresholdCheckStatus}
            />
            <SliderAndMeter
                {...props}
                ui_threshold={ui_threshold}
                setUiThresholdFunction={setUiThresholdFunction}
                setThresholdFunction={setThresholdFunction}
            />
            <ThresholdEntry
                {...props}
                ui_threshold={ui_threshold}
                setUiThresholdFunction={setUiThresholdFunction}
                setThresholdFunction={setThresholdFunction}
            />
        </>
    );
};
import HeadphonesSvg from "@images/headphones.svg?react";
import { useSpeakerThreshold } from "@logics_configs/useSpeakerThreshold";
const SpeakerComponent = (props) => {
    const { currentSpeakerThreshold, setSpeakerThreshold } = useSpeakerThreshold();
    const [ui_threshold, setUiThreshold] = useState(currentSpeakerThreshold);
    const {volumeCheckStart_Speaker, volumeCheckStop_Speaker, currentSpeakerThresholdCheckStatus } = useVolume();

    useEffect(() => {
        setUiThreshold(currentSpeakerThreshold);
    }, [currentSpeakerThreshold]);

    const setUiThresholdFunction = (payload_ui_threshold) => {
        setUiThreshold(payload_ui_threshold);
    };
    const setThresholdFunction = (payload_threshold) => {
        setSpeakerThreshold(payload_threshold);
    };

    return (
        <>
            <VolumeCheckButton
                {...props}
                SvgComponent={HeadphonesSvg}
                startFunction={volumeCheckStart_Speaker}
                stopFunction={volumeCheckStop_Speaker}
                isChecking={currentSpeakerThresholdCheckStatus}
            />
            <SliderAndMeter
                {...props}
                ui_threshold={ui_threshold}
                setUiThresholdFunction={setUiThresholdFunction}
                setThresholdFunction={setThresholdFunction}
            />
            <ThresholdEntry
                {...props}
                ui_threshold={ui_threshold}
                setUiThresholdFunction={setUiThresholdFunction}
                setThresholdFunction={setThresholdFunction}
            />
        </>
    );
};