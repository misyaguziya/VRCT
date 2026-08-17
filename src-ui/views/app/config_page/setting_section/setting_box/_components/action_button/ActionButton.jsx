import { useEffect, useRef, useState } from "react";
import clsx from "clsx";
import styles from "./ActionButton.module.scss";

export const ActionButton = ({
    IconComponent,
    ClickedIconComponent,
    clicked_duration,
    onclickFunction,
}) => {
    const [is_clicked, setIsClicked] = useState(false);
    const timeout_id_ref = useRef(null);

    useEffect(() => {
        return () => {
            if (timeout_id_ref.current) clearTimeout(timeout_id_ref.current);
        };
    }, []);

    const onClick = async () => {
        if (is_clicked) return;
        try {
            await onclickFunction?.();
        } catch {
            return;
        }
        if (!ClickedIconComponent || !clicked_duration) return;

        setIsClicked(true);
        timeout_id_ref.current = setTimeout(() => {
            setIsClicked(false);
            timeout_id_ref.current = null;
        }, clicked_duration);
    };

    const ShownIconComponent = is_clicked ? ClickedIconComponent : IconComponent;
    const button_wrapper_class_names = clsx(styles.button_wrapper, {
        [styles.is_clicked]: is_clicked,
    });
    const button_svg_class_names = clsx(styles.button_svg, {
        [styles.is_clicked]: is_clicked,
    });

    return (
        <div className={styles.container}>
            <button className={button_wrapper_class_names} onClick={onClick}>
                <ShownIconComponent className={button_svg_class_names}/>
            </button>
        </div>
    );
};
