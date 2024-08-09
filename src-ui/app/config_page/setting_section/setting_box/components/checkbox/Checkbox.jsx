import React, { useState } from 'react';
import styles from "./Checkbox.module.scss";

export const Checkbox = (props) => {
    const [isChecked, setIsChecked] = useState(false);

    const handleCheckboxChange = () => {
        setIsChecked(!isChecked);
    };

    return (
        <div className={styles.checkbox_container}>
            <label className={styles.checkbox_wrapper} htmlFor={props.checkbox_id}>
                <input
                    type="checkbox"
                    id={props.checkbox_id}
                    checked={isChecked}
                    onChange={handleCheckboxChange}
                />
                <span className={styles.cbx}>
                    <svg viewBox="0 0 12 12">
                        <polyline points="1 6.29411765 4.5 10 11 1"></polyline>
                    </svg>
                </span>
            </label>
        </div>
    );
};
