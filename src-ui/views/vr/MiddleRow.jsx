import { useEffect, useLayoutEffect, useRef, useState } from "react";
import clsx from "clsx";
import { useI18n } from "@useI18n";
import { useStdoutToPython } from "@useStdoutToPython";
import { isInteractionCancel } from "./interaction.js";
import styles from "./VrKeyboardWindow.module.scss";

// 入力欄とキーの間の段: 変換の候補、辞書の準備、コピーだけしたときの知らせ
const SENT_FEEDBACK_MS = 2500;

// これだけ横に動いたらスライド (候補は選ばない)。VR のコントローラーの手ぶれより大きく
const DRAG_FROM = 12;

// 変換の候補 (押して選ぶ)。英語・韓国語は候補がないので何も出さない
// 候補は帯の中に並び、入りきらなければ掴んで横にスライドできる (指を離したときに動いていなければ選ぶ)。
// スティック (縦のホイール) でも横に送る。‹ › は帯の外: 候補が多くてもいつも見える
export const Candidates = ({ state, language, lang, press, sendKey }) => {
    const { t } = useI18n();
    const { asyncStdoutToPython } = useStdoutToPython();
    const strip = useRef(null);
    const [dragging, setDragging] = useState(false);
    const highlighted = state.converting ? state.highlighted : -1;
    const shown = state.candidates.join("\n");
    // 候補が変わったら先頭から。変換中に選んでいる候補が帯の外なら、見える所までずらす
    useLayoutEffect(() => {
        const el = strip.current;
        if (!el) return;
        const item = el.children[highlighted];
        if (!item) { el.scrollLeft = 0; return; }
        if (item.offsetLeft < el.scrollLeft) el.scrollLeft = item.offsetLeft;
        else if (item.offsetLeft + item.offsetWidth > el.scrollLeft + el.clientWidth) el.scrollLeft = item.offsetLeft + item.offsetWidth - el.clientWidth;
    }, [state.page, shown, highlighted]);
    if (language === "ko" || language === "en") return <div className={styles.candidates} />;
    const select = (index) => press(() => asyncStdoutToPython("/run/keyboard_select", index), "key", `candidate:${index}`);
    const grab = (event) => {
        if (event.button !== 0) return;
        event.preventDefault();
        const el = strip.current;
        const index = [...el.children].indexOf(event.target.closest("button"));
        // 起点は押した点でなく最初の move の点: オーバーレイは down を引き金を引き始めた位置へ最大 12px 戻して送るため
        let x0 = null;
        let left0 = 0;
        let moved = false;
        const move = (e) => {
            if (e.clientX < 0) return; // パネルの外へ抜けた move (cancel の直前に -1 で届く)
            if (x0 === null) { x0 = e.clientX; left0 = el.scrollLeft; return; }
            if (!moved && Math.abs(e.clientX - x0) < DRAG_FROM) return;
            if (!moved) { moved = true; setDragging(true); }
            el.scrollLeft = left0 - (e.clientX - x0);
        };
        const up = (e) => {
            window.removeEventListener("mousemove", move);
            window.removeEventListener("mouseup", up);
            setDragging(false);
            if (moved || index < 0 || isInteractionCancel(e)) return;
            select(index)(e);
        };
        window.addEventListener("mousemove", move);
        window.addEventListener("mouseup", up);
    };
    // ponytail: 離した後の慣性スクロールは無し。素早く払って送りたくなったら足す
    return <div className={styles.candidates} lang={lang}>
        <div ref={strip} className={clsx(styles.candidate_strip, { [styles.is_dragging]: dragging })} onMouseDown={grab}
            onWheel={(e) => { strip.current.scrollLeft += e.deltaY; }}>
            {state.candidates.map((text, index) => (
                <button key={`${state.page}-${index}`} type="button" className={styles.candidate}
                    aria-pressed={state.converting && index === state.highlighted}>{text}</button>
            ))}
        </div>
        {state.candidates.length > 0 && <>
            <button type="button" className={styles.page} aria-label={t("vr_panel.keyboard.previous_candidates")} disabled={state.page === 0}
                onMouseDown={press(() => sendKey("PageUp"), "soft", "page_up")}>‹</button>
            <button type="button" className={styles.page} aria-label={t("vr_panel.keyboard.next_candidates")} disabled={state.last_page}
                onMouseDown={press(() => sendKey("PageDown"), "soft", "page_down")}>›</button>
        </>}
    </div>;
};

// 日本語・中国語の辞書の準備 (初回は取得してから組み立てる): 進み具合の線だけ。失敗したら「もう一度試す」だけ
export const Preparing = ({ state, press }) => {
    const { t } = useI18n();
    const { asyncStdoutToPython } = useStdoutToPython();
    if (state.status === "failed") {
        return <div className={styles.preparing}>
            <button type="button" className={styles.retry} aria-description={t("vr_panel.keyboard.failed")}
                onMouseDown={press(() => asyncStdoutToPython("/run/keyboard_retry"), "key", "retry")}>{t("vr_panel.keyboard.retry")}</button>
        </div>;
    }
    const building = state.status === "building";
    const percent = building ? 100 : Math.round((state.progress ?? 0) * 100);
    return <div className={styles.preparing}>
        <div className={styles.progress} role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={percent}
            aria-label={building ? t("vr_panel.keyboard.building") : t("vr_panel.keyboard.downloading", { percent })}>
            <div className={clsx(styles.progress_bar, { [styles.is_building]: building })} style={{ width: `${percent}%` }} />
        </div>
    </div>;
};

// VRChat に貼れず、コピーだけしたときに少しの間だけ知らせる (打った文字は入力欄に残っている)。
// 送れたときは何も出さない (入力欄が空になるのでわかる)
export const SentFeedback = ({ result }) => {
    const { t } = useI18n();
    const [shown, setShown] = useState(false);
    useEffect(() => {
        // 新しい結果が来たら、前の知らせは消す (出ている間に送り直して貼れたとき)
        setShown(false);
        if (!result || result.to !== "paste" || result.pasted || Date.now() - result.at > SENT_FEEDBACK_MS) return undefined;
        setShown(true);
        const timer = setTimeout(() => setShown(false), SENT_FEEDBACK_MS);
        return () => clearTimeout(timer);
    }, [result?.at]);
    if (!shown) return null;
    return <div className={styles.feedback} role="status">{t("vr_panel.keyboard.copied_only")}</div>;
};
