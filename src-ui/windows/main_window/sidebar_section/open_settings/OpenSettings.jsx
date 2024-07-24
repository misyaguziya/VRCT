import styles from "./OpenSettings.module.scss";
import ConfigurationSvg from "@images/configuration.svg?react";

import { useWindow } from "@utils/useWindow";

export const OpenSettings = () => {
    const { createConfigWindow } = useWindow();

    const openConfigWindow = () => {
        createConfigWindow();
    };

    return (
        <div className={styles.container}>
            <div className={styles.open_config_window_button} onClick={openConfigWindow}>
                <ConfigurationSvg className={styles.configuration_svg} />
            </div>
        </div>
    );
};