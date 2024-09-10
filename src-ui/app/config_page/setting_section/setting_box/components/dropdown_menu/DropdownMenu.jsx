import styles from "./DropdownMenu.module.scss";
import clsx from "clsx";
import ArrowLeftSvg from "@images/arrow_left.svg?react";
import { useStore_IsOpenedDropdownMenu } from "@store";

export const DropdownMenu = (props) => {
    const { updateIsOpenedDropdownMenu, currentIsOpenedDropdownMenu } = useStore_IsOpenedDropdownMenu();

    const toggleDropdownMenu = () => {
        if (currentIsOpenedDropdownMenu === props.dropdown_id) {
            updateIsOpenedDropdownMenu("");
        } else {
            if (props.openListFunction !== undefined) props.openListFunction();
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

    const getSelectedText = () => {
        if (props.state !== "hasData") return;
        return props.selected_id;
    };
    const list = (props.list === undefined) ? {} : props.list;

    return (
        <div className={styles.container}>
            <div className={dropdown_toggle_button_class_name} onClick={toggleDropdownMenu}>
                {(props.state === "loading")
                    ? <p className={styles.dropdown_selected_text}>Loading...</p>
                    : <p className={styles.dropdown_selected_text}>{getSelectedText()}</p>
                }
                {(props.state === "loading")
                    ? <span className={styles.loader}></span>
                    : <ArrowLeftSvg className={arrow_class_names} />
                }
            </div>
            <div className={dropdown_content_wrapper_class_name}>
                <div className={styles.dropdown_content}>
                    {(props.state === "hasData")
                        ? Object.entries(list).map(([key, value]) => {
                            return (
                                <div key={key} className={styles.value_button} onClick={() => selectValue(key)}>
                                    <p className={styles.value_text}>{value}</p>
                                </div>
                            );
                        })
                        : null
                    }
                </div>
            </div>
        </div>
    );
};