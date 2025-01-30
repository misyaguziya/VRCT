import styles from "./SidebarSection.module.scss";

export const SidebarSection = () => {
    return (
        <div className={styles.container}>
            <div className={styles.scroll_container}>
                <div className={styles.tabs_wrapper}>
                    <Tab tab_id="device" />
                    <Tab tab_id="appearance" />
                    <Tab tab_id="translation" />
                    <Tab tab_id="transcription" />
                    <Tab tab_id="vr" />
                    <Tab tab_id="others" />
                    <Tab tab_id="hotkeys" />
                    <Tab tab_id="advanced_settings" />
                </div>
                <div className={styles.separated_tabs_wrapper}>
                    <Tab tab_id="supporters" />
                    <Tab tab_id="about_vrct" />
                </div>
            </div>
        </div>
    );
};


import clsx from "clsx";
import { useTranslation } from "react-i18next";
import { useStore_SelectedConfigTabId } from "@store";

const Tab = (props) => {
    const { t } = useTranslation();
    const { updateSelectedConfigTabId, currentSelectedConfigTabId } = useStore_SelectedConfigTabId();
    const onclickFunction = () => {
        updateSelectedConfigTabId(props.tab_id);
    };

    const tab_container_class_names = clsx(styles["tab_container"], {
        [styles["is_selected"]]: (currentSelectedConfigTabId.data === props.tab_id) ? true : false
    });
    const switch_indicator_class_names = clsx(styles["switch_indicator"], {
        [styles["is_selected"]]: (currentSelectedConfigTabId.data === props.tab_id) ? true : false
    });

    return (
        <div className={tab_container_class_names} onClick={onclickFunction}>
            <p className={styles.tab_text}>{t(`config_page.side_menu_labels.${props.tab_id}`)}</p>
            <div className={switch_indicator_class_names}></div>
        </div>
    );
};