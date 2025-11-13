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
            {props.dropdown_settings.map((dropdown_props, index) => {
                if (dropdown_props.insert_component) {
                    const InsertComponent = dropdown_props.insert_component;
                    return <InsertComponent key={index} {...dropdown_props.insert_component_props} />;
                }
                return (
                    <DropdownMenu key={dropdown_props.dropdown_id} {...dropdown_props} />
                );
            }
        )}
        </div>
    );
};