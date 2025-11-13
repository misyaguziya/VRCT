import styles from "./DeeplAuthKey.module.scss";
import { useI18n } from "@useI18n";
import clsx from "clsx";
import CircularProgress from "@mui/material/CircularProgress";
import ExternalLink from "@images/external_link.svg?react";
import { _Entry } from "../_atoms/_entry/_Entry";
import { useState, useRef } from "react";
import { useEffect } from "react";

export const DeeplAuthKey = (props) => {
    const { t } = useI18n();
    const [is_editable, seIsEditable] = useState(false);
    const entryRef = useRef(null);

    const revealEditAuthKey = () => {
        seIsEditable(true);
        entryRef.current.focus();
    };

    const onchangeEntryAuthKey = (e) => {
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

    const save_button_class_names = clsx(styles.save_button, {
        [styles.is_disabled]: is_disabled
    });

    return (
        <div className={styles.container}>
            <div className={styles.entry_section_wrapper}>
                <_Entry ref={entryRef} width="30rem" onChange={onchangeEntryAuthKey} ui_variable={props.variable} is_disabled={is_disabled}/>
                <button className={save_button_class_names} onClick={saveAuthKey}>
                    {is_disabled
                    ? <CircularProgress size="1.4rem" sx={{ color: "var(--dark_basic_text_color)" }}/>
                    : <p className={styles.save_button_label}>{t("config_page.translation.deepl_auth_key.save")}</p>
                }
                </button>
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


export const OpenWebpage_DeeplAuthKey = (props) => {
    return (
        <div className={styles.open_webpage_button_wrapper}>
            <a className={styles.open_webpage_button} href={props.webpage_url} target="_blank" rel="noreferrer" >
                <p className={styles.open_webpage_text}>{props.open_webpage_label}</p>
                <ExternalLink className={styles.external_link_svg} />
            </a>
        </div>
    );
};