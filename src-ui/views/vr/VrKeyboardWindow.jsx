import { useEffect, useLayoutEffect, useRef, useState } from "react";
import clsx from "clsx";
import { useI18n } from "@useI18n";
import { useStdoutToPython } from "@useStdoutToPython";
import { useKeyboard } from "@logics_common";
import { useVr } from "@logics_configs";
import KeyboardSvg from "@images/mui_keyboard_alt.svg?react";
import SendSvg from "@images/send_message.svg?react";
import { VrWindow } from "./VrWindow";
import styles from "./VrKeyboardWindow.module.scss";

// VRキーボード。変換はバックエンド (vrct-ime: 日本語・中国語は RIME、韓国語は字母の組み立て) が行い、
// ここはキーを送って、返ってきた表示 (KeyboardState) を描くだけ。
// キーは押した瞬間 (mousedown) に送る (離すまで待つと、指すのがずれて別のキーになる)
const LANGUAGES = [["ja", "日本語"], ["en", "English"], ["ko", "한국어"], ["zh", "中文"]];
// 英字との切り替えキーの表示 (その言語の字 → A)
const MODE_MARK = { ja: "あ", ko: "한", zh: "中", en: "A" };
const CHAT_MAX = 144; // VRChat のチャットボックスの文字数
const SENT_FEEDBACK_MS = 2500;

// 2ボル式: 英字キーの字母 (Shift で濃音と ㅒ ㅖ)
const KOREAN = Object.fromEntries([..."qwertyuiopasdfghjklzxcvbnm"].map((c, i) => [c, [..."ㅂㅈㄷㄱㅅㅛㅕㅑㅐㅔㅁㄴㅇㄹㅎㅗㅓㅏㅣㅋㅌㅊㅍㅠㅜㅡ"][i]]));
const KOREAN_SHIFT = { q: "ㅃ", w: "ㅉ", e: "ㄸ", r: "ㄲ", t: "ㅆ", o: "ㅒ", p: "ㅖ" };

const LETTERS = ["qwertyuiop", "asdfghjkl", "zxcvbnm"];
const SYMBOLS = ["!?@#$%&*()", "~^=+/\\:;\"", "[]{}<>_"];
const PUNCTUATION = { ja: ["、", "。"], zh: ["，", "。"], ko: [",", "."], en: [",", "."] };

// キーの音 (短いクリック)。鳴らせない環境では何もしない
let audio_context = null;
const playKeySound = () => {
    try {
        audio_context ??= new AudioContext();
        const now = audio_context.currentTime;
        const oscillator = audio_context.createOscillator();
        const gain = audio_context.createGain();
        oscillator.type = "triangle";
        oscillator.frequency.setValueAtTime(1800, now);
        oscillator.frequency.exponentialRampToValueAtTime(900, now + 0.03);
        gain.gain.setValueAtTime(0.12, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.04);
        oscillator.connect(gain).connect(audio_context.destination);
        oscillator.start(now);
        oscillator.stop(now + 0.05);
    } catch {
        // 音が出せなくても入力は続ける
    }
};

