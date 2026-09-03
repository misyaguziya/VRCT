import { useI18n } from "@useI18n";
import clsx from "clsx";

import styles from "./Topbar.module.scss";
import { useIsOpenedConfigPage } from "@logics_common";
import ArrowLeftSvg from "@images/arrow_left.svg?react";

export const Topbar = () => {
    const { t } = useI18n();
    const { currentIsOpenedConfigPage, setIsOpenedConfigPage } = useIsOpenedConfigPage();
    const closeConfigPage = () => {
        setIsOpenedConfigPage(false);
    };
    return (
        <div className={clsx(styles.container, {
            [styles.show_config]: currentIsOpenedConfigPage.data,
            [styles.show_main]: !currentIsOpenedConfigPage.data
        })}>
            <div className={styles.wrapper} onClick={() => closeConfigPage()}>
                <div className={styles.go_back_button}>
                    <ArrowLeftSvg className={styles.arrow_left_svg} />
                </div>
                <div className={styles.go_back_text_wrapper}>
                    <p className={styles.go_back_text}>{t("common.go_back_button_label")}</p>
                </div>
            </div>
        </div>
    );
};