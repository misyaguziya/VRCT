import styles from "./Checkbox.module.scss";

export const Checkbox = ({
    checkboxId,
    variable,
    toggleFunction,
    state = "idle",
    size = "2.8rem",
    color = "var(--primary_600_color)",
    borderWidth = "0.2rem",
    padding = "2rem",
}) => {

    return (
        <div className={styles.checkbox_container}>
            <label
                className={styles.checkbox_wrapper}
                htmlFor={checkboxId}
                style={{
                    "--checkbox-size": size,
                    "--checkbox-color": color,
                    "--checkbox-border-width": borderWidth,
                    "--checkbox-padding": padding,
                }}
            >
                {state === "pending" ? (
                    <span className={styles.loader}></span>
                ) : (
                    <input
                        type="checkbox"
                        id={checkboxId}
                        checked={variable.data}
                        onClick={(e) => e.stopPropagation()}
                        onChange={() => {
                            if (toggleFunction) {
                                toggleFunction();
                            }
                        }}
                    />
                )}
                <span className={styles.cbx}>
                    <svg viewBox="0 0 12 12">
                        <polyline points="1 6.29411765 4.5 10 11 1"></polyline>
                    </svg>
                </span>
            </label>
        </div>
    );
};
