import styles from "./DeeplAuthKey.module.scss";

import clsx from "clsx";
import ExternalLink from "@images/external_link.svg?react";
import { _Entry } from "../_atoms/_Entry";

export const DeeplAuthKey = () => {

    return (
        <div className={styles.container}>
            <_Entry width="34rem"/>
            <div className={styles.open_webpage_button}>
                <p className={styles.open_webpage_text}>Open DeepL Account Webpage</p>
                <ExternalLink className={styles.external_link_svg} />
            </div>
        </div>
    );
};