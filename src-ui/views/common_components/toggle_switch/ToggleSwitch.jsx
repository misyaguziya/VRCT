import clsx from "clsx";
import styles from "./ToggleSwitch.module.scss";

export const ToggleSwitch = ({
    isActive = false,
    isPending = false,
    width,
    height,
    style,
    toggleFunction,
    showLoader = false,
    className,
}) => {
    const containerClasses = clsx(
        styles.toggle_switch_container,
        {
            [styles.is_active]: isActive,
            [styles.is_pending]: isPending,
        },
        className
    );

    const controlClasses = clsx(styles.control, {
        [styles.is_active]: isActive,
        [styles.is_pending]: isPending,
    });

    const customStyles = {
        ...(width ? { "--toggle_width": width } : {}),
        ...(height ? { "--toggle_height": height } : {}),
        ...style,
    };

    const handleClick = (e) => {
        if (toggleFunction) {
            e.stopPropagation();
            toggleFunction();
        }
    };

    return (
        <div className={containerClasses} style={customStyles} onClick={handleClick}>
            <span className={controlClasses}></span>
            {showLoader && isPending && (
                <span className={styles.loader}></span>
            )}
        </div>
    );
};
