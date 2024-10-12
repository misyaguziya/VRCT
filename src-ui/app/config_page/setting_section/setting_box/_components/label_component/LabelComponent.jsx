import styles from "./LabelComponent.module.scss";

export const LabelComponent = (props) => {
    return (
        <div className={styles.label_component}>
            <p className={styles.label}>{props.label}</p>
            {props.desc
                ? <p className={styles.desc}>{props.desc}</p>
                : null
            }
        </div>
    );
};