import { useEffect, useRef, useState } from "react";
import clsx from "clsx";
import styles from "./ActionButton.module.scss";

export const ActionButton = ({
    IconComponent,
    ClickedIconComponent,
    clicked_duration = 1000,
    onclickFunction,
    onErrorFunction,
}) => {
    const [is_clicked, setIsClicked] = useState(false);
    const timer_ref = useRef(null);

    useEffect(() => () => clearTimeout(timer_ref.current), []);

    const onClick = async () => {
        if (is_clicked) return;
        try {
            await onclickFunction?.();
            if (ClickedIconComponent) {
                setIsClicked(true);
                timer_ref.current = setTimeout(() => setIsClicked(false), clicked_duration);
            }
        } catch (error) {
            onErrorFunction?.(error);
        }
    };

    const ShownIcon = is_clicked && ClickedIconComponent ? ClickedIconComponent : IconComponent;
    const active_class = { [styles.is_clicked]: is_clicked };

    return (
        <div className={styles.container}>
            <button className={clsx(styles.button_wrapper, active_class)} onClick={onClick}>
                <ShownIcon className={clsx(styles.button_svg, active_class)} />
            </button>
        </div>
    );
};

