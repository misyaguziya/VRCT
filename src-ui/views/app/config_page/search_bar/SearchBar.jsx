import { useState, useRef, useEffect, useCallback } from "react";
import clsx from "clsx";
import { useI18n } from "@useI18n";
import { useStore_IsBreakPoint } from "@store";
import { useConfigSearch } from "@logics_configs";
import styles from "./SearchBar.module.scss";

import SearchSvg from "@images/search.svg?react";
import CancelSvg from "@images/cancel.svg?react";
import { TabIcon } from "../sidebar_section/SidebarSection.jsx";

// 検索文字列と一致する部分をハイライト表示するコンポーネント
const HighlightText = ({ text, query }) => {
    if (!text || !query) return text || null;
    const q = query.trim();
    if (!q) return text;

    try {
        const escaped = q.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
        const regex = new RegExp(`(${escaped})`, "gi");
        const parts = text.split(regex);
        if (parts.length === 1) return text;

        return (
            <>
                {parts.map((part, i) =>
                    part.toLowerCase() === q.toLowerCase() ? (
                        <span key={i} className={styles.match_highlight}>{part}</span>
                    ) : (
                        part
                    )
                )}
            </>
        );
    } catch {
        return text;
    }
};

export const SearchBar = () => {
    const { t } = useI18n();
    const { currentIsBreakPoint } = useStore_IsBreakPoint();
    const { query, setQuery, results, clearQuery, navigateToSetting } = useConfigSearch();

    const [isFocused, setIsFocused] = useState(false);
    const [selectedIndex, setSelectedIndex] = useState(-1);

    const containerRef = useRef(null);
    const inputRef = useRef(null);
    const listRef = useRef(null);

    const isOpen = isFocused && query.trim().length > 0;
    const isSmall = currentIsBreakPoint.data;

    // クエリ変更時に選択インデックスをリセット
    useEffect(() => {
        setSelectedIndex(-1);
    }, [query]);

    // コンテナ外クリックで閉じる
    useEffect(() => {
        const handleClickOutside = (e) => {
            if (containerRef.current && !containerRef.current.contains(e.target)) {
                setIsFocused(false);
            }
        };

        document.addEventListener("mousedown", handleClickOutside);
        return () => {
            document.removeEventListener("mousedown", handleClickOutside);
        };
    }, []);

    // キーボード操作で選択項目をスクロール表示
    useEffect(() => {
        if (selectedIndex >= 0 && listRef.current) {
            const activeEl = listRef.current.children[selectedIndex];
            if (activeEl) {
                activeEl.scrollIntoView({ block: "nearest" });
            }
        }
    }, [selectedIndex]);

    const handleSelect = useCallback((item) => {
        setIsFocused(false);
        if (inputRef.current) {
            inputRef.current.blur();
        }
        navigateToSetting(item);
    }, [navigateToSetting]);

    const handleKeyDown = (e) => {
        if (!isOpen) return;

        if (e.key === "ArrowDown") {
            e.preventDefault();
            setSelectedIndex((prev) => (prev < results.length - 1 ? prev + 1 : 0));
        } else if (e.key === "ArrowUp") {
            e.preventDefault();
            setSelectedIndex((prev) => (prev > 0 ? prev - 1 : results.length - 1));
        } else if (e.key === "Enter") {
            e.preventDefault();
            if (selectedIndex >= 0 && results[selectedIndex]) {
                handleSelect(results[selectedIndex]);
            } else if (results.length > 0) {
                handleSelect(results[0]);
            }
        } else if (e.key === "Escape") {
            e.preventDefault();
            setIsFocused(false);
            if (inputRef.current) {
                inputRef.current.blur();
            }
        }
    };

    const handleClear = () => {
        clearQuery();
        setSelectedIndex(-1);
        if (inputRef.current) {
            inputRef.current.focus();
        }
    };

    return (
        <div
            className={clsx(styles.search_wrapper, {
                [styles.is_small]: isSmall,
            })}
            ref={containerRef}
        >
            <div className={styles.search_input_container}>
                <SearchSvg className={styles.search_icon} />
                <input
                    ref={inputRef}
                    type="text"
                    className={styles.search_input}
                    placeholder={t("config_page.search.placeholder")}
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onFocus={() => setIsFocused(true)}
                    onKeyDown={handleKeyDown}
                />
                {query.length > 0 && (
                    <button
                        type="button"
                        className={styles.clear_button}
                        onClick={handleClear}
                        tabIndex={-1}
                        aria-label="Clear search"
                    >
                        <CancelSvg className={styles.clear_icon} />
                    </button>
                )}
            </div>

            {isOpen && (
                <div className={styles.dropdown_results} ref={listRef}>
                    {results.length > 0 ? (
                        results.map((item, idx) => (
                            <div
                                key={`${item.tab}_${item.setting_id}_${idx}`}
                                className={clsx(styles.result_item, {
                                    [styles.is_active]: idx === selectedIndex,
                                })}
                                onMouseDown={(e) => {
                                    e.preventDefault();
                                    handleSelect(item);
                                }}
                                onMouseEnter={() => setSelectedIndex(idx)}
                            >
                                <div className={styles.item_header}>
                                    <span className={styles.tab_badge}>
                                        <TabIcon tab_id={item.tab} className={styles.badge_tab_icon} />
                                        {item.tab_label}
                                    </span>
                                    <span className={styles.item_label}>
                                        <HighlightText text={item.label} query={query} />
                                    </span>
                                    {item.prereq && (
                                        <span className={styles.prereq_badge}>
                                            要: {item.prereq.required_label}
                                        </span>
                                    )}
                                </div>
                                {item.desc && (
                                    <span className={styles.item_desc}>
                                        <HighlightText text={item.desc} query={query} />
                                    </span>
                                )}
                            </div>
                        ))
                    ) : (
                        <div className={styles.no_results}>
                            {t("config_page.search.no_results")}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};
