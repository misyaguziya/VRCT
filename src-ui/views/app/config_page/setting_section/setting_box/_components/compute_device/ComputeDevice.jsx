import { useI18n } from "@useI18n";

import {
    MultiDropdownMenuContainer,
} from "../../_templates/Templates";

// Compute device helpers
const transformDeviceArray = (devices) => {
    const name_counts = Object.values(devices).reduce((counts, device) => {
        const name = device.device_name;
        counts[name] = (counts[name] || 0) + 1;
        return counts;
    }, {});

    const name_indices = {};
    const result = {};

    Object.entries(devices).forEach(([key, device]) => {
        const name = device.device_name;

        if (name_counts[name] > 1) {
            name_indices[name] = (name_indices[name] || 0);
            const value = `${name}:${name_indices[name]}`;
            name_indices[name]++;
            result[key] = value;
        } else {
            result[key] = name;
        }
    });

    return result;
};

const findKeyByDeviceValue = (devices, target_value) => {
    for (const [key, value] of Object.entries(devices)) {
        if (
            value.device === target_value.device &&
            value.device_index === target_value.device_index &&
            value.device_name === target_value.device_name
        ) {
            return parseInt(key);
        }
    }
    return null;
};

const DEFAULT_ORDER = [
    "auto",
    "int8",
    "int8_bfloat16",
    "int8_float16",
    "int8_float32",
    "bfloat16",
    "float16",
    "int16",
    "float32"
];

const sortComputeTypesArray = (compute_types_array = [], order) => {
    const src_set = new Set(compute_types_array);

    const from_order = order.filter((id) => src_set.has(id));

    const invalid_ids = compute_types_array.filter((id) => !order.includes(id));
    if (invalid_ids.length > 0) {
        console.error("[sortComputeTypesArray] Unsupported compute types ignored:", invalid_ids);
    }

    return from_order;
};

const buildSimpleLabels = (ordered_array = [], t) => {
    const n = ordered_array.length;
    if (n === 0) return {};

    const labels = {};

    ordered_array.forEach((id, idx) => {
        if (idx === 0 && id === "auto") {
            labels[id] = t("config_page.common.compute_device.type_template_auto");
            return;
        }

        if (idx === 1) {
            labels[id] = t(
                "config_page.common.compute_device.type_template_low",
                { type_name: id }
            );
            return;
        }

        if (idx === n - 1) {
            labels[id] = t(
                "config_page.common.compute_device.type_template_high",
                { type_name: id }
            );
            return;
        }

        labels[id] = id;
    });

    return labels;
};

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

    const list_for_ui = transformDeviceArray(currentDeviceList.data);

    const target_index = findKeyByDeviceValue(currentDeviceList.data, currentSelectedDevice.data);

    const computeTypesArray = currentDeviceList.data[target_index].compute_types;

    const ordered_array = sortComputeTypesArray(computeTypesArray, DEFAULT_ORDER);

    const new_compute_types_labels = buildSimpleLabels(ordered_array, t);

    const selectFunction_ComputeDevice = (selected_data) => {
        const target_obj = currentDeviceList.data[selected_data.selected_id];
        setSelectedDevice(target_obj);
    };

    const selectFunction_ComputeType = (selected_data) => {
        setSelectedComputeType(selected_data.selected_id);
    };

    const is_disabled_selector = currentSelectedDevice.state === "pending" || currentSelectedComputeType.state === "pending";

    return (
        <MultiDropdownMenuContainer
            label={label}
            desc={t("config_page.common.compute_device.desc")}
            dropdown_settings={[
                {
                    dropdown_id: `${dropdownIdPrefix}_compute_device`,
                    secondary_label: t("config_page.common.compute_device.label_device"),
                    selected_id: target_index,
                    list: list_for_ui,
                    selectFunction: selectFunction_ComputeDevice,
                    state: currentSelectedDevice.state,
                    is_disabled: is_disabled_selector,
                },
                {
                    dropdown_id: `${dropdownIdPrefix}_compute_type`,
                    secondary_label: t("config_page.common.compute_device.label_type"),
                    selected_id: currentSelectedComputeType.data,
                    list: new_compute_types_labels,
                    selectFunction: selectFunction_ComputeType,
                    state: currentSelectedComputeType.state,
                    is_disabled: is_disabled_selector,
                }
            ]}
        />
    );
};