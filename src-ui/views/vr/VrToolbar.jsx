import clsx from "clsx";

import { useI18n } from "@useI18n";
import { useStdoutToPython } from "@useStdoutToPython";
import { useVr } from "@logics_configs";

import styles from "./VrToolbar.module.scss";

// ログウィンドウの下の操作バー (XSOverlay と同じ位置)。出し入れは Python 側が決める
// (ログか操作バーを少し指し続けたら出し、外れて2秒で消す。models/overlay/overlay.py)。
// 並びは、位置に関わる操作 (固定先・呼び戻す・ロック) を左、見え方に関わる操作 (不透明度) を右にする
const ANCHORS = [
    { id: "Playspace", label: "vr_panel.anchor_playspace", Icon: () => <Svg d="M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM3 12h18M12 3c3 3.2 3 14.8 0 18M12 3c-3 3.2-3 14.8 0 18" /> },
    { id: "LeftHand", label: "vr_panel.anchor_left_hand", Icon: () => <HandIcon /> },
    { id: "RightHand", label: "vr_panel.anchor_right_hand", Icon: () => <HandIcon is_right={true} /> },
    { id: "HMD", label: "vr_panel.anchor_head", Icon: () => <Svg d="M12 3.5a4.5 4.5 0 1 0 0 9 4.5 4.5 0 0 0 0-9zM4 21c.8-4 4-6.5 8-6.5s7.2 2.5 8 6.5" /> },
];
// 不透明度は押すたびに下の順で切り替わる (100% の次は 80%、40% の次は 100% に戻る)
const OPACITY_STEPS = [1.0, 0.8, 0.6, 0.4];
const FONT_SIZE = { min: 14, max: 28 };

export const VrToolbar = () => {
    const { t } = useI18n();
    const { asyncStdoutToPython } = useStdoutToPython();
    const {
        currentOverlayVrPanelAnchor,
        setOverlayVrPanelAnchor,
        currentOverlayVrPanelLocked,
        toggleOverlayVrPanelLocked,
        currentOverlayVrPanelOpacity,
        setOverlayVrPanelOpacity,
        currentOverlayVrPanelFontSize,
        setOverlayVrPanelFontSize,
    } = useVr();
    const font_size = currentOverlayVrPanelFontSize;
    const is_font_pending = font_size.state === "pending";

    const anchor = currentOverlayVrPanelAnchor;
    const locked = currentOverlayVrPanelLocked;
    const opacity = currentOverlayVrPanelOpacity;

    const nextOpacity = () => {
        const current = Number(opacity.data);
        return OPACITY_STEPS.find(step => step < current - 0.01) ?? OPACITY_STEPS[0];
    };

    return (
        <div className={styles.bar}>
            {ANCHORS.map(({ id, label, Icon }) => (
                <Button key={id} label={t(label)} Icon={Icon}
                    is_on={anchor.data === id} is_pending={anchor.state === "pending"}
                    onClick={() => anchor.data !== id && setOverlayVrPanelAnchor(id)} />
            ))}
            <span className={styles.separator} />
            <Button label={t("vr_panel.recall_log")}
                Icon={() => <Svg d="M12 5V2M12 22v-3M5 12H2M22 12h-3M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8z" />}
                onClick={() => asyncStdoutToPython("/run/vr_panel_recall_log")} />
            {/* ロックは ON のとき塗るトグル (既存の「ONは塗り」)。アイコンと名前は変えない */}
            <Button label={t("vr_panel.lock")}
                Icon={() => <Svg d="M6 11h12v10H6zM8.5 11V7.5a3.5 3.5 0 0 1 7 0V11" />}
                is_on={locked.data === true} is_pending={locked.state === "pending"}
                onClick={toggleOverlayVrPanelLocked} />
            <span className={styles.separator} />
            {/* 文字の大きさ: 端まで来たら押せない (薄くする) */}
            <TextButton label="A−" is_disabled={font_size.data <= FONT_SIZE.min} is_pending={is_font_pending}
                onClick={() => setOverlayVrPanelFontSize(font_size.data - 1)} />
            <span className={styles.value}>{font_size.data}</span>
            <TextButton label="A＋" is_disabled={font_size.data >= FONT_SIZE.max} is_pending={is_font_pending}
                onClick={() => setOverlayVrPanelFontSize(font_size.data + 1)} />
            <span className={styles.separator} />
            {/* 不透明度: 名前の代わりに今の値を出す */}
            <Button label={`${Math.round(Number(opacity.data) * 100)}%`}
                Icon={() => <Svg d="M4 4h16v16H4zM4 12h16M12 4v16" />}
                is_pending={opacity.state === "pending"}
                onClick={() => setOverlayVrPanelOpacity(nextOpacity())} />
        </div>
    );
};

const Button = ({ label, Icon, is_on = false, is_pending = false, onClick }) => (
    <button
        className={clsx(styles.button, { [styles.is_on]: is_on, [styles.is_pending]: is_pending })}
        onClick={() => !is_pending && onClick()}
    >
        <Icon />
        <span className={styles.label}>{label}</span>
    </button>
);

const TextButton = ({ label, is_disabled, is_pending, onClick }) => (
    <button
        className={clsx(styles.button, styles.text_button, { [styles.is_disabled]: is_disabled, [styles.is_pending]: is_pending })}
        onClick={() => !is_disabled && !is_pending && onClick()}
    >
        {label}
    </button>
);

const Svg = ({ d }) => (
    <svg className={styles.icon} viewBox="0 0 24 24" aria-hidden="true">
        <path d={d} />
    </svg>
);

// 手のひら (右手は左右反転)
const HandIcon = ({ is_right = false }) => (
    <svg className={styles.icon} viewBox="0 0 24 24" aria-hidden="true" style={is_right ? { transform: "scaleX(-1)" } : undefined}>
        <path d="M8 21v-5l-3-4V7M8 12V4.5a1.5 1.5 0 0 1 3 0V11M11 10V3.5a1.5 1.5 0 0 1 3 0V11M14 10.5V5a1.5 1.5 0 0 1 3 0v8c0 4-2 8-6 8H8" />
    </svg>
);
