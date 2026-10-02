import { useState, useMemo, useCallback } from "react";
import { useI18n } from "@useI18n";
import { useStore_SelectedConfigTabId } from "@store";
import i18n from "@root/locales/config.js";

// 対象とする設定タブ一覧
const VALID_TABS = [
    "device",
    "appearance",
    "translation",
    "transcription",
    "ocr",
    "vr",
    "others",
    "hotkeys",
    "advanced_settings",
];

const TAB_LABEL_KEYS = {
    device: "config_page.side_menu_labels.device",
    appearance: "config_page.side_menu_labels.appearance",
    translation: "config_page.side_menu_labels.translation",
    transcription: "config_page.side_menu_labels.transcription",
    others: "config_page.side_menu_labels.others",
    vr: "config_page.side_menu_labels.vr",
    hotkeys: "config_page.side_menu_labels.hotkeys",
    advanced_settings: "config_page.side_menu_labels.advanced_settings",
    ocr: "config_page.side_menu_labels.ocr",
};

// 親項目（前提条件）の依存関係
const PREREQUISITES = {
    whisper_weight_type: {
        parent_id: "select_transcription_engine",
        required_label: "Whisper",
    },
    transcription_compute_device: {
        parent_id: "select_transcription_engine",
        required_label: "Whisper",
    },
};

// オブジェクト内のすべての文字列値を再帰的に収集
const collectStrings = (obj) => {
    const list = [];
    if (!obj) return list;
    if (typeof obj === "string") {
        list.push(obj);
        return list;
    }
    if (typeof obj === "object") {
        for (const val of Object.values(obj)) {
            list.push(...collectStrings(val));
        }
    }
    return list;
};

// 文字列内の {{variable}} などのテンプレート変数を整理
const cleanTemplateStr = (str) => {
    return typeof str === "string" ? str.replace(/\{\{[^}]+\}\}/g, "").trim() : "";
};

export const useConfigSearch = () => {
    const { t, i18n: i18nHook } = useI18n();
    const { currentSelectedConfigTabId, updateSelectedConfigTabId } = useStore_SelectedConfigTabId();
    const [query, setQuery] = useState("");

    // config_page 以下のリソースから動的に検索インデックスを生成
    const allEntries = useMemo(() => {
        const currentLng = i18nHook.language;
        const curRes = i18n.getResource(currentLng, "translation")?.config_page || {};
        const enRes = i18n.getResource("en", "translation")?.config_page || {};
        const isEn = currentLng === "en";

        const entries = [];

        for (const tab of VALID_TABS) {
            const curTab = curRes[tab] || {};
            const enTab = enRes[tab] || {};
            const allKeys = new Set([...Object.keys(curTab), ...Object.keys(enTab)]);

            for (const key of allKeys) {
                const curVal = curTab[key];
                const enVal = enTab[key];

                if (!curVal && !enVal) continue;

                // label の抽出（currentLng → en フォールバック）
                const rawLabel = (typeof curVal === "object" ? (curVal.label || curVal.label_for_automatic || curVal.label_for_manual) : null)
                    ?? (typeof enVal === "object" ? (enVal.label || enVal.label_for_automatic || enVal.label_for_manual) : null)
                    ?? (typeof curVal === "string" ? curVal : (typeof enVal === "string" ? enVal : key));

                // desc の抽出
                const rawDesc = (typeof curVal === "object" ? (curVal.desc || curVal.desc_for_automatic || curVal.desc_for_manual) : null)
                    ?? (typeof enVal === "object" ? (enVal.desc || enVal.desc_for_automatic || enVal.desc_for_manual) : null)
                    ?? "";

                // 検索対象テキストの収集（現在言語 + en の両方を包含）
                const searchStrings = [];
                if (curVal) {
                    searchStrings.push(...collectStrings(curVal));
                }
                if (!isEn && enVal) {
                    searchStrings.push(...collectStrings(enVal));
                }

                const searchTarget = searchStrings
                    .map((s) => cleanTemplateStr(s).toLowerCase())
                    .filter(Boolean);

                const tabLabel = t(TAB_LABEL_KEYS[tab] ?? tab);

                entries.push({
                    tab,
                    setting_id: key,
                    label: rawLabel,
                    desc: rawDesc,
                    tab_label: tabLabel,
                    searchTarget,
                    prereq: PREREQUISITES[key] || null,
                });
            }
        }
        return entries;
    }, [i18nHook.language, t]);

    const results = useMemo(() => {
        const q = query.trim().toLowerCase();
        if (q.length < 1) return [];

        return allEntries.filter((entry) => {
            return entry.searchTarget.some((text) => text.includes(q));
        });
    }, [query, allEntries]);

    const clearQuery = useCallback(() => setQuery(""), []);

    const navigateToSetting = useCallback((result) => {
        clearQuery();

        if (currentSelectedConfigTabId.data !== result.tab) {
            updateSelectedConfigTabId(result.tab);
        }

        let attempts = 0;
        const findAndScroll = () => {
            let target =
                document.querySelector(`[data-setting-id="${result.setting_id}"]`) ||
                document.querySelector(`[data-setting-label="${result.label}"]`);

            // 条件付き非表示などでDOMにない場合、親項目へフォールバック
            if (!target && result.prereq) {
                target = document.querySelector(`[data-setting-id="${result.prereq.parent_id}"]`);
            }

            if (target) {
                target.scrollIntoView({ behavior: "smooth", block: "center" });
                target.classList.remove("search_target_highlight");
                void target.offsetWidth; // trigger reflow
                target.classList.add("search_target_highlight");
                setTimeout(() => {
                    target.classList.remove("search_target_highlight");
                }, 2500);
            } else if (attempts < 25) {
                attempts++;
                setTimeout(findAndScroll, 40);
            }
        };

        setTimeout(findAndScroll, 60);
    }, [clearQuery, currentSelectedConfigTabId.data, updateSelectedConfigTabId]);

    return { query, setQuery, results, clearQuery, navigateToSetting };
};
