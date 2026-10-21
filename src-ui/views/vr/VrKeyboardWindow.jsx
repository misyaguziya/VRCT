import { useEffect, useLayoutEffect, useRef, useState } from "react";
import clsx from "clsx";
import { useI18n } from "@useI18n";
import { useStdoutToPython } from "@useStdoutToPython";
import { useKeyboard } from "@logics_common";
import { useVr } from "@logics_configs";
import KeyboardSvg from "@images/mui_keyboard_alt.svg?react";
import MicSvg from "@images/mic.svg?react";
import { VrWindow } from "./VrWindow";
import styles from "./VrKeyboardWindow.module.scss";

// VRキーボード。変換はバックエンド (vrct-ime: 日本語・中国語は RIME、韓国語は字母の組み立て) が行い、
// ここはキーを送って、返ってきた表示 (KeyboardState) を描くだけ。
// キーは押した瞬間 (mousedown) に送る (離すまで待つと、指すのがずれて別のキーになる)。
// 変換していないときの ↵ は、選んでいる送る先 (KeyboardSendTo) へ送る (バックエンドが決める)
const LANGUAGES = [["ja", "日本語"], ["en", "English"], ["ko", "한국어"], ["zh", "中文"]];
// 言語キーの字 (中国語は簡・繁)
const LANGUAGE_MARK = { ja: "あ", ko: "한", en: "A" };
const CHAT_MAX = 144; // VRChat のチャットボックスの文字数
// 文字数はこれを超えたときだけ出す (残りが少ないときだけ気にすればよい)
const COUNTER_FROM = 120;
const SENT_FEEDBACK_MS = 2500;
// Shift をこの間に2回押すとロック
const SHIFT_LOCK_MS = 400;
// 不透明度の切り替え (ログの窓と同じ段階)
const OPACITY_STEPS = [1.0, 0.8, 0.6, 0.4];

// 2ボル式: 英字キーの字母 (Shift で濃音と ㅒ ㅖ)
const KOREAN = Object.fromEntries([..."qwertyuiopasdfghjklzxcvbnm"].map((c, i) => [c, [..."ㅂㅈㄷㄱㅅㅛㅕㅑㅐㅔㅁㄴㅇㄹㅎㅗㅓㅏㅣㅋㅌㅊㅍㅠㅜㅡ"][i]]));
const KOREAN_SHIFT = { q: "ㅃ", w: "ㅉ", e: "ㄸ", r: "ㄲ", t: "ㅆ", o: "ㅒ", p: "ㅖ" };

// キーの並び: 日本語は JIS 配列、英語・中国語・韓国語は US 配列 (韓国語は KS X 5002、並びは US と同じ)。
// 文字のキーは "通常 Shift" の2文字 (英字は1文字: Shift で大文字)。Tab・Caps Lock・Ctrl・Alt は置かず、
// その分は空ける (文字のキーの位置は実際のキーボードと同じ)。1段は 15 キー分。
// 矢印はノートパソコンのように一番下の段の右端に
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
// 全消去は続けてもう1回押したときだけ (1回目から この間に)
const CLEAR_CONFIRM_MS = 2000;
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

// キーの音: 実際のキーボードの1打ずつの録音 (出典は assets/sounds/keyboard/SOURCE.md)。Enter・BackSpace・Space・半/全 は
// 決まった音、それ以外は残りから選ぶ (同じキーを続けて押した時は同じ音)。鳴らせない環境では何もしない
const KEYPRESS_URLS = import.meta.glob("../assets/sounds/keyboard/keypress-*.wav", { eager: true, query: "?url", import: "default" });
const keypressUrl = (number) => KEYPRESS_URLS[`../assets/sounds/keyboard/keypress-${number}.wav`];
const FIXED_KEY_SOUNDS = { enter: keypressUrl("031"), backspace: keypressUrl("019"), space: keypressUrl("028"), toggle: keypressUrl("029") };
const SCATTERED_KEY_SOUNDS = Object.values(KEYPRESS_URLS).filter((url) => !Object.values(FIXED_KEY_SOUNDS).includes(url));
// 文字を打たない Shift と、半/全・◀ ▶・切り替え・タブなどは控えめに
const KEY_SOUND_GAIN = { shift: 0.05, soft: 0.05, toggle: 0.05 };
const KEY_SOUND_GAIN_DEFAULT = 0.1;
let audio_context = null;
const key_buffers = {};
// 最後に鳴らしたキーとその音
let last_key_sound = { id: undefined, url: null };
const keyBuffer = (url) => key_buffers[url] ??= fetch(url).then((response) => response.arrayBuffer())
    .then((data) => audio_context.decodeAudioData(data));
