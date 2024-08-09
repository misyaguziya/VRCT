import styles from "./MainPage.module.scss";
import { SidebarSection } from "./sidebar_section/SidebarSection";
import { MainSection } from "./main_section/MainSection";

export const MainPage = () => {
    return (
        <div className={styles.container}>
            <SidebarSection />
            <MainSection />
            {/* <MainPageCover /> */}
        </div>
    );
};


// import { useTranslation } from "react-i18next";
// import { useIsOpenedConfigPage } from "@store";
// import { useWindow } from "@logics/useWindow";

// export const MainPageCover = () => {
//     const { t } = useTranslation();
//     const { currentIsOpenedConfigPage } = useIsOpenedConfigPage();
//     const { closeConfigPage } = useWindow();
//     if ( currentIsOpenedConfigPage === false) return null;

//     const closeSettingsWindow = () => closeConfigPage();

//     return (
//         <div className={styles.main_page_cover}>
//             <p className={styles.cover_message}>{t("main_page.cover_message")}</p>
//             <button
//             className={styles.close_settings_window_button}
//             onClick={closeSettingsWindow}
//             >
//                 {t("main_page.close_settings_window")}
//             </button>
//         </div>
//     );
// };