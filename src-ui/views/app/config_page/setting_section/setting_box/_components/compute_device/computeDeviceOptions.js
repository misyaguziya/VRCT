// PC と VR で同じデバイスの識別・表示名・対応精度を使う。
const transformDeviceArray = (devices = {}) => {
    if (!devices) return {};
    const name_counts = Object.values(devices).reduce((counts, device) => {
        const name = device?.device_name;
        if (name) {
            counts[name] = (counts[name] || 0) + 1;
        }
        return counts;
    }, {});

    const name_indices = {};
    const result = {};

    Object.entries(devices).forEach(([key, device]) => {
        const name = device?.device_name;
        if (!name) return;

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
    if (!devices || !target_value) return null;
    for (const [key, value] of Object.entries(devices)) {
        if (
            value &&
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

const sortComputeTypesArray = (compute_types_array = []) => {
    const src_set = new Set(compute_types_array || []);
    const from_order = DEFAULT_ORDER.filter((id) => src_set.has(id));

    const invalid_ids = (compute_types_array || []).filter((id) => !DEFAULT_ORDER.includes(id));
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

export const buildComputeDeviceOptions = (devices, selected_device, t) => {
    const selected_device_id = findKeyByDeviceValue(devices, selected_device);
    const compute_types = selected_device_id !== null
        ? devices[selected_device_id]?.compute_types ?? []
        : [];

    return {
        device_labels: transformDeviceArray(devices),
        selected_device_id,
        compute_type_labels: buildSimpleLabels(sortComputeTypesArray(compute_types), t),
    };
};
