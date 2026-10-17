import { useEffect, useLayoutEffect, useRef, useState } from "react";
import clsx from "clsx";
import { useI18n } from "@useI18n";
import { useStdoutToPython } from "@useStdoutToPython";
import { useKeyboard } from "@logics_common";
import { useVr } from "@logics_configs";
import KeyboardSvg from "@images/mui_keyboard_alt.svg?react";
import { VrWindow } from "./VrWindow";
import styles from "./VrKeyboardWindow.module.scss";

// VRキーボード。変換はバックエンド (vrct-ime: 日本語・中国語は RIME、韓国語は字母の組み立て) が行い、
// ここはキーを送って、返ってきた表示 (KeyboardState) を描くだけ。
// キーは押した瞬間 (mousedown) に送る (離すまで待つと、指すのがずれて別のキーになる)。
// 変換していないときの ↵ は、選んでいる送る先 (KeyboardSendTo) へ送る (バックエンドが決める)
const LANGUAGES = [["ja", "日本語"], ["en", "English"], ["ko", "한국어"], ["zh", "中文"]];
// 英字との切り替えキーの表示 (その言語の字 → A)
const MODE_MARK = { ja: "あ", ko: "한", zh: "中", en: "A" };
const CHAT_MAX = 144; // VRChat のチャットボックスの文字数
const SENT_FEEDBACK_MS = 2500;

// 2ボル式: 英字キーの字母 (Shift で濃音と ㅒ ㅖ)
const KOREAN = Object.fromEntries([..."qwertyuiopasdfghjklzxcvbnm"].map((c, i) => [c, [..."ㅂㅈㄷㄱㅅㅛㅕㅑㅐㅔㅁㄴㅇㄹㅎㅗㅓㅏㅣㅋㅌㅊㅍㅠㅜㅡ"][i]]));
const KOREAN_SHIFT = { q: "ㅃ", w: "ㅉ", e: "ㄸ", r: "ㄲ", t: "ㅆ", o: "ㅒ", p: "ㅖ" };

// キーの並び: 日本語は JIS 配列、英語・中国語・韓国語は US 配列 (韓国語は KS X 5002、並びは US と同じ)。
// 文字のキーは "通常 Shift" の2文字 (英字は1文字: Shift で大文字)。Tab・Caps Lock・Ctrl・Alt は置かず、
// その分は空ける (文字のキーの位置は実際のキーボードと同じ)。1段は 15 キー分。
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
const layoutOf = (language) => (language === "ja" ? JIS : US);
// 文字のキーの (通常, Shift) の字
const charsOf = (spec) => (spec.length === 1 ? [spec, spec.toUpperCase()] : [spec[0], spec[1] ?? spec[0]]);
// 日本語・中国語で、記号がどの字になるか (変換はバックエンドの vrct-ime が行う。ここは表示だけ)
const SHOWN_AS = {
    ja: { ",": "、", ".": "。", "?": "？", "!": "！", "[": "「", "]": "」", "/": "・", "~": "〜" },
    zh: { ",": "，", ".": "。", "?": "？", "!": "！", "[": "「", "]": "」", ";": "；", ":": "：", "(": "（", ")": "）" },
};
// キー1つ分の間隔 (px): キー 72px + すき間 6px。15 キー分で 1164px (窓の中は 1168px)
const PITCH = 78;
const GAP = 6;
const widthOf = (units) => units * PITCH - GAP;

// キーの音: 短いノイズの「カチッ」と低い胴鳴り (大きいキーは低め)。鳴らせない環境では何もしない
let audio_context = null;
const click_buffers = {};
const clickBuffer = (context, big) => {
    const rate = context.sampleRate;
    const buffer = context.createBuffer(1, Math.floor(rate * 0.035), rate);
    const data = buffer.getChannelData(0);
    let previous = 0;
    for (let i = 0; i < data.length; i++) {
        const t = i / rate;
        const noise = Math.random() * 2 - 1;
        // 差分でノイズの低い音を削る (高い「チッ」だけ残す)
        const tick = (noise - previous) * Math.exp(-t * (big ? 220 : 320));
        previous = noise;
        const body = Math.sin(2 * Math.PI * (big ? 120 : 180) * t) * Math.exp(-t * 110);
        data[i] = tick * 0.35 + body * 0.45;
    }
    return buffer;
};
const playKeySound = (big) => {
    try {
        audio_context ??= new AudioContext();
        if (audio_context.state === "suspended") audio_context.resume();
        click_buffers[big] ??= clickBuffer(audio_context, big);
        const source = audio_context.createBufferSource();
        source.buffer = click_buffers[big];
        source.playbackRate.value = 0.95 + Math.random() * 0.1; // 連打で同じ音に聞こえないよう少しずらす
        const gain = audio_context.createGain();
        gain.gain.value = 0.5;
        source.connect(gain).connect(audio_context.destination);
        source.start();
    } catch {
        // 音が出せなくても入力は続ける
    }
};

