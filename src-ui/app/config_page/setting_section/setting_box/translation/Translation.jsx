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
    DeeplAuthKeyContainer,

    useOnMouseLeaveDropdownMenu,
} from "../_templates/Templates";

import {
    DropdownMenu,
    LabelComponent,
} from "../_components/";

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
        pendingCTranslate2WeightType,
        downloadCTranslate2Weight,

        currentSelectedCTranslate2WeightType,
        setSelectedCTranslate2WeightType,
    } = useTranslation();

    const selectFunction = (id) => {
        setSelectedCTranslate2WeightType(id);
    };

    const downloadStartFunction = (id) => {
        pendingCTranslate2WeightType(id);
        downloadCTranslate2Weight(id);
    };

    const new_labels = [
        { id: "small", label: t("config_page.translation.ctranslate2_weight_type.small", {capacity: "418MB"}) },
        { id: "large", label: t("config_page.translation.ctranslate2_weight_type.large", {capacity: "1.2GB"}) },
    ];

    const c_translate2_weight_types = updateLabelsById(currentCTranslate2WeightTypeStatus.data, new_labels);

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
                options={c_translate2_weight_types}
                checked_variable={currentSelectedCTranslate2WeightType}
                selectFunction={selectFunction}
                downloadStartFunction={downloadStartFunction}
            />
        </>
    );
};

const TranslationComputeDevice_Box = () => {
    const { t } = useI18n();
    const {
        currentSelectableTranslationComputeDeviceList,
        currentSelectedTranslationComputeDevice,
        setSelectedTranslationComputeDevice,
        currentSelectedTranslationComputeType,
        setSelectedTranslationComputeType,
    } = useTranslation();
    const { onMouseLeaveFunction } = useOnMouseLeaveDropdownMenu();
    const { currentIsBreakPoint } = useStore_IsBreakPoint();

    const list_for_ui = transformDeviceArray(currentSelectableTranslationComputeDeviceList.data);

    const target_index = findKeyByDeviceValue(currentSelectableTranslationComputeDeviceList.data, currentSelectedTranslationComputeDevice.data);

    const selectable_compute_types = arrayToObject(currentSelectableTranslationComputeDeviceList.data[target_index].compute_types);


    const selectFunction_ComputeDevice = (selected_data) => {
        const target_obj = currentSelectableTranslationComputeDeviceList.data[selected_data.selected_id];
        setSelectedTranslationComputeDevice(target_obj);
    };

    const selectFunction_ComputeType = (selected_data) => {
        setSelectedTranslationComputeType(selected_data.selected_id);
    };

    const device_container_class = clsx(styles.device_container, {
        [styles.is_break_point]: currentIsBreakPoint.data,
    });

    const is_disabled_selector = currentSelectedTranslationComputeDevice.state === "pending" || currentSelectedTranslationComputeType.state === "pending";

    return (
        <div className={styles.mic_container}>
            <div className={device_container_class} onMouseLeave={onMouseLeaveFunction}>
                <LabelComponent label={t("config_page.translation.translation_compute_device.label")} />
                <div className={styles.device_contents}>

                    <div className={styles.device_dropdown_wrapper}>
                        <div className={styles.device_dropdown}>
                            <p className={styles.device_secondary_label}>{t("config_page.translation.translation_compute_device.label")}</p>
                            <DropdownMenu
                                dropdown_id="translation_compute_device"
                                selected_id={target_index}
                                list={list_for_ui}
                                selectFunction={selectFunction_ComputeDevice}
                                state={currentSelectedTranslationComputeDevice.state}
                                style={{ maxWidth: "20rem", minWidth: "10rem" }}
                                is_disabled={is_disabled_selector}
                            />
                        </div>

                        <div className={styles.device_dropdown}>
                            <p className={styles.device_secondary_label}>{t("config_page.translation.translation_compute_type.label")}</p>
                            <DropdownMenu
                                dropdown_id="translation_compute_type"
                                selected_id={currentSelectedTranslationComputeType.data}
                                list={selectable_compute_types}
                                selectFunction={selectFunction_ComputeType}
                                state={currentSelectedTranslationComputeType.state}
                                is_disabled={is_disabled_selector}
                            />
                        </div>
                    </div>
                </div>
            </div>
        </div>
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
        if (input_value === "") return deleteDeepLAuthKey();
        setDeepLAuthKey(input_value);
    };

    useEffect(() => {
        if (currentDeepLAuthKey.state === "pending") return;
        seInputValue(currentDeepLAuthKey.data);
    }, [currentDeepLAuthKey]);

    return (
        <>
            <DeeplAuthKeyContainer
                label={t("config_page.translation.deepl_auth_key.label")}
                desc={t(
                    "config_page.translation.deepl_auth_key.desc",
                    {translator: t("main_page.translator")}
                )}
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