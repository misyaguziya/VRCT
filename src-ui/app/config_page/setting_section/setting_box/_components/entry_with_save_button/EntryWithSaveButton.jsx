import styles from "./EntryWithSaveButton.module.scss";
import { _Entry } from "../_atoms/_entry/_Entry";
import CircularProgress from "@mui/material/CircularProgress";
import { useI18n } from "@useI18n";
import { clsx } from "clsx";

export const EntryWithSaveButton = (props) => {
    const { t } = useI18n();
    const onChangeFunction = (e) => {
        props.onChangeFunction?.(e.target.value);
    };
    const saveFunction = () => {
        props.saveFunction();
    };
    const is_disabled = props.state === "pending";

    const save_button_class_names = clsx(styles.save_button, {
        [styles.is_disabled]: is_disabled
    });

    return (
        <div className={styles.container}>
            <_Entry width={props.width} onChange={onChangeFunction} ui_variable={props.variable} is_disabled={is_disabled}/>
            <button className={save_button_class_names} onClick={saveFunction}>
                {is_disabled
                ? <CircularProgress size="1.4rem" sx={{ color: "var(--dark_basic_text_color)" }}/>
                : <p className={styles.save_button_label}>{t("config_page.translation.deepl_auth_key.save")}</p>
            }
            </button>
        </div>
    );
};