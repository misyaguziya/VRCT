import React from "react";
import styles from "./CircularProgress.module.scss";
import clsx from "clsx";

export const CircularProgress = ({
    variant = "indeterminate",
    value = 0,
    size = "4rem",
    sx = {},
    className,
    ...props
}) => {
    const rootStyle = {
        width: size,
        height: size,
        color: sx?.color || "inherit",
        ...sx,
    };

    const INDETERMINATE_DASH_ARRAY = "80, 200";
    const INDETERMINATE_DASH_OFFSET = 0;

    // For determinate: dash array is 2 * PI * r = 2 * 3.14159 * 20.2 ≈ 126.92
    const CIRCUMFERENCE = 126.92;
    const determinateOffset = CIRCUMFERENCE - (value / 100) * CIRCUMFERENCE;

    const isDeterminate = variant === "determinate";

    return (
        <span
            className={clsx(styles.root, { [styles.determinate]: isDeterminate }, className)}
            style={rootStyle}
            role="progressbar"
            {...props}
        >
            <svg className={styles.svg} viewBox="22 22 44 44">
                <circle
                    className={clsx(styles.circle, { [styles.circleDeterminate]: isDeterminate })}
                    cx="44"
                    cy="44"
                    r="20.2"
                    fill="none"
                    strokeWidth="3.6"
                    style={{
                        strokeDasharray: isDeterminate ? CIRCUMFERENCE : undefined,
                        strokeDashoffset: isDeterminate ? determinateOffset : undefined,
                    }}
                />
            </svg>
        </span>
    );
};
