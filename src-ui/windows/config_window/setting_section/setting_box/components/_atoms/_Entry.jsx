import React, { useState, useRef, forwardRef, useImperativeHandle } from "react";
import styles from "./_Entry.module.scss";

const _Entry = forwardRef(({ width, onChange, initialValue = "" }, ref) => {
    const [input_value, setInputValue] = useState(initialValue);
    const inputRef = useRef();

    const onChangeFunction = (e) => {
        setInputValue(e.currentTarget.value);
        if (onChange) {
            onChange(e);
        }
    };

    useImperativeHandle(ref, () => ({
        focus: () => {
            inputRef.current.focus();
        }
    }));

    return (
        <div className={styles.entry_container}>
            <div
                className={styles.entry_wrapper}
                style={{ width }}
            >
                <input
                    ref={inputRef}
                    className={styles.entry_input_area}
                    value={input_value}
                    onChange={onChangeFunction}
                />
            </div>
        </div>
    );
});

_Entry.displayName = "_Entry";

export { _Entry };