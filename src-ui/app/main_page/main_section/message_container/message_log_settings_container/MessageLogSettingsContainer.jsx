import { useState } from "react";
import styles from "./MessageLogSettingsContainer.module.scss";
import clsx from "clsx";
import { useTranslation } from "react-i18next";

import { useIsVisibleResendButton } from "@logics_main";
import { MessageLogUiScalingContainer } from "@setting_box";
import { Checkbox } from "@common_components";
import ConfigSvg from "@images/configuration.svg?react";

export const MessageLogSettingsContainer = (props) => {
    const { t } = useTranslation();
    const [is_opened, setIsOpened] = useState(false);
    const [is_hovered, setIsHovered] = useState(false);

    const { currentIsVisibleResendButton, toggleIsVisibleResendButton } = useIsVisibleResendButton();

    const container_class_name = clsx(styles.container, {
        [styles.to_visible_toggle_bar]: props.to_visible_toggle_bar,
        [styles.is_hovered]: is_hovered,
        [styles.is_opened]: is_opened
    });

    const toggleVisibleResendButton = () => {
        toggleIsVisibleResendButton();
    };

    return (
        <div className={container_class_name}
            onMouseOver={() => setIsHovered(true)}
            onMouseLeave={() => {setIsHovered(false); setIsOpened(false);}}
            onClick={() => setIsOpened(true)}
        >
            <div className={styles.container_relative_wrapper}>
                <div className={styles.config_svg_wrapper}>
                    <ConfigSvg className={styles.config_svg}/>
                </div>
            </div>
            <MessageLogUiScalingContainer />
            <div className={styles.others_wrapper}>
                <div className={styles.resend_checkbox_toggle} onClick={toggleVisibleResendButton}>
                    <p className={styles.resend_checkbox_label}>{t("main_page.message_log.show_resend_button")}</p>
                    <Checkbox
                        id="visible_resend_button"
                        variable={currentIsVisibleResendButton}
                        size="2rem"
                        padding="0"
                    />
                </div>
            </div>
        </div>
    );
};