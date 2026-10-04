import { useId, useState } from "react";
import { useI18n } from "@useI18n";
import clsx from "clsx";

import styles from "./VrSettingsWindow.module.scss";

// VR設定ウィンドウの行の部品。スライダーはレーザーの震えで値がぶれるので使わず、
// ON/OFF はトグル、選択肢は一覧の画面 (Picker)、数値は −/＋ にする。
// variable は設定の atom ({ state, data })。処理中 (pending) は押せない。

export const SectionLabel = ({ label }) => <h2 className={styles.section_label}>{label}</h2>;

export const ToggleRow = ({ label, sub, variable, onToggle, is_disabled = false, disabled_reason }) => {
    const { t } = useI18n();
    const is_pending = variable.state === "pending";
    const is_locked = is_pending || is_disabled;
    return (
        <button
            className={clsx(styles.row, styles.clickable, { [styles.is_disabled]: is_disabled })}
            role="switch" aria-checked={variable.data === true} disabled={is_disabled && !is_pending} aria-disabled={is_locked} aria-busy={is_pending}
            onClick={() => !is_locked && onToggle()}
        >
            <span className={styles.label}>
                {label}
                {sub && <span className={styles.sub}>{sub}</span>}
                {is_pending && <span className={styles.reason} role="status">{t("vr_panel.settings.changing")}</span>}
                {!is_pending && is_disabled && <span className={styles.reason}>{disabled_reason ?? t("vr_panel.settings.unavailable")}</span>}
            </span>
            <span className={clsx(styles.switch, { [styles.is_on]: variable.data === true })} />
        </button>
    );
};

export const SelectRow = ({ label, value, is_pending = false, is_disabled = false, disabled_reason, onOpen }) => {
    const { t } = useI18n();
    const reason = is_pending ? t("vr_panel.settings.changing") : is_disabled ? (disabled_reason ?? t("vr_panel.settings.unavailable")) : null;
    const is_long = String(value ?? "").length > 24;
    return (
        <button
            className={clsx(styles.row, styles.clickable, styles.select, { [styles.select_long]: is_long, [styles.is_disabled]: is_disabled })}
            disabled={is_disabled && !is_pending} aria-disabled={is_pending || is_disabled} aria-busy={is_pending}
            onClick={() => !is_pending && !is_disabled && onOpen()}
        >
            <span className={styles.label}>{label}{reason && <span className={styles.reason} role="status">{reason}</span>}</span>
            <span className={styles.select_value}>{value}</span>
            <span className={styles.chevron} aria-hidden="true">›</span>
        </button>
    );
};

export const StepperRow = ({ label, sub, variable, setValue, min, max, step, format = (v) => v, is_disabled = false }) => {
    // 小数の刻み (0.05 など) の誤差を丸める
    const decimals = (String(step).split(".")[1] ?? "").length;
    const value = Number(variable.data);
    const stepValue = (sign) => {
        const next = Number((value + sign * step).toFixed(decimals));
        setValue(Math.min(Math.max(next, min), max));
    };
    return (
        <div className={styles.row}>
            <span className={styles.label}>
                {label}
                {sub && <span className={styles.sub}>{sub}</span>}
            </span>
            <Stepper label={label}
                value={format(value)}
                is_pending={variable.state === "pending"}
                is_disabled={is_disabled}
                can_decrease={value > min}
                can_increase={value < max}
                onStep={stepValue}
            />
        </div>
    );
};

// 2〜3択を並べて直接選ぶ (選んでいるものは塗り)。options: [{ id, label }]
export const SegmentRow = ({ label, sub, variable, options, onSelect }) => {
    const { t } = useI18n();
    const is_pending = variable.state === "pending";
    return (
        <div className={styles.row} aria-busy={is_pending}>
            <span className={styles.label}>
                {label}
                {sub && <span className={styles.sub}>{sub}</span>}
                {is_pending && <span className={styles.reason} role="status">{t("vr_panel.settings.changing")}</span>}
            </span>
            <div className={styles.segment}>
                {options.map(option => (
                    <button key={option.id}
                        className={clsx(styles.button, styles.segment_button, { [styles.is_on]: option.id === variable.data })}
                        aria-disabled={is_pending} aria-pressed={option.id === variable.data}
                        onClick={() => !is_pending && option.id !== variable.data && onSelect(option.id)}
                    >
                        {option.label}
                    </button>
                ))}
            </div>
        </div>
    );
};

const Stepper = ({ label, value, is_pending, is_disabled = false, can_decrease, can_increase, onStep }) => {
    const is_locked = is_pending || is_disabled;
    const { t } = useI18n();
    return (
        <div className={styles.stepper} aria-busy={is_pending}>
            <StepButton label="−" accessibleLabel={t("vr_panel.settings.decrease", { label })} is_enabled={can_decrease && !is_locked} onClick={() => !is_locked && onStep(-1)} />
            <div className={clsx(styles.value, { [styles.is_disabled]: is_disabled })}>
                <output aria-live="polite" aria-label={label}>{value}</output>
                {is_pending && <span className={styles.step_status} role="status">{t("vr_panel.settings.changing_short")}</span>}
            </div>
            <StepButton label="＋" accessibleLabel={t("vr_panel.settings.increase", { label })} is_enabled={can_increase && !is_locked} onClick={() => !is_locked && onStep(1)} />
        </div>
    );
};

