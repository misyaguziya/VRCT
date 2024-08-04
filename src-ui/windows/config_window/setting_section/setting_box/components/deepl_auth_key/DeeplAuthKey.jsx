import styles from "./DeeplAuthKey.module.scss";
import { useTranslation } from "react-i18next";

import clsx from "clsx";
import ExternalLink from "@images/external_link.svg?react";
import { _Entry } from "../_atoms/_Entry";
import { useState } from "react";

export const DeeplAuthKey = () => {
    const { t } = useTranslation();
    const [is_editable, seIsEditable] = useState(false);
    const [input_value, seInputValue] = useState("");

    const revealEditAuthKey = () => {
        seIsEditable(true);
    };


    const onchangeEntryAuthKey = (e) => {
        seInputValue(e.target.value);
    };
    const saveAuthKey = () => {
        console.log(input_value);
    };

    return (
        <div className={styles.container}>
            <div className={styles.entry_section_wrapper}>
                <_Entry width="32rem" onChange={onchangeEntryAuthKey}/>
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
            <a className={styles.open_webpage_button} href="https://translate.google.com/?hl=ja&tab=TT&sl=en&tl=ja&op=translate" target="_blank" rel="noreferrer" >
                <p className={styles.open_webpage_text}>Open DeepL Account Webpage</p>
                <ExternalLink className={styles.external_link_svg} />
            </a>
        </div>
    );
};