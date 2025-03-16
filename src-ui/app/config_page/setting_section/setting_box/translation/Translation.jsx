import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import styles from "./Translation.module.scss";
import { updateLabelsById } from "@utils";

import {
    useDeepLAuthKey,
    useCTranslate2WeightTypeStatus,
    useSelectedCTranslate2WeightType,
    useSelectedCTranslate2ComputeDevice,
    useSelectableCTranslate2ComputeDeviceList,
} from "@logics_configs";

import {
    DownloadModelsContainer,
    DeeplAuthKeyContainer,
    DropdownMenuContainer,
    ComputeDeviceContainer,
} from "../_templates/Templates";

export const Translation = () => {
    return (
        <>
            <CTranslate2WeightType_Box />
            <CTranslation2ComputeDevice_Box />
            <DeeplAuthKey_Box />
        </>
    );
};

const CTranslate2WeightType_Box = () => {
    const { t } = useTranslation();
    const {
        currentCTranslate2WeightTypeStatus,
        pendingCTranslate2WeightType,
        downloadCTranslate2Weight,
    } = useCTranslate2WeightTypeStatus();
    const { currentSelectedCTranslate2WeightType, setSelectedCTranslate2WeightType } = useSelectedCTranslate2WeightType();

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
                    {translator: t("main_page.translator")}
                )}
                name="ctransalte2_weight_type"
                options={c_translate2_weight_types}
                checked_variable={currentSelectedCTranslate2WeightType}
                selectFunction={selectFunction}
                downloadStartFunction={downloadStartFunction}
            />
        </>
    );
};

// Duplicate
import { useComputeMode } from "@logics_common";
const CTranslation2ComputeDevice_Box = () => {
    const { t } = useTranslation();
    const { currentSelectedCTranslate2ComputeDevice, setSelectedCTranslate2ComputeDevice } = useSelectedCTranslate2ComputeDevice();
    const { currentSelectableCTranslate2ComputeDeviceList } = useSelectableCTranslate2ComputeDeviceList();

    const selectFunction = (selected_data) => {
        const target_obj = currentSelectableCTranslate2ComputeDeviceList.data[selected_data.selected_id];
        setSelectedCTranslate2ComputeDevice(target_obj);
    };

    const list_for_ui = transformDeviceArray(currentSelectableCTranslate2ComputeDeviceList.data);

    const target_index = findKeyByDeviceValue(currentSelectableCTranslate2ComputeDeviceList.data, currentSelectedCTranslate2ComputeDevice.data);


    const { currentComputeMode } = useComputeMode();
    const ctranslate2_compute_device_label = t("config_page.translation.ctranslate2_compute_device.label", {
        ctranslate2: "Ctranslate2"
    });
    if (currentComputeMode.data === "cpu") {
        return (
            <ComputeDeviceContainer
                label={ctranslate2_compute_device_label}
                selected_id={target_index}
                list={list_for_ui}
                selectFunction={selectFunction}
                state={currentSelectedCTranslate2ComputeDevice.state}
            />
        )
    }

    return (
        <DropdownMenuContainer
            dropdown_id="ctranslate2_compute_device"
            label={ctranslate2_compute_device_label}
            selected_id={target_index}
            list={list_for_ui}
            selectFunction={selectFunction}
            state={currentSelectedCTranslate2ComputeDevice.state}
        />
    );
};

const DeeplAuthKey_Box = () => {
    const { t } = useTranslation();
    const { currentDeepLAuthKey, setDeepLAuthKey, deleteDeepLAuthKey } = useDeepLAuthKey();
    const [input_value, seInputValue] = useState(currentDeepLAuthKey.data);

    const onChangeFunction = (value) => {
        seInputValue(value);
    };

    const saveFunction = () => {
        if (input_value === "") return deleteDeepLAuthKey();
        setDeepLAuthKey(input_value);
    };

    useEffect(() => {
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