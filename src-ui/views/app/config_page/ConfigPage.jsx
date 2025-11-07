import styles from "./ConfigPage.module.scss";

import { Topbar } from "./topbar/Topbar.jsx";
import { SidebarSection } from "./sidebar_section/SidebarSection.jsx";
import { SettingSection } from "./setting_section/SettingSection.jsx";
import { VersionLabel } from "./version_label/VersionLabel.jsx";

export const ConfigPage = () => {
    return (
        <div className={styles.page}>
            <div className={styles.container}>
                <Topbar />
                <div className={styles.main_container}>
                    <SidebarSection />
                    <SettingSection />
                </div>
                <VersionLabel />
            </div>
        </div>
    );
};