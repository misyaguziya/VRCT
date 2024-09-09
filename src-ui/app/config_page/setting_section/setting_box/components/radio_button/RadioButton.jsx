import styles from "./RadioButton.module.scss";

export const RadioButton = (props) => {
    return (
        <div className={styles.container}>
            {props.options.map((option) => (
                <label key={option.radio_button_id} className={styles.radio_button_wrapper}>
                    {props.checked_variable.data === option.radio_button_id
                        ? <>
                            { props.checked_variable.state === "loading" && <span className={styles.loader}></span> }
                            <input
                                type="radio"
                                name="radio"
                                value={option.radio_button_id}
                                onChange={() => props.selectFunction(option.radio_button_id)}
                                checked
                            />
                        </>
                        : <input
                            type="radio"
                            name="radio"
                            value={option.radio_button_id}
                            onChange={() => props.selectFunction(option.radio_button_id)}
                        />
                    }
                    <p className={styles.radio_button_label}>{option.label}</p>
                </label>
            ))}
        </div>
    );
};
