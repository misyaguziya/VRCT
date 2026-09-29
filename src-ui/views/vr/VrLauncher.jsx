import { useEffect, useRef, useState } from "react";
import clsx from "clsx";

import { useI18n } from "@useI18n";
import { useIsOpenedConfigPage, useVrPanelLogOutOfView } from "@logics_common";
import { useStdoutToPython } from "@useStdoutToPython";
import { useMainFunction } from "@logics_main";
import { useOcr } from "@logics_configs";

import TranslationSvg from "@images/translation.svg?react";
import MicSvg from "@images/mic.svg?react";
import HeadphonesSvg from "@images/headphones.svg?react";
import ChatTranscribeSvg from "@images/chat_transcribe.svg?react";
import CopyThinSvg from "@images/copy_thin.svg?react";
import HmdSvg from "@images/mui_head_mounted_device.svg?react";

import styles from "./VrLauncher.module.scss";

// ボタンをこの時間押し続けると長押し (ログの呼び戻し)
const LONG_PRESS_MS = 600;

// 手首に付ける横長の帯。4機能のON/OFFと、各ウィンドウを開くボタン。
export const VrLauncher = ({ windows, toggleLog, openLog, togglePopup }) => {
    const { t } = useI18n();
    const { currentIsOpenedConfigPage } = useIsOpenedConfigPage();
    const {
        toggleTranslation, currentTranslationStatus,
        toggleTranscriptionSend, currentTranscriptionSendStatus,
        toggleTranscriptionReceive, currentTranscriptionReceiveStatus,
    } = useMainFunction();
    const { currentEnableOcrCapture, toggleEnableOcrCapture } = useOcr();
    const { currentVrPanelLogOutOfView } = useVrPanelLogOutOfView();
    const { asyncStdoutToPython } = useStdoutToPython();
    // ログウィンドウを開いたまま見失っているときは、閉じる代わりに目の前へ呼び戻す
    const is_log_lost = windows.log && currentVrPanelLogOutOfView.data === true;

    const is_locked = currentIsOpenedConfigPage.data === true;
    // ログボタンの長押し: 固定先によらず、ログを目の前へ呼び戻す (閉じていれば開いてから)
    const recallLog = () => {
        openLog();
        asyncStdoutToPython("/run/vr_panel_recall_log");
    };

    return (
        <div className={styles.container}>
            <div className={styles.group}>
                <FunctionButton Svg={TranslationSvg} label={t("main_page.translation")}
                    state={currentTranslationStatus} onClick={toggleTranslation} is_locked={is_locked} />
                <FunctionButton Svg={MicSvg} label={t("main_page.transcription_send")}
                    state={currentTranscriptionSendStatus} onClick={toggleTranscriptionSend} is_locked={is_locked} />
                <FunctionButton Svg={HeadphonesSvg} label={t("main_page.transcription_receive")}
                    state={currentTranscriptionReceiveStatus} onClick={toggleTranscriptionReceive} is_locked={is_locked} />
                <FunctionButton Svg={ChatTranscribeSvg} label={t("main_page.ocr")}
                    state={currentEnableOcrCapture} onClick={toggleEnableOcrCapture} is_locked={is_locked} />
            </div>
            <div className={styles.divider} />
            <div className={styles.group}>
                {/* ウィンドウの開閉は状態を変えないので、設定画面を開いている間も使える */}
                <WindowButton Svg={CopyThinSvg} label={is_log_lost ? t("vr_panel.recall_log") : t("vr_panel.window_log")}
                    is_open={windows.log} is_attention={is_log_lost}
                    onClick={is_log_lost ? () => asyncStdoutToPython("/run/vr_panel_recall_log") : toggleLog}
                    onLongPress={recallLog} long_press_label={t("vr_panel.recall_log")} />
                <WindowButton Svg={TranslationSvg} label={t("vr_panel.window_language")}
                    is_open={windows.popup === "language"} onClick={() => togglePopup("language")} />
                <WindowButton Svg={HmdSvg} label={t("vr_panel.window_settings")}
                    is_open={windows.popup === "settings"} onClick={() => togglePopup("settings")} />
            </div>
        </div>
    );
};

const FunctionButton = ({ Svg, label, state, onClick, is_locked }) => {
    const is_pending = state.state === "pending";
    // 処理中の二度押し (モデル読み込み中の ON→OFF など) と、設定画面を開いている間の操作は受け付けない
    const onClickButton = () => {
        if (is_pending || is_locked) return;
        onClick();
    };
    return (
        <button
            className={clsx(styles.button, {
                [styles.is_on]: state.data === true,
                [styles.is_pending]: is_pending,
                [styles.is_disabled]: is_locked,
            })}
            onClick={onClickButton}
        >
            <Svg className={styles.icon} />
            <span className={styles.label}>{is_pending ? "…" : label}</span>
        </button>
    );
};

// onLongPress があれば、押し続けている間は long_press_label を出し、長押しで onLongPress を呼ぶ (クリックはしない)
const WindowButton = ({ Svg, label, is_open, is_attention = false, onClick, onLongPress = null, long_press_label = null }) => {
    const timer = useRef(null);
    const long_pressed = useRef(false);
    const [is_holding, setIsHolding] = useState(false);
    useEffect(() => () => clearTimeout(timer.current), []);

    const stopTimer = () => {
        clearTimeout(timer.current);
        timer.current = null;
        setIsHolding(false);
    };
    const onMouseDown = () => {
        clearTimeout(timer.current); // 1回の押し込みで長押しは1回だけ
        long_pressed.current = false;
        if (!onLongPress) return;
        setIsHolding(true);
        timer.current = setTimeout(() => {
            long_pressed.current = true;
            stopTimer();
            onLongPress();
        }, LONG_PRESS_MS);
    };
    const onClickButton = () => {
        if (long_pressed.current) return; // 長押しの後の離しではクリックしない
        onClick();
    };
    return (
        <button
            className={clsx(styles.button, styles.window_button, {
                [styles.is_open]: is_open, [styles.is_attention]: is_attention, [styles.is_holding]: is_holding,
            })}
            onMouseDown={onMouseDown} onMouseUp={stopTimer} onMouseLeave={stopTimer} onClick={onClickButton}
        >
            <Svg className={styles.icon} />
            <span className={styles.label}>{is_holding && long_press_label ? long_press_label : label}</span>
        </button>
    );
};
