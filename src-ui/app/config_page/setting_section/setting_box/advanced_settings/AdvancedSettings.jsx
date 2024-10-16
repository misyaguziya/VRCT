import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import styles from "./AdvancedSettings.module.scss";

import { useOpenFolder } from "@logics_common";
import {
    useOscIpAddress,
    useOscPort,
} from "@logics_configs";

import {
    ActionButtonContainer,
    EntryContainer,
} from "../_templates/Templates";


import OpenFolderSvg from "@images/open_folder.svg?react";

export const AdvancedSettings = () => {
    return (
        <>
            <OscIpAddressContainer />
            <OscPortContainer />
            <OpenConfigFolderContainer />
        </>
    );
};

const OscIpAddressContainer = () => {
    const { t } = useTranslation();
    const [ui_variable, setUiVariable] = useState("");
    const { currentOscIpAddress, setOscIpAddress } = useOscIpAddress();
    const onChangeFunction = (e) => {
        const value = e.currentTarget.value;
        if (value === "") {
            setUiVariable("");
        } else {
            setUiVariable(value);
            setOscIpAddress(value);
        }
    };

    useEffect(()=> {
        setUiVariable(currentOscIpAddress.data);
    }, [currentOscIpAddress]);

    return (
        <EntryContainer
            label={t("config_page.osc_ip_address.label")}
            ui_variable={ui_variable}
            onChange={onChangeFunction}
        />
    );
};

const OscPortContainer = () => {
    const { t } = useTranslation();
    const [ui_variable, setUiVariable] = useState("");
    const { currentOscPort, setOscPort } = useOscPort();
    const onChangeFunction = (e) => {
        const value = e.currentTarget.value;
        if (value === "") {
            setUiVariable("");
        } else {
            setUiVariable(value);
            setOscPort(value);
        }
    };

    useEffect(()=> {
        setUiVariable(currentOscPort.data);
    }, [currentOscPort]);

    return (
        <EntryContainer
            label={t("config_page.osc_port.label")}
            ui_variable={ui_variable}
            onChange={onChangeFunction}
        />
    );
};
const OpenConfigFolderContainer = () => {
    const { t } = useTranslation();
    const { openFolder_ConfigFile } = useOpenFolder();

    return (
        <>
            <ActionButtonContainer
                label={t("config_page.auto_export_message_logs.label")}
                desc={t("config_page.auto_export_message_logs.desc")}
                IconComponent={OpenFolderSvg}
                onclickFunction={openFolder_ConfigFile}
            />
        </>
    );
};