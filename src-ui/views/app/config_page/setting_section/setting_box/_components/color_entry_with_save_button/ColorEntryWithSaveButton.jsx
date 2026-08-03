import { useMemo, useState } from "react";
import Popover from "@mui/material/Popover";
import ClickAwayListener from "@mui/material/ClickAwayListener";
import CircularProgress from "@mui/material/CircularProgress";
import { HexColorPicker } from "react-colorful";

import styles from "./ColorEntryWithSaveButton.module.scss";
import { _Entry } from "../_atoms/_entry/_Entry";
import { useI18n } from "@useI18n";
import { clsx } from "clsx";

const HEX_COLOR_RE = /^#[0-9a-fA-F]{6}$/;

export const ColorEntryWithSaveButton = (props) => {
    const { t } = useI18n();
    const is_disabled = props.state === "pending";
    const [anchorEl, setAnchorEl] = useState(null);

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

    const openPicker = (event) => {
        if (is_disabled) return;
        setAnchorEl(event.currentTarget);
    };

    const closePicker = () => {
        setAnchorEl(null);
    };

    const saveFunction = () => {
        closePicker();
        props.saveFunction();
    };

    const is_open = Boolean(anchorEl);

    const swatch_button_class_names = clsx(styles.swatch_button, {
        [styles.is_disabled]: is_disabled,
    });

    const save_button_class_names = clsx(styles.save_button, {
        [styles.is_disabled]: is_disabled,
    });

    return (
        <div className={styles.container}>
            <_Entry
                width={props.width}
                onChange={onChangeFunction}
                ui_variable={props.variable}
                is_disabled={is_disabled}
            />
            <button
                className={swatch_button_class_names}
                type="button"
                aria-label="Open color picker"
                onClick={openPicker}
            >
                <span className={styles.swatch} style={{ backgroundColor: swatch_color }} />
            </button>
            <button className={save_button_class_names} onClick={saveFunction}>
                {is_disabled ? (
                    <CircularProgress size="1.4rem" sx={{ color: "var(--dark_basic_text_color)" }} />
                ) : (
                    <p className={styles.save_button_label}>{t("config_page.translation.deepl_auth_key.save")}</p>
                )}
            </button>

            <Popover
                open={is_open}
                anchorEl={anchorEl}
                onClose={closePicker}
                anchorOrigin={{ vertical: "bottom", horizontal: "left" }}
                transformOrigin={{ vertical: "top", horizontal: "left" }}
                PaperProps={{ className: styles.popover_paper }}
            >
                <ClickAwayListener onClickAway={closePicker}>
                    <div className={styles.popover_content}>
                        <HexColorPicker color={picker_color} onChange={onPickerChange} />
                    </div>
                </ClickAwayListener>
            </Popover>
        </div>
    );
};
