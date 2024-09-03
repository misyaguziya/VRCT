import clsx from "clsx";

import styles from "./Topbar.module.scss";
import { useIsOpenedConfigPage } from "@store";
import ArrowLeftSvg from "@images/arrow_left.svg?react";

import { TitleBox } from "./title_box/TitleBox";
import { SectionTitleBox } from "./section_title_box/SectionTitleBox";
import { CompactSwitchBox } from "./compact_switch_box/CompactSwitchBox";

export const Topbar = () => {
    const { currentIsOpenedConfigPage, updateIsOpenedConfigPage } = useIsOpenedConfigPage();
    const closeConfigPage = () => {
        updateIsOpenedConfigPage(false);
    };

    return (
        <div className={clsx(styles.container, {
            [styles.show_config]: currentIsOpenedConfigPage,
            [styles.show_main]: !currentIsOpenedConfigPage
        })}>
            <div className={styles.wrapper} onClick={() => closeConfigPage()}>
                <div className={styles.go_back_button}>
                    <ArrowLeftSvg className={styles.arrow_left_svg} />
                </div>
                <div className={styles.go_back_text_wrapper}>
                    <p className={styles.go_back_text}>Go Back</p>
                </div>


                {/* <TitleBox />
                <SectionTitleBox />
                <CompactSwitchBox /> */}
            </div>
        </div>
    );
};