import styles from "./ConfigPage.module.scss";

import { Topbar } from "./topbar/Topbar.jsx";
import { SidebarSection } from "./sidebar_section/SidebarSection.jsx";
import { SettingSection } from "./setting_section/SettingSection.jsx";

export const ConfigPage = () => {
    return (
        <div className={styles.page}>
            <div className={styles.container}>
                <SidebarSection />
                <div className={styles.content_wrapper}>
                    <Topbar />
                    <div className={styles.main_container}>
                        <SettingSection />
                    </div>
                </div>
            </div>
        </div>
    );
};