import clsx from "clsx";
import { useI18n } from "@useI18n";
import { useStdoutToPython } from "@useStdoutToPython";
import { useVr } from "@logics_configs";
import { VrTooltipButton } from "./VrTooltip";
import shared from "./VrSettingsWindow.module.scss";
import styles from "./VrToolbar.module.scss";

const PATHS = {
    world: "M2 22l2.5-5h15l2.5 5zM12 2a4.5 4.5 0 0 0-4.5 4.5c0 3.4 4.5 8.5 4.5 8.5s4.5-5.1 4.5-8.5A4.5 4.5 0 0 0 12 2zM12 5.5a1 1 0 1 0 0 2 1 1 0 0 0 0-2z", // 床に立てたピン
    hand: "M8 21v-5l-3-4V7M8 12V4.5a1.5 1.5 0 0 1 3 0V11M11 10V3.5a1.5 1.5 0 0 1 3 0V11M14 10.5V5a1.5 1.5 0 0 1 3 0v8c0 4-2 8-6 8H8",
    head: "M12 3.5a4.5 4.5 0 1 0 0 9 4.5 4.5 0 0 0 0-9zM4 21c.8-4 4-6.5 8-6.5s7.2 2.5 8 6.5",
    recall: "M12 5V2M12 22v-3M5 12H2M22 12h-3M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8z",
    lock: "M6 11h12v10H6zM8.5 11V7.5a3.5 3.5 0 0 1 7 0V11",
    unlock: "M6 11h12v10H6zM8.5 11V7.5a3.5 3.5 0 0 1 7-1",
    opacity: "M4 4h16v16H4zM4 12h16M12 4v16",
};
const ANCHORS = [["Playspace", "anchor_playspace", "world"], ["LeftHand", "anchor_left_hand", "hand"],
    ["RightHand", "anchor_right_hand", "hand"], ["HMD", "anchor_head", "head"]];
const OPACITY_STEPS = [1.0, 0.8, 0.6, 0.4];
const FONT_SIZE = { min: 14, max: 28 };

export const VrToolbar = () => {
    const { t } = useI18n();
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentOverlayVrPanelAnchor: anchor, setOverlayVrPanelAnchor,
        currentOverlayVrPanelLocked: locked, toggleOverlayVrPanelLocked,
        currentOverlayVrPanelOpacity: opacity, setOverlayVrPanelOpacity,
        currentOverlayVrPanelFontSize: font, setOverlayVrPanelFontSize } = useVr();
    const currentAnchor = t(`vr_panel.${ANCHORS.find(([id]) => id === anchor.data)?.[1] ?? "anchor_playspace"}`);
    const current = t("vr_panel.tooltip.current");
    const percent = Math.round(Number(opacity.data) * 100);
    const nextOpacity = () => OPACITY_STEPS.find(step => step < Number(opacity.data) - 0.01) ?? OPACITY_STEPS[0];
    return <div className={styles.bar} role="group" aria-label={t("vr_panel.tooltip.controls_group")}>
        <div className={styles.group} role="group" aria-label={t("vr_panel.tooltip.anchor")}>
            {ANCHORS.map(([id, key, icon]) => <Button key={id} className={styles.anchor_button}
                label={`${t("vr_panel.tooltip.anchor")}: ${t(`vr_panel.${key}`)}`}
                tipState={anchor.data === id ? t("vr_panel.language.selected") : `${current}: ${currentAnchor}`}
                tipHelp={anchor.data === id ? "" : t("vr_panel.tooltip.choose_anchor")}
                selected={anchor.data === id} state={anchor} onClick={() => { if (anchor.data !== id) setOverlayVrPanelAnchor(id); }}>
                <Icon name={icon} right={id === "RightHand"} />
                {(id === "LeftHand" || id === "RightHand") && <span className={styles.hand_side} aria-hidden="true">{id === "LeftHand" ? "L" : "R"}</span>}
            </Button>)}
        </div>
        <div className={styles.group} role="group" aria-label={t("vr_panel.tooltip.position")}>
            <Button className={styles.recall_button} label={t("vr_panel.recall_log")}
                tipState={`${t("vr_panel.tooltip.anchor")}: ${currentAnchor}`} tipHelp={t("vr_panel.tooltip.recall_help")}
                onClick={() => asyncStdoutToPython("/run/vr_panel_recall_log")}><Icon name="recall" /></Button>
            <Button className={styles.lock_button} label={t("vr_panel.lock")} selected={locked.data === true} state={locked}
                tipState={locked.data === true ? t("vr_panel.locked") : t("vr_panel.tooltip.unlocked")}
                tipHelp={t(`vr_panel.tooltip.${locked.data === true ? "unlock_help" : "lock_help"}`)}
                onClick={toggleOverlayVrPanelLocked}><Icon name={locked.data === true ? "lock" : "unlock"} /></Button>
        </div>
        <div className={styles.group} role="group" aria-label={t("vr_panel.tooltip.font")}>
            <Button className={styles.font_button} label={t("vr_panel.tooltip.smaller")} state={font}
                tipState={t("vr_panel.tooltip.font_current", { size: font.data })} tipHelp={t(`vr_panel.tooltip.${font.data <= FONT_SIZE.min ? "font_limit" : "font_help"}`)}
                disabled={font.data <= FONT_SIZE.min} onClick={() => setOverlayVrPanelFontSize(font.data - 1)}>A−</Button>
            <span className={styles.value} aria-label={`${t("vr_panel.tooltip.font")}: ${font.data}`}>{font.data}</span>
            <Button className={styles.font_button} label={t("vr_panel.tooltip.larger")} state={font}
                tipState={t("vr_panel.tooltip.font_current", { size: font.data })} tipHelp={t(`vr_panel.tooltip.${font.data >= FONT_SIZE.max ? "font_limit" : "font_help"}`)}
                disabled={font.data >= FONT_SIZE.max} onClick={() => setOverlayVrPanelFontSize(font.data + 1)}>A＋</Button>
        </div>
        <div className={styles.group}>
            <Button className={styles.opacity_button} label={`${t("vr_panel.log_opacity")}: ${percent}%`} tipTitle={t("vr_panel.log_opacity")}
                state={opacity} tipState={`${current}: ${percent}%`} tipHelp={t("vr_panel.tooltip.opacity_help")}
                onClick={() => setOverlayVrPanelOpacity(nextOpacity())}><Icon name="opacity" /><span className={styles.opacity_value}>{percent}%</span></Button>
        </div>
    </div>;
};

const Button = ({ children, className, label, tipTitle = label, tipState, tipHelp, selected, state, disabled, onClick }) => {
    const { t } = useI18n();
    const busy = state?.state === "pending";
    return <VrTooltipButton className={clsx(shared.button, styles.button, className, {
        [shared.is_on]: selected, [styles.is_pending]: busy, [styles.is_disabled]: disabled,
    })} aria-label={label} aria-pressed={selected} aria-disabled={busy || disabled || undefined} aria-busy={busy || undefined}
        tipTitle={tipTitle} tipState={busy ? `${tipState} · ${t("vr_panel.settings.changing_short")}` : tipState}
        tipHelp={busy ? t("vr_panel.tooltip.busy_help") : tipHelp}
        onClick={() => { if (!busy && !disabled) onClick(); }}>{children}</VrTooltipButton>;
};
const Icon = ({ name, right = false }) => <svg className={styles.icon} viewBox="0 0 24 24" aria-hidden="true"
    style={right ? { transform: "scaleX(-1)" } : undefined}><path d={PATHS[name]} /></svg>;
