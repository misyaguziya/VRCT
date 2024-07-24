import styles from "./LabelComponent.module.scss";

export const LabelComponent = (props) => {
    return (
        <div className={styles.label_component}>
            <p>{props.label}</p>
            <p>{props.desc}</p>
        </div>
    );
};