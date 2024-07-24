import clsx from "clsx";
import styles from "./LanguageSelectorOpenButton.module.scss";
import ArrowLeftSvg from "@images/arrow_left.svg?react";
import { useSvg } from "@utils/useSvg";
export const LanguageSelectorOpenButton = (props) => {

    const toggleLanguageSelector = () => {
        props.onClickFunction();
    };

    const class_names = clsx(styles["arrow_left_svg"], {
        [styles["reverse"]]: props.is_opened
    });

    const SvgComponent = useSvg(props.TurnedOnSvgComponent,
        {className: clsx(styles["category_svg"], {
            [styles["is_turned_on"]]: props.is_turned_on
        })}
    );

    return (
        <div className={styles.container}>
            <div className={styles.title_container}>
                {SvgComponent}
                <p className={styles.title}>{props.title}</p>
            </div>
            <div className={styles.dropdown_menu_container} onClick={toggleLanguageSelector}>
                <p className={styles.selected_language}>Japanese</p>
                <p className={styles.selected_language}>(Japan)</p>
                <ArrowLeftSvg className={class_names} />
            </div>
        </div>
    );
};