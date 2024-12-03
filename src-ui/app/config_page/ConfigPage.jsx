import styles from "./ConfigPage.module.scss";

import { Topbar } from "./topbar/Topbar.jsx";
import { SidebarSection } from "./sidebar_section/SidebarSection.jsx";
import { SettingSection } from "./setting_section/SettingSection.jsx";

import { useSoftwareVersion } from "@logics_configs";
import { useComputeMode } from "@logics_common";
import { useTranslation } from "react-i18next";

export const ConfigPage = () => {
    const { t } = useTranslation();
    const { currentSoftwareVersion } = useSoftwareVersion();
    const { currentComputeMode } = useComputeMode();

    const version_label = currentComputeMode.data === "cpu"
        ? t("config_page.version", { version: currentSoftwareVersion.data })
        : currentComputeMode.data === "cuda"
        ? t("config_page.version", { version: currentSoftwareVersion.data }) + " CUDA"
        : t("config_page.version", { version: currentSoftwareVersion.data });

    return (
        <div className={styles.page}>
            <div className={styles.container}>
                <Topbar />
                <div className={styles.main_container}>
                    <SidebarSection />
                    <SettingSection />
                </div>
                <p className={styles.software_version}>{version_label}</p>
            </div>
        </div>
    );
};