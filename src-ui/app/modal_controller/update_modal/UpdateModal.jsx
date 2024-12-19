import styles from "./UpdateModal.module.scss";
import { useTranslation } from "react-i18next";
import { useStore_OpenedQuickSetting } from "@store";
import { useComputeMode, useUpdateSoftware } from "@logics_common";
import { useIsSoftwareUpdating } from "@logics_common";

export const UpdateModal = () => {
    const { t } = useTranslation();
    const { updateOpenedQuickSetting } = useStore_OpenedQuickSetting();
    const { updateSoftware } = useUpdateSoftware();
    const { updateIsSoftwareUpdating } = useIsSoftwareUpdating();
    const { currentComputeMode } = useComputeMode();

    const is_cpu_version = currentComputeMode.data === "cpu";

    const onClickUpdateSoftware = () => {
        updateIsSoftwareUpdating(true);
        // Update to the same as now compute device
        if (is_cpu_version === true) {
            updateSoftware();
        } else {
            updateSoftware_CUDA();
        }
    };

    return (
        <div className={styles.container}>
            <p className={styles.label}>{t("update_modal.update_software_desc")}</p>
            <div className={styles.button_wrapper}>
                <button className={styles.deny_button} onClick={() => updateOpenedQuickSetting("")} >{t("update_modal.deny_update_software")}</button>
                <button className={styles.accept_button} onClick={onClickUpdateSoftware}>{t("update_modal.accept_update_software")}</button>
            </div>
        </div>
    );
};