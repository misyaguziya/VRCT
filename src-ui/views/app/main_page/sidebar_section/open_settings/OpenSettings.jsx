import styles from "./OpenSettings.module.scss";
import { useIsOpenedConfigPage } from "@logics_common";
import ConfigurationSvg from "@images/configuration.svg?react";

export const OpenSettings = () => {
    const { setIsOpenedConfigPage } = useIsOpenedConfigPage();

    const openConfigPage = () => {
        setIsOpenedConfigPage(true);
    };

    return (
        <div className={styles.container}>
            <div className={styles.open_config_page_button} onClick={openConfigPage}>
                <ConfigurationSvg className={styles.configuration_svg} />
            </div>
        </div>
    );
};