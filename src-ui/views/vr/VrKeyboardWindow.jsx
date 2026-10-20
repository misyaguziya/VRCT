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
// 英字との切り替えキーの表示 (その言語の字 → A)
const MODE_MARK = { ja: "あ", ko: "한", zh: "中", en: "A" };
const CHAT_MAX = 144; // VRChat のチャットボックスの文字数
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
// その分は空ける (文字のキーの位置は実際のキーボードと同じ)。1段は 15 キー分で左に寄せ、
// 右に離して別の区画 (言語・送る先と、矢印キーの逆 T 字) を置く (SIDE)
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
// 右の区画: 3 キー分の幅。本体との間は1キー分あける (↵ や ← を狙って、言語・送る先を押さないように)
const SIDE_UNITS = 3;
const SIDE_GAP_UNITS = 1;
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
// キー1つ分の間隔 (px): キー 55px + すき間 6px。本体 15 + 間 1 + 右の区画 3 = 19 キー分で 1153px (窓の中は 1168px)
const PITCH = 61;
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
    // ↵: Shift と一緒なら改行 (送らない)
    const pressEnter = () => {
        if (!is_shift) return sendKey("Enter");
        sendKey("\n");
        if (shift === "once") setShift("off");
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
    const nextOpacity = () => OPACITY_STEPS.find(step => step < opacity - 0.01) ?? OPACITY_STEPS[0];
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
    // Space は何も印字しない (読み上げ用の名前だけ)。↵ は送るときだけ送る先を添える (変換中の確定・Shift との改行は印字しない)
    const space_name = !composing ? t("vr_panel.keyboard.space")
        : language === "ja" ? t("vr_panel.keyboard.convert") : t("vr_panel.keyboard.select_first");
    const enter_name = composing ? t("vr_panel.keyboard.commit") : is_shift ? t("vr_panel.keyboard.newline") : t("vr_panel.keyboard.send_to");
    const enter_label = composing || is_shift ? null : send_to === "paste" ? "→ VRChat" : "→ VRCT";
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
                return <Key press={press} key="backspace" sound="backspace" label="←" w={w} kind="mod" aria={t("vr_panel.keyboard.delete")} disabled={!is_ready}
                    onPress={() => repeat.start(() => sendKey("Backspace"))} onLeave={repeat.stop} />;
            case "enter":
                return <Key press={press} key="enter" sound="enter" label="↵" sub={enter_label} w={w} kind="act" aria={enter_name}
                    onPress={pressEnter} disabled={!is_ready} />;
            // JIS の L 字の Enter: どちらの部分を押しても Enter (印字は上の部分)
            case "enter_top":
                return <Key press={press} key="enter_top" sound="enter" label="↵" sub={enter_label} w={w} kind="act" extra={clsx(styles.enter_part, styles.enter_top)}
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

    // 右の区画のボタン (言語・送る先): キーと同じ高さ、選んでいるものは枠と字の色 (塗りは ON になっている機能だけに使う)
    const choice = (key, label, onPress, extra) => (
        <button key={key} type="button" className={clsx(styles.key, styles.mod, styles.choice)} style={{ width: widthOf(SIDE_UNITS / 2) }}
            {...extra} onMouseDown={press(onPress, "soft", key)}>{label}</button>
    );
    // 右の区画: 上の3段は言語 (2段) と ↵ で送る先、下の2段は矢印キーの逆 T 字
    const side = <div className={styles.side} style={{ marginLeft: SIDE_GAP_UNITS * PITCH }}>
        {[LANGUAGES.slice(0, 2), LANGUAGES.slice(2)].map((pair, r) => (
            <div key={`languages-${r}`} className={styles.row} role="group" aria-label={t("vr_panel.keyboard.language")}>
                {pair.map(([code, name]) => choice(`language:${code}`, name, () => changeLanguage(code),
                    { lang: code, "aria-pressed": code === language }))}
            </div>
        ))}
        <div className={styles.row} role="radiogroup" aria-label={t("vr_panel.keyboard.send_to")}>
            {/* ↵ で送る先 (短く ↵ VRCT / ↵ VRChat。読み上げは長い名前) */}
            {[["vrct", "send_vrct", "VRCT"], ["paste", "send_paste", "VRChat"]].map(([to, title, short]) => choice(`send_to:${to}`, `↵ ${short}`,
                () => { if (send_to !== to) setKeyboardSendTo(to); },
                { role: "radio", "aria-checked": send_to === to, "aria-label": t(`vr_panel.keyboard.${title}`) }))}
        </div>
        <div className={styles.row}>
            <span className={styles.gap} style={{ width: widthOf(1) }} aria-hidden="true" />
            {/* ▲ ▼ は送った文の呼び出し、◀ ▶ は文節・文字 */}
            <Key press={press} sound="soft" label="▲" kind="mod" aria={t("vr_panel.keyboard.history_older")} onPress={() => sendKey("Up")} />
        </div>
        <div className={styles.row}>
            <Key press={press} sound="soft" label="◀" kind="mod" aria={t("vr_panel.keyboard.left")} disabled={!is_ready}
                onPress={() => repeat.start(() => sendKey("Left"))} onLeave={repeat.stop} />
            <Key press={press} sound="soft" label="▼" kind="mod" aria={t("vr_panel.keyboard.history_newer")} onPress={() => sendKey("Down")} />
            <Key press={press} sound="soft" label="▶" kind="mod" aria={t("vr_panel.keyboard.right")} disabled={!is_ready}
                onPress={() => repeat.start(() => sendKey("Right"))} onLeave={repeat.stop} />
        </div>
    </div>;
    // 中国語の簡体字・繁体字 (中国語のときだけ、タイトルバーに)
    const simplified = language === "zh" && <div className={styles.tabs}>
        <button type="button" className={styles.tab} lang="zh" aria-pressed={currentIsEnabledKeyboardChineseSimplified.data === true}
            aria-label={t("vr_panel.keyboard.simplified")} onMouseDown={press(toggleIsEnabledKeyboardChineseSimplified, "soft", "simplified")}>
            {currentIsEnabledKeyboardChineseSimplified.data === true ? "简" : "繁"}
        </button>
    </div>;

    // 不透明度 (押すたびに 100 → 80 → 60 → 40 → 100%)
    const opacity_button = <div className={styles.tabs}>
        <button type="button" className={clsx(styles.tab, styles.opacity)} aria-label={`${t("vr_panel.keyboard.opacity")}: ${Math.round(opacity * 100)}%`}
            onMouseDown={press(() => setKeyboardOpacity(nextOpacity()), "soft", "opacity")}>
            {/* ログの窓のツールバーと同じ印 */}
            <svg className={styles.opacity_icon} viewBox="0 0 24 24" aria-hidden="true"><path d="M4 4h16v16H4zM4 12h16M12 4v16" /></svg>
            {Math.round(opacity * 100)}%
        </button>
    </div>;

    return (
        <VrWindow Icon={KeyboardSvg} title={t("vr_panel.keyboard.title")} title_extra={<>{simplified}{opacity_button}</>} onClose={onClose}>
            <div className={styles.keyboard}>
                <div className={styles.top}>
                    <Composition state={state} language={language} />
                </div>
                <div className={styles.middle}>
                    {!is_ready ? <Preparing state={state} press={press} />
                        : <Candidates state={state} language={language} press={press} sendKey={sendKey} />}
                    <SentFeedback result={currentKeyboardSendResult.data} />
                </div>
                <div className={clsx(styles.keys_area, { [styles.is_waiting]: !is_ready })} style={{ "--key_gap": `${GAP}px` }}>
                    <div className={styles.keys}>
                        {layoutOf(language).map((row, r) => <div key={r} className={styles.row}>{row.map(keyOf)}</div>)}
                        <div className={styles.row}>
                            {/* 英字との切り替え (準備中でも押せる: 英字に切り替えれば、その間も打てる)。
                                JIS は左上の 半/全 で切り替えるので置かず、全消去を左端に。Space は実際のキーボードと同じ辺り */}
                            {language !== "ja" && <Key press={press} sound="toggle" label={mode_label} w={widthOf(1.75)} kind="mod"
                                aria={t("vr_panel.keyboard.switch_english")} onPress={toggleEnglish} />}
                            <Key press={press} sound="soft" label={t(clear_armed ? "vr_panel.keyboard.clear_confirm" : "vr_panel.keyboard.clear")}
                                w={widthOf(1.75)} kind="mod" extra={clsx(styles.clear, { [styles.is_armed]: clear_armed })}
                                disabled={state.length === 0} onPress={pressClear} />
                            <span className={styles.gap} style={{ width: widthOf(language === "ja" ? 2 : 0.25) }} aria-hidden="true" />
                            <Key press={press} sound="space" label="" w={widthOf(7)} kind="act" aria={space_name}
                                onPress={() => sendKey("Space")} disabled={!is_ready} />
                            {/* マイク: 聞き取った文を入力欄に入れる (送らない。直して ↵ で送る) */}
                            <button type="button" className={clsx(styles.key, styles.mod, { [styles.is_locked]: dictating })}
                                style={{ width: widthOf(1.25) }} aria-label={t("vr_panel.keyboard.dictation")} aria-pressed={dictating}
                                onMouseDown={press(toggleIsEnabledKeyboardDictation, "soft", "dictation")}>
                                <MicSvg className={styles.mic_icon} aria-hidden="true" />
                            </button>
                        </div>
                    </div>
                    {side}
                </div>
            </div>
        </VrWindow>
    );
};

