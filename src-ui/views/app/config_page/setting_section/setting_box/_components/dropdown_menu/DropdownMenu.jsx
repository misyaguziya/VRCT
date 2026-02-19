import clsx from "clsx";
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
    const container_class = clsx(styles.container, {
        [styles.is_break_point]: props.is_break_point,
    });

    return (
        <div className={container_class}>
            {(() => {
                const beforeInserts = [];
                const afterInserts = [];
                const innerSettings = [];

                props.dropdown_settings.forEach((dropdown_props, index) => {
                    if (dropdown_props.insert_component && dropdown_props.insert_to === "before") {
                        beforeInserts.push({ props: dropdown_props, key: `before-${index}` });
                    } else if (dropdown_props.insert_component && dropdown_props.insert_to === "after") {
                        afterInserts.push({ props: dropdown_props, key: `after-${index}` });
                    } else {
                        innerSettings.push({ props: dropdown_props, key: dropdown_props.dropdown_id || `inner-${index}` });
                    }
                });

                return (
                    <>
                        {beforeInserts.map((item, i) => {
                            const InsertComponent = item.props.insert_component;
                            return <InsertComponent key={item.key} {...item.props.insert_component_props} />;
                        })}

                        <div className={styles.wrapper}>
                            {innerSettings.map((item) => {
                                const dropdown_props = item.props;
                                if (dropdown_props.insert_component && !dropdown_props.insert_to) {
                                    const InsertComponent = dropdown_props.insert_component;
                                    return <InsertComponent key={item.key} {...dropdown_props.insert_component_props} />;
                                }
                                return <DropdownMenu key={item.key} {...dropdown_props} />;
                            })}
                        </div>

                        {afterInserts.map((item) => {
                            const InsertComponent = item.props.insert_component;
                            return <InsertComponent key={item.key} {...item.props.insert_component_props} />;
                        })}
                    </>
                );
            })()}
        </div>
    );
};