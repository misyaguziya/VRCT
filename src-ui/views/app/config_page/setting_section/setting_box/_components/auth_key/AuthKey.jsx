import styles from "./AuthKey.module.scss";
import { useI18n } from "@useI18n";
import { _Entry } from "../_atoms/_entry/_Entry";
import { _SaveButton } from "../_atoms/_save_button/_SaveButton";
import { useState, useRef, useEffect } from "react";

export const AuthKey = (props) => {
    const { t } = useI18n();
    const [is_editable, seIsEditable] = useState(false);
    const entryRef = useRef(null);

    const revealEditAuthKey = () => {
        seIsEditable(true);
        entryRef.current.focus();
    };

    const onChangeEntryAuthKey = (e) => {
        props.onChangeFunction(e.target.value);
    };
    const saveAuthKey = () => {
        props.saveFunction();
    };

    useEffect(() => {
        if (props.variable === "" || props.variable === null) {
            seIsEditable(true);
        }
    }, [props.variable]);

    const is_disabled = props.state === "pending";

    const handleEnterPressed = (e) => {
        if (is_disabled) return;
        saveAuthKey();
        entryRef.current?.blur();
    };

    return (
        <div className={styles.container}>
            <div className={styles.entry_section_wrapper}>
                <_Entry ref={entryRef} width="24rem" onChange={onChangeEntryAuthKey} onEnterPressed={handleEnterPressed} ui_variable={props.variable} is_disabled={is_disabled}/>
                <_SaveButton onClick={saveAuthKey} is_disabled={is_disabled} />
                {is_editable
                ? null
                :
                    <div className={styles.entry_edit_cover} onClick={revealEditAuthKey}>
                        <button className={styles.edit_button}>{t("config_page.translation.deepl_auth_key.edit")}</button>
                    </div>
                }
            </div>
        </div>
    );
};