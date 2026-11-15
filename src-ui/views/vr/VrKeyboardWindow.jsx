import { useEffect, useState } from "react";
import clsx from "clsx";
import { useI18n } from "@useI18n";
import { useStdoutToPython } from "@useStdoutToPython";
import { useKeyboard } from "@logics_common";
import { useVr } from "@logics_configs";
import KeyboardSvg from "@images/mui_keyboard_alt.svg?react";
import MicSvg from "@images/mic.svg?react";
import ConfigurationSvg from "@images/configuration.svg?react";
import { VrWindow } from "./VrWindow";
import { GAP, charsOf, layoutOf, legendOf, widthOf } from "./keyboard_layout";
import { loadKeySounds, playKeySound } from "./keyboard_sounds";
import { useConfirm, useLegendMotion, useRepeat, useShift } from "./keyboard_hooks";
import { BackspaceIcon, EnterIcon, EnterShape, Key, SendToIcon, ShiftIcon } from "./KeyboardKeys";
import { Composition } from "./Composition";
import { Candidates, Preparing, SentFeedback } from "./MiddleRow";
import { LanguageMenu, TRADITIONAL_METHODS } from "./LanguageMenu";
import { KeyboardSettings } from "./KeyboardSettings";
import styles from "./VrKeyboardWindow.module.scss";

// 言語キーの印 (地球儀)。他のキーと同じ色 (currentColor)
const GlobeIcon = () => (
    <svg className={styles.stroke_icon} viewBox="0 0 24 24" aria-hidden="true">
        <circle cx="12" cy="12" r="9" /><ellipse cx="12" cy="12" rx="4" ry="9" /><path d="M3 12h18" />
    </svg>
);

// VRキーボード。変換はバックエンド (vrct-ime: 日本語・中国語は RIME、韓国語は字母の組み立て) が行い、
// ここはキーを送って、返ってきた表示 (KeyboardState) を描くだけ。
// キーは押した瞬間 (mousedown) に送る (離すまで待つと、指すのがずれて別のキーになる)。
// 変換していないときの ↵ は、選んでいる送る先 (KeyboardSendTo) へ送る (バックエンドが決める)
// Ctrl と一緒に押すキーと、その働き (バックエンドのキーの名前)。Ctrl の間はこのキーだけを出し、ほかは薄くする
const CTRL_ACTIONS = { c: "Copy", v: "Paste", a: "SelectAll", z: "Undo", y: "Redo", x: "Cut" };
// 働きの名前 (表示の言語で、字の下に添える)
const EDIT_NAMES = { SelectAll: "select_all", Copy: "copy", Cut: "cut", Paste: "paste", Undo: "undo", Redo: "redo" };
// 全消去は続けてもう1回押したときだけ (1回目から この間に)
const CLEAR_CONFIRM_MS = 2000;
// 言語を変えたとき、言語キーから一番遠いキー (キー約16個分) の字が変わり始めるまで
const LANGUAGE_WAVE_MS = 100;
const LANGUAGE_WAVE_KEYS = 16;

// 言語キー (左下) から、ある段のキーの中心 (左端からキー何個分) までの距離で、字が変わり始めるまで
const waveDelay = (x, rows_apart) => `${Math.round(Math.hypot(x, rows_apart) / LANGUAGE_WAVE_KEYS * LANGUAGE_WAVE_MS)}ms`;

