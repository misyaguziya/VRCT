import { useState } from "react";
import clsx from "clsx";
import { useTranslation } from "react-i18next";

import styles from "./LanguageSwapButton.module.scss";

import NarrowArrowDownSvg from "@images/narrow_arrow_down.svg?react";
import { useLanguageSettings } from "@logics_main";

export const LanguageSwapButton = () => {
    const [isHovered, setIsHovered] = useState(false);
    const { t } = useTranslation();
    const { runLanguageSwap } = useLanguageSettings();

    const label = isHovered
        ? t("main_page.swap_button_label")
        : t("main_page.translate_each_other_label");

    const labelClassName = clsx(styles["label"], {
        [styles["is_hovered"]]: isHovered
    });

    const handleMouseEnter = () => setIsHovered(true);
    const handleMouseLeave = () => setIsHovered(false);

    return (
        <div className={styles.container}>
            <div
                className={styles.swap_button_wrapper}
                onMouseEnter={handleMouseEnter}
                onMouseLeave={handleMouseLeave}
                onClick={runLanguageSwap}
            >
                <NarrowArrowDownSvg className={clsx(styles.narrow_arrow_down_svg, styles.reverse)} />
                <p className={labelClassName}>{label}</p>
                <NarrowArrowDownSvg className={styles.narrow_arrow_down_svg} />
            </div>
        </div>
    );
};
