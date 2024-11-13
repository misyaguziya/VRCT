import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import styles from "./Translation.module.scss";
import { updateLabelsById } from "@utils";

import {
    useDeepLAuthKey,
    useCTranslate2WeightTypeStatus,
    useSelectedCTranslate2WeightType,
} from "@logics_configs";

import {
    DownloadModelsContainer,
    DeeplAuthKeyContainer,
} from "../_templates/Templates";

export const Translation = () => {
    return (
        <>
            <CTranslate2WeightType_Box />
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
        { id: "small", label: t("config_page.ctranslate2_weight_type.small", {capacity: "418MB"}) },
        { id: "large", label: t("config_page.ctranslate2_weight_type.large", {capacity: "1.2GB"}) },
    ];

    const c_translate2_weight_types = updateLabelsById(currentCTranslate2WeightTypeStatus.data, new_labels);

    return (
        <>
            <DownloadModelsContainer
                label={t("config_page.ctranslate2_weight_type.label")}
                desc={t(
                    "config_page.ctranslate2_weight_type.desc",
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

const DeeplAuthKey_Box = () => {
    const [input_value, seInputValue] = useState("");
    const { t } = useTranslation();
    const { currentDeepLAuthKey, setDeepLAuthKey, deleteDeepLAuthKey } = useDeepLAuthKey();

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
                label={t("config_page.deepl_auth_key.label")}
                desc={t(
                    "config_page.deepl_auth_key.desc",
                    {translator: t("main_page.translator")}
                )}
                variable={input_value}
                onChangeFunction={onChangeFunction}
                saveFunction={saveFunction}
            />
        </>
    );
};