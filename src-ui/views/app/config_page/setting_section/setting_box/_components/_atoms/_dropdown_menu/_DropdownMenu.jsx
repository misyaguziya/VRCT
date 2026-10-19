import { useRef, useEffect, useLayoutEffect, useState } from "react";
import styles from "./_DropdownMenu.module.scss";
import clsx from "clsx";
import ArrowLeftSvg from "@images/arrow_left.svg?react";
import { useStore_IsOpenedDropdownMenu } from "@store";

export const _DropdownMenu = (props) => {
    const { updateIsOpenedDropdownMenu, currentIsOpenedDropdownMenu } = useStore_IsOpenedDropdownMenu();
    const is_opened = currentIsOpenedDropdownMenu.data === props.dropdown_id;
    const [openAbove, setOpenAbove] = useState(false);

    const containerRef = useRef(null);
    const contentRef = useRef(null);

    const toggleDropdownMenu = () => {
        if (props.is_disabled || props.state === "pending") return;

        if (is_opened) {
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

    useLayoutEffect(() => {
        if (!is_opened || !containerRef.current) return;

        const updatePlacement = () => {
            const container = containerRef.current;
            if (!container) return;

            const rect = container.getBoundingClientRect();
            const spaceBelow = window.innerHeight - rect.bottom;
            const spaceAbove = rect.top;
            const menuHeight = contentRef.current ? contentRef.current.offsetHeight : 200;

            setOpenAbove(spaceBelow < menuHeight && spaceAbove > spaceBelow);
        };

        updatePlacement();
        window.addEventListener("resize", updatePlacement);
        return () => {
            window.removeEventListener("resize", updatePlacement);
        };
    }, [is_opened]);

    useEffect(() => {
        if (!is_opened) return;

        const handlePointerDown = (event) => {
            if (containerRef.current && !containerRef.current.contains(event.target)) {
                updateIsOpenedDropdownMenu("");
            }
        };

        const handleKeyDown = (event) => {
            if (event.key === "Escape") {
                updateIsOpenedDropdownMenu("");
            }
        };

        document.addEventListener("pointerdown", handlePointerDown);
        document.addEventListener("keydown", handleKeyDown);
        return () => {
            document.removeEventListener("pointerdown", handlePointerDown);
            document.removeEventListener("keydown", handleKeyDown);
        };
    }, [is_opened, updateIsOpenedDropdownMenu]);

    const dropdown_content_wrapper_class_name = clsx(styles["dropdown_content_wrapper"], {
        [styles.is_opened]: is_opened,
        [styles.is_disabled]: props.is_disabled,
        [styles.open_above]: openAbove,
        [styles.open_below]: !openAbove,
    });

    const dropdown_toggle_button_class_name = clsx(styles["dropdown_toggle_button"], {
        [styles.is_pending]: (props.state === "pending") ? true : false,
        [styles.is_disabled]: props.is_disabled,
    });

    const arrow_class_names = clsx(styles["arrow_left_svg"], {
        [styles.is_opened]: is_opened,
    });

    const getSelectedText = () => {
        if (props.state !== "ok") return;
        if (props.list[props.selected_id] === undefined) return props.selected_id; // [Fix me]

        return props.list[props.selected_id];
    };
    const list = (props.list === undefined) ? {} : props.list;

    return (
        <div ref={containerRef} className={styles.container}>
            <div className={dropdown_toggle_button_class_name} onClick={toggleDropdownMenu} style={props.style}>
                {(props.state === "pending")
                    ? <p className={styles.dropdown_selected_text}>Loading...</p>
                    : <p className={styles.dropdown_selected_text}>{getSelectedText()}</p>
                }
                {(props.state === "pending")
                    ? <span className={styles.loader}></span>
                    : <ArrowLeftSvg className={arrow_class_names} />
                }
            </div>
            <div className={dropdown_content_wrapper_class_name}>
                <div ref={contentRef} className={styles.dropdown_content}>
                    {(props.state === "ok")
                        ? Object.entries(list).map(([key, value]) => {
                            const is_selected = String(key) === String(props.selected_id);
                            const value_button_class_name = clsx(styles.value_button, {
                                [styles.is_selected]: is_selected,
                            });
                            return (
                                <div
                                    key={key}
                                    className={value_button_class_name}
                                    onClick={() => selectValue(key)}
                                    role="option"
                                    aria-selected={is_selected}
                                >
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