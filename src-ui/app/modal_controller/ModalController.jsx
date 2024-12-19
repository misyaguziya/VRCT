import styles from "./ModalController.module.scss";
import { useStore_OpenedQuickSetting } from "@store";
import { Vr, VrcMicMuteSyncContainer } from "@setting_box";
import { UpdateModal } from "./update_modal/UpdateModal";
import { SwitchComputeDeviceModal } from "./switch_compute_device_modal/SwitchComputeDeviceModal";
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
        case "overlay":
            return <Vr />;
        case "vrc_mic_mute_sync":
            return <VrcMicMuteSyncContainer />;
        case "update_software":
            return <UpdateModal />;
        case "switch_compute_device":
            return <SwitchComputeDeviceModal />;
        default:
            return null;
    }
};