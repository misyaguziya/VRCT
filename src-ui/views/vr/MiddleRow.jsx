import { useEffect, useState } from "react";
import clsx from "clsx";
import { useI18n } from "@useI18n";
import { useStdoutToPython } from "@useStdoutToPython";
import styles from "./VrKeyboardWindow.module.scss";

// 入力欄とキーの間の段: 変換の候補、辞書の準備、コピーだけしたときの知らせ
const SENT_FEEDBACK_MS = 2500;

// 変換の候補 (押して選ぶ)。英語・韓国語は候補がないので何も出さない
export const Candidates = ({ state, language, lang, press, sendKey }) => {
    const { t } = useI18n();
    const { asyncStdoutToPython } = useStdoutToPython();
    if (language === "ko" || language === "en") return <div className={styles.candidates} />;
    return <div className={styles.candidates} lang={lang}>
        {state.candidates.map((text, index) => (
            <button key={`${state.page}-${index}`} type="button" className={styles.candidate}
                aria-pressed={state.converting && index === state.highlighted}
                onMouseDown={press(() => asyncStdoutToPython("/run/keyboard_select", index), "key", `candidate:${index}`)}>{text}</button>
        ))}
        <span className={styles.spacer} />
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
