import styles from "./RadioButton.module.scss";
import clsx from "clsx";

export const RadioButton = (props) => {
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
                        </label>
                        {props.ChildComponent && <props.ChildComponent option={option} {...props} />}
                    </div>
                );
            })}
        </div>
    );
};
