import { useEffect, useRef, useState } from "react";
import clsx from "clsx";
import { useI18n } from "@useI18n";
import { useIsOpenedConfigPage, useVrPanelLogOutOfView, useVrPanelLauncherIntro } from "@logics_common";
import { useStdoutToPython } from "@useStdoutToPython";
import { useMainFunction } from "@logics_main";
import TranslationSvg from "@images/translation.svg?react";
import MicSvg from "@images/mic.svg?react";
import HeadphonesSvg from "@images/headphones.svg?react";
import ChatTranscribeSvg from "@images/chat_transcribe.svg?react";
import CopyThinSvg from "@images/copy_thin.svg?react";
import ConfigurationSvg from "@images/configuration.svg?react";
import LanguageSvg from "@images/mui_language.svg?react";
import vrct_logo from "@images/vrct_logo_for_dark_mode.png";
import vrct_icon from "@images/vrct_icon_for_vr_intro.png";
import { VrTooltipButton } from "./VrTooltip";
import shared from "./VrSettingsWindow.module.scss";
import styles from "./VrLauncher.module.scss";

const LONG_PRESS_MS = 600;
export const VrLauncher = ({ windows, toggleLog, openLog, togglePopup }) => {
    const { t } = useI18n();
    const { currentIsOpenedConfigPage } = useIsOpenedConfigPage();
    const { toggleTranslation, currentTranslationStatus, toggleTranscriptionSend, currentTranscriptionSendStatus,
        toggleTranscriptionReceive, currentTranscriptionReceiveStatus, toggleOcrCapture, currentOcrCaptureStatus } = useMainFunction();
    const { currentVrPanelLogOutOfView } = useVrPanelLogOutOfView();
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentVrPanelLauncherIntro } = useVrPanelLauncherIntro();
    const intro = currentVrPanelLauncherIntro.data;
    const is_log_lost = windows.log && currentVrPanelLogOutOfView.data === true;
    const is_locked = currentIsOpenedConfigPage.data === true;
    const recallLog = () => { openLog(); asyncStdoutToPython("/run/vr_panel_recall_log"); };
    return <div className={styles.root} style={{ "--vrct-logo": `url("${vrct_logo}")` }}>
        {intro === "playing" && <>
            <img className={styles.intro_icon} src={vrct_icon} alt="" aria-hidden="true" />
            <div className={styles.intro_logo} aria-hidden="true"><div className={styles.intro_text} /><div className={styles.intro_mark} /></div>
        </>}
        <div className={clsx(styles.container, { [styles.is_intro_pending]: intro === "pending", [styles.is_intro_playing]: intro === "playing" })}>
            <span className={styles.mark} aria-hidden="true" />
            <div className={styles.group} role="group" aria-label={t("vr_panel.tooltip.functions_group")}>
                <FunctionButton Svg={TranslationSvg} label={t("vr_panel.tooltip.translate")} name={t("main_page.translation")}
                    state={currentTranslationStatus} onClick={toggleTranslation} is_locked={is_locked} />
                <FunctionButton Svg={MicSvg} label={t("vr_panel.tooltip.microphone")} name={t("main_page.transcription_send")}
                    state={currentTranscriptionSendStatus} onClick={toggleTranscriptionSend} is_locked={is_locked} />
                <FunctionButton Svg={HeadphonesSvg} label={t("vr_panel.tooltip.listen")} name={t("main_page.transcription_receive")}
                    state={currentTranscriptionReceiveStatus} onClick={toggleTranscriptionReceive} is_locked={is_locked} />
                <FunctionButton Svg={ChatTranscribeSvg} label={t("vr_panel.tooltip.chat_detect")} name={t("main_page.ocr")}
                    state={currentOcrCaptureStatus} onClick={toggleOcrCapture} is_locked={is_locked} />
            </div>
            <span className={styles.divider} aria-hidden="true" />
            <div className={styles.group} role="group" aria-label={t("vr_panel.tooltip.windows_group")}>
                <WindowButton Svg={CopyThinSvg} label={is_log_lost ? t("vr_panel.recall_log") : t("vr_panel.window_log")}
                    name={t("vr_panel.window_log")} is_open={windows.log} is_attention={is_log_lost}
                    onClick={is_log_lost ? () => asyncStdoutToPython("/run/vr_panel_recall_log") : toggleLog} onLongPress={recallLog} />
                <WindowButton Svg={LanguageSvg} label={t("vr_panel.window_language")}
                    is_open={windows.popup === "language"} onClick={() => togglePopup("language")} />
                <WindowButton Svg={ConfigurationSvg} label={t("vr_panel.window_settings")}
                    is_open={windows.popup === "settings"} onClick={() => togglePopup("settings")} />
            </div>
        </div>
    </div>;
};

