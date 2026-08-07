import { useI18n } from "@useI18n";
import styles from "./ComputeDevice.module.scss";

import { useComputeMode } from "@logics_common";
import { useStore_OpenedQuickSetting } from "@store";

import { ActionButtonContainer } from "../_templates/Templates";
import { SectionLabelComponent } from "../_components";

import RefreshSvg from "@images/refresh.svg?react";

export const ComputeDevice = () => {
    const { t } = useI18n();

    return (
        <div className={styles.container}>
            <SectionLabelComponent label={t("config_page.compute_device.section_label")} />
            <SwitchComputeDeviceContainer />
        </div>
    );
};

const SwitchComputeDeviceContainer = () => {
    const { t } = useI18n();
    const { updateOpenedQuickSetting } = useStore_OpenedQuickSetting();
    const { currentComputeMode } = useComputeMode();

    const onClickFunction = () => {
        updateOpenedQuickSetting("update_software");
    };

    const is_cuda = currentComputeMode.data === "cuda";
    const current_version_label = t(is_cuda
        ? "config_page.compute_device.desc_current_cuda"
        : "config_page.compute_device.desc_current_cpu");

    return (
        <ActionButtonContainer
            label={t("config_page.compute_device.label")}
            desc={current_version_label}
            IconComponent={RefreshSvg}
            onclickFunction={onClickFunction}
        />
    );
};
