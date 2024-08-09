import clsx from "clsx";
import { useState } from "react";
import styles from "./RadioButton.module.scss";

export const RadioButton = (props) => {
    const options = [
        { radio_button_id: "1", label: "AAAAAAAA" },
        { radio_button_id: "2", label: "BBBBBB" }
    ];

    const changeValue = (e) => {
        console.log(e.target.value);
    };

    return (
        <div className={styles.container}>
            {options.map((option) => (
                <label key={option.radio_button_id} className={styles.radio_button_wrapper}>
                    <input
                        type="radio"
                        name="radio"
                        value={option.radio_button_id}
                        onChange={changeValue}
                    />
                    <p className={styles.radio_button_label}>{option.label}</p>
                </label>
            ))}
        </div>
    );
};
