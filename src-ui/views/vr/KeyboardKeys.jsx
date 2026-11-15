import { useState } from "react";
import clsx from "clsx";
import { widthOf } from "./keyboard_layout";
import styles from "./VrKeyboardWindow.module.scss";

// BackSpace と ↵ の印: 字の ← ↵ は細くて小さく見えるので、線で太く・大きく描く
export const BackspaceIcon = () => (
    <svg className={styles.backspace_icon} viewBox="0 0 24 24" aria-hidden="true"><path d="M20 12H5M11 5l-7 7 7 7" /></svg>
);
export const EnterIcon = () => (
    <svg className={styles.enter_icon} viewBox="0 0 24 24" aria-hidden="true"><path d="M19 4v8a3 3 0 0 1-3 3H5M10 10l-5 5 5 5" /></svg>
);

// JIS の L 字の Enter の形: 上の段の部分の中に描き、下の段の部分へはみ出す。2つの部分を1つの形で塗る
// (別々に塗ると、つなぎ目に線が出て、不透明度を下げると重なった所が濃くなる)。枠 (指している間) は内側に描く
const KEY_H = 56;
const ROW_GAP = 8;
const RADIUS = 10;
const INNER_RADIUS = 6;
const RING = 3;
export const EnterShape = ({ top_w, bottom_w }) => {
    const s = RING / 2;
    const r = RADIUS - s;
    const ri = INNER_RADIUS + s;
    const height = KEY_H * 2 + ROW_GAP;
    const [left, right, top, bottom] = [s, top_w - s, s, height - s];
    // 上の部分の下辺と、下の部分の左辺
    const [step_y, step_x] = [KEY_H - s, top_w - bottom_w + s];
    const d = `M${left + r} ${top}H${right - r}A${r} ${r} 0 0 1 ${right} ${top + r}V${bottom - r}A${r} ${r} 0 0 1 ${right - r} ${bottom}`
        + `H${step_x + r}A${r} ${r} 0 0 1 ${step_x} ${bottom - r}V${step_y + ri}A${ri} ${ri} 0 0 0 ${step_x - ri} ${step_y}`
        + `H${left + r}A${r} ${r} 0 0 1 ${left} ${step_y - r}V${top + r}A${r} ${r} 0 0 1 ${left + r} ${top}Z`;
    return <svg className={styles.enter_shape} width={top_w} height={height} aria-hidden="true"><path d={d} strokeWidth={RING} /></svg>;
};

// ↵ で送る先の印: VRCT で送る = 吹き出し、VRChat に貼る = クリップボード
export const SendToIcon = ({ to }) => (
    <svg className={styles.stroke_icon} viewBox="0 0 24 24" aria-hidden="true">
        {to === "paste"
            ? <path d="M9 4h6v3H9zM8 5.5H6v15h12v-15h-2M9.5 12h5M9.5 16h5" />
            : <path d="M4 5h16v11h-9l-5 4v-4H4zM8 9.5h8M8 12.5h5" />}
    </svg>
);

// Shift の印 (字の ⇧ ⇪ はフォントによって色付きの絵文字になり、左右で色が揃わないので線で描く)。ロック中は塗って下に線
export const ShiftIcon = ({ locked }) => (
    <svg className={clsx(styles.shift_icon, { [styles.is_locked]: locked })} viewBox="0 0 24 24" aria-hidden="true">
        <path d="M12 3.5 20 12h-4.5v5.5h-7V12H4z" />{locked && <path d="M8.5 21h7" />}
    </svg>
);

// label: 大きい字、corner: 左上の小さい字 (Shift の字)。字は変わるたびに作り直す (変わった字だけが動く)。
// id: 音の上でどのキーか (既定は印字。文字のキーは Shift で印字が変わるのでキーの並びの名前を渡す)
export const Key = ({ press, id, label, corner, lang, w = widthOf(1), kind = "char", extra, sound = "key", aria, onPress, onLeave, disabled = false, motion, delay }) => (
        <button type="button" className={clsx(styles.key, styles[kind], extra)} style={{ width: w, "--key-width": w, "--delay": delay }}
            aria-label={aria ?? label} lang={lang} disabled={disabled} onMouseDown={press(onPress, sound, id ?? label)} onMouseLeave={onLeave}>
            <span className={styles.key_face}>
            {/* (key は大きい字と左上で別の名前: Shift で字が入れ替わるとき、同じ字として使い回されないように) */}
            {corner && <Legend key={`corner:${corner}`} text={corner} className={styles.key_corner} motion={motion} aria-hidden="true" />}
            {typeof label === "string" && label ? <Legend key={`label:${label}`} text={label} motion={motion} /> : label}
            </span>
        </button>
);

// 字1つ。作られたときの動き (motion) で現れ、その後は変えない (変えると、変わっていない字まで動き直す)
const Legend = ({ text, className, motion, ...rest }) => {
    const [appear] = useState(motion);
    return <span className={clsx(className, appear && styles[`appear_${appear}`])} {...rest}>{text}</span>;
};
