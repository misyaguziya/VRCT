import styles from "./DownloadModelsContainer.module.scss";
import vrct_logo_for_dark_mode from "@images/vrct_logo_for_dark_mode.png";
import vrct_now_downloading from "@images/VRCT_now_downloading.png";

import {
    useCTranslate2WeightTypeStatus,
    useWhisperWeightTypeStatus,
} from "@logics_configs";

export const DownloadModelsContainer = () => {
    const { currentCTranslate2WeightTypeStatus } = useCTranslate2WeightTypeStatus();
    const { currentWhisperWeightTypeStatus } = useWhisperWeightTypeStatus();

    const c_translate_2 = currentCTranslate2WeightTypeStatus.data.find(d => d.id === "small");
    const whisper = currentWhisperWeightTypeStatus.data.find(d => d.id === "base");

    if (c_translate_2.progress === null && whisper.progress === null) return null;

    return (
        <div className={styles.container}>
            <div className={styles.progress_container}>
                <DownloadModelsProgress progress={c_translate_2.progress} type_label="CTranslate2 Model"/>
                <DownloadModelsProgress progress={whisper.progress} type_label="Whisper Model"/>
            </div>
            <div className={styles.labels_wrapper}>
                <img src={vrct_logo_for_dark_mode} className={styles.logo_img}/>
                <img src={vrct_now_downloading} className={styles.vrct_now_downloading_img}/>
            </div>
        </div>
    );
};


const DownloadModelsProgress = (props) => {
    if (props.progress === null) return null;
    const circular_progress = Math.floor(props.progress / 5) * 5;

    const progress_color = generateGradientColor({
        value: circular_progress,
        colorStart: [242, 242, 242], // #f2f2f2
        colorEnd: [72, 164, 149], // #48a495
    });

    return(
        <div className={styles.progress_bar_container}>
            <div className={styles.progress_bar_wrapper}>
                <div
                    className={styles.progress_bar}
                    style={{
                        width: `${props.progress}%`,
                        backgroundColor: progress_color,
                    }}
                />
            </div>
            <p className={styles.progress_label}>{`${props.type_label}: ${Math.round(props.progress)}%`}</p>
        </div>
    );
};


const generateGradientColor = ({ value, colorStart, colorEnd }) => {
    const normalizedValue = Math.max(0, Math.min(100, value)) / 100;
    const interpolatedColor = colorStart.map((start, i) => {
        const end = colorEnd[i];
        return Math.round(start + (end - start) * normalizedValue);
    });
    const hexColor = `#${interpolatedColor.map(val => val.toString(16).padStart(2, '0')).join('')}`;
    return hexColor;
};