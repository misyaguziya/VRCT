import { useRef, useLayoutEffect, useEffect } from "react";

import styles from "./SettingSection.module.scss";
import { SettingBox } from "./setting_box/SettingBox";
import { store, useStore_SelectedConfigTabId } from "@store";
import { useSettingBoxScrollPosition } from "@logics_configs";

export const SettingSection = () => {
    const { currentSelectedConfigTabId } = useStore_SelectedConfigTabId();
    const { resetScrollPosition } = useSettingBoxScrollPosition();
    const scrollContainerRef = useRef(null);

    useLayoutEffect(() => {
        store.setting_box_scroll_container = scrollContainerRef;
    }, []);

    useEffect(() => {
        resetScrollPosition();
    }, [currentSelectedConfigTabId.data]);

    return (
        <div ref={scrollContainerRef} className={styles.scroll_container}>
            <div className={styles.container}>
                <SettingBox />
            </div>
        </div>
    );
};