import styles from "./RadioButton.module.scss";
import clsx from "clsx";
import { useI18n } from "@useI18n";

export const RadioButton = (props) => {
    const { t } = useI18n();
    const containerClass = clsx(styles.container, {
        [styles.column]: props.column === true,
    });

    return (
        <div className={containerClass}>
            {props.checked_variable.state === "pending" && <span className={styles.loader}></span>}
            {props.options.map((option) => {
                const radioWrapperClass = clsx(styles.radio_button_container, {
                    [styles.is_selected]: props.checked_variable.data === option.id,
                });

                const labelClass = clsx(styles.radio_button_wrapper, {
                    [styles.is_selected]: props.checked_variable.data === option.id,
                    [styles.disabled]: option.disabled === true || props.checked_variable.state === "pending",
                });

                return (
                    <div key={option.id} className={radioWrapperClass}>
                        <label className={labelClass}>
                            <input
                                className={styles.radio_button_input}
                                type="radio"
                                name={props.name}
                                value={option.id}
                                onChange={() => props.selectFunction(option.id)}
                                checked={props.checked_variable.data === option.id}
                                disabled={option.disabled === true || props.checked_variable.state === "pending"}
                            />
                            <p className={styles.radio_button_label}>{option.label}</p>
                            {option.is_default && (
                                <span className={styles.default_badge}>
                                    {t("common.default_label")}
                                </span>
                            )}
                            {option.capacity && (
                                <span className={styles.capacity_label}>{option.capacity}</span>
                            )}
                        </label>
                        {props.ChildComponent && <props.ChildComponent option={option} {...props} />}
                    </div>
                );
            })}
        </div>
    );
};
