// ログ窓を字幕の形にしたときに出す件 (オーバーレイの small / large と同じ規則)。
// 処理中・システムの件は出さない。複数行は送受信の直近 5 件 (過去の件も)、1 行は出し始めてから受けた
// 受信 (OCR を除く) の最新 1 件。
// 翻訳だけを出すとき (OVERLAY_SHOW_ONLY_TRANSLATED_MESSAGES) は原文を隠し、翻訳の無い件は出さない。
// 翻訳が無い件は原文を大きく出す。
// 返す件: { id, category, is_ocr (OCR で読んだ受信), created_at, small: 小さく出す原文 (無ければ null), large: 大きく出す文の並び }
export const SUBTITLE_FORMS = ["multi_line", "single_line"];
// 字幕の文字の大きさ (訳文の px)。範囲は native/vrct-overlay/src/layout.rs SUBTITLE_FONT_SIZE_RANGE と同じ。
export const SUBTITLE_FONT_SIZE = { min: 16, max: 56 };
// 原文・時刻の行は訳文の約 2/3 (オーバーレイの large の 20 / 30)
export const subtitleSmallFontSize = (size) => Math.round(size * 2 / 3);
const MULTI_LINE_COUNT = 5;

// after_id: この id の件より後だけを出す (1 行は、出し始めてから受けた発言だけ。過去の件は出さない)
export const subtitleEntries = (logs, form, only_translated, after_id = null) => {
    const multi = form === "multi_line";
    const entries = [];
    const start = after_id === null ? 0 : logs.findIndex(log => log.id === after_id) + 1;
    for (const log of logs.slice(start)) {
        if (log.status !== "ok" || !(log.category === "sent" || log.category === "received")) continue;
        if (!multi && (log.category !== "received" || log.source === "ocr")) continue;
        const translations = log.messages?.translations ?? [];
        if (only_translated && translations.length === 0) continue;
        entries.push({
            id: log.id,
            category: log.category,
            is_ocr: log.source === "ocr",
            created_at: log.created_at,
            small: translations.length > 0 && !only_translated ? log.messages.original : null,
            large: translations.length > 0 ? translations : [log.messages.original],
        });
    }
    return entries.slice(multi ? -MULTI_LINE_COUNT : -1);
};

// 1 行の字幕の出し始め: 形が変わったか、ログ窓が開いたときに、その時点の最後の件 (last_id) から数え直す。
// 返す { form, is_open, after_id } の after_id を subtitleEntries に渡す (1 行以外は null)
export const nextShownSince = (prev, form, is_open, last_id) =>
    !prev || prev.form !== form || (is_open && !prev.is_open)
        ? { form, is_open, after_id: form === "single_line" ? last_id : null }
        : { ...prev, is_open };

// 見せる中身が変わったか (新しい件・翻訳が届いた・形が変わった) を見分けるための印。出す件の全部
// (5 件以下) をつなぐ (送信の訳が後の受信より遅れて届くこともある)。出す件が無くても形ごとの印を返す
// (空の板もすぐ知らせる。知らせないと、形を変えたときに vrct-overlay の待ちの上限 1.5 秒まで出ない)
export const subtitleKey = (form, entries) =>
    `${form}|${entries.map(e => `${e.id}:${e.large.length}:${e.small ? 1 : 0}`).join("|")}`;
