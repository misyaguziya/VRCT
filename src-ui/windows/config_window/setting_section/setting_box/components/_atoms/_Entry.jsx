import React, { useState } from "react";
import styles from "./_Entry.module.scss";

export const _Entry = ({ width, onChange, initialValue = "" }) => {
    const [input_value, setInputValue] = useState(initialValue);

    const onChangeFunction = (e) => {
        setInputValue(e.currentTarget.value);
        if (onChange) {
            onChange(e);
        }
    };

    return (
        <div className={styles.entry_container}>
            <div
                className={styles.entry_wrapper}
                style={{ width }}
            >
                <input
                    className={styles.entry_input_area}
                    value={input_value}
                    onChange={onChangeFunction}
                />
            </div>
        </div>
    );
};
