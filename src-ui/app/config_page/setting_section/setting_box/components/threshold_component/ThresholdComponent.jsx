import { useState } from "react";

import styles from "./ThresholdComponent.module.scss";
import { SliderAndMeter } from "./slider_and_meter/SliderAndMeter";
import { ThresholdEntry } from "./threshold_entry/ThresholdEntry";
import { VolumeCheckButton } from "./volume_check_button/VolumeCheckButton";
import { useConfig } from "@logics/useConfig";

export const ThresholdComponent = (props) => {
    return (
        <div className={styles.container}>
            <VolumeCheckButton {...props} />
            {props.id === "mic_threshold"
                ? <MicComponent {...props} />
                : <SpeakerComponent {...props} />
            }
        </div>
    );
};

const MicComponent = (props) => {
    const { currentMicThreshold, setMicThreshold } = useConfig();
    const [ui_threshold, setUiThreshold] = useState(currentMicThreshold);

    const setUiThresholdFunction = (payload_ui_threshold) => {
        setUiThreshold(payload_ui_threshold);
    };
    const setThresholdFunction = (payload_threshold) => {
        setMicThreshold(payload_threshold);
    };

    return (
        <>
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

const SpeakerComponent = (props) => {

    const { currentSpeakerThreshold, setSpeakerThreshold } = useConfig();
    const [ui_threshold, setUiThreshold] = useState(currentSpeakerThreshold);

    const setUiThresholdFunction = (payload_ui_threshold) => {
        setUiThreshold(payload_ui_threshold);
    };
    const setThresholdFunction = (payload_threshold) => {
        setSpeakerThreshold(payload_threshold);
    };

    return (
        <>
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