// 最初の1打が遅れないよう、開いた時に読んでおく
const loadKeySounds = () => {
    try {
        audio_context ??= new AudioContext();
        Object.values(KEYPRESS_URLS).forEach((url) => keyBuffer(url).catch(() => delete key_buffers[url]));
    } catch {
        // 音が出せなくても入力は続ける
    }
};
const playKeySound = (name, id) => {
    try {
        audio_context ??= new AudioContext();
        if (audio_context.state === "suspended") audio_context.resume();
        const same_key = id !== undefined && id === last_key_sound.id;
        const url = FIXED_KEY_SOUNDS[name]
            ?? (same_key ? last_key_sound.url : SCATTERED_KEY_SOUNDS[Math.floor(Math.random() * SCATTERED_KEY_SOUNDS.length)]);
        last_key_sound = { id, url };
        keyBuffer(url).then((buffer) => {
            const source = audio_context.createBufferSource();
            source.buffer = buffer;
            source.playbackRate.value = 0.95 + Math.random() * 0.1; // 連打で同じ音に聞こえないよう少しずらす
            const gain = audio_context.createGain();
            gain.gain.value = KEY_SOUND_GAIN[name] ?? KEY_SOUND_GAIN_DEFAULT;
            source.connect(gain).connect(audio_context.destination);
            source.start();
        }).catch(() => delete key_buffers[url]);
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
    // (離したことはオーバーレイが必ず送る。窓が切り替わったときも止める)
    useEffect(() => {
        window.addEventListener("mouseup", stop);
        window.addEventListener("blur", stop);
        return () => { stop(); window.removeEventListener("mouseup", stop); window.removeEventListener("blur", stop); };
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
        currentIsEnabledKeyboardKeySound, currentIsEnabledKeyboardChineseSimplified, toggleIsEnabledKeyboardChineseSimplified,
        currentIsEnabledKeyboardDictation, toggleIsEnabledKeyboardDictation, currentKeyboardOpacity, setKeyboardOpacity } = useVr();
    const { currentKeyboardSendResult } = useKeyboard();
    const repeat = useRepeat();
    const state = currentKeyboardState.data;
    const language = currentKeyboardLanguage.data;
    const send_to = currentKeyboardSendTo.data;
    // Shift: 1回押すと次の1文字だけ、素早く2回でロック (ロック中・次の1文字を待っている間にもう1回で解除)。左右は同じ状態
    const [shift, setShift] = useState("off");
    const shift_pressed_at = useRef(0);
    // 英字との切り替えキーで戻る言語
    const before_english = useRef("ja");

    const needs_dictionary = language === "ja" || language === "zh";
    const is_ready = !needs_dictionary || state.status === "ready";
    const composing = state.composition !== null;
    const is_shift = shift !== "off";

    useEffect(() => {
        if (currentIsEnabledKeyboardKeySound.data === true) loadKeySounds();
    }, [currentIsEnabledKeyboardKeySound.data]);

    // id: どのキーか (同じキーを続けて押した時は同じ音にする)
    const press = (handler, sound = "key", id = undefined) => (event) => {
        if (event.button !== 0) return;
        event.preventDefault();
        if (currentIsEnabledKeyboardKeySound.data === true) playKeySound(sound, id);
        handler();
    };
    const sendKey = (key) => asyncStdoutToPython("/run/keyboard_key", key);
    // 入力欄の文を押した位置へカーソルを置く
    const placeCursorAt = (index) => {
        if (currentIsEnabledKeyboardKeySound.data === true) playKeySound("soft", "cursor");
        asyncStdoutToPython("/run/keyboard_cursor", index);
    };
    // 長押しでくり返すキー (← ◀ ▶): くり返すたびに音も鳴らす (最初の1回の音は press が鳴らす)
    // id: 押したキーと同じ (同じキーの音のまま)
    const repeatKey = (key, sound, id = key) => {
        let first = true;
        repeat.start(() => {
            if (!first && currentIsEnabledKeyboardKeySound.data === true) playKeySound(sound, id);
            first = false;
            sendKey(key);
        });
    };
    const typeChar = (spec) => {
        const [normal, shifted] = charsOf(spec);
        sendKey(is_shift ? shifted : normal);
        if (shift === "once") setShift("off");
    };
    const pressShift = () => {
        const now = Date.now();
        const quick = now - shift_pressed_at.current < SHIFT_LOCK_MS;
        shift_pressed_at.current = now;
        setShift(s => (s === "off" ? "once" : s === "once" && quick ? "lock" : "off"));
    };
    // ↵: Shift を1回押した後なら改行 (送らない)。ロック中・変換中はいつもの ↵ (送る・確定)
    const is_newline = shift === "once" && !composing;
    const pressEnter = () => {
        if (!is_newline) return sendKey("Enter");
        sendKey("\n");
        setShift("off");
    };
    // 全消去: 1回目で「もう一度で消す」にして、続けてもう1回で消す (VR で間違えて押しても消えない)
    const [clear_armed, setClearArmed] = useState(false);
    useEffect(() => {
        if (!clear_armed) return undefined;
        const timer = setTimeout(() => setClearArmed(false), CLEAR_CONFIRM_MS);
        return () => clearTimeout(timer);
    }, [clear_armed]);
    const pressClear = () => {
        if (!clear_armed) return setClearArmed(true);
        setClearArmed(false);
        asyncStdoutToPython("/run/keyboard_clear");
    };
    const dictating = currentIsEnabledKeyboardDictation.data === true;
    const opacity = Number(currentKeyboardOpacity.data);
    // 開いている一覧: "language" (左下の言語キー) / "settings" (タイトルバーの不透明度の印) / null
    const [menu, setMenu] = useState(null);
    // 言語キーの字 (中国語は簡体字・繁体字のどちらか)
    const language_mark = language === "zh" ? (currentIsEnabledKeyboardChineseSimplified.data === true ? "简" : "繁") : LANGUAGE_MARK[language];
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
    // Space と ↵ は何も添えない (読み上げ用の名前だけ。↵ の送る先は入力欄の右端の印)
    const space_name = !composing ? t("vr_panel.keyboard.space")
        : language === "ja" ? t("vr_panel.keyboard.convert") : t("vr_panel.keyboard.select_first");
    const enter_name = composing ? t("vr_panel.keyboard.commit") : is_newline ? t("vr_panel.keyboard.newline") : t("vr_panel.keyboard.send_to");
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
                return <Key press={press} key="backspace" sound="backspace" label={<BackspaceIcon />} w={w} kind="mod" aria={t("vr_panel.keyboard.delete")} disabled={!is_ready}
                    onPress={() => repeatKey("Backspace", "backspace")} onLeave={repeat.stop} />;
            case "enter":
                return <Key press={press} key="enter" sound="enter" label={<EnterIcon />} w={w} kind="act" aria={enter_name}
                    onPress={pressEnter} disabled={!is_ready} />;
            // JIS の L 字の Enter: どちらの部分を押しても Enter (印字は上の部分)
            case "enter_top":
                return <Key press={press} key="enter_top" sound="enter" label={<EnterIcon />} w={w} kind="act" extra={clsx(styles.enter_part, styles.enter_top)}
                    aria={enter_name} onPress={pressEnter} disabled={!is_ready} />;
            case "enter_bottom":
                return <Key press={press} key="enter_bottom" sound="enter" label="" w={w} kind="act" extra={clsx(styles.enter_part, styles.enter_bottom)}
                    aria={enter_name} onPress={pressEnter} disabled={!is_ready} />;
            case "shift":
                return <button key={`shift-${index}`} type="button" className={clsx(styles.key, styles.mod, { [styles.is_locked]: shift === "lock" })}
                    style={{ width: w }} aria-label={t("vr_panel.keyboard.shift")} aria-pressed={is_shift}
                    disabled={!is_ready} onMouseDown={press(pressShift, "shift", "shift")}><ShiftIcon locked={shift === "lock"} /></button>;
            // JIS の左上 (半角/全角): 英字との切り替え
            case "toggle":
                return <Key press={press} key="toggle" sound="toggle" label="半/全" w={w} kind="mod" aria={t("vr_panel.keyboard.switch_english")} onPress={toggleEnglish} />;
            default:
                return null;
        }
    };

    // 一覧 (言語・不透明度) の1つの項目。選んでいるものはアクセントの字 (枠は描かない)。選ぶと閉じる
    const option = (key, label, selected, onPick, extra = {}) => (
        <button key={key} type="button" className={styles.option} aria-pressed={selected} {...extra}
            onMouseDown={press(() => { setMenu(null); onPick(); }, "soft", key)}>{label}</button>
    );
    const simplified_on = currentIsEnabledKeyboardChineseSimplified.data === true;
    // 言語の一覧 (左下の言語キーから)。中国語は簡体字・繁体字を別の項目に
    const pickChinese = (simplified) => {
        changeLanguage("zh");
        if (simplified !== simplified_on) toggleIsEnabledKeyboardChineseSimplified();
    };
    const language_menu = <div className={clsx(styles.menu, styles.language_menu)} role="menu" aria-label={t("vr_panel.keyboard.language")}>
        {LANGUAGES.filter(([code]) => code !== "zh").map(([code, name]) => option(`language:${code}`, name, code === language,
            () => changeLanguage(code), { lang: code }))}
        {option("language:zh-hans", "简体中文", language === "zh" && simplified_on, () => pickChinese(true), { lang: "zh-Hans" })}
        {option("language:zh-hant", "繁體中文", language === "zh" && !simplified_on, () => pickChinese(false), { lang: "zh-Hant" })}
    </div>;
    const percent = (o) => `${Math.round(o * 100)}%`;
    // 不透明度: タイトルバーの印から一覧を開いて選ぶ
    const settings_menu = <div className={clsx(styles.menu, styles.settings_menu)} role="menu" aria-label={t("vr_panel.keyboard.opacity")}>
        <div className={styles.menu_row}>
            {OPACITY_STEPS.map((o) => option(`opacity:${o}`, percent(o), Math.abs(o - opacity) < 0.01, () => setKeyboardOpacity(o)))}
        </div>
    </div>;
    const menu_button = <button type="button" className={styles.menu_button} aria-label={`${t("vr_panel.keyboard.opacity")}: ${percent(opacity)}`}
        aria-expanded={menu === "settings"} onMouseDown={press(() => setMenu(m => (m === "settings" ? null : "settings")), "soft", "menu")}>
        <svg className={styles.stroke_icon} viewBox="0 0 24 24" aria-hidden="true">
            <circle cx="12" cy="12" r="8" /><path className={styles.filled} d="M12 4a8 8 0 0 1 0 16z" />
        </svg>
    </button>;
    // ↵ で送る先: 入力欄の右端に今の送る先の印だけ。押すたびに切り替わる
    const send_to_button = <button type="button" className={styles.send_to} aria-label={t(`vr_panel.keyboard.${send_to === "paste" ? "send_paste" : "send_vrct"}`)}
        onMouseDown={press(() => setKeyboardSendTo(send_to === "paste" ? "vrct" : "paste"), "soft", "send_to")}>
        <SendToIcon to={send_to} />
    </button>;
    // 矢印キー (ノートパソコンの並び): 一番下の段の右端に ◀ ▲▼ ▶。▲ ▼ は1キー分を上下に分ける。
    // ◀ ▶ はカーソル (変換中は文節)、▲ ▼ は送った文の呼び出し
    const arrows = <>
        <Key press={press} sound="soft" label="◀" kind="mod" aria={t("vr_panel.keyboard.left")}
            onPress={() => repeatKey("Left", "soft", "◀")} onLeave={repeat.stop} />
        <div className={styles.updown} style={{ width: widthOf(1) }}>
            <Key press={press} sound="soft" label="▲" kind="mod" extra={styles.half} aria={t("vr_panel.keyboard.history_older")} onPress={() => sendKey("Up")} />
            <Key press={press} sound="soft" label="▼" kind="mod" extra={styles.half} aria={t("vr_panel.keyboard.history_newer")} onPress={() => sendKey("Down")} />
        </div>
        <Key press={press} sound="soft" label="▶" kind="mod" aria={t("vr_panel.keyboard.right")}
            onPress={() => repeatKey("Right", "soft", "▶")} onLeave={repeat.stop} />
    </>;

    return (
        <VrWindow Icon={KeyboardSvg} title="" title_extra={menu_button} onClose={onClose}>
            <div className={styles.keyboard}>
                {/* 一覧を開いている間は、外を押すと閉じる (その押下はキーに届かない) */}
                {menu && <div className={styles.backdrop} onMouseDown={(e) => { e.preventDefault(); setMenu(null); }} aria-hidden="true" />}
                {menu === "settings" && settings_menu}
                {menu === "language" && language_menu}
                <div className={styles.top}>
                    <Composition state={state} language={language} clear_armed={clear_armed} onClear={press(pressClear, "soft", "clear")}
                        send_to_button={send_to_button} onCursor={placeCursorAt} />
                </div>
                <div className={styles.middle}>
                    {!is_ready ? <Preparing state={state} press={press} />
                        : <Candidates state={state} language={language} press={press} sendKey={sendKey} />}
                    <SentFeedback result={currentKeyboardSendResult.data} />
                </div>
                <div className={clsx(styles.keys, { [styles.is_waiting]: !is_ready })} style={{ "--key_gap": `${GAP}px` }}>
                    {layoutOf(language).map((row, r) => <div key={r} className={styles.row}>{row.map(keyOf)}</div>)}
                    <div className={styles.row}>
                        {/* 言語: 今の言語の字だけを出し、押すと一覧 (準備中でも押せる: 英字に切り替えれば、その間も打てる) */}
                        <Key press={press} sound="toggle" label={language_mark} w={widthOf(1.75)} kind="mod" extra={styles.mark} lang={language}
                            aria={t("vr_panel.keyboard.language")} onPress={() => setMenu(m => (m === "language" ? null : "language"))} />
                        <Key press={press} sound="space" label="" w={widthOf(9)} kind="act" aria={space_name}
                            onPress={() => sendKey("Space")} disabled={!is_ready} />
                        {/* マイク: 聞き取った文を入力欄に入れる (送らない。直して ↵ で送る) */}
                        <button type="button" className={clsx(styles.key, styles.mod, { [styles.is_locked]: dictating })}
                            style={{ width: widthOf(1.25) }} aria-label={t("vr_panel.keyboard.dictation")} aria-pressed={dictating}
                            onMouseDown={press(toggleIsEnabledKeyboardDictation, "soft", "dictation")}>
                            <MicSvg className={styles.mic_icon} aria-hidden="true" />
                        </button>
                        {arrows}
                    </div>
                </div>
            </div>
        </VrWindow>
    );
};

