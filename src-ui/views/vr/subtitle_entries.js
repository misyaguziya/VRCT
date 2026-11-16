// ログ窓を字幕の形にしたときに出す件 (オーバーレイの small / large と同じ規則)。
// 処理中・システムの件は出さない。複数行は送受信の直近 5 件、1 行は受信 (OCR を除く) の最新 1 件。
// 翻訳だけを出すとき (OVERLAY_SHOW_ONLY_TRANSLATED_MESSAGES) は原文を隠し、翻訳の無い件は出さない。
// 翻訳が無い件は原文を大きく出す。
// 返す件: { id, category, created_at, small: 小さく出す原文 (無ければ null), large: 大きく出す文の並び }
export const SUBTITLE_FORMS = ["multi_line", "single_line"];
const MULTI_LINE_COUNT = 5;

export const subtitleEntries = (logs, form, only_translated) => {
    const multi = form === "multi_line";
    const entries = [];
    for (const log of logs) {
        if (log.status !== "ok" || !(log.category === "sent" || log.category === "received")) continue;
        if (!multi && (log.category !== "received" || log.source === "ocr")) continue;
        const translations = log.messages?.translations ?? [];
        if (only_translated && translations.length === 0) continue;
        entries.push({
            id: log.id,
            category: log.category,
            created_at: log.created_at,
            small: translations.length > 0 && !only_translated ? log.messages.original : null,
            large: translations.length > 0 ? translations : [log.messages.original],
        });
    }
    return entries.slice(multi ? -MULTI_LINE_COUNT : -1);
};

// 見せる中身が変わったか (新しい件・翻訳が届いた・形が変わった) を見分けるための印
export const subtitleKey = (form, entries) => {
    const last = entries[entries.length - 1];
    return last ? `${form}:${last.id}:${last.large.length}:${last.small ? 1 : 0}` : `${form}:`;
};