// Shift の印 (字の ⇧ ⇪ はフォントによって色付きの絵文字になり、左右で色が揃わないので線で描く)。ロック中は塗って下に線
const ShiftIcon = ({ locked }) => (
    <svg className={clsx(styles.shift_icon, { [styles.is_locked]: locked })} viewBox="0 0 24 24" aria-hidden="true">
        <path d="M12 3.5 20 12h-4.5v5.5h-7V12H4z" />{locked && <path d="M8.5 21h7" />}
    </svg>
);

// label: 大きい字、corner: 左上の小さい字 (Shift の字)、sub: 下の小さい字 (↵ の送る先)
const Key = ({ press, label, corner, sub, lang, w = widthOf(1), kind = "char", extra, sound = "key", aria, onPress, onLeave, disabled = false }) => (
    <button type="button" className={clsx(styles.key, styles[kind], extra)} style={{ width: w }} aria-label={aria ?? label} lang={lang}
        disabled={disabled} onMouseDown={press(onPress, sound, label)} onMouseLeave={onLeave}>
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

// 日本語・中国語の辞書の準備 (初回は取得してから組み立てる)
const Preparing = ({ state, press }) => {
    const { t } = useI18n();
    const { asyncStdoutToPython } = useStdoutToPython();
    if (state.status === "failed") {
        return <div className={styles.preparing}><span className={styles.preparing_title}>{t("vr_panel.keyboard.failed")}</span>
            <button type="button" className={styles.retry} onMouseDown={press(() => asyncStdoutToPython("/run/keyboard_retry"), "key", "retry")}>
                {t("vr_panel.keyboard.retry")}
            </button>
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
