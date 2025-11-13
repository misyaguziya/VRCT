import { useEffect, useState } from "react";
import { useI18n } from "@useI18n";
import styles from "./Translation.module.scss";
import { updateLabelsById, arrayToObject } from "@utils";
import { useStore_IsBreakPoint } from "@store";

import {
    useTranslation,
} from "@logics_configs";

import {
    DownloadModelsContainer,
    AuthKeyContainer,
    MultiDropdownMenuContainer,

    useOnMouseLeaveDropdownMenu,
} from "../_templates/Templates";

import {
    DropdownMenu,
    MultiDropdownMenu,
    LabelComponent,
} from "../_components";

import { deepl_auth_key_url } from "@ui_configs";

export const Translation = () => {
    return (
        <>
            <CTranslate2WeightType_Box />
            <TranslationComputeDevice_Box />
            <DeeplAuthKey_Box />
        </>
    );
};

const CTranslate2WeightType_Box = () => {
    const { t } = useI18n();
    const {
        currentCTranslate2WeightTypeStatus,
        pendingCTranslate2WeightTypeStatus,
        downloadCTranslate2WeightTypeStatus,

        currentSelectedCTranslate2WeightType,
        setSelectedCTranslate2WeightType,
    } = useTranslation();

    const selectFunction = (id) => {
        setSelectedCTranslate2WeightType(id);
    };

    const downloadStartFunction = (id) => {
        pendingCTranslate2WeightTypeStatus(id);
        downloadCTranslate2WeightTypeStatus(id);
    };


    const c_translate2_weight_types_object = currentCTranslate2WeightTypeStatus.data.map(item => {
        return {
            ...item,
            label: `${item.id} (${item.capacity})`,
        };
    });


    return (
        <>
            <DownloadModelsContainer
                label={t(
                    "config_page.translation.ctranslate2_weight_type.label",
                    {ctranslate2: "CTranslate2"}
                )}
                desc={t(
                    "config_page.translation.ctranslate2_weight_type.desc",
                    {ctranslate2: "CTranslate2"}
                )}
                name="ctranslate2_weight_type"
                options={c_translate2_weight_types_object}
                checked_variable={currentSelectedCTranslate2WeightType}
                selectFunction={selectFunction}
                downloadStartFunction={downloadStartFunction}
            />
        </>
    );
};
// Duplicate
const TranslationComputeDevice_Box = () => {
    const { t } = useI18n();
    const {
        currentSelectableTranslationComputeDeviceList,
        currentSelectedTranslationComputeDevice,
        setSelectedTranslationComputeDevice,
        currentSelectedTranslationComputeType,
        setSelectedTranslationComputeType,
    } = useTranslation();

    const list_for_ui = transformDeviceArray(currentSelectableTranslationComputeDeviceList.data);

    const target_index = findKeyByDeviceValue(currentSelectableTranslationComputeDeviceList.data, currentSelectedTranslationComputeDevice.data);

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


    const buildSimpleLabels = (ordered_array = []) => {
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


    const computeTypesArray = currentSelectableTranslationComputeDeviceList.data[target_index].compute_types;

    const ordered_array = sortComputeTypesArray(computeTypesArray, DEFAULT_ORDER);

    const new_compute_types_labels = buildSimpleLabels(ordered_array);

    const selectFunction_ComputeDevice = (selected_data) => {
        const target_obj = currentSelectableTranslationComputeDeviceList.data[selected_data.selected_id];
        setSelectedTranslationComputeDevice(target_obj);
    };

    const selectFunction_ComputeType = (selected_data) => {
        setSelectedTranslationComputeType(selected_data.selected_id);
    };

    const is_disabled_selector = currentSelectedTranslationComputeDevice.state === "pending" || currentSelectedTranslationComputeType.state === "pending";

    return (
        <MultiDropdownMenuContainer
            label={t("config_page.translation.translation_compute_device.label")}
            desc={t("config_page.common.compute_device.desc")}
            dropdown_settings={[
                {
                    dropdown_id: "translation_compute_device",
                    secondary_label: t("config_page.common.compute_device.label_device"),
                    selected_id: target_index,
                    list: list_for_ui,
                    selectFunction: selectFunction_ComputeDevice,
                    state: currentSelectedTranslationComputeDevice.state,
                    style: { maxWidth: "20rem", minWidth: "10rem" },
                    is_disabled: is_disabled_selector,
                },
                {
                    dropdown_id: "translation_compute_type",
                    secondary_label: t("config_page.common.compute_device.label_type"),
                    selected_id: currentSelectedTranslationComputeType.data,
                    list: new_compute_types_labels,
                    selectFunction: selectFunction_ComputeType,
                    state: currentSelectedTranslationComputeType.state,
                    is_disabled: is_disabled_selector,
                }
            ]}
        />
    );
};

const DeeplAuthKey_Box = () => {
    const { t } = useI18n();
    const { currentDeepLAuthKey, setDeepLAuthKey, deleteDeepLAuthKey } = useTranslation();
    const [input_value, seInputValue] = useState(currentDeepLAuthKey.data);

    const onChangeFunction = (value) => {
        seInputValue(value);
    };

    const saveFunction = () => {
        if (input_value === "" || input_value === null) {
            return deleteDeepLAuthKey();
        };
        setDeepLAuthKey(input_value);
    };

    useEffect(() => {
        if (currentDeepLAuthKey.state === "pending") return;
        seInputValue(currentDeepLAuthKey.data);
    }, [currentDeepLAuthKey]);

    return (
        <>
            <AuthKeyContainer
                label={t("config_page.translation.deepl_auth_key.label")}
                desc={t(
                    "config_page.translation.deepl_auth_key.desc",
                    {translator: t("main_page.translator")}
                )}
                webpage_url={deepl_auth_key_url}
                open_webpage_label={t("config_page.translation.deepl_auth_key.open_auth_key_webpage")}
                variable={input_value}
                state={currentDeepLAuthKey.state}
                onChangeFunction={onChangeFunction}
                saveFunction={saveFunction}
            />
        </>
    );
};

// Duplicate
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