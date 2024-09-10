import { useEffect, useState } from "react";
import styles from "./ThresholdComponent.module.scss";
import { SliderAndMeter } from "./slider_and_meter/SliderAndMeter";
import { ThresholdEntry } from "./threshold_entry/ThresholdEntry";
import { VolumeCheckButton } from "./volume_check_button/VolumeCheckButton";

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

import { useMicThreshold } from "@logics_configs/useMicThreshold";
const MicComponent = (props) => {
    const { currentMicThreshold, setMicThreshold } = useMicThreshold();
    const [ui_threshold, setUiThreshold] = useState(currentMicThreshold);

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

import { useSpeakerThreshold } from "@logics_configs/useSpeakerThreshold";
const SpeakerComponent = (props) => {
    const { currentSpeakerThreshold, setSpeakerThreshold } = useSpeakerThreshold();
    const [ui_threshold, setUiThreshold] = useState(currentSpeakerThreshold);

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