// BackSpace と ↵ の印: 字の ← ↵ は細くて小さく見えるので、線で太く・大きく描く
const BackspaceIcon = () => (
    <svg className={styles.backspace_icon} viewBox="0 0 24 24" aria-hidden="true"><path d="M20 12H5M11 5l-7 7 7 7" /></svg>
);
const EnterIcon = () => (
    <svg className={styles.enter_icon} viewBox="0 0 24 24" aria-hidden="true"><path d="M19 4v8a3 3 0 0 1-3 3H5M10 10l-5 5 5 5" /></svg>
);

// ↵ で送る先の印: VRCT で送る = チャットボックスの吹き出し、VRChat に貼る = クリップボード
const SendToIcon = ({ to }) => (
    <svg className={styles.stroke_icon} viewBox="0 0 24 24" aria-hidden="true">
        {to === "paste"
            ? <path d="M9 4h6v3H9zM8 5.5H6v15h12v-15h-2M9.5 12h5M9.5 16h5" />
            : <path d="M4 5h16v11h-9l-5 4v-4H4zM8 9.5h8M8 12.5h5" />}
    </svg>
);

// Shift の印 (字の ⇧ ⇪ はフォントによって色付きの絵文字になり、左右で色が揃わないので線で描く)。ロック中は塗って下に線
const ShiftIcon = ({ locked }) => (
    <svg className={clsx(styles.shift_icon, { [styles.is_locked]: locked })} viewBox="0 0 24 24" aria-hidden="true">
        <path d="M12 3.5 20 12h-4.5v5.5h-7V12H4z" />{locked && <path d="M8.5 21h7" />}
    </svg>
);

