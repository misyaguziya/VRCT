import styles from "./LabelComponent.module.scss";
import { _OpenWebpageButton } from "../_atoms/_open_webpage_button/_OpenWebpageButton";
import WarningSvg from "@images/warning.svg?react";

export const LabelComponent = (props) => {
    return (
        <div className={styles.label_component}>
            <p className={styles.label}>{props.label}</p>
            {props.desc
                ? <p className={styles.desc}>{props.desc}</p>
                : null
            }
            {props.add_warnings && Array.isArray(props.add_warnings) && props.add_warnings.length > 0 && (
                <div className={styles.warnings_section}>
                    {props.add_warnings.map((w, i) => (
                        <div className={styles.warning_item} key={i}>
                            <WarningSvg className={styles.warning_svg} />
                            <p className={styles.warning_label}>{w.label}</p>
                        </div>
                    ))}
                </div>
            )}

            {props.webpage_url && <_OpenWebpageButton webpage_url={props.webpage_url} open_webpage_label={props.open_webpage_label} /> }
        </div>
    );
};