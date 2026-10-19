import { useI18n } from "@useI18n";

import {
    MultiDropdownMenuContainer,
} from "../../_templates/Templates";

import { buildComputeDeviceOptions } from "./computeDeviceOptions";

export const ComputeDevice = ({
    label,
    dropdownIdPrefix,
    currentDeviceList,
    currentSelectedDevice,
    setSelectedDevice,
    currentSelectedComputeType,
    setSelectedComputeType,
}) => {
    const { t } = useI18n();

    const { device_labels, selected_device_id, compute_type_labels } = buildComputeDeviceOptions(
        currentDeviceList.data, currentSelectedDevice.data, t
    );

    const selectFunction_ComputeDevice = (selected_data) => {
        const target_obj = currentDeviceList.data?.[selected_data.selected_id];
        if (target_obj) {
            setSelectedDevice(target_obj);
        }
    };

    const selectFunction_ComputeType = (selected_data) => {
        setSelectedComputeType(selected_data.selected_id);
    };

    const is_disabled_selector = currentSelectedDevice.state === "pending" || currentSelectedComputeType.state === "pending";

    return (
        <MultiDropdownMenuContainer
            setting_id={`${dropdownIdPrefix}_compute_device`}
            label={label}
            desc={t("config_page.common.compute_device.desc")}
            dropdown_settings={[
                {
                    dropdown_id: `${dropdownIdPrefix}_compute_device`,
                    secondary_label: t("config_page.common.compute_device.label_device"),
                    selected_id: selected_device_id,
                    list: device_labels,
                    selectFunction: selectFunction_ComputeDevice,
                    state: currentSelectedDevice.state,
                    is_disabled: is_disabled_selector,
                },
                {
                    dropdown_id: `${dropdownIdPrefix}_compute_type`,
                    secondary_label: t("config_page.common.compute_device.label_type"),
                    selected_id: currentSelectedComputeType.data,
                    list: compute_type_labels,
                    selectFunction: selectFunction_ComputeType,
                    state: currentSelectedComputeType.state,
                    is_disabled: is_disabled_selector,
                }
            ]}
        />
    );
};