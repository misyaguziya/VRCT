import { useEffect, useState } from "react";
import styles from "./ThresholdComponent.module.scss";
import { SliderAndMeter } from "./slider_and_meter/SliderAndMeter";
import { ThresholdEntry } from "./threshold_entry/ThresholdEntry";
import { VolumeCheckButton } from "./volume_check_button/VolumeCheckButton";
import { useVolume } from "@logics_common";
import MicSvg from "@images/mic.svg?react";
import HeadphonesSvg from "@images/headphones.svg?react";
import {
    useDevice,
} from "@logics_configs";
import { useI18n } from "@useI18n";

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

const MicComponent = (props) => {
    const { t } = useI18n();
    const {
        currentMicThreshold,
        setMicThreshold,
        currentEnableAutomaticMicThreshold,
    } = useDevice();
    const [ui_threshold, setUiThreshold] = useState(currentMicThreshold.data);
    const {
        volumeCheckStart_Mic,
        volumeCheckStop_Mic,
        currentMicThresholdCheckStatus,
    } = useVolume();


    useEffect(() => {
        if (currentEnableAutomaticMicThreshold.data === true || props.is_vad_active === true) {
            setUiThreshold(t("config_page.device.mic_dynamic_energy_threshold.option_auto"));
        } else {
            setUiThreshold(currentMicThreshold.data);
        }
    }, [currentMicThreshold.data, currentEnableAutomaticMicThreshold, props.is_vad_active]);

    const setUiThresholdFunction = (payload_ui_threshold) => {
        setUiThreshold(payload_ui_threshold);
    };
    const setThresholdFunction = (payload_threshold) => {
        setMicThreshold(payload_threshold);
    };

    const is_disable = currentEnableAutomaticMicThreshold.data === true || props.is_vad_active === true ? true : false;

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
                is_disable={is_disable}
            />
        </>
    );
};

const SpeakerComponent = (props) => {
    const { t } = useI18n();
    const {
        currentSpeakerThreshold,
        setSpeakerThreshold,
        currentEnableAutomaticSpeakerThreshold,
    } = useDevice();
    const [ui_threshold, setUiThreshold] = useState(currentSpeakerThreshold.data);
    const {
        volumeCheckStart_Speaker,
        volumeCheckStop_Speaker,
        currentSpeakerThresholdCheckStatus,
    } = useVolume();

    useEffect(() => {
        if (currentEnableAutomaticSpeakerThreshold.data === true || props.is_vad_active === true) {
            setUiThreshold(t("config_page.device.speaker_dynamic_energy_threshold.option_auto"));
        } else {
            setUiThreshold(currentSpeakerThreshold.data);
        }
    }, [currentSpeakerThreshold.data, currentEnableAutomaticSpeakerThreshold, props.is_vad_active]);

    const setUiThresholdFunction = (payload_ui_threshold) => {
        setUiThreshold(payload_ui_threshold);
    };
    const setThresholdFunction = (payload_threshold) => {
        setSpeakerThreshold(payload_threshold);
    };

    const is_disable = currentEnableAutomaticSpeakerThreshold.data === true || props.is_vad_active === true ? true : false;

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
                is_disable={is_disable}
            />
        </>
    );
};