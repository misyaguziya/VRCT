import clsx from "clsx";
import styles from "./ConfigPage.module.scss";

import { useIsOpenedConfigPage } from "@logics_common";

import { Topbar } from "./topbar/Topbar.jsx";
import { SidebarSection } from "./sidebar_section/SidebarSection.jsx";
import { SettingSection } from "./setting_section/SettingSection.jsx";
import { SearchBar } from "./search_bar/SearchBar.jsx";

export const ConfigPage = () => {
    const { currentIsOpenedConfigPage } = useIsOpenedConfigPage();
    const isClosed = currentIsOpenedConfigPage.data === false;

    return (
        <div className={clsx(styles.page, { [styles.is_closed]: isClosed })}>
            <div className={styles.container}>
                <SidebarSection />
                <div className={styles.content_wrapper}>
                    <div className={styles.main_container}>
                        <SettingSection />
                    </div>
                </div>
                <Topbar />
                <SearchBar />
            </div>
        </div>
    );
};