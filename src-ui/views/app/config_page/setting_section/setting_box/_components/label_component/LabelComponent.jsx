import styles from "./LabelComponent.module.scss";
import { _OpenWebpageButton } from "../_atoms/_open_webpage_button/_OpenWebpageButton";

export const LabelComponent = (props) => {
    return (
        <div className={styles.label_component}>
            <p className={styles.label}>{props.label}</p>
            {props.desc
                ? <p className={styles.desc}>{props.desc}</p>
                : null
            }
            {props.webpage_url && <_OpenWebpageButton webpage_url={props.webpage_url} open_webpage_label={props.open_webpage_label} /> }
        </div>
    );
};