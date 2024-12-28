import clsx from "clsx";
import React, { useRef, forwardRef, useImperativeHandle } from "react";
import styles from "./_Entry.module.scss";

const _Entry = forwardRef((props, ref) => {
    const inputRef = useRef();

    useImperativeHandle(ref, () => ({
        focus: () => {
            inputRef.current.focus();
        }
    }));
    const input_class_names = clsx(styles.entry_input_area, {
        [styles.is_disabled]: props.is_disabled
    });

    return (
        <div className={styles.entry_container}>
            <div
                className={styles.entry_wrapper}
                style={{width: props.width }}
            >
                <input
                    ref={inputRef}
                    className={input_class_names}
                    value={props.ui_variable === null ? "" : props.ui_variable}
                    onChange={(e) => props.onChange(e)}
                />
            </div>
        </div>
    );
});

_Entry.displayName = "_Entry";

export { _Entry };