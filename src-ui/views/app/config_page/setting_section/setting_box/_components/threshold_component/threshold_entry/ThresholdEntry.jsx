import clsx from "clsx";
import { useEffect, useRef, useState } from "react";
import styles from "./ThresholdEntry.module.scss";

const INPUT_DEBOUNCE_DELAY = 1000; // ms

export const ThresholdEntry = (props) => {
    return (
        <div className={styles.container}>
            <div className={styles.entry_wrapper}>
                <ThresholdEntryInput {...props} />
            </div>
        </div>
    );
};

const ThresholdEntryInput = (props) => {
    const [inputValue, setInputValue] = useState(props.ui_threshold ?? "");
    const debounceTimerRef = useRef(null);
    const lastSavedValueRef = useRef(props.ui_threshold);
    const isFocusedRef = useRef(false);

    useEffect(() => {
        if (props.ui_threshold !== "" && props.ui_threshold !== null && props.ui_threshold !== undefined) {
            lastSavedValueRef.current = props.ui_threshold;
        }
        if (!isFocusedRef.current) {
            setInputValue(props.ui_threshold ?? "");
        }
    }, [props.ui_threshold]);

    useEffect(() => {
        return () => {
            if (debounceTimerRef.current) {
                clearTimeout(debounceTimerRef.current);
            }
        };
    }, []);

    const commitValue = (val) => {
        if (debounceTimerRef.current) {
            clearTimeout(debounceTimerRef.current);
            debounceTimerRef.current = null;
        }

        if (val === "" || val === null || val === undefined) {
            const restored = lastSavedValueRef.current ?? "";
            setInputValue(restored);
            props.setUiThresholdFunction?.(restored);
            return;
        }

        let num = parseInt(val, 10);
        if (isNaN(num)) {
            const restored = lastSavedValueRef.current ?? "";
            setInputValue(restored);
            props.setUiThresholdFunction?.(restored);
            return;
        }

        if (props.max !== undefined && num > props.max) num = props.max;
        if (props.min !== undefined && num < props.min) num = props.min;

        const normalized = String(num);
        setInputValue(normalized);
        props.setUiThresholdFunction?.(normalized);
        props.setThresholdFunction(normalized);
        lastSavedValueRef.current = normalized;
    };

    const onChangeFunction = (e) => {
        const val = e.currentTarget.value;
        if (!/^\d*$/.test(val)) {
            return;
        }

        setInputValue(val);

        if (debounceTimerRef.current) {
            clearTimeout(debounceTimerRef.current);
            debounceTimerRef.current = null;
        }

        if (val === "") {
            return;
        }

        const num = parseInt(val, 10);
        if (!isNaN(num)) {
            const clampedUi = props.max !== undefined && num > props.max
                ? props.max
                : (props.min !== undefined && num < props.min ? props.min : num);
            props.setUiThresholdFunction?.(clampedUi);
        }

        // max値を超えている場合は自動保存タイマーをセットしない（blur/Enterでの意図的な確定時にmax値へ丸めて保存）
        if (props.max !== undefined && !isNaN(num) && num > props.max) {
            return;
        }

        debounceTimerRef.current = setTimeout(() => {
            let sendNum = parseInt(val, 10);
            if (props.max !== undefined && sendNum > props.max) sendNum = props.max;
            if (props.min !== undefined && sendNum < props.min) sendNum = props.min;
            const sendVal = String(sendNum);
            props.setThresholdFunction(sendVal);
            lastSavedValueRef.current = sendVal;
            debounceTimerRef.current = null;
        }, INPUT_DEBOUNCE_DELAY);
    };

    const onFocusFunction = () => {
        isFocusedRef.current = true;
    };

    const onBlurFunction = () => {
        isFocusedRef.current = false;
        commitValue(inputValue);
    };

    const onKeyDownFunction = (e) => {
        if (e.key === "Enter" && !e.nativeEvent.isComposing && e.keyCode !== 229) {
            e.preventDefault();
            commitValue(inputValue);
            e.currentTarget.blur();
        }
    };

    const class_names = clsx(styles.entry_input_area, {
        [styles.is_disable]: props.is_disable,
    });

    return (
        <input
            className={class_names}
            value={inputValue}
            onChange={onChangeFunction}
            onFocus={onFocusFunction}
            onBlur={onBlurFunction}
            onKeyDown={onKeyDownFunction}
            disabled={props.is_disable}
        />
    );
};