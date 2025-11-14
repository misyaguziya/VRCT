import styles from "./_OpenWebpageButton.module.scss";
import ExternalLink from "@images/external_link.svg?react";

export const _OpenWebpageButton = (props) => {
    return (
        <div className={styles.open_webpage_button_wrapper}>
            <a className={styles.open_webpage_button} href={props.webpage_url} target="_blank" rel="noreferrer" >
                <p className={styles.open_webpage_text}>{props.open_webpage_label}</p>
                <ExternalLink className={styles.external_link_svg} />
            </a>
        </div>
    );
};