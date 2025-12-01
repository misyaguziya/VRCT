import styles from "./ConnectionCheckButton.module.scss";

export const ConnectionCheckButton = (props) => {
    const label = props.state === "pending"
        ? "Checking... 🌀"
        : props.variable === true
            ? "Connected ✅"
            : "Disconnected ❌";

    return (
        <div className={styles.container}>
            <p>{label}</p>
            <p>{`UI Status: ${props.state}`}</p>
            <button className={styles.button_wrapper} onClick={props.checkFunction}>
                <p className={styles.button_label}>Connection Check</p>
            </button>
        </div>
    );
};