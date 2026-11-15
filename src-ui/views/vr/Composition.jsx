import { useLayoutEffect, useRef } from "react";
import clsx from "clsx";
import { useI18n } from "@useI18n";
import { compositionParts } from "./composition_parts.js";
import styles from "./VrKeyboardWindow.module.scss";

const CHAT_MAX = 144; // VRChat のチャットボックスの文字数
// 文字数はこれを超えたときだけ出す (残りが少ないときだけ気にすればよい)
const COUNTER_FROM = 120;

// 打った文字と、変換中の語 (文節を選んでいるところを強調)。長くなったら終わりの方を見せる
// 長くなると折り返し (最大4行)、入りきらなければ字を小さくする: 144文字まで全部見える
const LINE_FONT_SIZES = [28, 24, 20, 17];

// 右端: 残りが少ないときだけ文字数、何か入っていれば × (1回目で注意の色、続けてもう1回で全部消す)、
// 一番右に ↵ で送る先の印 (いつも同じ場所)。文を押すと、その位置にカーソルを置く (変換中は置かない)
export const Composition = ({ state, language, clear_armed, onClear, send_to_button, onCursor }) => {
    const { t } = useI18n();
    const line = useRef(null);
    // 入る大きさのうち一番大きい字に (それでも入らなければ最後を見せる)
    useLayoutEffect(() => {
        const el = line.current;
        if (!el) return;
        for (const size of LINE_FONT_SIZES) {
            el.style.fontSize = `${size}px`;
            if (el.scrollHeight <= el.clientHeight) break;
        }
        el.scrollTop = el.scrollHeight;
    });
    const c = state.composition;
    const all = compositionParts(state, styles);
    const parts = all.filter(p => !p.after);
    const after_parts = all.filter(p => p.after);
    // 押した点が文の何文字目か (字の間のどこか。字のない所は終わり)
    const placeCursor = (event) => {
        if (event.button !== 0) return;
        event.preventDefault();
        if (c) return;
        const at = document.caretPositionFromPoint?.(event.clientX, event.clientY);
        const node = at?.offsetNode ?? document.caretRangeFromPoint?.(event.clientX, event.clientY)?.startContainer;
        const offset = at?.offset ?? document.caretRangeFromPoint?.(event.clientX, event.clientY)?.startOffset ?? 0;
        let index = 0;
        for (const span of line.current.querySelectorAll("span:not([aria-hidden])")) {
            if (span.contains(node)) {
                index += [...(node.textContent ?? "").slice(0, offset)].length;
                return onCursor(index);
            }
            index += [...span.textContent].length;
        }
        onCursor(index);
    };
    return (
        <div className={styles.composition}>
            <div ref={line} className={styles.line} lang={language} onMouseDown={placeCursor}>
                {parts.map(p => <span key={p.key} className={p.className}>{p.text}</span>)}
                <span className={styles.caret} aria-hidden="true" />
                {after_parts.map(p => <span key={p.key} className={p.className}>{p.text}</span>)}
            </div>
            {state.length > COUNTER_FROM &&
                <span className={clsx(styles.counter, { [styles.is_over]: state.length > CHAT_MAX })}>{CHAT_MAX - state.length}</span>}
            {state.length > 0 && <button type="button" className={clsx(styles.clear, { [styles.is_armed]: clear_armed })}
                aria-label={t("vr_panel.keyboard.clear")} onMouseDown={onClear}>
                <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18" /></svg>
            </button>}
            {send_to_button}
        </div>
    );
};
