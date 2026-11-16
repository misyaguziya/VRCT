import { useRef, useState } from "react";
import clsx from "clsx";
import { useI18n } from "@useI18n";
import { useVr } from "@logics_configs";
import styles from "./VrKeyboardWindow.module.scss";

// キーボードを開閉するコントローラのショートカット (off は手首のランチャーからだけ開く)
const SHORTCUTS = ["off", "stick_double", "menu_long", "menu_double"];

// つまみを引いて選ぶ値 (min〜max を step ごと)。動かす間に何度も送る (すぐ見た目に出る)
const Slider = ({ value, min, max, step, format, onChange }) => {
    const track = useRef(null);
    const [drag, setDrag] = useState(null);
    const valueAt = (event) => {
        const r = track.current.getBoundingClientRect();
        const x = Math.min(1, Math.max(0, (event.clientX - r.left) / r.width));
        return Number((min + Math.round((x * (max - min)) / step) * step).toFixed(2));
    };
    const onMouseDown = (event) => {
        if (event.button !== 0) return;
        event.preventDefault();
        let last = valueAt(event);
        setDrag(last);
        onChange(last);
        const move = (e) => {
            const v = valueAt(e);
            if (v === last) return;
            last = v;
            setDrag(v);
            onChange(v);
        };
        const up = () => {
            window.removeEventListener("mousemove", move);
            window.removeEventListener("mouseup", up);
            setDrag(null);
        };
        window.addEventListener("mousemove", move);
        window.addEventListener("mouseup", up);
    };
    const shown = drag ?? value;
    const at = `${((shown - min) / (max - min)) * 100}%`;
    return <>
        <div ref={track} className={styles.slider} role="slider" aria-valuemin={min} aria-valuemax={max} aria-valuenow={shown}
            onMouseDown={onMouseDown}>
            <span className={styles.slider_fill} style={{ width: at }} />
            <span className={styles.slider_thumb} style={{ left: at }} />
        </div>
        <span className={styles.setting_value}>{format(shown)}</span>
    </>;
};

// 歯車のパネル: キーボードだけの設定 (VR 設定ウィンドウには置かない)。歯車の下に右寄せ、縦1列。
// press: キーと同じ押し方 (音を鳴らして handler)
export const KeyboardSettings = ({ press, onClose }) => {
    const { t } = useI18n();
    const { currentKeyboardOpacity, setKeyboardOpacity, currentIsEnabledKeyboardKeySound, toggleIsEnabledKeyboardKeySound,
        currentKeyboardKeySoundVolume, setKeyboardKeySoundVolume, currentIsEnabledKeyboardTypingIndicator,
        toggleIsEnabledKeyboardTypingIndicator, currentKeyboardShortcut, setKeyboardShortcut } = useVr();
    // ショートカットの一覧はその行の下に広がる (パネルはスクロールするので、下に開く窓だと切れる)
    const [shortcuts_open, setShortcutsOpen] = useState(false);
    const shortcut = SHORTCUTS.includes(currentKeyboardShortcut.data) ? currentKeyboardShortcut.data : "off";
    const percent = (v) => `${Math.round(v)}%`;
    const toggle = (label, sub, variable, onToggle) => (
        <button type="button" className={styles.setting} aria-pressed={variable.data === true} onMouseDown={press(onToggle, "soft", label)}>
            <span className={styles.setting_label}>{label}{sub && <span className={styles.setting_sub}>{sub}</span>}</span>
            <span className={clsx(styles.switch, { [styles.is_on]: variable.data === true })} aria-hidden="true" />
        </button>
    );
    return <div className={clsx(styles.menu, styles.settings_menu)} role="dialog" aria-label={t("vr_panel.keyboard.customize")}>
        <div className={styles.settings}>
            <div className={styles.setting}>
                <span className={styles.setting_label}>{t("vr_panel.keyboard.opacity")}</span>
                <Slider value={Number(currentKeyboardOpacity.data) * 100} min={20} max={100} step={5} format={percent}
                    onChange={(v) => setKeyboardOpacity(v / 100)} />
            </div>
            {toggle(t("vr_panel.keyboard.key_sound"), null, currentIsEnabledKeyboardKeySound, toggleIsEnabledKeyboardKeySound)}
            <div className={clsx(styles.setting, { [styles.is_off]: currentIsEnabledKeyboardKeySound.data !== true })}>
                <span className={styles.setting_label}>{t("vr_panel.keyboard.key_sound_volume")}</span>
                <Slider value={Number(currentKeyboardKeySoundVolume.data)} min={0} max={100} step={5} format={percent}
                    onChange={setKeyboardKeySoundVolume} />
            </div>
            {toggle(t("vr_panel.keyboard.typing_indicator"), t("vr_panel.keyboard.typing_indicator_desc"),
                currentIsEnabledKeyboardTypingIndicator, toggleIsEnabledKeyboardTypingIndicator)}
            <div className={clsx(styles.fold, { [styles.is_open]: shortcuts_open })}>
                <button type="button" className={styles.fold_head} aria-expanded={shortcuts_open} aria-haspopup="listbox"
                    onMouseDown={press(() => setShortcutsOpen(o => !o), "soft", "shortcut")}>
                    <span className={styles.setting_label}>{t("vr_panel.keyboard.shortcut")}</span>
                    <span className={styles.fold_current}>{t(`vr_panel.keyboard.shortcut_${shortcut}`)}</span>
                    <svg className={styles.fold_chevron} viewBox="0 0 20 20" aria-hidden="true"><path d="m4 7.5 6 6 6-6" /></svg>
                </button>
                <div className={styles.fold_panel}>
                    <div className={styles.fold_inner}>
                        <div className={styles.fold_options} role="listbox" aria-label={t("vr_panel.keyboard.shortcut")}>
                            {SHORTCUTS.map((s) => (
                                <button key={s} type="button" role="option" aria-selected={s === shortcut} className={styles.fold_option}
                                    onMouseDown={press(() => { setKeyboardShortcut(s); setShortcutsOpen(false); }, "soft", `shortcut:${s}`)}>
                                    <svg viewBox="0 0 18 18" aria-hidden="true"><path d="m3 9.5 4 4L15 5" /></svg>
                                    <span>{t(`vr_panel.keyboard.shortcut_${s}`)}</span>
                                </button>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <button type="button" className={styles.settings_close} onMouseDown={press(onClose, "soft", "close")}>{t("common.close_button_label")}</button>
    </div>;
};
