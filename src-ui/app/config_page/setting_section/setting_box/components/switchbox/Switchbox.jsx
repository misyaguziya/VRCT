import clsx from "clsx";
import { useState } from "react";
import styles from "./Switchbox.module.scss";

export const Switchbox = (props) => {
    const [is_hovered, setIsHovered] = useState(false);
    const [is_mouse_down, setIsMouseDown] = useState(false);

    const is_loading = (props.variable.state === "pending");

    const getClassNames = (base_class) => clsx(base_class, {
        [styles.is_active]: (props.variable.data === true),
        [styles.is_loading]: is_loading,
        [styles.is_hovered]: is_hovered,
        [styles.is_mouse_down]: is_mouse_down,
    });

    const onMouseEnter = () => setIsHovered(true);
    const onMouseLeave = () => setIsHovered(false);
    const onMouseDown = () => setIsMouseDown(true);
    const onMouseUp = () => setIsMouseDown(false);

    const toggleFunction = () => {
        props.toggleFunction();
    };


    return (
        <div className={styles.switchbox_container}>
            <div className={getClassNames(styles.switchbox_wrapper)}
                onMouseEnter={onMouseEnter}
                onMouseLeave={onMouseLeave}
                onMouseDown={onMouseDown}
                onMouseUp={onMouseUp}
                onClick={toggleFunction}
            >
                <div className={getClassNames(styles.toggle_control)}>
                    <span className={getClassNames(styles.control)}></span>
                    {is_loading && <span className={styles.loader}></span>}
                </div>
            </div>
        </div>
    );
};