export const VrKeyboardWindow = ({ onClose }) => {
    const { t } = useI18n();
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentKeyboardState, currentKeyboardLanguage, setKeyboardLanguage,
        currentIsEnabledKeyboardKeySound, currentIsEnabledKeyboardChineseSimplified, toggleIsEnabledKeyboardChineseSimplified } = useVr();
    const { currentKeyboardSendResult } = useKeyboard();
    const state = currentKeyboardState.data;
    const language = currentKeyboardLanguage.data;
    const [is_shift, setIsShift] = useState(false);
    const [is_symbols, setIsSymbols] = useState(false);
    // 英字との切り替えキーで戻る言語
    const before_english = useRef("ja");

    const needs_dictionary = language === "ja" || language === "zh";
    const is_ready = !needs_dictionary || state.status === "ready";
    const composing = state.composition !== null;

    const press = (handler) => (event) => {
        if (event.button !== 0) return;
        event.preventDefault();
        if (currentIsEnabledKeyboardKeySound.data === true) playKeySound();
        handler();
    };
    const sendKey = (key) => asyncStdoutToPython("/run/keyboard_key", key);
    const typeChar = (c) => {
        sendKey(is_shift ? c.toUpperCase() : c);
        setIsShift(false);
    };
    const changeLanguage = (code) => {
        if (code === language) return;
        setIsSymbols(false);
        setKeyboardLanguage(code);
    };
    const toggleEnglish = () => {
        if (language === "en") {
            changeLanguage(before_english.current);
        } else {
            before_english.current = language;
            changeLanguage("en");
        }
    };
    const send = (to) => asyncStdoutToPython("/run/keyboard_send", { to, id: crypto.randomUUID() });

    const charLabel = (c) => {
        if (language !== "ko" || is_symbols) return is_shift ? c.toUpperCase() : c;
        return (is_shift && KOREAN_SHIFT[c]) || KOREAN[c] || c;
    };
    const rows = is_symbols ? SYMBOLS : LETTERS;
    const [comma, period] = PUNCTUATION[language] ?? PUNCTUATION.en;
    const space_label = !composing ? t("vr_panel.keyboard.space")
        : language === "ja" ? t("vr_panel.keyboard.convert") : t("vr_panel.keyboard.select_first");
    const mode_label = language === "en" ? `A → ${MODE_MARK[before_english.current]}` : `${MODE_MARK[language]} → A`;

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

    return (
        <VrWindow Icon={KeyboardSvg} title={t("vr_panel.keyboard.title")} title_extra={tabs} onClose={onClose}>
            <div className={styles.keyboard}>
                <div className={styles.top}>
                    <Composition state={state} language={language} />
                    <button type="button" className={clsx(styles.send, styles.send_vrct)} disabled={!is_ready || state.length === 0}
                        onMouseDown={press(() => send("vrct"))}>
                        <span className={styles.send_title}><SendSvg className={styles.send_icon} aria-hidden="true" />{t("vr_panel.keyboard.send_vrct")}</span>
                        <span className={styles.send_help}>{t("vr_panel.keyboard.send_vrct_help")}</span>
                    </button>
                    <button type="button" className={clsx(styles.send, styles.send_paste)} disabled={!is_ready || state.length === 0}
                        onMouseDown={press(() => send("paste"))}>
                        <span className={styles.send_title}>{t("vr_panel.keyboard.send_paste")}</span>
                        <span className={styles.send_help}>{t("vr_panel.keyboard.send_paste_help")}</span>
                    </button>
                </div>
                <div className={styles.middle}>
                    {!is_ready ? <Preparing state={state} />
                        : <Candidates state={state} language={language} press={press} sendKey={sendKey} />}
                    <SentFeedback result={currentKeyboardSendResult.data} />
                </div>
                <div className={clsx(styles.keys, { [styles.is_waiting]: !is_ready })}>
                    <div className={styles.row}>
                        {[..."1234567890-"].map(c => <Key press={press} key={c} label={c} onPress={() => sendKey(c)} disabled={!is_ready} />)}
                        <Key press={press} label={t("vr_panel.keyboard.delete")} w={120} kind="mod" onPress={() => sendKey("Backspace")} disabled={!is_ready} />
                    </div>
                    <div className={styles.row}>
                        {[...rows[0]].map(c => <Key press={press} key={c} label={charLabel(c)} onPress={() => typeChar(c)} disabled={!is_ready} />)}
                    </div>
                    <div className={styles.row}>
                        {[...rows[1]].map(c => <Key press={press} key={c} label={charLabel(c)} onPress={() => typeChar(c)} disabled={!is_ready} />)}
                        <Key press={press} label={t("vr_panel.keyboard.commit")} w={160} kind="act" onPress={() => sendKey("Enter")} disabled={!is_ready} />
                    </div>
                    <div className={styles.row}>
                        <button type="button" className={clsx(styles.key, styles.mod)} style={{ width: 120 }} aria-label={t("vr_panel.keyboard.shift")}
                            aria-pressed={is_shift} disabled={!is_ready} onMouseDown={press(() => setIsShift(s => !s))}>⇧</button>
                        {[...rows[2]].map(c => <Key press={press} key={c} label={charLabel(c)} onPress={() => typeChar(c)} disabled={!is_ready} />)}
                        <Key press={press} label={comma} onPress={() => sendKey(comma)} disabled={!is_ready} />
                        <Key press={press} label={period} onPress={() => sendKey(period)} disabled={!is_ready} />
                    </div>
                    <div className={styles.row}>
                        {/* 準備中でも押せる (英字に切り替えれば、その間も打てる) */}
                        <Key press={press} label={mode_label} w={120} kind="mod" aria={t("vr_panel.keyboard.switch_english")} onPress={toggleEnglish} />
                        <button type="button" className={clsx(styles.key, styles.mod)} style={{ width: 120 }} aria-pressed={is_symbols}
                            disabled={!is_ready} onMouseDown={press(() => setIsSymbols(s => !s))}>
                            {is_symbols ? "ABC" : t("vr_panel.keyboard.symbols")}
                        </button>
                        <Key press={press} label={space_label} w={480} kind="act" onPress={() => sendKey("Space")} disabled={!is_ready} />
                        <Key press={press} label="←" kind="mod" aria={t("vr_panel.keyboard.left")} onPress={() => sendKey("Left")} disabled={!is_ready} />
                        <Key press={press} label="→" kind="mod" aria={t("vr_panel.keyboard.right")} onPress={() => sendKey("Right")} disabled={!is_ready} />
                    </div>
                </div>
            </div>
        </VrWindow>
    );
};

