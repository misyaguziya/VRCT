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
        props.setThresholdFunction(e.currentTarget.value);
    };

    return (
        <input
            className={styles.entry_input_area}
            onChange={onChangeFunction}
            value={props.ui_threshold}
        />
    );
};

const ThresholdEntry_Speaker = (props) => {
    const onChangeFunction = (e) => {
        props.setThresholdFunction(e.currentTarget.value);
    };

    return (
        <input
            className={styles.entry_input_area}
            onChange={onChangeFunction}
            value={props.ui_threshold}
        />
    );
};