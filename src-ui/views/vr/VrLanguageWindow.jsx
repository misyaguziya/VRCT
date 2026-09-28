import { useState } from "react";
import clsx from "clsx";

import { useI18n } from "@useI18n";
import { useLanguageSettings } from "@logics_main";

import TranslationSvg from "@images/translation.svg?react";
import WarningSvg from "@images/warning.svg?react";

import { VrWindow } from "./VrWindow";
import styles from "./VrLanguageWindow.module.scss";

const MAX_TARGETS = 3;
const TARGET_KEYS = ["1", "2", "3"];
const LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("");
const same = (a, b) => a.language === b.language && a.country === b.country;

// 相手の言語の候補: プリセット1〜3に保存済みの言語 (自分の言語・相手の言語、有効無効を問わず)。
// 新しい保存領域は作らない。今は選べない言語 (SelectableLanguageList に無いもの) は除く
const collectCandidates = (your_languages, target_languages, selectable) => {
    const candidates = [];
    const add = (entry) => {
        if (!entry?.language) return;
        if (!selectable.some(s => same(s, entry))) return;
        if (candidates.some(c => same(c, entry))) return;
        candidates.push({ language: entry.language, country: entry.country });
    };
    for (const tab of ["1", "2", "3"]) {
        add(your_languages[tab]?.["1"]);
        for (const key of TARGET_KEYS) add(target_languages[tab]?.[key]);
    }
    return candidates;
};

// 言語ウィンドウ: プリセット、自分の言語 (候補か A〜Z から選ぶ)、言語の入れ替え、
// 相手の言語 (候補から選ぶ・外す、無ければ A〜Z)、翻訳エンジン
export const VrLanguageWindow = ({ onClose }) => {
    const { t } = useI18n();
    // 画面の切り替えはこのウィンドウの中だけで持つ: main / letters / letter (A〜Zの1文字) / engine
    const [view, setView] = useState({ name: "main" });
    const settings = useLanguageSettings();
    const {
        currentSelectedPresetTabNumber: tab,
        currentSelectedYourLanguages: your,
        currentSelectedTargetLanguages: target,
        currentTranslationEngines: engines,
        currentSelectedTranslationEngines: selected_engines,
        currentSelectableLanguageList: selectable,
    } = settings;

    const tab_no = tab.data;
    const your_language = your.data?.[tab_no]?.["1"];
    const target_slots = target.data?.[tab_no];
    // メインから同期される前はデータが空
    const is_ready = your_language && target_slots && Array.isArray(selectable.data);
    // 処理中に操作すると古い値で別のプリセットを書き換えるおそれがあるので止める
    const is_busy = [tab, your, target, selected_engines].some(s => s.state === "pending");

    const title = t("vr_panel.window_language");
    if (!is_ready) {
        return <VrWindow Icon={TranslationSvg} title={title} onClose={onClose} />;
    }

    const selected_targets = TARGET_KEYS.filter(k => target_slots[k]?.enable).map(k => target_slots[k]);
    const toggleTarget = (language) => {
        if (is_busy) return;
        const index = selected_targets.findIndex(s => same(s, language));
        if (index >= 0) {
            if (selected_targets.length === 1) return; // 相手の言語は最低1つ
            settings.setTargetLanguagesInOrder(selected_targets.filter((_, i) => i !== index));
        } else if (selected_targets.length < MAX_TARGETS) {
            settings.setTargetLanguagesInOrder([...selected_targets, language]);
        }
    };

    const setYourLanguage = (language) => {
        if (is_busy || same(language, your_language)) return;
        settings.setSelectedYourLanguages(language);
    };

    const selected_engine_id = selected_engines.data?.[tab_no];
    const engine_label = (id) => (engines.data.find(e => e.id === id)?.label ?? id ?? "").replace("\n", " ");
    const is_same_language = selected_targets.some(s => same(s, your_language));

    const candidates = collectCandidates(your.data, target.data, selectable.data);
    for (const s of selected_targets) {
        if (!candidates.some(c => same(c, s))) candidates.push(s);
    }

    // A〜Z は相手の言語 (view.for === "target") と自分の言語 (view.for === "your") で共用する
    if (view.name === "letters" || view.name === "letter") {
        const is_your = view.for === "your";
        return (
            <VrWindow Icon={TranslationSvg} title={title} onClose={onClose}>
                <div className={styles.body}>
                    <BackButton label={t("common.go_back_button_label")}
                        onClick={() => setView(view.name === "letter"
                            ? { name: "letters", for: view.for }
                            : { name: is_your ? "your" : "main" })} />
                    {view.name === "letters"
                        ? <LetterGrid languages={selectable.data} onPick={(letter) => setView({ name: "letter", for: view.for, letter })} />
                        : <LanguageList
                            languages={selectable.data.filter(l => l.language[0].toUpperCase() === view.letter)}
                            selected={is_your ? [your_language] : selected_targets}
                            is_full={!is_your && selected_targets.length >= MAX_TARGETS}
                            onPick={(language) => {
                                if (is_your) setYourLanguage(language);
                                else toggleTarget(language);
                                setView({ name: "main" });
                            }}
                        />
                    }
                </div>
            </VrWindow>
        );
    }

    if (view.name === "your") {
        return (
            <VrWindow Icon={TranslationSvg} title={title} onClose={onClose}>
                <div className={styles.body}>
                    <BackButton label={t("common.go_back_button_label")} onClick={() => setView({ name: "main" })} />
                    <p className={styles.caption}>{t("main_page.your_language")}</p>
                    <div className={styles.grid_3}>
                        {candidates.map(c => (
                            <LanguageChip key={`${c.language}/${c.country}`} language={c}
                                is_selected={same(c, your_language)}
                                onClick={() => { setYourLanguage(c); setView({ name: "main" }); }} />
                        ))}
                        <MoreChip onClick={() => setView({ name: "letters", for: "your" })} />
                    </div>
                </div>
            </VrWindow>
        );
    }

    if (view.name === "engine") {
        return (
            <VrWindow Icon={TranslationSvg} title={title} onClose={onClose}>
                <div className={styles.body}>
                    <BackButton label={t("common.go_back_button_label")} onClick={() => setView({ name: "main" })} />
                    <div className={styles.grid_2}>
                        {engines.data.map(engine => (
                            <button key={engine.id}
                                className={clsx(styles.item, { [styles.is_selected]: engine.id === selected_engine_id, [styles.is_disabled]: !engine.is_available })}
                                onClick={() => {
                                    if (!engine.is_available || is_busy) return;
                                    settings.setSelectedTranslationEngines(engine.id);
                                    setView({ name: "main" });
                                }}
                            >
                                {engine_label(engine.id)}
                                {engine.is_default && <span className={styles.sub}>{t("common.default_label")}</span>}
                            </button>
                        ))}
                    </div>
                    {is_same_language && <SameLanguageWarning t={t} your_language={your_language} />}
                </div>
            </VrWindow>
        );
    }

    return (
        <VrWindow Icon={TranslationSvg} title={title} onClose={onClose}>
            <div className={clsx(styles.body, { [styles.is_busy]: is_busy })}>
                <div className={styles.row}>
                    {["1", "2", "3"].map(n => (
                        <button key={n} className={clsx(styles.preset, { [styles.is_current]: n === tab_no })}
                            onClick={() => !is_busy && n !== tab_no && settings.setSelectedPresetTabNumber(n)}>
                            {n}
                        </button>
                    ))}
                    <button className={styles.your_language} onClick={() => !is_busy && setView({ name: "your" })}>
                        <span className={styles.your_language_text}>
                            <span className={styles.caption}>{t("main_page.your_language")}</span>
                            <span className={styles.value}>{your_language.language}</span>
                        </span>
                        <span className={styles.chevron}>›</span>
                    </button>
                    <button className={styles.swap} onClick={() => !is_busy && settings.swapSelectedLanguages()}>
                        {t("main_page.swap_button_label")}
                    </button>
                </div>

                <p className={styles.caption}>{t("main_page.target_language")}</p>
                <div className={styles.grid_3}>
                    {candidates.map(c => {
                        const order = selected_targets.findIndex(s => same(s, c));
                        const is_full = order < 0 && selected_targets.length >= MAX_TARGETS;
                        return (
                            <LanguageChip key={`${c.language}/${c.country}`} language={c}
                                is_selected={order >= 0} is_disabled={is_full}
                                order={order >= 0 ? order + 1 : null}
                                onClick={() => !is_full && toggleTarget(c)} />
                        );
                    })}
                    <MoreChip onClick={() => setView({ name: "letters", for: "target" })} />
                </div>

                <button className={styles.engine} onClick={() => setView({ name: "engine" })}>
                    <span className={styles.caption}>{t("main_page.translator")}</span>
                    <span className={styles.value}>{engine_label(selected_engine_id)}</span>
                    {is_same_language && <WarningSvg className={styles.warning_icon} />}
                    <span className={styles.chevron}>›</span>
                </button>
            </div>
        </VrWindow>
    );
};