// 押している間くり返す (←・◀ ▶)。離す・外れるで止まる
const REPEAT_DELAY_MS = 500;
const REPEAT_EVERY_MS = 80;
const useRepeat = () => {
    const timer = useRef(null);
    const stop = () => {
        clearTimeout(timer.current);
        clearInterval(timer.current);
        timer.current = null;
    };
    useEffect(() => {
        window.addEventListener("mouseup", stop);
        return () => { stop(); window.removeEventListener("mouseup", stop); };
    }, []);
    const start = (action) => {
        stop();
        action();
        timer.current = setTimeout(() => { timer.current = setInterval(action, REPEAT_EVERY_MS); }, REPEAT_DELAY_MS);
    };
    return { start, stop };
};

export const VrKeyboardWindow = ({ onClose }) => {
    const { t } = useI18n();
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentKeyboardState, currentKeyboardLanguage, setKeyboardLanguage, currentKeyboardSendTo, setKeyboardSendTo,
        currentIsEnabledKeyboardKeySound, currentIsEnabledKeyboardChineseSimplified, toggleIsEnabledKeyboardChineseSimplified } = useVr();
    const { currentKeyboardSendResult } = useKeyboard();
    const repeat = useRepeat();
    const state = currentKeyboardState.data;
    const language = currentKeyboardLanguage.data;
    const send_to = currentKeyboardSendTo.data;
    // Shift: 1回押すと次の1文字だけ、続けてもう1回でロック (もう1回で解除)。左右は同じ状態
    const [shift, setShift] = useState("off");
    // 英字との切り替えキーで戻る言語
    const before_english = useRef("ja");

    const needs_dictionary = language === "ja" || language === "zh";
    const is_ready = !needs_dictionary || state.status === "ready";
    const composing = state.composition !== null;
    const is_shift = shift !== "off";

    const press = (handler, big = false) => (event) => {
        if (event.button !== 0) return;
        event.preventDefault();
        if (currentIsEnabledKeyboardKeySound.data === true) playKeySound(big);
        handler();
    };
    const sendKey = (key) => asyncStdoutToPython("/run/keyboard_key", key);
    const typeChar = (spec) => {
        const [normal, shifted] = charsOf(spec);
        sendKey(is_shift ? shifted : normal);
        if (shift === "once") setShift("off");
    };
    const pressShift = () => setShift(s => (s === "off" ? "once" : s === "once" ? "lock" : "off"));
    const changeLanguage = (code) => {
        if (code !== language) setKeyboardLanguage(code);
    };
    const toggleEnglish = () => {
        if (language === "en") {
            changeLanguage(before_english.current);
        } else {
            before_english.current = language;
            changeLanguage("en");
        }
    };

    // キーの印字: 大きい字 (今押すと入る字) と、左上の小さい字 (もう一方の字。Shift で入る / Shift を外すと入る)。
    // 英字は大文字で印字 (実際のキーと同じ)。韓国語は字母 (濃音などのあるキーは Shift の字母も)。
    // 日本語・中国語の記号は入る字で (、。「」 など)
    // (\ は日本語の字体で ¥ に見えて ¥ のキーと区別できないので、どの言語でも ＼ と印字する)
    const shown = (c) => SHOWN_AS[language]?.[c] ?? (c === "\\" ? "＼" : c);
    const legendOf = (spec) => {
        const [normal, shifted] = charsOf(spec);
        if (language === "ko" && KOREAN[normal]) {
            const tense = KOREAN_SHIFT[normal];
            return { main: is_shift && tense ? tense : KOREAN[normal], sub: tense && (is_shift ? KOREAN[normal] : tense) };
        }
        if (spec.length === 1) return { main: is_shift ? shifted : normal.toUpperCase(), sub: null };
        if (shifted === normal) return { main: shown(normal), sub: null };
        return is_shift ? { main: shown(shifted), sub: shown(normal) } : { main: shown(normal), sub: shown(shifted) };
    };
    const space_label = !composing ? t("vr_panel.keyboard.space")
        : language === "ja" ? t("vr_panel.keyboard.convert") : t("vr_panel.keyboard.select_first");
    // 変換中は確定、そうでなければ送る先
    const enter_label = composing ? t("vr_panel.keyboard.commit") : send_to === "paste" ? "→ VRChat" : "→ VRCT";
    const mode_label = language === "en" ? `A → ${MODE_MARK[before_english.current]}` : `${MODE_MARK[language]} → A`;
    // 1つのキー (文字・空き・文字以外)
    const keyOf = (item, index) => {
        if (typeof item === "string") {
            const { main, sub } = legendOf(item);
            return <Key press={press} key={item} label={main} corner={sub} lang={language} aria={main}
                onPress={() => typeChar(item)} disabled={!is_ready} />;
        }
        if (item.gap) return <span key={`gap-${index}`} className={styles.gap} style={{ width: widthOf(item.gap) }} aria-hidden="true" />;
        const w = widthOf(item.w);
        switch (item.special) {
            case "backspace":
                return <Key press={press} key="backspace" big label="←" w={w} kind="mod" aria={t("vr_panel.keyboard.delete")} disabled={!is_ready}
                    onPress={() => repeat.start(() => sendKey("Backspace"))} onLeave={repeat.stop} />;
            case "enter":
                return <Key press={press} key="enter" big label="↵" sub={enter_label} w={w} kind="act" aria={t("vr_panel.keyboard.commit")}
                    onPress={() => sendKey("Enter")} disabled={!is_ready} />;
            // JIS の L 字の Enter: どちらの部分を押しても Enter (印字は上の部分)
            case "enter_top":
                return <Key press={press} key="enter_top" big label="↵" sub={enter_label} w={w} kind="act" extra={clsx(styles.enter_part, styles.enter_top)}
                    aria={t("vr_panel.keyboard.commit")} onPress={() => sendKey("Enter")} disabled={!is_ready} />;
            case "enter_bottom":
                return <Key press={press} key="enter_bottom" big label="" w={w} kind="act" extra={clsx(styles.enter_part, styles.enter_bottom)}
                    aria={t("vr_panel.keyboard.commit")} onPress={() => sendKey("Enter")} disabled={!is_ready} />;
            case "shift":
                return <button key={`shift-${index}`} type="button" className={clsx(styles.key, styles.mod, { [styles.is_locked]: shift === "lock" })}
                    style={{ width: w }} aria-label={t("vr_panel.keyboard.shift")} aria-pressed={is_shift}
                    disabled={!is_ready} onMouseDown={press(pressShift, true)}>{shift === "lock" ? "⇪" : "⇧"}</button>;
            // JIS の左上 (半角/全角): 英字との切り替え
            case "toggle":
                return <Key press={press} key="toggle" big label="半/全" w={w} kind="mod" aria={t("vr_panel.keyboard.switch_english")} onPress={toggleEnglish} />;
            default:
                return null;
        }
    };

    const tabs = <div className={styles.tabs} role="group" aria-label={t("vr_panel.keyboard.language")}>
        {LANGUAGES.map(([code, name]) => (
            <button key={code} type="button" lang={code} className={styles.tab} aria-pressed={code === language}
                onMouseDown={press(() => changeLanguage(code))}>{name}</button>
        ))}
        {language === "zh" && (
            <button type="button" className={styles.tab} lang="zh" aria-pressed={currentIsEnabledKeyboardChineseSimplified.data === true}
                aria-label={t("vr_panel.keyboard.simplified")} onMouseDown={press(toggleIsEnabledKeyboardChineseSimplified)}>
                {currentIsEnabledKeyboardChineseSimplified.data === true ? "简" : "繁"}
            </button>
        )}
    </div>;
    // ↵ で送る先 (切り替え)。変換していないときに ↵ を押すと、選んでいる方へ送る。
    // タイトルバーに置いて、入力欄を端から端まで使う
    const send_to_switch = <div className={styles.tabs} role="radiogroup" aria-label={t("vr_panel.keyboard.send_to")}>
        {[["vrct", "send_vrct"], ["paste", "send_paste"]].map(([to, title]) => (
            <button key={to} type="button" role="radio" aria-checked={send_to === to} className={styles.tab}
                onMouseDown={press(() => { if (send_to !== to) setKeyboardSendTo(to); })}>
                {t(`vr_panel.keyboard.${title}`)}
            </button>
        ))}
    </div>;

    return (
        <VrWindow Icon={KeyboardSvg} title={t("vr_panel.keyboard.title")} title_extra={<>{tabs}{send_to_switch}</>} onClose={onClose}>
            <div className={styles.keyboard}>
                <div className={styles.top}>
                    <Composition state={state} language={language} />
                </div>
                <div className={styles.middle}>
                    {!is_ready ? <Preparing state={state} />
                        : <Candidates state={state} language={language} press={press} sendKey={sendKey} />}
                    <SentFeedback result={currentKeyboardSendResult.data} />
                </div>
                <div className={clsx(styles.keys, { [styles.is_waiting]: !is_ready })} style={{ "--key_gap": `${GAP}px` }}>
                    {layoutOf(language).map((row, r) => <div key={r} className={styles.row}>{row.map(keyOf)}</div>)}
                    <div className={styles.row}>
                        {/* 英字との切り替え (準備中でも押せる: 英字に切り替えれば、その間も打てる)。
                            JIS は左上の 半/全 で切り替えるので置かない */}
                        {language !== "ja" && <Key press={press} big label={mode_label} w={widthOf(1.75)} kind="mod"
                            aria={t("vr_panel.keyboard.switch_english")} onPress={toggleEnglish} />}
                        <Key press={press} big label={space_label} w={widthOf(7)} kind="act" onPress={() => sendKey("Space")} disabled={!is_ready} />
                        <Key press={press} big label="◀" w={widthOf(1)} kind="mod" aria={t("vr_panel.keyboard.left")} disabled={!is_ready}
                            onPress={() => repeat.start(() => sendKey("Left"))} onLeave={repeat.stop} />
                        <Key press={press} big label="▶" w={widthOf(1)} kind="mod" aria={t("vr_panel.keyboard.right")} disabled={!is_ready}
                            onPress={() => repeat.start(() => sendKey("Right"))} onLeave={repeat.stop} />
                    </div>
                </div>
            </div>
        </VrWindow>
    );
};

