import styles from "./LabelComponent.module.scss";

export const LabelComponent = (props) => {
    return (
        <div className={styles.label_component}>
            <p className={styles.label}>{props.label}</p>
            <p className={styles.desc}>{props.desc}</p>
        </div>
    );
};