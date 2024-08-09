import styles from "./ConfigPage.module.scss";

import { Topbar } from "./topbar/Topbar.jsx";
import { SidebarSection } from "./sidebar_section/SidebarSection.jsx";
import { SettingSection } from "./setting_section/SettingSection.jsx";

import { useSoftwareVersion  } from "@store";
import { useTranslation } from "react-i18next";

// import { useConfig } from "@logics/useConfig";
export const ConfigPage = () => {
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
                    t("config_page.version", {version: currentSoftwareVersion})
                }
            </p>
        </div>
    );
};