const FunctionButton = ({ Svg, label, name, state, onClick, is_locked }) => {
    const { t } = useI18n();
    const is_pending = state.state === "pending";
    const status = [state.data === true ? "ON" : "OFF", is_locked ? t("vr_panel.tooltip.config_open") :
        is_pending ? t("vr_panel.settings.changing_short") : ""].filter(Boolean).join(" · ");
    return <VrTooltipButton className={clsx(shared.button, styles.button, {
        [shared.is_on]: state.data === true, [styles.is_pending]: is_pending, [styles.is_disabled]: is_locked,
    })} aria-label={name} aria-pressed={state.data === true} aria-disabled={is_pending || is_locked || undefined}
        aria-busy={is_pending || undefined} tipTitle={label} tipState={status}
        tipHelp={is_locked ? t("vr_panel.locked_by_config_page") : is_pending ? t("vr_panel.tooltip.busy_help") :
            t(`vr_panel.tooltip.${state.data === true ? "disable" : "enable"}`)}
        onClick={() => { if (!is_pending && !is_locked) onClick(); }}>
        <Svg className={styles.icon} aria-hidden="true" />
        {(is_locked || is_pending) && <span className={styles.state_mark} aria-hidden="true">
            <svg viewBox="0 0 24 24"><path d={is_locked ? "M6 11h12v10H6zM8.5 11V7.5a3.5 3.5 0 0 1 7 0V11" :
                "M6 3h12M6 21h12M7 3v4l5 5-5 5v4M17 3v4l-5 5 5 5v4"} /></svg>
        </span>}
    </VrTooltipButton>;
};

const WindowButton = ({ Svg, label, name = label, is_open, is_attention = false, onClick, onLongPress = null }) => {
    const { t } = useI18n();
    const timer = useRef(null);
    const long_pressed = useRef(false);
    const [is_holding, setIsHolding] = useState(false);
    useEffect(() => () => clearTimeout(timer.current), []);
    const stopTimer = () => { clearTimeout(timer.current); timer.current = null; setIsHolding(false); };
    const onMouseDown = event => {
        if (event.button !== 0) return;
        clearTimeout(timer.current);
        long_pressed.current = false;
        if (!onLongPress) return;
        setIsHolding(true);
        timer.current = setTimeout(() => { long_pressed.current = true; stopTimer(); onLongPress(); }, LONG_PRESS_MS);
    };
    return <VrTooltipButton className={clsx(shared.button, styles.button, styles.window_button, {
        [shared.is_on]: is_open, [styles.is_attention]: is_attention, [styles.is_holding]: is_holding,
    })} aria-label={is_attention ? t("vr_panel.recall_log") : name} aria-pressed={is_open}
        tipTitle={name} tipState={t(`vr_panel.tooltip.${is_holding ? "holding" : is_attention ? "lost" : is_open ? "open" : "hidden"}`)}
        tipHelp={t(`vr_panel.tooltip.${is_holding ? "holding_help" : is_attention ? "click_recall" :
            onLongPress ? "log_help" : is_open ? "close_view" : "open_view"}`)}
        onMouseDown={onMouseDown} onMouseUp={stopTimer} onMouseLeave={stopTimer} onBlur={stopTimer}
        onClick={() => { if (!long_pressed.current) onClick(); long_pressed.current = false; }}>
        <Svg className={styles.icon} aria-hidden="true" />
    </VrTooltipButton>;
};
