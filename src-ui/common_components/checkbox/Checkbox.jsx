import { clsx } from "clsx";
import styles from "./Checkbox.module.scss";
export const Checkbox = ({
    checkboxId,
    variable,
    toggleFunction,
    size = "2.8rem",
    color = "var(--primary_600_color)",
    borderWidth = "0.2rem",
    padding = "2rem",
}) => {

    const wrapper_class_names = clsx(styles.checkbox_wrapper, {
        [styles.is_disabled]: variable.state === "pending",
    });

    return (
        <div className={styles.checkbox_container}>
            <label
                className={wrapper_class_names}
                htmlFor={checkboxId}
                style={{
                    "--checkbox-size": size,
                    "--checkbox-color": color,
                    "--checkbox-border-width": borderWidth,
                    "--checkbox-padding": padding,
                }}
            >
                {variable.state === "pending" ? (
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
