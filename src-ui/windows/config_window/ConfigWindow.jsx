import styles from "./ConfigWindow.module.scss";

import { Topbar } from "./topbar/Topbar";
import { SidebarSection } from "./sidebar_section/SidebarSection";
import { SettingSection } from "./setting_section/SettingSection.jsx";

import { useSoftwareVersion  } from "@store";
import { useTranslation } from "react-i18next";

// import { useConfig } from "@logics/useConfig";
export const ConfigWindow = () => {
    const { currentSoftwareVersion, updateSoftwareVersion } = useSoftwareVersion();
    const { t } = useTranslation();

    return (
        <div className={styles.container}>
            <Topbar />
            <div className={styles.main_container}>
                <SidebarSection />
                <SettingSection />
            </div>
            <p className={styles.software_version}>
                {
                    t("config_window.version", {version: currentSoftwareVersion})
                }
            </p>
        </div>
    );
};