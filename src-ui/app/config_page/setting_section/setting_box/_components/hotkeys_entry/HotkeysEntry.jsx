import styles from "./HotkeysEntry.module.scss";
import { _Entry } from "../_atoms/_entry/_Entry";
import { useState, useRef } from "react";

export const HotkeysEntry = (props) => {
    const [isAcceptingInput, setIsAcceptingInput] = useState(false);
    const [displayValue, setDisplayValue] = useState(props.value[props.hotkey_id]);
    const lastKeyRef = useRef(null);
    const isModifierOnlyRef = useRef(false);
    const entryRef = useRef(null);
    const pressedKeys = useRef(new Set());
    const keysRef = useRef([]);

    const updateHotkeys = (keys) => {
        entryRef.current.blur();
        props.setHotkeys({ [props.hotkey_id]: keys });
    };

    const processKey = (key) => {
        if (/^[a-zA-Z]$/.test(key)) return key.toUpperCase();
        if (key === "Meta") return "Super";
        return key;
    };

    const handleKeyInput = (event) => {
        const keys = [];
        const nonModifierKeys = [];

        ["Ctrl", "Shift", "Alt", "Super"].forEach((modKey) => {
            if (event[`${modKey.toLowerCase()}Key`] && !keys.includes(modKey)) {
                keys.push(modKey);
            }
        });

        const key = processKey(event.key);
        if (!["Control", "Shift", "Alt", "Meta"].includes(event.key)) {
            keys.push(key);
            nonModifierKeys.push(key);
        }

        if (!pressedKeys.current.has(key)) {
            pressedKeys.current.add(key);
        }

        keysRef.current = keys;
        setDisplayValue(keys.join(" + "));
        isModifierOnlyRef.current = nonModifierKeys.length === 0;
    };

    const handleKeyDown = (event) => {
        event.preventDefault();
        if (lastKeyRef.current === event.key) return;

        lastKeyRef.current = event.key;
        handleKeyInput(event);
    };

    const handleKeyUp = (event) => {
        lastKeyRef.current = null;

        const key = processKey(event.key);
        pressedKeys.current.delete(key);

        if (isModifierOnlyRef.current) {
            setDisplayValue("");
        }

        if (pressedKeys.current.size === 0) {
            const hasNonModifierKeys = keysRef.current.some(
                (key) => !["Ctrl", "Shift", "Alt", "Super"].includes(key)
            );
            if (hasNonModifierKeys) {
                updateHotkeys(keysRef.current);
            }
        }
    };

    const handleBlur = () => {
        setIsAcceptingInput(false);
        pressedKeys.current.clear();
    };

    const handleDelete = () => {
        updateHotkeys(null);
        setDisplayValue("");
    };

    return (
        <div className={styles.container}>
            <_Entry
                ref={entryRef}
                type="text"
                placeholder="Press hotkeys keys"
                onFocus={() => setIsAcceptingInput(true)}
                onBlur={handleBlur}
                onKeyDown={handleKeyDown}
                onKeyUp={handleKeyUp}
                value={displayValue}
                width="20rem"
                is_activated={isAcceptingInput}
                readOnly
            />
            <button className={styles.delete_button} onClick={handleDelete}>
                Delete
            </button>
        </div>
    );
};
