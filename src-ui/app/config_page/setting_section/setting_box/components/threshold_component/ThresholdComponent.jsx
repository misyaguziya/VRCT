import styles from "./ThresholdComponent.module.scss";
import { SliderAndMeter } from "./slider_and_meter/SliderAndMeter";
import { ThresholdEntry } from "./threshold_entry/ThresholdEntry";
import { VolumeCheckButton } from "./volume_check_button/VolumeCheckButton";

export const ThresholdComponent = (props) => {
    return (
        <div className={styles.container}>
            <VolumeCheckButton {...props}/>
            <SliderAndMeter {...props}/>
            <ThresholdEntry {...props}/>
        </div>
    );
};