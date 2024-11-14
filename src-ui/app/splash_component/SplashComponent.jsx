import { useState, useEffect } from "react";

import CircularProgress from '@mui/material/CircularProgress';
import styles from "./SplashComponent.module.scss";
import {
    useCTranslate2WeightTypeStatus,
    useWhisperWeightTypeStatus,
} from "@logics_configs";

export const SplashComponent = () => {
    const { currentCTranslate2WeightTypeStatus } = useCTranslate2WeightTypeStatus();
    const { currentWhisperWeightTypeStatus } = useWhisperWeightTypeStatus();

    const [circular_color, setCircularColor] = useState("");
    useEffect(() => {
        const circular_color = getComputedStyle(document.documentElement).getPropertyValue("--primary_300_color");
        setCircularColor(circular_color.trim());
    }, []);

    console.log(currentCTranslate2WeightTypeStatus);
    const c_translate_2 = currentCTranslate2WeightTypeStatus.data.find(d => d.id === "small");
    const whisper = currentWhisperWeightTypeStatus.data.find(d => d.id === "base");
    console.log(c_translate_2, whisper);



    return (
        <div>
            <DownloadModelsProgress color={circular_color} progress={c_translate_2.progress}/>
            <CircularProgress size="14rem" sx={{ color: circular_color }}/>
            <DownloadModelsProgress color={circular_color} progress={whisper.progress}/>
        </div>
    );
};

const DownloadModelsProgress = (props) => {
    if (props.progress === null) return null;
    const circular_progress = Math.floor(props.progress / 10) * 10;

    return(
        <div className={styles.progress_container}>
            <CircularProgress
                variant={(props.progress === 100) ? "indeterminate" : "determinate"}
                value={circular_progress}
                size="4rem"
                sx={{ color: props.color }}
            />
            <p className={styles.progress_label}>{`${Math.round(props.progress)}%`}</p>
        </div>
    );
};