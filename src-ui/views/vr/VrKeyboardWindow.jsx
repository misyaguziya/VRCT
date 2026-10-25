import { useEffect, useLayoutEffect, useRef, useState } from "react";
import clsx from "clsx";
import { useI18n } from "@useI18n";
import { useStdoutToPython } from "@useStdoutToPython";
import { useKeyboard } from "@logics_common";
import { useVr } from "@logics_configs";
import KeyboardSvg from "@images/mui_keyboard_alt.svg?react";
import MicSvg from "@images/mic.svg?react";
import { VrWindow } from "./VrWindow";
import { GAP, charsOf, layoutOf, legendOf, widthOf } from "./keyboard_layout";
import { loadKeySounds, playKeySound } from "./keyboard_sounds";
import styles from "./VrKeyboardWindow.module.scss";

// VRキーボード。変換はバックエンド (vrct-ime: 日本語・中国語は RIME、韓国語は字母の組み立て) が行い、
// ここはキーを送って、返ってきた表示 (KeyboardState) を描くだけ。
// キーは押した瞬間 (mousedown) に送る (離すまで待つと、指すのがずれて別のキーになる)。
// 変換していないときの ↵ は、選んでいる送る先 (KeyboardSendTo) へ送る (バックエンドが決める)
// 言語の一覧 (中国語の拼音は簡体字・繁体字を別の項目にして、その後ろに並べる。注音・倉頡・速成は繁体字で、その後ろ)
const LANGUAGES = [["ja", "日本語"], ["en", "English"], ["ko", "한국어"]];
const TRADITIONAL_METHODS = [["zhuyin", "注音"], ["cangjie", "倉頡"], ["quick", "速成"]];
// 言語キーの字 (中国語の拼音は簡・繁)
// Ctrl と一緒に押すキーと、その働き (バックエンドのキーの名前)。Ctrl の間はこのキーだけを出し、ほかは薄くする
const CTRL_ACTIONS = { c: "Copy", v: "Paste", a: "SelectAll", z: "Undo", y: "Redo", x: "Cut" };
const LANGUAGE_MARK = { ja: "あ", ko: "한", en: "A", zhuyin: "注", cangjie: "倉", quick: "速" };
const CHAT_MAX = 144; // VRChat のチャットボックスの文字数
// 文字数はこれを超えたときだけ出す (残りが少ないときだけ気にすればよい)
const COUNTER_FROM = 120;
const SENT_FEEDBACK_MS = 2500;
// Shift をこの間に2回押すとロック
const SHIFT_LOCK_MS = 400;
// 全消去は続けてもう1回押したときだけ (1回目から この間に)
const CLEAR_CONFIRM_MS = 2000;
// 不透明度の切り替え (ログの窓と同じ段階)
const OPACITY_STEPS = [1.0, 0.8, 0.6, 0.4];
// 言語を変えたとき、言語キーから一番遠いキー (キー約16個分) の字が変わり始めるまで
const LANGUAGE_WAVE_MS = 100;
const LANGUAGE_WAVE_KEYS = 16;

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

// Shift: 1回押すと次の1文字だけ ("once")、素早く2回でロック ("lock")。ロック中・次の1文字を待っている間に
// もう1回で解除。左右は同じ状態
const useShift = () => {
    const [shift, setShift] = useState("off");
    const pressed_at = useRef(0);
    const press = () => {
        const now = Date.now();
        const quick = now - pressed_at.current < SHIFT_LOCK_MS;
        pressed_at.current = now;
        setShift(s => (s === "off" ? "once" : s === "once" && quick ? "lock" : "off"));
    };
    // 1文字打った: 1回押しの Shift はそこで外れる
    const used = () => {
        if (shift === "once") setShift("off");
    };
    return { shift, is_shift: shift !== "off", press, used };
};

// 2回押しで実行するもの (全消去): 1回目で構え (armed)、within_ms の間にもう1回で実行。間があけば戻る
// (VR で間違えて押しても消えない)
const useConfirm = (action, within_ms) => {
    const [armed, setArmed] = useState(false);
    useEffect(() => {
        if (!armed) return undefined;
        const timer = setTimeout(() => setArmed(false), within_ms);
        return () => clearTimeout(timer);
    }, [armed, within_ms]);
    const press = () => {
        if (!armed) return setArmed(true);
        setArmed(false);
        action();
    };
    return { armed, press };
};

