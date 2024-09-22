import styles from "./ConfigPage.module.scss";

import { Topbar } from "./topbar/Topbar.jsx";
import { SidebarSection } from "./sidebar_section/SidebarSection.jsx";
import { SettingSection } from "./setting_section/SettingSection.jsx";

import { useSoftwareVersion } from "@logics_configs/useSoftwareVersion";
import { useTranslation } from "react-i18next";

export const ConfigPage = () => {
    const { currentSoftwareVersion } = useSoftwareVersion();
    const { t } = useTranslation();

    return (
        <div className={styles.page}>
            <div className={styles.container}>
                <Topbar />
                <div className={styles.main_container}>
                    <SidebarSection />
                    <SettingSection />
                </div>
                <p className={styles.software_version}>
                    {
                        t("config_page.version", {version: currentSoftwareVersion.data})
                    }
                </p>
            </div>
        </div>
    );
};