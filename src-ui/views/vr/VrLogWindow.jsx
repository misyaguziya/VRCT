import { useI18n } from "@useI18n";
import { useIsOpenedConfigPage } from "@logics_common";

import CopyThinSvg from "@images/copy_thin.svg?react";
import WarningSvg from "@images/warning.svg?react";
import { LogBox } from "../app/main_page/main_section/message_container/log_box/LogBox";

import styles from "./VrWindow.module.scss";

// ログウィンドウ。絞り込みタブは次の段階で追加する
export const VrLogWindow = () => {
    const { t } = useI18n();
    const { currentIsOpenedConfigPage } = useIsOpenedConfigPage();

    return (
        <div className={styles.window}>
            <div className={styles.title_bar}>
                <CopyThinSvg className={styles.title_icon} />
                <p className={styles.title}>{t("vr_panel.window_log")}</p>
            </div>
            <div className={styles.body}>
                <div className={styles.log_box_wrapper}>
                    <LogBox />
                </div>
                {currentIsOpenedConfigPage.data === true && (
                    <div className={styles.locked}>
                        <WarningSvg className={styles.locked_icon} />
                        <p>{t("vr_panel.locked_by_config_page")}</p>
                    </div>
                )}
            </div>
        </div>
    );
};
