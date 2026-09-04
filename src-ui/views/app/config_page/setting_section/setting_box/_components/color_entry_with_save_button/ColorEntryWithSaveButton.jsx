import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { HexColorPicker } from "react-colorful";

import styles from "./ColorEntryWithSaveButton.module.scss";
import { _Entry } from "../_atoms/_entry/_Entry";
import { _SaveButton } from "../_atoms/_save_button/_SaveButton";
import { clsx } from "clsx";

const HEX_COLOR_RE = /^#[0-9a-fA-F]{6}$/;
const PICKER_GAP_REM = 0.4;
const VIEWPORT_PADDING_REM = 0.8;

const remToPx = (rem) => {
    const root_font_size = parseFloat(getComputedStyle(document.documentElement).fontSize);
    return rem * root_font_size;
};

export const ColorEntryWithSaveButton = (props) => {
    const is_disabled = props.state === "pending";
    const [is_open, setIsOpen] = useState(false);
    const [placement, setPlacement] = useState({ open_above: true, align_end: true });
    const popover_ref = useRef(null);
    const swatch_ref = useRef(null);

    const current_color = useMemo(() => {
        if (typeof props.variable !== "string") return "";
        return props.variable.trim();
    }, [props.variable]);

    const is_valid_color = useMemo(() => HEX_COLOR_RE.test(current_color), [current_color]);
    const swatch_color = is_valid_color ? current_color : "transparent";
    const picker_color = is_valid_color ? current_color : "#FFFFFF";

    const onChangeFunction = (e) => {
        props.onChangeFunction?.(e.target.value);
    };

    const onPickerChange = (color) => {
        props.onChangeFunction?.(color);
    };

    const openPicker = () => {
        if (is_disabled) return;
        setIsOpen(true);
    };

    const closePicker = () => {
        setIsOpen(false);
    };

    const saveFunction = () => {
        closePicker();
        props.saveFunction();
    };

    useLayoutEffect(() => {
        if (!is_open) return;

        const updatePlacement = () => {
            const swatch = swatch_ref.current;
            const popover = popover_ref.current;
            if (!swatch || !popover) return;

            const swatch_rect = swatch.getBoundingClientRect();
            const popover_height = popover.offsetHeight;
            const popover_width = popover.offsetWidth;
            const gap = remToPx(PICKER_GAP_REM);
            const viewport_padding = remToPx(VIEWPORT_PADDING_REM);

            const space_below = window.innerHeight - swatch_rect.bottom - gap - viewport_padding;
            const space_above = swatch_rect.top - gap - viewport_padding;
            const space_right = window.innerWidth - swatch_rect.left - viewport_padding;

            setPlacement({
                open_above: space_below < popover_height && space_above > space_below,
                align_end: space_right < popover_width,
            });
        };

        updatePlacement();
        window.addEventListener("resize", updatePlacement);
        return () => {
            window.removeEventListener("resize", updatePlacement);
        };
    }, [is_open]);

    useEffect(() => {
        if (!is_open) return;
        const onDocumentMouseDown = (event) => {
            if (popover_ref.current?.contains(event.target)) return;
            if (swatch_ref.current?.contains(event.target)) return;
            closePicker();
        };
        const onKeyDown = (event) => {
            if (event.key === "Escape") closePicker();
        };
        document.addEventListener("mousedown", onDocumentMouseDown);
        document.addEventListener("keydown", onKeyDown);
        return () => {
            document.removeEventListener("mousedown", onDocumentMouseDown);
            document.removeEventListener("keydown", onKeyDown);
        };
    }, [is_open]);

    const swatch_button_class_names = clsx(styles.swatch_button, {
        [styles.is_disabled]: is_disabled,
    });

    const popover_paper_class_names = clsx(styles.popover_paper, {
        [styles.open_above]: placement.open_above,
        [styles.open_below]: !placement.open_above,
        [styles.align_end]: placement.align_end,
        [styles.align_start]: !placement.align_end,
    });

    const handleEnterPressed = (e) => {
        if (is_disabled) return;
        saveFunction();
        e.target.blur();
    };

    return (
        <div className={styles.container}>
            <_Entry
                width={props.width}
                onChange={onChangeFunction}
                onEnterPressed={handleEnterPressed}
                ui_variable={props.variable}
                is_disabled={is_disabled}
            />
            <div className={styles.swatch_wrapper}>
                <button
                    ref={swatch_ref}
                    className={swatch_button_class_names}
                    type="button"
                    aria-label="Open color picker"
                    onClick={openPicker}
                >
                    <span className={styles.swatch} style={{ backgroundColor: swatch_color }} />
                </button>
                {is_open && (
                    <div ref={popover_ref} className={popover_paper_class_names}>
                        <div className={styles.popover_content}>
                            <HexColorPicker color={picker_color} onChange={onPickerChange} />
                        </div>
                    </div>
                )}
            </div>
            <_SaveButton onClick={saveFunction} is_disabled={is_disabled} />
        </div>
    );
};
