import "../../../locales/config.js";
import "@utils/root.css";

import styles from "./ConfigWindow.module.scss";

import { Topbar } from "./topbar/Topbar";
import { SidebarSection } from "./sidebar_section/SidebarSection";
import { SettingSection } from "./setting_section/SettingSection.jsx";

export const ConfigWindow = () => {
    return (
        <div className={styles.container}>
            <Topbar />
            <div className={styles.main_container}>
                <SidebarSection />
                <SettingSection />
            </div>
        </div>
    );
};