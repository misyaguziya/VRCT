import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import styles from "./Translation.module.scss";

import {
    useDeepLAuthKey,
} from "@logics_configs";

import {
    DeeplAuthKeyContainer,
} from "../_templates/Templates";

export const Translation = () => {
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