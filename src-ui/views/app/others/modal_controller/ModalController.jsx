import styles from "./ModalController.module.scss";
import { useI18n } from "@useI18n";
import { useStore_OpenedQuickSetting } from "@store";
import { useMainFunction } from "@logics_main";
import { Vr, VrcMicMuteSyncContainer, Updater } from "@setting_box";
import { SwitchBoxContainer } from "../../config_page/setting_section/setting_box/_templates/Templates";

export const ModalController = () => {
    const { currentOpenedQuickSetting, updateOpenedQuickSetting } = useStore_OpenedQuickSetting();
    if (currentOpenedQuickSetting.data === "") return null;
    return (
        <div className={styles.container}>
            <div className={styles.bg_onclick_close_area} onClick={() => updateOpenedQuickSetting("")}></div>
            <div className={styles.wrapper}>
                <QuickSettingsController />
            </div>
        </div>
    );
};

const QuickSettingsController = () => {
    const { currentOpenedQuickSetting, updateOpenedQuickSetting } = useStore_OpenedQuickSetting();

    switch (currentOpenedQuickSetting.data) {
        case "foreground":
            return <ForegroundContainer />;
        case "vrc_mic_mute_sync":
            return <VrcMicMuteSyncContainer />;
        case "overlay":
            return <Vr />;
        case "update_software":
            return <Updater />;
        default:
            return null;
    }
};

const ForegroundContainer = () => {
    const { t } = useI18n();
    const { currentForegroundStatus, toggleForeground } = useMainFunction();

    return (
        <SwitchBoxContainer
            label={t("main_page.foreground")}
            variable={currentForegroundStatus}
            toggleFunction={toggleForeground}
        />
    );
};