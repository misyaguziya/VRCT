import { useRef, useLayoutEffect, useEffect } from "react";

import styles from "./SettingSection.module.scss";
import { SettingBox } from "./setting_box/SettingBox";
import { store } from "@store";

export const SettingSection = () => {
    const scrollContainerRef = useRef(null);
    useLayoutEffect(() => {
        store.setting_box_scroll_container = scrollContainerRef;
    }, []);

    return (
        <div ref={scrollContainerRef} className={styles.scroll_container}>
            <div className={styles.container}>
                <SettingBox />
            </div>
        </div>
    );
};