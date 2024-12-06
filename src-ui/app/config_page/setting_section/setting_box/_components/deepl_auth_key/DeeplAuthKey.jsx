import styles from "./DeeplAuthKey.module.scss";
import { useTranslation } from "react-i18next";
import clsx from "clsx";
import ExternalLink from "@images/external_link.svg?react";
import { _Entry } from "../_atoms/_entry/_Entry";
import { useState, useRef } from "react";
import { useEffect } from "react";

export const DeeplAuthKey = (props) => {
    const { t } = useTranslation();
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

    return (
        <div className={styles.container}>
            <div className={styles.entry_section_wrapper}>
                <_Entry ref={entryRef} width="30rem" onChange={onchangeEntryAuthKey} ui_variable={props.variable}/>
                <button className={styles.save_button} onClick={saveAuthKey}>Save</button>
                {is_editable
                ? null
                :
                    <div className={styles.entry_edit_cover} onClick={revealEditAuthKey}>
                        <button className={styles.edit_button}>Edit</button>
                    </div>
                }
            </div>
        </div>
    );
};


export const OpenWebpage_DeeplAuthKey = () => {
    return (
        <div className={styles.open_webpage_button_wrapper}>
            <a className={styles.open_webpage_button} href="https://www.deepl.com/ja/your-account/keys" target="_blank" rel="noreferrer" >
                <p className={styles.open_webpage_text}>Open DeepL Account Webpage</p>
                <ExternalLink className={styles.external_link_svg} />
            </a>
        </div>
    );
};