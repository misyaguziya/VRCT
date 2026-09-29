import { useI18n } from "@useI18n";
import { useIsOpenedConfigPage } from "@logics_common";

import XMarkSvg from "@images/x_mark.svg?react";
import WarningSvg from "@images/warning.svg?react";

import styles from "./VrWindow.module.scss";

// VR UIのウィンドウ共通の枠 (タイトルバー・閉じるボタン・設定画面中のロック表示)。
// ロックは本文だけを覆い、閉じる操作は残す (状態を変えないため)。
// VR設定ウィンドウは設定画面そのものなのでロックしない (is_lockable=false)。
// is_grab_locked: 操作バーのロック中 (掴めない)。タイトルバーに錠と「ロック中」を出す
export const VrWindow = ({ Icon, title, onClose, is_lockable = true, is_grab_locked = false, children }) => {
    const { t } = useI18n();
    const { currentIsOpenedConfigPage } = useIsOpenedConfigPage();

    return (
        <div className={styles.window}>
            <div className={styles.title_bar}>
                <Icon className={styles.title_icon} />
                <p className={styles.title}>{title}</p>
                {is_grab_locked && (
                    <span className={styles.grab_locked}>
                        <svg className={styles.grab_locked_icon} viewBox="0 0 24 24" aria-hidden="true">
                            <path d="M6 11h12v10H6zM8.5 11V7.5a3.5 3.5 0 0 1 7 0V11" />
                        </svg>
                        {t("vr_panel.locked")}
                    </span>
                )}
                <button className={styles.close_button} onClick={onClose}>
                    <XMarkSvg className={styles.close_icon} />
                </button>
            </div>
            <div className={styles.body}>
                {children}
                {is_lockable && currentIsOpenedConfigPage.data === true && (
                    <div className={styles.locked}>
                        <WarningSvg className={styles.locked_icon} />
                        <p>{t("vr_panel.locked_by_config_page")}</p>
                    </div>
                )}
            </div>
        </div>
    );
};
