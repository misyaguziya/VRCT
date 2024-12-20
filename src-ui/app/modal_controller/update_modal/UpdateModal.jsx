import styles from "./UpdateModal.module.scss";
import { useTranslation } from "react-i18next";
import { useStore_OpenedQuickSetting } from "@store";
import { useComputeMode, useUpdateSoftware } from "@logics_common";
import { useIsSoftwareUpdating, useIsSoftwareUpdateAvailable } from "@logics_common";
import clsx from "clsx";

export const UpdateModal = () => {
    const { t } = useTranslation();
    const { updateOpenedQuickSetting } = useStore_OpenedQuickSetting();
    const { updateSoftware, updateSoftware_CUDA } = useUpdateSoftware();
    const { updateIsSoftwareUpdating } = useIsSoftwareUpdating();
    const { currentComputeMode } = useComputeMode();
    const { currentIsSoftwareUpdateAvailable } = useIsSoftwareUpdateAvailable();

    const is_latest_version_already = currentIsSoftwareUpdateAvailable.data === false;
    const is_cpu_version = currentComputeMode.data === "cpu";

    const onClickUpdateSoftware = () => {
        updateIsSoftwareUpdating(true);
        updateSoftware();
    }
    const onClickUpdateSoftware_CUDA = () => {
        updateIsSoftwareUpdating(true);
        updateSoftware_CUDA();
    }

    const cpu_accept_button_class_name = clsx(styles.accept_button, {
        [styles.current_compute_version]: is_cpu_version,
        [styles.is_latest_version_already]: is_latest_version_already,
    })
    const cuda_accept_button_class_name = clsx(styles.accept_button, {
        [styles.current_compute_version]: !is_cpu_version,
        [styles.is_latest_version_already]: is_latest_version_already,
    })

    return (
        <div className={styles.container}>
            <div className={styles.wrapper}>
                <div className={styles.update_section}>
                    <div className={styles.cpu_section}>
                        <div className={styles.button_wrapper}>
                            <button className={cpu_accept_button_class_name} onClick={onClickUpdateSoftware}>CPU</button>
                            {is_cpu_version ? <CurrentVersionLabel is_latest_version_already={is_latest_version_already} /> : null}
                        </div>
                        <div>
                            <VersionDescComponent desc={t("update_modal.cpu_desc")} />
                        </div>
                    </div>
                    <div className={styles.cuda_section}>
                        <div className={styles.button_wrapper}>
                            <button className={cuda_accept_button_class_name} onClick={onClickUpdateSoftware_CUDA}>CUDA (GPU)</button>
                            {!is_cpu_version ? <CurrentVersionLabel is_latest_version_already={is_latest_version_already} is_cuda={true}/> : null}
                        </div>
                        <div>
                            <VersionDescComponent desc={t("update_modal.cuda_desc")} />
                            <VersionDescComponent desc={t("update_modal.cuda_disk_space_desc", {size: "5GB"})} />
                        </div>
                    </div>

                    <p className={styles.update_desc}>{t("update_modal.download_latest_and_restart")}</p>
                </div>
                <div className={styles.button_wrapper}>
                    <button className={styles.deny_button} onClick={() => updateOpenedQuickSetting("")} >{t("update_modal.close_modal")}</button>
                </div>
            </div>
        </div>
    );
};

const VersionDescComponent = (props) => {
    return (
        <div className={styles.version_desc_wrapper}>
            <div className={styles.version_desc_point}></div>
            <p className={styles.version_desc}>{props.desc}</p>
        </div>
    );
};

const CurrentVersionLabel = (props) => {
    const { t } = useTranslation();

    if (props.is_latest_version_already) {
        return <p className={clsx(styles.current_version_label, {[styles.is_cuda]: props.is_cuda})}>{t("update_modal.is_latest_version_already")}</p>;
    }
    return <p className={clsx(styles.current_version_label, {[styles.is_cuda]: props.is_cuda})}>{t("update_modal.is_current_compute_device")}</p>;
};