import { useI18n } from "@useI18n";

import CopyThinSvg from "@images/copy_thin.svg?react";
import { LogBox } from "../app/main_page/main_section/message_container/log_box/LogBox";

import { VrWindow } from "./VrWindow";
import styles from "./VrWindow.module.scss";

// ログウィンドウ。絞り込みタブは後の段階で追加する
export const VrLogWindow = ({ onClose }) => {
    const { t } = useI18n();
    return (
        <VrWindow Icon={CopyThinSvg} title={t("vr_panel.window_log")} onClose={onClose}>
            <div className={styles.log_box_wrapper}>
                <LogBox />
            </div>
        </VrWindow>
    );
};