const LanguageChip = ({ language, is_selected, is_disabled, order, onClick }) => (
    <button className={clsx(styles.chip, { [styles.is_selected]: is_selected, [styles.is_disabled]: is_disabled })} onClick={onClick}>
        <span className={styles.chip_name}>{language.language}</span>
        <span className={styles.sub}>{language.country}</span>
        {order && <span className={styles.order}>{order}</span>}
    </button>
);

const MoreChip = ({ onClick }) => (
    <button className={clsx(styles.chip, styles.more)} onClick={onClick}>A–Z ›</button>
);

const BackButton = ({ label, onClick }) => (
    <button className={styles.back} onClick={onClick}>‹ {label}</button>
);

const LetterGrid = ({ languages, onPick }) => {
    const letters_with_languages = new Set(languages.map(l => l.language[0].toUpperCase()));
    return (
        <div className={styles.letters}>
            {LETTERS.map(letter => {
                const is_empty = !letters_with_languages.has(letter);
                return (
                    <button key={letter} className={clsx(styles.letter, { [styles.is_disabled]: is_empty })}
                        onClick={() => !is_empty && onPick(letter)}>
                        {letter}
                    </button>
                );
            })}
        </div>
    );
};

const LanguageList = ({ languages, selected, is_full, onPick }) => (
    <div className={clsx(styles.grid_2, styles.scroll)}>
        {languages.map(l => {
            const is_selected = selected.some(s => same(s, l));
            const is_disabled = is_selected || is_full;
            return (
                <button key={`${l.language}/${l.country}`}
                    className={clsx(styles.item, { [styles.is_selected]: is_selected, [styles.is_disabled]: is_disabled })}
                    onClick={() => !is_disabled && onPick(l)}>
                    <span className={styles.chip_name}>{l.language}</span>
                    <span className={styles.sub}>{l.country}</span>
                </button>
            );
        })}
    </div>
);

const SameLanguageWarning = ({ t, your_language }) => (
    <p className={styles.warning}>
        <WarningSvg className={styles.warning_icon} />
        {t("main_page.translator_selector.is_selected_same_language", {
            your_language: t("main_page.your_language"),
            target_language: t("main_page.target_language"),
            ctranslate2: "CTranslate2",
        })}
    </p>
);
