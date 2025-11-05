import styles from "./HotkeysEntry.module.scss";
import { _Entry } from "../_atoms/_entry/_Entry";
import { useState, useRef, useEffect } from "react";
import DeleteSvg from "@images/cancel.svg?react";
import clsx from "clsx";

export const HotkeysEntry = (props) => {
    const [isAcceptingInput, setIsAcceptingInput] = useState(false);
    const [displayValue, setDisplayValue] = useState("");
    const lastKeyRef = useRef(null);
    const isModifierOnlyRef = useRef(false);
    const entryRef = useRef(null);
    const pressedKeys = useRef(new Set());
    const keysRef = useRef([]);

    useEffect(() => {
        const init_display_value = props.value[props.hotkey_id] ? props.value[props.hotkey_id].join(" + ") : "";
        setDisplayValue(init_display_value);
    }, []);

    const updateHotkeys = (keys) => {
        entryRef.current.blur();
        const result = props.setHotkeys({ [props.hotkey_id]: keys });
        if (result === false) setDisplayValue("");
    };

    const processKey = (key) => {
        if (/^[a-zA-Z]$/.test(key)) return key.toUpperCase();
        if (key === "Meta") return "Super";
        return key;
    };

    const handleKeyInput = (event) => {
        const keys = [];
        const nonModifierKeys = [];

        ["Ctrl", "Shift", "Alt", "Meta"].forEach((modKey) => {
            if (event[`${modKey.toLowerCase()}Key`] && !keys.includes(modKey)) {
                let register_mod_key =  (modKey === "Meta") ? "Super" : modKey;
                keys.push(register_mod_key);
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
            } else {
                const display_value = props.value[props.hotkey_id] ? props.value[props.hotkey_id].join(" + ") : "";
                setDisplayValue(display_value);
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

    const is_pending = props.state === "pending";
    return (
        <div className={styles.container}>
            {is_pending && <span className={styles.loader}></span>}
            <_Entry
                ref={entryRef}
                type="text"
                onFocus={() => setIsAcceptingInput(true)}
                onBlur={handleBlur}
                onKeyDown={handleKeyDown}
                onKeyUp={handleKeyUp}
                ui_variable={displayValue}
                width="20rem"
                is_activated={isAcceptingInput}
                is_disabled={is_pending}
                readOnly
            />
            <button className={clsx(styles.delete_button, { [styles.is_pending]: is_pending })} onClick={handleDelete}>
                <DeleteSvg className={styles.delete_svg}/>
            </button>
        </div>
    );
};
