import { useState, useEffect } from "react";
import styles from "./ThresholdEntry.module.scss";
import { useConfig } from "@logics/useConfig";

export const ThresholdEntry = (props) => {
    return (
        <div className={styles.container}>
            <div className={styles.entry_wrapper}>
                {props.id === "mic_threshold"
                    ? <ThresholdEntry_Mic />
                    : <ThresholdEntry_Speaker />
                }
            </div>
        </div>
    );
};

const ThresholdEntry_Mic = () => {
    const { currentMicThreshold, setMicThreshold } = useConfig();
    const onChangeFunction = (e) => {
        setMicThreshold(e.currentTarget.value);
    };

    return (
        <input
            className={styles.entry_input_area}
            onChange={onChangeFunction}
            value={currentMicThreshold}
        />
    );
};

const ThresholdEntry_Speaker = () => {
    const { currentSpeakerThreshold, setSpeakerThreshold } = useConfig();
    const onChangeFunction = (e) => {
        setSpeakerThreshold(e.currentTarget.value);
    };

    return (
        <input
            className={styles.entry_input_area}
            onChange={onChangeFunction}
            value={currentSpeakerThreshold}
        />
    );
};