import styles from "./OpenSettings.module.scss";
import { useStore_IsOpenedConfigPage } from "@store";
import ConfigurationSvg from "@images/configuration.svg?react";

export const OpenSettings = () => {
    const { updateIsOpenedConfigPage } = useStore_IsOpenedConfigPage();

    const openConfigPage = () => {
        updateIsOpenedConfigPage(true);
    };

    return (
        <div className={styles.container}>
            <div className={styles.open_config_page_button} onClick={openConfigPage}>
                <ConfigurationSvg className={styles.configuration_svg} />
            </div>
        </div>
    );
};