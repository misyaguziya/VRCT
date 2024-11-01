import React, { useRef, forwardRef, useImperativeHandle } from "react";
import styles from "./_Entry.module.scss";

const _Entry = forwardRef((props, ref) => {
    const inputRef = useRef();

    useImperativeHandle(ref, () => ({
        focus: () => {
            inputRef.current.focus();
        }
    }));

    return (
        <div className={styles.entry_container}>
            <div
                className={styles.entry_wrapper}
                style={{width: props.width }}
            >
                <input
                    ref={inputRef}
                    className={styles.entry_input_area}
                    value={props.ui_variable === null ? "" : props.ui_variable}
                    onChange={(e) => props.onChange(e)}
                />
            </div>
        </div>
    );
});

_Entry.displayName = "_Entry";

export { _Entry };