// label: 大きい字、corner: 左上の小さい字 (Shift の字)、sub: 下の小さい字 (↵ の送る先)
const Key = ({ press, label, corner, sub, lang, w = widthOf(1), kind = "char", extra, big = false, aria, onPress, onLeave, disabled = false }) => (
    <button type="button" className={clsx(styles.key, styles[kind], extra)} style={{ width: w }} aria-label={aria ?? label} lang={lang}
        disabled={disabled} onMouseDown={press(onPress, big)} onMouseLeave={onLeave}>
        {corner && <span className={styles.key_corner} aria-hidden="true">{corner}</span>}
        {label}{sub && <span className={styles.key_sub}>{sub}</span>}
    </button>
);

// 打った文字と、変換中の語 (文節を選んでいるところを強調)。長くなったら終わりの方を見せる
// 長くなると折り返し (最大4行)、入りきらなければ字を小さくする: 144文字まで全部見える
const LINE_FONT_SIZES = [28, 24, 20, 17];

// 字の並び (表示の部品ごと) を、144文字目までとそれより後に分ける (後ろは VRChat で切れる)
const splitAtLimit = (parts) => {
    let count = 0;
    return parts.flatMap(({ text, className }, i) => {
        const chars = [...text];
        const keep = Math.max(0, Math.min(chars.length, CHAT_MAX - count));
        count += chars.length;
        return [
            { key: `${i}`, text: chars.slice(0, keep).join(""), className },
            { key: `${i}-over`, text: chars.slice(keep).join(""), className: clsx(className, styles.over) },
        ].filter(p => p.text);
    });
};

