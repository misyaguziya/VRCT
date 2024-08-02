import { useState } from "react";
import styles from "./Entry.module.scss";

export const Entry = (props) => {
    const [input_value, setInputValue] = useState();

    const onChangeFunction = (e) => {
        setInputValue(e.currentTarget.value);
    };


    return (
        <div className={styles.entry_container}>
            <div className={styles.entry_wrapper}>
                <input
                    className={styles.entry_input_area}
                    onChange={onChangeFunction}
                />
            </div>
        </div>
    );
};
