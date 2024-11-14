import { useState, useEffect } from "react";
import clsx from "clsx";
import CircularProgress from "@mui/material/CircularProgress";
import styles from "./DownloadModels.module.scss";
import {
    RadioButton,
    // DownloadModels,
} from "../index";
export const DownloadModels = (props) => {
    const options = props.options.map(item => ({
        ...item,
        disabled: !item.is_downloaded
    }));

    return (
        <>
            <RadioButton
                selectFunction={props.selectFunction}
                name={props.name}
                options={options}
                checked_variable={props.checked_variable}
                column={true}
                ChildComponent={ModelSelector}
                downloadStartFunction={props.downloadStartFunction}
            />
        </>
        // <div className={styles.container}>
        //     {props.models.map((option) => (
        //         <ModelSelector key={option.model_id} option={option} {...props}/>
        //     ))}
        // </div>
    );
};

const ModelSelector = ({option, ...props}) => {
    const [circular_color, setCircularColor] = useState("");
    const [circular_color_2, setCircularColor2] = useState("");
    useEffect(() => {
        const circular_color = getComputedStyle(document.documentElement).getPropertyValue("--dark_600_color");
        setCircularColor(circular_color.trim());
        const circular_color_2 = getComputedStyle(document.documentElement).getPropertyValue("--primary_300_color");
        setCircularColor2(circular_color_2.trim());
    }, []);


    const renderContent = () => {
        const circular_progress = Math.floor(option.progress / 10) * 10;

        switch (true) {
            case option.progress !== null:
                return (
                    <>
                        <CircularProgress
                            variant={(option.progress === 100) ? "indeterminate" : "determinate"}
                            value={circular_progress}
                            size="3rem"
                            sx={{ color: circular_color_2 }}
                        />
                        <p className={styles.progress_label}>{`${Math.round(option.progress)}%`}</p>
                    </>
                );
            case option.is_pending:
                return <CircularProgress size="3rem" sx={{ color: circular_color }}/>;
            case !option.is_downloaded:
                return (
                    <button
                        className={styles.download_button}
                        onClick={() => props.downloadStartFunction(option.id)}
                    >
                        <p className={styles.download_button_label}>Download</p>
                    </button>
                );
            default:
                return null;
        }
    };

    return <div className={styles.download_container}>{renderContent()}</div>;
};
