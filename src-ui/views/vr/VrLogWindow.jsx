import { useI18n } from "@useI18n";
import { useVr } from "@logics_configs";

import CopyThinSvg from "@images/copy_thin.svg?react";
import { LogBox } from "../app/main_page/main_section/message_container/log_box/LogBox";

import { VrWindow } from "./VrWindow";
import styles from "./VrWindow.module.scss";

// ログウィンドウ。固定先・ロックなどは下の操作バー (VrToolbar) で変える
export const VrLogWindow = ({ onClose }) => {
    const { t } = useI18n();
    const { currentOverlayVrPanelLocked, currentOverlayVrPanelFontSize } = useVr();
    return (
        <VrWindow Icon={CopyThinSvg} title={t("vr_panel.window_log")} onClose={onClose}
            is_grab_locked={currentOverlayVrPanelLocked.data === true}>
            <div className={styles.log_box_wrapper} style={{ "--vr_log_font_size": `${currentOverlayVrPanelFontSize.data}px` }}>
                <LogBox />
            </div>
        </VrWindow>
    );
};