const Composition = ({ state, language }) => {
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
    const preedit = c ? [...c.preedit] : [];
    const [start, end] = c ? c.selection : [0, 0];
    const parts = splitAtLimit([
        { text: state.text },
        ...(c ? [
            { text: preedit.slice(0, start).join(""), className: styles.preedit },
            { text: preedit.slice(start, end).join(""), className: styles.selection },
            { text: preedit.slice(end).join(""), className: styles.preedit },
        ] : []),
        ...(state.syllable ? [{ text: state.syllable.text, className: styles.selection }] : []),
    ]);
    return (
        <div className={styles.composition}>
            <div ref={line} className={styles.line} lang={language}>
                {parts.map(p => <span key={p.key} className={p.className}>{p.text}</span>)}
                <span className={styles.caret} aria-hidden="true" />
            </div>
            <span className={clsx(styles.counter, { [styles.is_over]: state.length > CHAT_MAX })}>{state.length} / {CHAT_MAX}</span>
        </div>
    );
};

// 変換の候補 (押して選ぶ)。韓国語は組み立て中の字の字母、英語は何も出さない
const Candidates = ({ state, language, press, sendKey }) => {
    const { t } = useI18n();
    const { asyncStdoutToPython } = useStdoutToPython();
    if (language === "ko") {
        return <div className={styles.candidates} lang="ko">
            {state.syllable && <span className={styles.syllable}>
                <b>{state.syllable.text}</b> = {state.syllable.jamo.join(" + ")}
            </span>}
            <span className={styles.hint}>{t("vr_panel.keyboard.korean_hint")}</span>
        </div>;
    }
    if (language === "en") return <div className={styles.candidates} />;
    return <div className={styles.candidates} lang={language}>
        {state.candidates.map((text, index) => (
            <button key={`${state.page}-${index}`} type="button" className={styles.candidate}
                aria-pressed={state.converting && index === state.highlighted}
                onMouseDown={press(() => asyncStdoutToPython("/run/keyboard_select", index))}>{text}</button>
        ))}
        <span className={styles.spacer} />
        {state.candidates.length > 0 && <>
            <button type="button" className={styles.page} aria-label={t("vr_panel.keyboard.previous_candidates")} disabled={state.page === 0}
                onMouseDown={press(() => sendKey("PageUp"))}>‹</button>
            <button type="button" className={styles.page} aria-label={t("vr_panel.keyboard.next_candidates")} disabled={state.last_page}
                onMouseDown={press(() => sendKey("PageDown"))}>›</button>
        </>}
    </div>;
};