// マイク: 聞き取った文を入力欄に入れる (VRCT の文字起こし。送らない)。↵ で送る先は入力欄の右端の印で、押すたびに入れ替わる。
// タイトルバーの歯車でキーボードの設定、ピンで掴んでも動かなくする
export const VrKeyboardWindow = ({ onClose }) => {
    const { t } = useI18n();
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentKeyboardState, currentKeyboardLanguage, setKeyboardLanguage, currentKeyboardSendTo, setKeyboardSendTo,
        currentIsEnabledKeyboardKeySound, currentIsEnabledKeyboardChineseSimplified, toggleIsEnabledKeyboardChineseSimplified,
        currentIsEnabledKeyboardDictation, toggleIsEnabledKeyboardDictation, currentKeyboardLocked, toggleKeyboardLocked,
        currentKeyboardKeySoundVolume } = useVr();
    const { currentKeyboardSendResult } = useKeyboard();
    const repeat = useRepeat();
    const { shift, is_shift, press: pressShift, used: shiftUsed, toggleLock: toggleCaps } = useShift();
    // Ctrl も Shift と同じ (1回押すと次の1キーだけ、素早く2回でロック)
    const { shift: ctrl, is_shift: is_ctrl, press: pressCtrl, used: ctrlUsed } = useShift();
    const clear = useConfirm(() => asyncStdoutToPython("/run/keyboard_clear"), CLEAR_CONFIRM_MS);
    const state = currentKeyboardState.data;
    const language = currentKeyboardLanguage.data;
    const send_to = currentKeyboardSendTo.data;
    const motion = useLegendMotion(is_shift, language);
    // 言語キーの段 (言語を変えたときの字の動きはそこから広がる: 一番下の段)
    const language_row = layoutOf(language).length;
    // 開いている一覧: "language" (言語キー) / "settings" (歯車) / null
    const [menu, setMenu] = useState(null);

    // 英語・韓国語のほかは RIME の辞書で打つ
    const needs_dictionary = language !== "en" && language !== "ko";
    // 字の言語 (lang 属性: 漢字の字形が言語で変わる)。注音・倉頡・速成は繁体字
    const text_lang = TRADITIONAL_METHODS.some(([code]) => code === language) ? "zh-Hant" : language;
    const is_ready = !needs_dictionary || state.status === "ready";
    const composing = state.composition !== null;
    const sound_on = currentIsEnabledKeyboardKeySound.data === true;
    const volume = Number(currentKeyboardKeySoundVolume.data) / 100;
    const dictating = currentIsEnabledKeyboardDictation.data === true;
    const simplified_on = currentIsEnabledKeyboardChineseSimplified.data === true;

    useEffect(() => {
        if (sound_on) loadKeySounds();
    }, [sound_on]);

    // sound: 音の種類、id: どのキーか (同じキーを続けて押した時は同じ音にする)
    const press = (handler, sound = "key", id = undefined) => (event) => {
        if (event.button !== 0) return;
        event.preventDefault();
        if (sound_on) playKeySound(sound, id, volume);
        handler();
    };
    const sendKey = (key) => asyncStdoutToPython("/run/keyboard_key", key);
    // 入力欄の文を押した位置へカーソルを置く
    const placeCursorAt = (index) => {
        if (sound_on) playKeySound("soft", "cursor", volume);
        asyncStdoutToPython("/run/keyboard_cursor", index);
    };
    // 長押しでくり返すキー (← ◀ ▶): くり返すたびに音も鳴らす (最初の1回の音は press が鳴らす)。
    // id: 押したキーと同じ (同じキーの音のまま)
    const repeatKey = (key, sound, id) => {
        let first = true;
        repeat.start(() => {
            if (!first && sound_on) playKeySound(sound, id, volume);
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
        repeatKey(name, "soft", arrow.toLowerCase());
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
    // 言語の一覧で選んだ: 中国語は簡体字・繁体字 (simplified) も
    const pickLanguage = (code, { simplified } = {}) => {
        if (code !== language) setKeyboardLanguage(code);
        if (simplified !== undefined && simplified !== simplified_on) toggleIsEnabledKeyboardChineseSimplified();
    };

    // Space と ↵ は何も添えない (読み上げ用の名前だけ。↵ の送る先は入力欄の右端の印)
    const space_name = !composing ? t("vr_panel.keyboard.space")
        : language === "ja" ? t("vr_panel.keyboard.convert") : t("vr_panel.keyboard.select_first");
    const enter_name = composing ? t("vr_panel.keyboard.commit") : is_newline ? t("vr_panel.keyboard.newline") : t("vr_panel.keyboard.send_to");
    // Ctrl・Shift・Caps のように押したままの状態を持つキー
    const modKey = (id, label, aria, pressed, locked, onPress, sound, w) => (
        <button key={id} type="button" className={clsx(styles.key, styles.mod, { [styles.ctrl]: id !== "shift", [styles.is_locked]: locked })}
            style={{ width: w, "--key-width": w }} aria-label={aria} aria-pressed={pressed}
            disabled={!is_ready} onMouseDown={press(onPress, sound, id)}><span className={styles.key_face}>{label}</span></button>
    );
    // 1つのキー (文字・空き・文字以外)。delay: 言語を変えたとき、そのキーの字が変わり始めるまで
    const keyOf = (item, index, delay) => {
        if (typeof item === "string") {
            // Ctrl の間: 働きのあるキー (C・V・A・Z・Y・X) だけが押せる。印字はショートカットの書き方どおり大文字で、下に働きの名前
            if (is_ctrl) {
                const action = item.length === 1 ? CTRL_ACTIONS[item] : undefined;
                if (!action) return <Key press={press} key={item} id={item} label={legendOf(item, language, false).main} lang={text_lang}
                    extra={styles.ctrl_off} disabled />;
                const name = t(`vr_panel.keyboard.${EDIT_NAMES[action]}`);
                return <Key press={press} key={item} id={item} aria={name} onPress={() => { sendKey(action); ctrlUsed(); }} disabled={!is_ready}
                    label={<><span>{item.toUpperCase()}</span><span className={styles.ctrl_name}>{name}</span></>} />;
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
            // JIS の L 字の Enter: どちらの部分を押しても Enter (印字と形は上の部分に描く)
            case "enter_top":
                return <Key press={press} key="enter_top" sound="enter" w={w} kind="act" extra={clsx(styles.enter_part, styles.enter_top)}
                    label={<><EnterShape top_w={w} bottom_w={widthOf(item.below)} /><EnterIcon /></>}
                    aria={enter_name} onPress={pressEnter} disabled={!is_ready} />;
            case "enter_bottom":
                return <Key press={press} key="enter_bottom" sound="enter" label="" w={w} kind="act" extra={clsx(styles.enter_part, styles.enter_bottom)}
                    aria={enter_name} onPress={pressEnter} disabled={!is_ready} />;
            case "shift":
                return modKey(`shift-${index}`, <ShiftIcon locked={shift === "lock"} />, t("vr_panel.keyboard.shift"), is_shift, shift === "lock", pressShift, "shift", w);
            // 言語: 🌐 の印で固定。押すと一覧 (準備中でも押せる: 英字に切り替えれば、その間も打てる)
            case "language":
                return <Key press={press} key="language" id="language" sound="toggle" label={<GlobeIcon />} w={w} kind="mod"
                    aria={t("vr_panel.keyboard.language")} onPress={() => setMenu(m => (m === "language" ? null : "language"))} />;
            // Caps Lock: Shift のロックと同じ (もう1回で解除)
            case "caps":
                return modKey("caps", "Caps", t("vr_panel.keyboard.caps"), shift === "lock", shift === "lock", toggleCaps, "shift", w);
            // Tab: 変換中の候補を取る (変換していないときは押せない)
            case "tab":
                return <Key press={press} key="tab" id="tab" sound="soft" label="Tab" w={w} kind="mod" aria={t("vr_panel.keyboard.tab")}
                    onPress={() => sendKey("Tab")} disabled={!is_ready || !composing} />;
            case "ctrl":
                return modKey("ctrl", "Ctrl", t("vr_panel.keyboard.ctrl"), is_ctrl, ctrl === "lock", pressCtrl, "shift", w);
            // JIS の左上 (半角/全角): 日本語のまま、JIS の並びで打った字をそのまま入れる / かなに戻す。今の方を光らせる
            case "toggle":
                return <Key press={press} key="toggle" id="toggle" sound="toggle" w={w} kind="mod" aria={t("vr_panel.keyboard.switch_half_width")} onPress={() => sendKey("HalfWidth")}
                    label={<span className={styles.half_full}>
                        <span className={clsx({ [styles.is_on]: state.half_width })}>半</span>/<span className={clsx({ [styles.is_on]: !state.half_width })}>全</span>
                    </span>}
                    motion={motion} delay={delay} />;
            default:
                return null;
        }
    };

    // ピン: 押している間はキーボードを掴んでも動かない
    const pinned = currentKeyboardLocked.data === true;
    const pin_button = <button type="button" className={styles.menu_button} aria-label={t("vr_panel.keyboard.pin")} aria-pressed={pinned}
        onMouseDown={press(toggleKeyboardLocked, "soft", "pin")}>
        <svg className={clsx(styles.stroke_icon, styles.pin_icon)} viewBox="0 0 24 24" aria-hidden="true">
            <path className={clsx({ [styles.filled]: pinned })} d="M9 3.5h6l-1 6 3.5 3.5v1.5h-11V13L10 9.5z" /><path d="M12 14.5v6" />
        </svg>
    </button>;
    // 歯車: キーボードだけの設定 (不透明度・キーの音・入力中の表示・開くショートカット)
    const settings_button = <button type="button" className={styles.menu_button} aria-label={t("vr_panel.keyboard.customize")}
        aria-expanded={menu === "settings"} onMouseDown={press(() => setMenu(m => (m === "settings" ? null : "settings")), "soft", "settings")}>
        <ConfigurationSvg className={styles.gear_icon} aria-hidden="true" />
    </button>;
    // ↵ で送る先: 入力欄の右端に今の送る先の印だけ。押すたびに切り替わる
    const send_to_button = <button type="button" className={styles.send_to} aria-label={t(`vr_panel.keyboard.send_${send_to}`)}
        onMouseDown={press(() => setKeyboardSendTo(send_to === "paste" ? "vrct" : "paste"), "soft", "send_to")}>
        <SendToIcon to={send_to} />
    </button>;
    // 矢印キー (ノートパソコンの並び): 一番下の段の右端に ◀ ▲▼ ▶。▲ ▼ は1キー分を上下に分ける。
    // ◀ ▶ はカーソル (変換中は文節)、▲ ▼ は送った文の呼び出し
    const arrows = <>
        <Key press={press} id="left" sound="soft" label="◀" kind="mod" aria={t("vr_panel.keyboard.left")}
            onPress={() => arrowKey("Left")} onLeave={repeat.stop} />
        <div className={styles.updown} style={{ width: widthOf(1) }}>
            <Key press={press} id="up" sound="soft" label="▲" kind="mod" extra={styles.half} aria={t("vr_panel.keyboard.history_older")} onPress={() => sendKey("Up")} />
            <Key press={press} id="down" sound="soft" label="▼" kind="mod" extra={styles.half} aria={t("vr_panel.keyboard.history_newer")} onPress={() => sendKey("Down")} />
        </div>
        <Key press={press} id="right" sound="soft" label="▶" kind="mod" aria={t("vr_panel.keyboard.right")}
            onPress={() => arrowKey("Right")} onLeave={repeat.stop} />
    </>;

    return (
        <VrWindow Icon={KeyboardSvg} title={t("vr_panel.keyboard.title")} onClose={onClose}
            title_extra={<span className={styles.title_buttons}>{settings_button}{pin_button}</span>}>
            <div className={styles.keyboard}>
                {/* 一覧を開いている間は、外を押すと閉じる (その押下はキーに届かない) */}
                {menu && <div className={styles.backdrop} onMouseDown={(e) => { e.preventDefault(); setMenu(null); }} aria-hidden="true" />}
                {menu === "settings" && <KeyboardSettings press={press} onClose={() => setMenu(null)} />}
                {menu === "language" && <LanguageMenu press={press} language={language} simplified_on={simplified_on}
                    onPick={pickLanguage} onClose={() => setMenu(null)} />}
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
                        {/* Ctrl: 実際のキーボードと同じ左下。その隣に言語 */}
                        {keyOf({ special: "ctrl", w: 1.75 })}
                        {keyOf({ special: "language", w: 1.25 })}
                        <Key press={press} sound="space" label="" w={widthOf(7.75)} kind="act" aria={space_name}
                            onPress={() => sendKey("Space")} disabled={!is_ready} />
                        {/* マイク: 聞き取った文を入力欄に入れる (送らない。直して ↵ で送る) */}
                        <button type="button" className={clsx(styles.key, styles.mod, { [styles.is_locked]: dictating })}
                            style={{ width: widthOf(1.25), "--key-width": widthOf(1.25) }} aria-label={t("vr_panel.keyboard.dictation")} aria-pressed={dictating}
                            onMouseDown={press(toggleIsEnabledKeyboardDictation, "soft", "dictation")}>
                            <span className={styles.key_face}><MicSvg className={styles.mic_icon} aria-hidden="true" /></span>
                        </button>
                        {arrows}
                    </div>
                </div>
            </div>
        </VrWindow>
    );
};