// label: 大きい字、corner: 左上の小さい字 (Shift の字)
const Key = ({ press, label, corner, lang, w = widthOf(1), kind = "char", extra, sound = "key", aria, onPress, onLeave, disabled = false }) => (
    <button type="button" className={clsx(styles.key, styles[kind], extra)} style={{ width: w }} aria-label={aria ?? label} lang={lang}
        disabled={disabled} onMouseDown={press(onPress, sound, label)} onMouseLeave={onLeave}>
        {corner && <span className={styles.key_corner} aria-hidden="true">{corner}</span>}
        {label}
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

// 右端: 残りが少ないときだけ文字数、何か入っていれば × (1回目で注意の色、続けてもう1回で全部消す)、
// 一番右に ↵ で送る先の印 (いつも同じ場所)。文を押すと、その位置にカーソルを置く (変換中は置かない)
const Composition = ({ state, language, clear_armed, onClear, send_to_button, onCursor }) => {
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
    const preedit = c ? [...c.preedit] : [];
    const [start, end] = c ? c.selection : [0, 0];
    // カーソルまで・変換中の語・カーソルの後 (カーソルは変換中の語のすぐ後ろ)
    const pieces = [
        { text: state.text },
        ...(c ? [
            { text: preedit.slice(0, start).join(""), className: styles.preedit },
            { text: preedit.slice(start, end).join(""), className: styles.selection },
            { text: preedit.slice(end).join(""), className: styles.preedit },
        ] : []),
        ...(state.syllable ? [{ text: state.syllable.text, className: styles.selection }] : []),
        { text: state.after ?? "" },
    ];
    const after_key = String(pieces.length - 1);
    const all = splitAtLimit(pieces);
    const parts = all.filter(p => p.key.split("-")[0] !== after_key);
    const after_parts = all.filter(p => p.key.split("-")[0] === after_key);
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

// 変換の候補 (押して選ぶ)。英語・韓国語は候補がないので何も出さない
const Candidates = ({ state, language, press, sendKey }) => {
    const { t } = useI18n();
    const { asyncStdoutToPython } = useStdoutToPython();
    if (language === "en" || language === "ko") return <div className={styles.candidates} />;
    return <div className={styles.candidates} lang={language}>
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
const Preparing = ({ state, press }) => {
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
const SentFeedback = ({ result }) => {
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
