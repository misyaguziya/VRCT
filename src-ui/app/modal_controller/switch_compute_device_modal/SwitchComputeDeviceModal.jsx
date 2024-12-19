import styles from "./SwitchComputeDeviceModal.module.scss";
import { useTranslation } from "react-i18next";
import { useStore_OpenedQuickSetting } from "@store";
import { useComputeMode, useUpdateSoftware } from "@logics_common";
import { useIsSoftwareUpdating } from "@logics_common";

export const SwitchComputeDeviceModal = () => {
    const { t } = useTranslation();
    const { updateOpenedQuickSetting } = useStore_OpenedQuickSetting();
    const { updateSoftware, updateSoftware_CUDA } = useUpdateSoftware();
    const { updateIsSoftwareUpdating } = useIsSoftwareUpdating();
    const { currentComputeMode } = useComputeMode();


    const is_cpu_version = currentComputeMode.data === "cpu";

    const switch_compute_device_desc = is_cpu_version
    ? t("switch_compute_device_modal.switch_to_cuda_desc")
    : t("switch_compute_device_modal.switch_to_cpu_desc");

    const accept_button_label = is_cpu_version
    ? t("switch_compute_device_modal.switch_to_cuda_button") // to CUDA
    : t("switch_compute_device_modal.switch_to_cpu_button"); // to CPU


    const onClickUpdateSoftware = () => {
        updateIsSoftwareUpdating(true);
        if (is_cpu_version === true) {
            updateSoftware_CUDA();
        } else {
            updateSoftware();
        }
    };

    return (
        <div className={styles.container}>
            <p className={styles.label}>{switch_compute_device_desc}</p>
            <div className={styles.button_wrapper}>
                <button className={styles.deny_button} onClick={() => updateOpenedQuickSetting("")} >{t("switch_compute_device_modal.close_modal")}</button>
                <button className={styles.accept_button} onClick={onClickUpdateSoftware}>
                    {accept_button_label}
                    <p className={styles.restart_desc}>{t("switch_compute_device_modal.restart_desc")}</p>
                </button>
            </div>
        </div>
    );
};