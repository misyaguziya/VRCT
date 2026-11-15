// Build display spans in text order, with the caret separating before/after spans.
// All offsets (including the chat limit) count Unicode characters, not UTF-16 units.
export const compositionParts = (state, styles) => {
    const c = state.composition;
    const text = [...state.text];
    const after = [...(state.after ?? "")];
    const [selectedBefore, selectedAfter] = state.selected ?? [0, 0];
    const preedit = c ? [...c.preedit] : [];
    const cursor = Math.max(0, Math.min(preedit.length, c?.cursor ?? preedit.length));
    const [start, end] = c?.selection ?? [0, 0];
    const composing = [[0, start, styles.preedit], [start, end, styles.selection], [end, preedit.length, styles.preedit]]
        .flatMap(([from, to, className]) => [
            { text: preedit.slice(from, Math.min(to, cursor)).join(""), className },
            { text: preedit.slice(Math.max(from, cursor), to).join(""), className, after: true },
        ]);
    const pieces = [
        { text: text.slice(0, text.length - selectedBefore).join("") },
        { text: text.slice(text.length - selectedBefore).join(""), className: styles.selected },
        ...composing,
        ...(state.syllable ? [{ text: state.syllable, className: styles.selection }] : []),
        { text: after.slice(0, selectedAfter).join(""), className: styles.selected, after: true },
        { text: after.slice(selectedAfter).join(""), after: true },
    ];
    let count = 0;
    return pieces.flatMap(({ text, className, after }, i) => {
        const chars = [...text];
        const keep = Math.max(0, Math.min(chars.length, 144 - count));
        count += chars.length;
        return [
            { key: `${i}`, text: chars.slice(0, keep).join(""), className, after },
            { key: `${i}-over`, text: chars.slice(keep).join(""), className: [className, styles.over].filter(Boolean).join(" "), after },
        ].filter(p => p.text);
    });
};
