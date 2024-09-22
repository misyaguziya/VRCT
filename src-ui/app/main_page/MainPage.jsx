import clsx from "clsx";
import styles from "./MainPage.module.scss";
import { SidebarSection } from "./sidebar_section/SidebarSection";
import { MainSection } from "./main_section/MainSection";
import { useStore_IsOpenedConfigPage } from "@store";

export const MainPage = () => {
    const { currentIsOpenedConfigPage } = useStore_IsOpenedConfigPage();

    return (
        <div className={clsx(styles.page, styles.main_page, {
            [styles.show_config]: currentIsOpenedConfigPage.data,
            [styles.show_main]: !currentIsOpenedConfigPage.data
        })}>
            <div className={styles.container}>
                <SidebarSection />
                <MainSection />
            </div>
        </div>
    );
};