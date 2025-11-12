import styles from "./DropdownMenu.module.scss";
import { _DropdownMenu } from "../_atoms/_dropdown_menu/_DropdownMenu";

export const DropdownMenu = (props) => {
    return (
        <div className={styles.each_dropdown_menu_wrapper}>
            {props.secondary_label && <p className={styles.secondary_label}>{props.secondary_label}</p>}
            <_DropdownMenu {...props} />
        </div>
    );
};

export const MultiDropdownMenu = (props) => {
    return (
        <div className={styles.container}>
            {props.settings.map((dropdown_props, index) => (
                <DropdownMenu {...dropdown_props} />
            ))}
        </div>
    );
};