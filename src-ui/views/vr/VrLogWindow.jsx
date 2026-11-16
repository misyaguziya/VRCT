import { useEffect } from "react";
import { useI18n } from "@useI18n";
import { useVr } from "@logics_configs";
import { useMessage } from "@logics_common";
import { useStdoutToPython } from "@useStdoutToPython";

import CopyThinSvg from "@images/copy_thin.svg?react";
import { LogBox } from "../app/main_page/main_section/message_container/log_box/LogBox";

import { VrWindow } from "./VrWindow";
import { VrSubtitleWindow } from "./VrSubtitleWindow";
import { SUBTITLE_FORMS, subtitleEntries, subtitleKey } from "./subtitle_entries";
import styles from "./VrWindow.module.scss";

// ログウィンドウ。形 (履歴 / 字幕・複数行 / 字幕・1行) と固定先・ロックなどは下の操作バー (VrToolbar) で変える
export const VrLogWindow = ({ onClose }) => {
    const { t } = useI18n();
    const { currentOverlayVrPanelLocked, currentOverlayVrPanelFontSize, currentOverlayVrPanelForm,
        currentOverlayShowOnlyTranslatedMessages } = useVr();
    const { currentMessageLogs } = useMessage();
    const { asyncStdoutToPython } = useStdoutToPython();
    const form = SUBTITLE_FORMS.includes(currentOverlayVrPanelForm.data) ? currentOverlayVrPanelForm.data : "history";
    const entries = form === "history" ? [] : subtitleEntries(currentMessageLogs.data, form, currentOverlayShowOnlyTranslatedMessages.data === true);
    // 見せる中身が変わったら、描き終えてから (2 フレーム後) バックエンドに知らせる。撮れたら表示され、
    // 字幕の表示秒が始まる (形を変えたときは、それまで透明)
    const key = form === "history" ? form : subtitleKey(form, entries);
    useEffect(() => {
        if (key === null) return undefined;
        let second = null;
        const first = requestAnimationFrame(() => {
            second = requestAnimationFrame(() => asyncStdoutToPython("/run/vr_panel_log_rendered"));
        });
        return () => {
            cancelAnimationFrame(first);
            if (second !== null) cancelAnimationFrame(second);
        };
    }, [key]);

    const is_locked = currentOverlayVrPanelLocked.data === true;
    if (form !== "history") return <VrSubtitleWindow form={form} entries={entries} is_locked={is_locked} />;
    return (
        <VrWindow Icon={CopyThinSvg} title={t("vr_panel.window_log")} onClose={onClose}
            is_grab_locked={is_locked} is_resizable={true}>
            <div className={styles.log_box_wrapper} style={{ "--vr_log_font_size": `${currentOverlayVrPanelFontSize.data}px` }}>
                <LogBox />
            </div>
        </VrWindow>
    );
};
