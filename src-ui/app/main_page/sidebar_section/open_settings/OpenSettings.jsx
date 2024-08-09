import styles from "./OpenSettings.module.scss";
import ConfigurationSvg from "@images/configuration.svg?react";

// import { useWindow } from "@logics/useWindow";

export const OpenSettings = () => {
    // const { createConfigPage } = useWindow();

    const openConfigPage = () => {

        // createConfigPage();
    };

    return (
        <div className={styles.container}>
            <div className={styles.open_config_page_button} onClick={openConfigPage}>
                <ConfigurationSvg className={styles.configuration_svg} />
            </div>
        </div>
    );
};