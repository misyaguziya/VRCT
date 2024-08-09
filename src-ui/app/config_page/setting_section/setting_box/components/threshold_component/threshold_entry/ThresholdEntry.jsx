import { useState, useEffect } from "react";
import styles from "./ThresholdEntry.module.scss";

export const ThresholdEntry = () => {
    const [input_value, setInputValue] = useState();

    const onChangeFunction = (e) => {
        setInputValue(e.currentTarget.value);
    };


    return (
        <div className={styles.container}>
            <div className={styles.entry_wrapper}>
                <input
                    className={styles.entry_input_area}
                    onChange={onChangeFunction}
                />
            </div>
        </div>
    );
};