const Key = ({ press, label, w = 80, kind = "char", aria, onPress, disabled = false }) => (
    <button type="button" className={clsx(styles.key, styles[kind])} style={{ width: w }} aria-label={aria ?? label}
        disabled={disabled} onMouseDown={press(onPress)}>{label}</button>
);

// 打った文字と、変換中の語 (文節を選んでいるところを強調)。長くなったら終わりの方を見せる
const Composition = ({ state, language }) => {
    const line = useRef(null);
    useLayoutEffect(() => {
        if (line.current) line.current.scrollLeft = line.current.scrollWidth;
    });
    const c = state.composition;
    const preedit = c ? [...c.preedit] : [];
    const [start, end] = c ? c.selection : [0, 0];
    return (
        <div className={styles.composition}>
            <div ref={line} className={styles.line} lang={language}>
                <span>{state.text}</span>
                {c && <>
                    <span className={styles.preedit}>{preedit.slice(0, start).join("")}</span>
                    <span className={styles.selection}>{preedit.slice(start, end).join("")}</span>
                    <span className={styles.preedit}>{preedit.slice(end).join("")}</span>
                </>}
                {state.syllable && <span className={styles.selection}>{state.syllable.text}</span>}
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

// 送った直後に、どうなったかを少しの間だけ出す
const SentFeedback = ({ result }) => {
    const { t } = useI18n();
    const [shown, setShown] = useState(null);
    useEffect(() => {
        if (!result || Date.now() - result.at > SENT_FEEDBACK_MS) return undefined;
        setShown(result);
        const timer = setTimeout(() => setShown(null), SENT_FEEDBACK_MS);
        return () => clearTimeout(timer);
    }, [result?.at]);
    if (!shown) return null;
    const message = shown.to === "vrct" ? t("vr_panel.keyboard.sent_vrct")
        : shown.pasted ? t("vr_panel.keyboard.pasted") : t("vr_panel.keyboard.copied_only");
    return <div className={clsx(styles.feedback, { [styles.is_warning]: shown.to === "paste" && !shown.pasted })} role="status">{message}</div>;
};
