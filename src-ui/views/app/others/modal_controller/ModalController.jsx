import styles from "./ModalController.module.scss";
import { useStore_OpenedQuickSetting } from "@store";
import { Vr, VrcMicMuteSyncContainer, Updater, Ocr } from "@setting_box";

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
        case "ocr":
            return <Ocr />;
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