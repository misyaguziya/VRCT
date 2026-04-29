import styles from "./SectionLabelComponent.module.scss";
import clsx from "clsx";

export const SectionLabelComponent = (props) => {
    return (
        <div className={styles.container}>
            <label className={styles.section_label}>{props.label}</label>
            <div className={styles.section_line}></div>
        </div>
    );
};