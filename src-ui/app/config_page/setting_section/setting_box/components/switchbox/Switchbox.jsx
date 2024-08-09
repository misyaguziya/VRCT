import clsx from "clsx";
import { useState } from "react";
import styles from "./Switchbox.module.scss";

export const Switchbox = (props) => {

    const [is_turned_on, setIsTurnedOn] = useState(false);
    const [is_hovered, setIsHovered] = useState(false);
    const [is_mouse_down, setIsMouseDown] = useState(false);

    const getClassNames = (baseClass) => clsx(baseClass, {
        [styles.is_active]: (is_turned_on === true),
        // [styles.is_loading]: (currentState.state === "loading"),
        [styles.is_hovered]: is_hovered,
        [styles.is_mouse_down]: is_mouse_down,
    });

    const onMouseEnter = () => setIsHovered(true);
    const onMouseLeave = () => setIsHovered(false);
    const onMouseDown = () => setIsMouseDown(true);
    const onMouseUp = () => setIsMouseDown(false);

    const toggleFunction = () => {
        setIsTurnedOn(!is_turned_on);
    };


    return (
        <div className={styles.switchbox_container}>
            <div className={styles.switchbox_wrapper}
            onMouseEnter={onMouseEnter}
            onMouseLeave={onMouseLeave}
            onMouseDown={onMouseDown}
            onMouseUp={onMouseUp}
            onClick={toggleFunction}
            >
                <div className={getClassNames(styles.toggle_control)}>
                    <span className={getClassNames(styles.control)}></span>
                </div>
            </div>
        </div>
    );
};
