import clsx from "clsx";
import styles from "./LanguageSelectorOpenButton.module.scss";
import ArrowLeftSvg from "@images/arrow_left.svg?react";

export const LanguageSelectorOpenButton = ({ title, onClickFunction, is_opened, TurnedOnSvgComponent, is_turned_on, variable }) => {
    const arrow_class_names = clsx(styles.arrow_left_svg, {
        [styles.reverse]: is_opened,
    });

    const category_class_names = clsx(styles.category_svg, {
        [styles.is_turned_on]: is_turned_on,
    });

    const languageText = variable?.language ?? "Loading...";
    const countryText = variable?.country ?? "Loading...";

    return (
        <div className={styles.container}>
            <div className={styles.title_container}>
                <TurnedOnSvgComponent className={category_class_names} />
                <p className={styles.title}>{title}</p>
            </div>
            <div className={styles.dropdown_menu_container} onClick={onClickFunction}>
                <p className={styles.selected_language}>{languageText}</p>
                <p className={styles.selected_language}>({countryText})</p>
                <ArrowLeftSvg className={arrow_class_names} />
            </div>
        </div>
    );
};