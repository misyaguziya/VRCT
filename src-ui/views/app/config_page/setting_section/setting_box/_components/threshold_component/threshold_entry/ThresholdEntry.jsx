import clsx from "clsx";
import styles from "./ThresholdEntry.module.scss";

export const ThresholdEntry = (props) => {
    return (
        <div className={styles.container}>
            <div className={styles.entry_wrapper}>
                {props.id === "mic_threshold"
                    ? <ThresholdEntry_Mic {...props}/>
                    : <ThresholdEntry_Speaker {...props}/>
                }
            </div>
        </div>
    );
};

const ThresholdEntry_Mic = (props) => {
    const onChangeFunction = (e) => {
        if (e.currentTarget.value === "") {
            props.setThresholdFunction("0");
        } else {
            props.setThresholdFunction(e.currentTarget.value);
        }
    };

    const class_names = clsx(styles.entry_input_area, {
        [styles.is_disable]: props.is_disable
    });

    return (
        <input
            className={class_names}
            onChange={onChangeFunction}
            value={props.ui_threshold}
        />
    );
};

const ThresholdEntry_Speaker = (props) => {
    const onChangeFunction = (e) => {
        if (e.currentTarget.value === "") {
            props.setThresholdFunction("0");
        } else {
            props.setThresholdFunction(e.currentTarget.value);
        }
    };

    const class_names = clsx(styles.entry_input_area, {
        [styles.is_disable]: props.is_disable
    });

    return (
        <input
            className={class_names}
            onChange={onChangeFunction}
            value={props.ui_threshold}
        />
    );
};