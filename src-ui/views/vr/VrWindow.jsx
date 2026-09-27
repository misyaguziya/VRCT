import { useI18n } from "@useI18n";
import { useIsOpenedConfigPage } from "@logics_common";

import XMarkSvg from "@images/x_mark.svg?react";
import WarningSvg from "@images/warning.svg?react";

import styles from "./VrWindow.module.scss";

// VR UIのウィンドウ共通の枠 (タイトルバー・閉じるボタン・設定画面中のロック表示)。
// ロックは本文だけを覆い、閉じる操作は残す (状態を変えないため)。
export const VrWindow = ({ Icon, title, onClose, children }) => {
    const { t } = useI18n();
    const { currentIsOpenedConfigPage } = useIsOpenedConfigPage();

    return (
        <div className={styles.window}>
            <div className={styles.title_bar}>
                <Icon className={styles.title_icon} />
                <p className={styles.title}>{title}</p>
                <button className={styles.close_button} onClick={onClose}>
                    <XMarkSvg className={styles.close_icon} />
                </button>
            </div>
            <div className={styles.body}>
                {children}
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
