import clsx from "clsx";
import { useI18n } from "@useI18n";
import styles from "./VrKeyboardWindow.module.scss";

// 言語の一覧 (中国語の拼音は簡体字・繁体字を別の項目にして、その後ろに並べる。注音・倉頡・速成は繁体字で、その後ろ)
const LANGUAGES = [["ja", "日本語"], ["en", "English"], ["ko", "한국어"]];
export const TRADITIONAL_METHODS = [["zhuyin", "注音"], ["cangjie", "倉頡"], ["quick", "速成"]];

// 言語キーから開く一覧。選んでいるものはアクセントの字 (枠は描かない)。選ぶと閉じる。
// onPick(code, { simplified }): simplified は中国語の簡体字・繁体字 (その言語のときだけ)
export const LanguageMenu = ({ press, language, simplified_on, onPick, onClose }) => {
    const { t } = useI18n();
    const option = (key, label, selected, pick, lang) => (
        <button key={key} type="button" className={styles.option} aria-pressed={selected} lang={lang}
            onMouseDown={press(() => { onClose(); pick(); }, "soft", key)}>{label}</button>
    );
    return <div className={clsx(styles.menu, styles.language_menu)} role="menu" aria-label={t("vr_panel.keyboard.language")}>
        {LANGUAGES.map(([code, name]) => option(`language:${code}`, name, code === language, () => onPick(code), code))}
        {option("language:zh-hans", "简体中文", language === "zh" && simplified_on, () => onPick("zh", { simplified: true }), "zh-Hans")}
        {option("language:zh-hant", "繁體中文", language === "zh" && !simplified_on, () => onPick("zh", { simplified: false }), "zh-Hant")}
        {TRADITIONAL_METHODS.map(([code, name]) => option(`language:${code}`, name, code === language, () => onPick(code, { simplified: false }), "zh-Hant"))}
    </div>;
};