// 日本語・中国語の辞書の準備 (初回は取得してから組み立てる)
const Preparing = ({ state }) => {
    const { t } = useI18n();
    if (state.status === "failed") {
        return <div className={styles.preparing}><span className={styles.preparing_title}>{t("vr_panel.keyboard.failed")}</span>
            <span className={styles.hint}>{t("vr_panel.keyboard.use_english")}</span></div>;
    }
    const percent = Math.round((state.progress ?? 0) * 100);
    return <div className={styles.preparing}>
        <span className={styles.preparing_title}>
            {state.status === "building" ? t("vr_panel.keyboard.building") : t("vr_panel.keyboard.downloading", { percent })}
        </span>
        <div className={styles.progress} role="progressbar" aria-valuemin={0} aria-valuemax={100}
            aria-valuenow={state.status === "building" ? 100 : percent}>
            <div className={clsx(styles.progress_bar, { [styles.is_building]: state.status === "building" })}
                style={{ width: `${state.status === "building" ? 100 : percent}%` }} />
        </div>
        <span className={styles.hint}>{t("vr_panel.keyboard.use_english")}</span>
    </div>;
};

// VRChat に貼れず、コピーだけしたときに少しの間だけ知らせる (打った文字は入力欄に残っている)。
// 送れたときは何も出さない (入力欄が空になるのでわかる)
const SentFeedback = ({ result }) => {
    const { t } = useI18n();
    const [shown, setShown] = useState(false);
    useEffect(() => {
        if (!result || result.to !== "paste" || result.pasted || Date.now() - result.at > SENT_FEEDBACK_MS) return undefined;
        setShown(true);
        const timer = setTimeout(() => setShown(false), SENT_FEEDBACK_MS);
        return () => clearTimeout(timer);
    }, [result?.at]);
    if (!shown) return null;
    return <div className={styles.feedback} role="status">{t("vr_panel.keyboard.copied_only")}</div>;
};
