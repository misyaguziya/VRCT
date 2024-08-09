import styles from "./DropdownMenu.module.scss";

import clsx from "clsx";
import ArrowLeftSvg from "@images/arrow_left.svg?react";
import { useIsOpenedDropdownMenu } from "@store";

export const DropdownMenu = (props) => {

    const { updateIsOpenedDropdownMenu, currentIsOpenedDropdownMenu } = useIsOpenedDropdownMenu();
    const toggleDropdownMenu = () => {
        if (currentIsOpenedDropdownMenu === props.dropdown_id) {
            updateIsOpenedDropdownMenu("");
        } else {
            updateIsOpenedDropdownMenu(props.dropdown_id);
        }
    };

    const selectValue = (key) => {
        updateIsOpenedDropdownMenu("");
        props.selectFunction({
            dropdown_id: props.dropdown_id,
            selected_id: key,
        });
    };

    const dropdown_content_wrapper_class_name = clsx(styles["dropdown_content_wrapper"], {
        [styles["is_opened"]]: (currentIsOpenedDropdownMenu === props.dropdown_id) ? true : false
    });

    const dropdown_toggle_button_class_name = clsx(styles["dropdown_toggle_button"], {
        [styles["is_loading"]]: (props.state === "loading") ? true : false
    });

    const arrow_class_names = clsx(styles["arrow_left_svg"], {
        [styles["is_opened"]]: (currentIsOpenedDropdownMenu === props.dropdown_id) ? true : false
    });

    return (
        <div className={styles.container}>
            <div className={dropdown_toggle_button_class_name} onClick={toggleDropdownMenu}>
                {(props.state === "loading")
                    ? <p className={styles.dropdown_selected_text}>Loading...</p>
                    : <p className={styles.dropdown_selected_text}>{props.list[props.selected_id]}</p>
                }
                {(props.state === "loading")
                    ? <span className={styles.loader}></span>
                    : <ArrowLeftSvg className={arrow_class_names} />
                }
            </div>
            <div className={dropdown_content_wrapper_class_name}>
                <div className={styles.dropdown_content}>
                    {
                        Object.entries(props.list).map(([key, value]) => {
                            return (
                                <div key={key} className={styles.value_button} onClick={() => selectValue(key)}>
                                    <p className={styles.value_text} >{value}</p>
                                </div>
                            );
                        })
                    }
                </div>
            </div>
        </div>
    );
};