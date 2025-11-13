import clsx from "clsx";
import { useState } from "react";
import styles from "./SwitchBox.module.scss";
import { _SwitchBox } from "../_atoms/_switch_box/_SwitchBox";

export const SwitchBox = (props) => {
    return (
        <div className={styles.container}>
            {props.secondary_label && <p className={styles.secondary_label}>{props.secondary_label}</p>}
            <_SwitchBox {...props} />
        </div>
    );
};