// 印字が変わるときの動き: Shift のオン・オフ ("shift_on" / "shift_off")、言語の切り替え ("language")。
// 動くのは字が変わったキーだけ (変わった字は作り直され、その時の動きで現れる: Legend)。
// 入力は押した瞬間に変わっていて、見た目だけが追いつく
const useLegendMotion = (is_shift, language) => {
    const motion = useRef({ is_shift, language, kind: null });
    if (motion.current.language !== language) motion.current = { is_shift, language, kind: "language" };
    else if (motion.current.is_shift !== is_shift) motion.current = { is_shift, language, kind: is_shift ? "shift_on" : "shift_off" };
    return motion.current.kind;
};

// 言語キー (左端) から、ある段のキーの中心 (左端からキー何個分) までの距離で、字が変わり始めるまで
const waveDelay = (x, rows_apart) => `${Math.round(Math.hypot(x, rows_apart) / LANGUAGE_WAVE_KEYS * LANGUAGE_WAVE_MS)}ms`;

export const VrKeyboardWindow = ({ onClose }) => {
    const { t } = useI18n();
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentKeyboardState, currentKeyboardLanguage, setKeyboardLanguage, currentKeyboardSendTo, setKeyboardSendTo,
        currentIsEnabledKeyboardKeySound, currentIsEnabledKeyboardChineseSimplified, toggleIsEnabledKeyboardChineseSimplified,
        currentIsEnabledKeyboardDictation, toggleIsEnabledKeyboardDictation, currentKeyboardOpacity, setKeyboardOpacity, currentKeyboardLocked,
        toggleKeyboardLocked } = useVr();
    const { currentKeyboardSendResult } = useKeyboard();
    const repeat = useRepeat();
    const { shift, is_shift, press: pressShift, used: shiftUsed } = useShift();
    // Ctrl も Shift と同じ (1回押すと次の1キーだけ、素早く2回でロック)
    const { shift: ctrl, is_shift: is_ctrl, press: pressCtrl, used: ctrlUsed } = useShift();
    const clear = useConfirm(() => asyncStdoutToPython("/run/keyboard_clear"), CLEAR_CONFIRM_MS);
    const state = currentKeyboardState.data;
    const language = currentKeyboardLanguage.data;
    const send_to = currentKeyboardSendTo.data;
    const motion = useLegendMotion(is_shift, language);
    // 言語キーの段 (言語を変えたときの字の動きはそこから広がる)
    const language_row = layoutOf(language).findIndex(row => row.some(item => item.special === "language"));
    // 開いている一覧: "language" (言語キー) / "settings" (タイトルバーの不透明度の印) / null
    const [menu, setMenu] = useState(null);

    // 英語・韓国語のほかは RIME の辞書で打つ
    const needs_dictionary = language !== "en" && language !== "ko";
    // 字の言語 (lang 属性: 漢字の字形が言語で変わる)。注音・倉頡・速成は繁体字
    const text_lang = TRADITIONAL_METHODS.some(([code]) => code === language) ? "zh-Hant" : language;
    const is_ready = !needs_dictionary || state.status === "ready";
    const composing = state.composition !== null;
    const sound_on = currentIsEnabledKeyboardKeySound.data === true;
    const dictating = currentIsEnabledKeyboardDictation.data === true;
    const simplified_on = currentIsEnabledKeyboardChineseSimplified.data === true;
    const opacity = Number(currentKeyboardOpacity.data);

    useEffect(() => {
        if (sound_on) loadKeySounds();
    }, [sound_on]);

    // sound: 音の種類、id: どのキーか (同じキーを続けて押した時は同じ音にする)
    const press = (handler, sound = "key", id = undefined) => (event) => {
        if (event.button !== 0) return;
        event.preventDefault();
        if (sound_on) playKeySound(sound, id);
        handler();
    };
    const sendKey = (key) => asyncStdoutToPython("/run/keyboard_key", key);
    // 入力欄の文を押した位置へカーソルを置く
    const placeCursorAt = (index) => {
        if (sound_on) playKeySound("soft", "cursor");
        asyncStdoutToPython("/run/keyboard_cursor", index);
    };
    // 長押しでくり返すキー (← ◀ ▶): くり返すたびに音も鳴らす (最初の1回の音は press が鳴らす)。
    // id: 押したキーと同じ (同じキーの音のまま)
    const repeatKey = (key, sound, id) => {
        let first = true;
        repeat.start(() => {
            if (!first && sound_on) playKeySound(sound, id);
            first = false;
            sendKey(key);
        });
    };
    const typeChar = (spec) => {
        const [normal, shifted] = charsOf(spec);
        sendKey(is_shift ? shifted : normal);
        shiftUsed();
    };
    // ◀ ▶: Ctrl で単語ごと、Shift で選びながら (Windows と同じ)
    const arrowKey = (arrow) => {
        const name = [is_ctrl && "Ctrl", is_shift && "Shift", arrow].filter(Boolean).join("+");
        repeatKey(name, "soft", arrow);
        shiftUsed();
        ctrlUsed();
    };
    // ↵: Shift を1回押した後なら改行 (送らない)。ロック中・変換中はいつもの ↵ (送る・確定)
    const is_newline = shift === "once" && !composing;
    const pressEnter = () => {
        if (!is_newline) return sendKey("Enter");
        sendKey("\n");
        shiftUsed();
    };
    // 言語キーの字 (中国語は簡体字・繁体字のどちらか。日本語の半角入力中は A)
    const language_mark = language === "zh" ? (simplified_on ? "简" : "繁") : state.half_width ? "A" : LANGUAGE_MARK[language];
    const changeLanguage = (code) => {
        if (code !== language) setKeyboardLanguage(code);
    };

    // Space と ↵ は何も添えない (読み上げ用の名前だけ。↵ の送る先は入力欄の右端の印)
    const space_name = !composing ? t("vr_panel.keyboard.space")
        : language === "ja" ? t("vr_panel.keyboard.convert") : t("vr_panel.keyboard.select_first");
    const enter_name = composing ? t("vr_panel.keyboard.commit") : is_newline ? t("vr_panel.keyboard.newline") : t("vr_panel.keyboard.send_to");
    // 1つのキー (文字・空き・文字以外)。delay: 言語を変えたとき、そのキーの字が変わり始めるまで
    const keyOf = (item, index, delay) => {
        if (typeof item === "string") {
            // Ctrl の間: 働きのあるキー (C・V・A・Z・Y・X) だけが押せる。印字はショートカットの書き方どおり大文字
            if (is_ctrl) {
                const action = item.length === 1 ? CTRL_ACTIONS[item] : undefined;
                return <Key press={press} key={item} id={item} label={action ? item.toUpperCase() : legendOf(item, language, false).main} lang={text_lang}
                    extra={!action && styles.ctrl_off} onPress={() => { sendKey(action); ctrlUsed(); }} disabled={!action || !is_ready} />;
            }
            const { main, sub } = legendOf(item, language, is_shift);
            return <Key press={press} key={item} id={item} label={main} corner={sub} lang={text_lang} aria={main} motion={motion} delay={delay}
                onPress={() => typeChar(item)} disabled={!is_ready} />;
        }
        if (item.gap) return <span key={`gap-${index}`} className={styles.gap} style={{ width: widthOf(item.gap) }} aria-hidden="true" />;
        const w = widthOf(item.w);
        switch (item.special) {
            case "backspace":
                return <Key press={press} key="backspace" sound="backspace" label={<BackspaceIcon />} w={w} kind="mod" aria={t("vr_panel.keyboard.delete")} disabled={!is_ready}
                    onPress={() => repeatKey("Backspace", "backspace", "backspace")} onLeave={repeat.stop} />;
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
            // 言語: 今の言語の字だけを出し、押すと一覧 (準備中でも押せる: 英字に切り替えれば、その間も打てる)
            case "language":
                return <Key press={press} key="language" sound="toggle" label={language_mark} w={w} kind="mod" extra={styles.mark} lang={text_lang} motion={motion}
                    aria={t("vr_panel.keyboard.language")} onPress={() => setMenu(m => (m === "language" ? null : "language"))} />;
            case "ctrl":
                return <button key="ctrl" type="button" className={clsx(styles.key, styles.mod, styles.ctrl, { [styles.is_locked]: ctrl === "lock" })}
                    style={{ width: w }} aria-label={t("vr_panel.keyboard.ctrl")} aria-pressed={is_ctrl}
                    disabled={!is_ready} onMouseDown={press(pressCtrl, "shift", "ctrl")}>Ctrl</button>;
            // JIS の左上 (半角/全角): 日本語のまま、JIS の並びで打った字をそのまま入れる / かなに戻す
            case "toggle":
                return <Key press={press} key="toggle" sound="toggle" label="半/全" w={w} kind="mod" aria={t("vr_panel.keyboard.switch_half_width")} onPress={() => sendKey("HalfWidth")}
                    motion={motion} delay={delay} />;
            default:
                return null;
        }
    };

    // 一覧 (言語・不透明度) の1つの項目。選んでいるものはアクセントの字 (枠は描かない)。選ぶと閉じる
    const option = (key, label, selected, onPick, extra = {}) => (
        <button key={key} type="button" className={styles.option} aria-pressed={selected} {...extra}
            onMouseDown={press(() => { setMenu(null); onPick(); }, "soft", key)}>{label}</button>
    );
    // 言語の一覧 (言語キーから)。中国語の拼音は簡体字・繁体字を別の項目に。注音・倉頡・速成は繁体字にする
    const pickChinese = (code, simplified) => {
        changeLanguage(code);
        if (simplified !== simplified_on) toggleIsEnabledKeyboardChineseSimplified();
    };
    const language_menu = <div className={clsx(styles.menu, styles.language_menu)} role="menu" aria-label={t("vr_panel.keyboard.language")}>
        {LANGUAGES.map(([code, name]) => option(`language:${code}`, name, code === language, () => changeLanguage(code), { lang: code }))}
        {option("language:zh-hans", "简体中文", language === "zh" && simplified_on, () => pickChinese("zh", true), { lang: "zh-Hans" })}
        {option("language:zh-hant", "繁體中文", language === "zh" && !simplified_on, () => pickChinese("zh", false), { lang: "zh-Hant" })}
        {TRADITIONAL_METHODS.map(([code, name]) => option(`language:${code}`, name, code === language, () => pickChinese(code, false), { lang: "zh-Hant" }))}
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
    // ピン: 留めている間はキーボードを掴んでも動かない (外れている間は傾けて薄く)
    const pinned = currentKeyboardLocked.data === true;
    const pin_button = <button type="button" className={styles.menu_button} aria-label={t("vr_panel.keyboard.pin")} aria-pressed={pinned}
        onMouseDown={press(toggleKeyboardLocked, "soft", "pin")}>
        <svg className={clsx(styles.stroke_icon, styles.pin_icon)} viewBox="0 0 24 24" aria-hidden="true">
            <path className={clsx({ [styles.filled]: pinned })} d="M9 3.5h6l-1 6 3.5 3.5v1.5h-11V13L10 9.5z" /><path d="M12 14.5v6" />
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
            onPress={() => arrowKey("Left")} onLeave={repeat.stop} />
        <div className={styles.updown} style={{ width: widthOf(1) }}>
            <Key press={press} sound="soft" label="▲" kind="mod" extra={styles.half} aria={t("vr_panel.keyboard.history_older")} onPress={() => sendKey("Up")} />
            <Key press={press} sound="soft" label="▼" kind="mod" extra={styles.half} aria={t("vr_panel.keyboard.history_newer")} onPress={() => sendKey("Down")} />
        </div>
        <Key press={press} sound="soft" label="▶" kind="mod" aria={t("vr_panel.keyboard.right")}
            onPress={() => arrowKey("Right")} onLeave={repeat.stop} />
    </>;

    return (
        <VrWindow Icon={KeyboardSvg} title="" title_extra={<>{pin_button}{menu_button}</>} onClose={onClose}>
            <div className={styles.keyboard}>
                {/* 一覧を開いている間は、外を押すと閉じる (その押下はキーに届かない) */}
                {menu && <div className={styles.backdrop} onMouseDown={(e) => { e.preventDefault(); setMenu(null); }} aria-hidden="true" />}
                {menu === "settings" && settings_menu}
                {menu === "language" && language_menu}
                <div className={styles.top}>
                    <Composition state={state} language={text_lang} clear_armed={clear.armed} onClear={press(clear.press, "soft", "clear")}
                        send_to_button={send_to_button} onCursor={placeCursorAt} />
                </div>
                <div className={styles.middle}>
                    {!is_ready ? <Preparing state={state} press={press} />
                        : <Candidates state={state} language={language} lang={text_lang} press={press} sendKey={sendKey} />}
                    <SentFeedback result={currentKeyboardSendResult.data} />
                </div>
                <div className={clsx(styles.keys, { [styles.is_waiting]: !is_ready })} style={{ "--key_gap": `${GAP}px` }}>
                    {layoutOf(language).map((row, r) => {
                        let x = 0;
                        return <div key={r} className={styles.row}>{row.map((item, i) => {
                            const w = item.w ?? item.gap ?? 1;
                            x += w;
                            return keyOf(item, i, waveDelay(x - w / 2, Math.abs(r - language_row)));
                        })}</div>;
                    })}
                    <div className={styles.row}>
                        {/* Ctrl: 実際のキーボードと同じ左下 */}
                        {keyOf({ special: "ctrl", w: 1.75 })}
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

// label: 大きい字、corner: 左上の小さい字 (Shift の字)。字は変わるたびに作り直す (変わった字だけが動く)。
// id: 音の上でどのキーか (既定は印字。文字のキーは Shift で印字が変わるのでキーの並びの名前を渡す)
const Key = ({ press, id, label, corner, lang, w = widthOf(1), kind = "char", extra, sound = "key", aria, onPress, onLeave, disabled = false, motion, delay }) => (
    <button type="button" className={clsx(styles.key, styles[kind], extra)} style={{ width: w, "--delay": delay }} aria-label={aria ?? label} lang={lang}
        disabled={disabled} onMouseDown={press(onPress, sound, id ?? label)} onMouseLeave={onLeave}>
        {/* (key は大きい字と左上で別の名前: Shift で字が入れ替わるとき、同じ字として使い回されないように) */}
        {corner && <Legend key={`corner:${corner}`} text={corner} className={styles.key_corner} motion={motion} aria-hidden="true" />}
        {typeof label === "string" && label ? <Legend key={`label:${label}`} text={label} motion={motion} /> : label}
    </button>
);

// 字1つ。作られたときの動き (motion) で現れ、その後は変えない (変えると、変わっていない字まで動き直す)
const Legend = ({ text, className, motion, ...rest }) => {
    const [appear] = useState(motion);
    return <span className={clsx(className, appear && styles[`appear_${appear}`])} {...rest}>{text}</span>;
};

// 打った文字と、変換中の語 (文節を選んでいるところを強調)。長くなったら終わりの方を見せる
// 長くなると折り返し (最大4行)、入りきらなければ字を小さくする: 144文字まで全部見える
const LINE_FONT_SIZES = [28, 24, 20, 17];

// 字の並び (表示の部品ごと) を、144文字目までとそれより後に分ける (後ろは VRChat で切れる)
const splitAtLimit = (parts) => {
    let count = 0;
    return parts.flatMap(({ text, className, after }, i) => {
        const chars = [...text];
        const keep = Math.max(0, Math.min(chars.length, CHAT_MAX - count));
        count += chars.length;
        return [
            { key: `${i}`, text: chars.slice(0, keep).join(""), className, after },
            { key: `${i}-over`, text: chars.slice(keep).join(""), className: clsx(className, styles.over), after },
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
    // カーソルまで (選んだ所はその終わり)・変換中の語・カーソルの後 (選んだ所はその始め)。
    // カーソルは変換中の語のすぐ後ろ
    const text = [...state.text];
    const after = [...(state.after ?? "")];
    const [selected_before, selected_after] = state.selected ?? [0, 0];
    const pieces = [
        { text: text.slice(0, text.length - selected_before).join("") },
        { text: text.slice(text.length - selected_before).join(""), className: styles.selected },
        ...(c ? [
            { text: preedit.slice(0, start).join(""), className: styles.preedit },
            { text: preedit.slice(start, end).join(""), className: styles.selection },
            { text: preedit.slice(end).join(""), className: styles.preedit },
        ] : []),
        ...(state.syllable ? [{ text: state.syllable, className: styles.selection }] : []),
        { text: after.slice(0, selected_after).join(""), className: styles.selected, after: true },
        { text: after.slice(selected_after).join(""), after: true },
    ];
    const all = splitAtLimit(pieces);
    const parts = all.filter(p => !p.after);
    const after_parts = all.filter(p => p.after);
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
const Candidates = ({ state, language, lang, press, sendKey }) => {
    const { t } = useI18n();
    const { asyncStdoutToPython } = useStdoutToPython();
    if (language === "en" || language === "ko") return <div className={styles.candidates} />;
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
