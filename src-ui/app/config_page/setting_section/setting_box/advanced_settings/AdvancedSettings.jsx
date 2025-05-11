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
    EntryWithSaveButtonContainer,
} from "../_templates/Templates";

import OpenFolderSvg from "@images/open_folder.svg?react";
import HelpSvg from "@images/help.svg?react";

export const AdvancedSettings = () => {
    return (
        <div className={styles.container}>
            <div>
                <OscIpAddressContainer />
                <OscPortContainer />
                <OpenConfigFolderContainer />
                <OpenSwitchComputeDeviceModalContainer />
            </div>
        </div>
    );
};

const OscIpAddressContainer = () => {
    const { t } = useTranslation();
    const { currentOscIpAddress, setOscIpAddress } = useOscIpAddress();
    const [input_value, setInputValue] = useState(currentOscIpAddress.data);

    const onChangeFunction = (value) => {
        setInputValue(value);
    };

    const saveFunction = () => {
        setOscIpAddress(input_value);
    };

    useEffect(()=> {
        setInputValue(currentOscIpAddress.data);
    }, [currentOscIpAddress]);

    return (
        <EntryWithSaveButtonContainer
            label={t("config_page.advanced_settings.osc_ip_address.label")}
            variable={input_value}
            saveFunction={saveFunction}
            onChangeFunction={onChangeFunction}
            state={currentOscIpAddress.state}
            width="14rem"
        />
    );
};

const OscPortContainer = () => {
    const { t } = useTranslation();
    const { currentOscPort, setOscPort } = useOscPort();
    const [input_value, setInputValue] = useState(currentOscPort.data);

    const onChangeFunction = (value) => {
        value = value.replace(/[^0-9]/g, "");
        setInputValue(value);
    };

    const saveFunction = () => {
        setOscPort(input_value);
    };

    useEffect(()=> {
        setInputValue(currentOscPort.data);
    }, [currentOscPort]);

    return (
        <EntryWithSaveButtonContainer
            label={t("config_page.advanced_settings.osc_port.label")}
            variable={input_value}
            saveFunction={saveFunction}
            onChangeFunction={onChangeFunction}
            state={currentOscPort.state}
            width="10rem"
        />
    );
};
const OpenConfigFolderContainer = () => {
    const { t } = useTranslation();
    const { openFolder_ConfigFile } = useOpenFolder();

    return (
        <>
            <ActionButtonContainer
                label={t("config_page.advanced_settings.open_config_filepath.label")}
                IconComponent={OpenFolderSvg}
                onclickFunction={openFolder_ConfigFile}
            />
        </>
    );
};

// Duplicate
import { useStore_OpenedQuickSetting } from "@store";
const OpenSwitchComputeDeviceModalContainer = () => {
    const { t } = useTranslation();
    const { updateOpenedQuickSetting } = useStore_OpenedQuickSetting();
    const onClickFunction = () => {
        updateOpenedQuickSetting("update_software");
    };

    return (
        <>
            <ActionButtonContainer
                label={t("config_page.advanced_settings.switch_compute_device.label")}
                IconComponent={HelpSvg}
                onclickFunction={onClickFunction}
            />
        </>
    );
};