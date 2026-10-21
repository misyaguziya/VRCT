import KEYS from "@root/native/vrct-ime/keys.yaml";

// VRキーボードのキーの並びと印字。何が入るかはバックエンド (vrct-ime) が決め、記号と韓国語の字母の表
// (keys.yaml) はバックエンドと同じものを使う (印字と入る字が食い違わないように)

// キーの並び: 日本語は JIS 配列、英語・中国語・韓国語は US 配列 (韓国語は KS X 5002、並びは US と同じ)。
// 文字のキーは "通常 Shift" の2文字 (英字は1文字: Shift で大文字)。Tab・Caps Lock・Ctrl・Alt は置かず、
// その分は空ける (文字のキーの位置は実際のキーボードと同じ)。1段は 15 キー分。
// 一番下の段 (言語・空白・マイク・矢印) は VrKeyboardWindow が並べる
// { gap }: 空き、{ special }: 文字以外のキー (w はキー何個分)
const LETTERS_1 = [..."qwertyuiop"];
const LETTERS_2 = [..."asdfghjkl"];
const LETTERS_3 = [..."zxcvbnm"];
const JIS = [
    [{ special: "toggle", w: 1 }, "1!", "2\"", "3#", "4$", "5%", "6&", "7'", "8(", "9)", "0", "-=", "^~", "¥|", { special: "backspace", w: 1 }],
    // Enter は2段にまたがる L 字 (上の段の 1.5 キー分と、下の段の 1.25 キー分を1つのキーに見せる)
    [{ gap: 1.5 }, ...LETTERS_1, "@`", "[{", { special: "enter_top", w: 1.5 }],
    [{ gap: 1.75 }, ...LETTERS_2, ";+", ":*", "]}", { special: "enter_bottom", w: 1.25 }],
    [{ special: "shift", w: 2.25 }, ...LETTERS_3, ",<", ".>", "/?", "\\_", { special: "shift", w: 1.75 }],
];
const US = [
    ["`~", "1!", "2@", "3#", "4$", "5%", "6^", "7&", "8*", "9(", "0)", "-_", "=+", { special: "backspace", w: 2 }],
    [{ gap: 1.5 }, ...LETTERS_1, "[{", "]}", "\\|"],
    [{ gap: 1.75 }, ...LETTERS_2, ";:", "'\"", { special: "enter", w: 2.25 }],
    [{ special: "shift", w: 2.25 }, ...LETTERS_3, ",<", ".>", "/?", { special: "shift", w: 2.75 }],
];
export const layoutOf = (language) => (language === "ja" ? JIS : US);

// キー1つ分の間隔 (px): キー 72px + すき間 6px。15 キー分で 1164px (窓の中は 1168px)
const PITCH = 78;
export const GAP = 6;
export const widthOf = (units) => units * PITCH - GAP;

// 文字のキーの (通常, Shift) の字
export const charsOf = (spec) => (spec.length === 1 ? [spec, spec.toUpperCase()] : [spec[0], spec[1] ?? spec[0]]);

// 記号の印字: 日本語・中国語は入る字で (、。「」 など)。
// (\ はそのままだと日本語の字体で ¥ に見えて ¥ のキーと区別できないので ＼ と印字する)
const shownAs = (language, c) => KEYS.punctuation[language]?.[c] ?? (c === "\\" ? "＼" : c);

// キーの印字: 大きい字 (今押すと入る字) と、左上の小さい字 (もう一方の字。Shift で入る / Shift を外すと入る)。
// 英字は大文字で印字 (実際のキーと同じ)。韓国語は字母 (濃音などのあるキーは Shift の字母も)
export const legendOf = (spec, language, is_shift) => {
    const [normal, shifted] = charsOf(spec);
    if (language === "ko" && KEYS.korean[normal]) {
        const tense = KEYS.korean_shift[normal];
        return { main: is_shift && tense ? tense : KEYS.korean[normal], sub: tense && (is_shift ? KEYS.korean[normal] : tense) };
    }
    if (spec.length === 1) return { main: is_shift ? shifted : normal.toUpperCase(), sub: null };
    if (shifted === normal) return { main: shownAs(language, normal), sub: null };
    return is_shift ? { main: shownAs(language, shifted), sub: shownAs(language, normal) } : { main: shownAs(language, normal), sub: shownAs(language, shifted) };
};