const StepButton = ({ label, accessibleLabel, is_enabled, onClick }) => (
    <button
        className={clsx(styles.button, styles.step, { [styles.is_disabled]: !is_enabled })}
        aria-disabled={!is_enabled} aria-label={accessibleLabel}
        onClick={() => is_enabled && onClick()}
    >
        {label}
    </button>
);

// 自動がONの間は値を変えられない (デスクトップの設定画面と同じ)。
// 音量の確認はデスクトップと同じく、設定画面を閉じると止まる (ConfigPageCloseTriggerController)
export const ThresholdRow = ({
    label, automatic_label, CheckIcon, threshold, setThreshold, automatic, toggleAutomatic,
    check_status, startCheck, stopCheck, volume, min, max, step,
}) => {
    const { t } = useI18n();
    const is_automatic = automatic.data === true;
    const is_pending = threshold.state === "pending" || automatic.state === "pending";
    const is_checking = check_status.data === true;
    const is_check_pending = check_status.state === "pending";
    const level = Math.min(Number(volume) || 0, max);
    return (
        <div className={clsx(styles.row, styles.threshold_row)}>
            <div className={styles.row_line}>
                <span className={styles.label}>{label}{(is_pending || is_check_pending) && <span className={styles.reason} role="status">{t("vr_panel.settings.changing")}</span>}</span>
                <button
                    className={clsx(styles.button, styles.automatic, { [styles.is_on]: is_automatic })}
                    aria-disabled={is_pending} aria-pressed={is_automatic} aria-label={`${label}: ${automatic_label}`}
                    onClick={() => !is_pending && toggleAutomatic()}
                >
                    {automatic_label}
                </button>
            </div>
            <div className={styles.row_line}>
                <button
                    className={clsx(styles.button, styles.check, { [styles.is_on]: is_checking })}
                    aria-disabled={is_check_pending} aria-pressed={is_checking} aria-label={`${label}: ${t("vr_panel.settings.volume_check")}`}
                    onClick={() => !is_check_pending && (is_checking ? stopCheck() : startCheck())}
                >
                    <CheckIcon className={styles.check_icon} aria-hidden="true" />
                </button>
                <div className={styles.meter}>
                    <div
                        className={clsx(styles.meter_level, { [styles.is_over]: !is_automatic && level >= threshold.data })}
                        style={{ width: `${(level / max) * 100}%` }}
                    />
                    {!is_automatic && (
                        <div className={styles.meter_threshold} style={{ left: `${(threshold.data / max) * 100}%` }} />
                    )}
                </div>
                <Stepper label={label}
                    value={threshold.data}
                    is_pending={is_pending}
                    is_disabled={is_automatic}
                    can_decrease={threshold.data > min}
                    can_increase={threshold.data < max}
                    onStep={(sign) => setThreshold(Math.min(Math.max(threshold.data + sign * step, min), max))}
                />
            </div>
        </div>
    );
};

// 選択肢の一覧 (右側の一覧の代わりに表示する)。options: [{ id, label }]
export const Picker = ({ title, options, selected_id, back_label, onPick, onBack }) => (
    <>
        <div className={styles.picker_head}>
            <button className={clsx(styles.button, styles.back)} onClick={onBack}>‹ {back_label}</button>
            <span className={styles.picker_title}>{title}</span>
        </div>
        {options.map(option => (
            <button
                key={option.id}
                className={clsx(styles.row, styles.clickable, styles.option, { [styles.is_selected]: option.id === selected_id })}
                aria-pressed={option.id === selected_id}
                onClick={() => onPick(option.id)}
            >
                <span className={styles.label}>{option.label}</span>
            </button>
        ))}
    </>
);

export const Disclosure = ({ label, summary, is_pending = false, children }) => {
    const [expanded, setExpanded] = useState(false);
    const id = useId();
    const { t } = useI18n();
    return (
        <div className={styles.disclosure}>
            <button className={clsx(styles.row, styles.clickable, styles.disclosure_toggle)}
                aria-expanded={expanded} aria-controls={id} onClick={() => setExpanded(v => !v)}>
                <span className={styles.label}>{label}<span className={styles.summary}>{is_pending ? t("vr_panel.settings.changing") : summary}</span></span>
                <span className={styles.expand_label} aria-hidden="true">{expanded ? t("vr_panel.settings.collapse") : t("vr_panel.settings.expand")} {expanded ? "−" : "＋"}</span>
            </button>
            <div id={id} className={styles.disclosure_content} hidden={!expanded}>{children}</div>
        </div>
    );
};
