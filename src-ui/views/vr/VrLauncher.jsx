import clsx from "clsx";

import { useI18n } from "@useI18n";
import { useIsOpenedConfigPage } from "@logics_common";
import { useMainFunction } from "@logics_main";
import { useOcr } from "@logics_configs";

import TranslationSvg from "@images/translation.svg?react";
import MicSvg from "@images/mic.svg?react";
import HeadphonesSvg from "@images/headphones.svg?react";
import ChatTranscribeSvg from "@images/chat_transcribe.svg?react";
import CopyThinSvg from "@images/copy_thin.svg?react";
import HmdSvg from "@images/mui_head_mounted_device.svg?react";

import styles from "./VrLauncher.module.scss";

// 手首に付ける横長の帯。4機能のON/OFFと、各ウィンドウを開くボタン。
export const VrLauncher = () => {
    const { t } = useI18n();
    const { currentIsOpenedConfigPage } = useIsOpenedConfigPage();
    const {
        toggleTranslation, currentTranslationStatus,
        toggleTranscriptionSend, currentTranscriptionSendStatus,
        toggleTranscriptionReceive, currentTranscriptionReceiveStatus,
    } = useMainFunction();
    const { currentEnableOcrCapture, toggleEnableOcrCapture } = useOcr();

    const is_locked = currentIsOpenedConfigPage.data === true;

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
                {/* ウィンドウの開閉は次の段階で実装する。今はログが常に開いている */}
                <WindowButton Svg={CopyThinSvg} label={t("vr_panel.window_log")} is_open={true} />
                <WindowButton Svg={TranslationSvg} label={t("vr_panel.window_language")} is_disabled={true} />
                <WindowButton Svg={HmdSvg} label={t("vr_panel.window_settings")} is_disabled={true} />
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

const WindowButton = ({ Svg, label, is_open = false, is_disabled = false }) => (
    <button className={clsx(styles.button, styles.window_button, { [styles.is_open]: is_open, [styles.is_disabled]: is_disabled })}>
        <Svg className={styles.icon} />
        <span className={styles.label}>{label}</span>
    </button>
);
