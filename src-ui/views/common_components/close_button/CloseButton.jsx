import clsx from "clsx";
import XMarkSvg from "@images/cancel.svg?react";
import styles from "./CloseButton.module.scss";

export const CloseButton = ({ onClick, size = "large", variant = "default", className }) => {
    return (
        <button
            className={clsx(
                styles.close_button_wrapper,
                styles[`size_${size}`],
                styles[`variant_${variant}`],
                className
            )}
            onClick={onClick}
        >
            <div className={styles.close_button}>
                <XMarkSvg className={styles.x_mark_svg}/>
            </div>
        </button>
    );
};
