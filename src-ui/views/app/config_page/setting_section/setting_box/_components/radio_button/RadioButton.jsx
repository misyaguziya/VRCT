import styles from "./RadioButton.module.scss";
import clsx from "clsx";
import { useI18n } from "@useI18n";

export const RadioButton = (props) => {
    const { t } = useI18n();
    const has_desc = props.options.some((option) => Boolean(option.desc));
    const containerClass = clsx(styles.container, {
        [styles.column]: props.column === true,
        [styles.has_desc]: has_desc,
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
                    [styles.has_desc]: Boolean(option.desc),
                });

                return (
                    <div key={option.id} className={radioWrapperClass}>
                        <label className={labelClass}>
                            <div className={styles.radio_button_header}>
                                <input
                                    type="radio"
                                    className={styles.radio_button_input}
                                    name={props.name}
                                    value={option.id}
                                    onChange={() => props.selectFunction(option.id)}
                                    checked={props.checked_variable.data === option.id}
                                    disabled={option.disabled === true || props.checked_variable.state === "pending"}
                                />
                                <div className={styles.label_heading_wrapper}>
                                    <p className={styles.radio_button_label}>{option.label}</p>
                                    {option.capacity && (
                                        <span className={styles.capacity_label}>{option.capacity}</span>
                                    )}
                                </div>
                            </div>
                            {option.desc && (
                                <p className={styles.radio_button_desc}>{option.desc}</p>
                            )}
                        </label>
                        {props.ChildComponent && <props.ChildComponent option={option} {...props} />}
                    </div>
                );
            })}
        </div>
    );
};
