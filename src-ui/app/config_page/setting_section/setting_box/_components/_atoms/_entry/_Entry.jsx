import clsx from "clsx";
import React, { useRef, forwardRef, useImperativeHandle } from "react";
import styles from "./_Entry.module.scss";

const _Entry = forwardRef((props, ref) => {
    const inputRef = useRef();

    useImperativeHandle(ref, () => ({
        focus: () => {
            inputRef.current.focus();
        },
        blur: () => {
            inputRef.current.blur();
        }
    }));
    const input_class_names = clsx(styles.entry_input_area, {
        [styles.is_disabled]: props.is_disabled,
    });
    const input_wrapper_class_names = clsx(styles.entry_wrapper, {
        [styles.is_activated]: props.is_activated,
    });

    return (
        <div className={styles.entry_container}>
            <div
                className={input_wrapper_class_names}
                style={{width: props.width }}
            >
                <input
                    ref={inputRef}
                    text={props.text ? props.text : "text"}
                    placeholder={props.placeholder ? props.placeholder : ""}
                    className={input_class_names}
                    value={props.ui_variable === null ? "" : props.ui_variable}
                    onChange={(e) => props.onChange?.(e)}
                    onFocus={(e) => props.onFocus?.(e)}
                    onBlur={(e) => props.onBlur?.(e)}
                    onKeyDown={(e) => props.onKeyDown?.(e)}
                    onKeyUp={(e) => props.onKeyUp?.(e)}
                    readOnly={props.readOnly === true ? true : false}
                />
            </div>
        </div>
    );
});

_Entry.displayName = "_Entry";

export { _Entry };