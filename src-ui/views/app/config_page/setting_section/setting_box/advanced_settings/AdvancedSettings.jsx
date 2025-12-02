import { useEffect, useState } from "react";
import { useI18n } from "@useI18n";
import styles from "./AdvancedSettings.module.scss";

import { useOpenFolder } from "@logics_common";
import {
    useAdvancedSettings,
} from "@logics_configs";

import {
    CheckboxContainer,
    ActionButtonContainer,
    EntryWithSaveButtonContainer,
} from "../_templates/Templates";

import {
    SectionLabelComponent,
} from "../_components";

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
                <ZLUDAInfoContainer />
            </div>
            <WebsocketContainer />
        </div>
    );
};

const OscIpAddressContainer = () => {
    const { t } = useI18n();
    const { currentOscIpAddress, setOscIpAddress } = useAdvancedSettings();
    const [input_value, setInputValue] = useState(currentOscIpAddress.data);

    const onChangeFunction = (value) => {
        setInputValue(value);
    };

    const saveFunction = () => {
        setOscIpAddress(input_value);
    };

    useEffect(()=> {
        if (currentOscIpAddress.state === "pending") return;
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
    const { t } = useI18n();
    const { currentOscPort, setOscPort } = useAdvancedSettings();
    const [input_value, setInputValue] = useState(currentOscPort.data);

    const onChangeFunction = (value) => {
        value = value.replace(/[^0-9]/g, "");
        setInputValue(value);
    };

    const saveFunction = () => {
        setOscPort(input_value);
    };

    useEffect(()=> {
        if (currentOscPort.state === "pending") return;
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
    const { t } = useI18n();
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
    const { t } = useI18n();
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


const WebsocketContainer = () => {
    return (
        <div>
            <SectionLabelComponent label="WebSocket" />
            <EnableWebsocketContainer />
            <WebsocketHostContainer />
            <WebsocketPortContainer />
        </div>
    );
};

const EnableWebsocketContainer = () => {
    const { t } = useI18n();
    const { currentEnableWebsocket, toggleEnableWebsocket } = useAdvancedSettings();

    return (
        <CheckboxContainer
            label={t("config_page.advanced_settings.enable_websocket.label")}
            variable={currentEnableWebsocket}
            toggleFunction={toggleEnableWebsocket}
        />
    );
};

const WebsocketHostContainer = () => {
    const { t } = useI18n();
    const { currentWebsocketHost, setWebsocketHost } = useAdvancedSettings();
    const [input_value, setInputValue] = useState(currentWebsocketHost.data);

    const onChangeFunction = (value) => {
        setInputValue(value);
    };

    const saveFunction = () => {
        setWebsocketHost(input_value);
    };

    useEffect(()=> {
        if (currentWebsocketHost.state === "pending") return;
        setInputValue(currentWebsocketHost.data);
    }, [currentWebsocketHost]);

    return (
        <EntryWithSaveButtonContainer
            label={t("config_page.advanced_settings.websocket_host.label")}
            variable={input_value}
            saveFunction={saveFunction}
            onChangeFunction={onChangeFunction}
            state={currentWebsocketHost.state}
            width="14rem"
        />
    );
};

const WebsocketPortContainer = () => {
    const { t } = useI18n();
    const { currentWebsocketPort, setWebsocketPort } = useAdvancedSettings();
    const [input_value, setInputValue] = useState(currentWebsocketPort.data);

    const onChangeFunction = (value) => {
        value = value.replace(/[^0-9]/g, "");
        setInputValue(value);
    };

    const saveFunction = () => {
        setWebsocketPort(input_value);
    };

    useEffect(()=> {
        if (currentWebsocketPort.state === "pending") return;
        setInputValue(currentWebsocketPort.data);
    }, [currentWebsocketPort]);

    return (
        <EntryWithSaveButtonContainer
            label={t("config_page.advanced_settings.websocket_port.label")}
            variable={input_value}
            saveFunction={saveFunction}
            onChangeFunction={onChangeFunction}
            state={currentWebsocketPort.state}
            width="10rem"
        />
    );
};

// Import for Python communication
import { useStdoutToPython } from "@useStdoutToPython";

// ZLUDA Information Display Component
const ZLUDAInfoContainer = () => {
    const { t } = useI18n();
    const { asyncStdoutToPython } = useStdoutToPython();
    const [zludaInfo, setZludaInfo] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchZLUDAInfo = async () => {
            try {
                // Call Python backend using the standard IPC method
                const response = await asyncStdoutToPython("/get/data/zluda_installation_info");
                if (response && response.status === 200) {
                    setZludaInfo(response.result);
                }
            } catch (error) {
                console.error("Failed to fetch ZLUDA info:", error);
            } finally {
                setLoading(false);
            }
        };

        fetchZLUDAInfo();
    }, [asyncStdoutToPython]);

    if (loading) {
        return (
            <div className={styles.zludaInfoContainer}>
                <div className={styles.zludaLabel}>
                    {t("config_page.advanced_settings.zluda_info.label")}
                </div>
                <div className={styles.zludaLoading}>Loading...</div>
            </div>
        );
    }

    if (!zludaInfo) {
        return null;
    }

    const openHelpLink = () => {
        if (zludaInfo.help_url) {
            window.open(zludaInfo.help_url, "_blank");
        }
    };

    return (
        <div className={styles.zludaInfoContainer}>
            <div className={styles.zludaHeader}>
                <span className={styles.zludaLabel}>
                    {t("config_page.advanced_settings.zluda_info.label")}
                </span>
            </div>

            <div className={styles.zludaContent}>
                {/* Installation Status */}
                <div className={styles.zludaStatusRow}>
                    <span className={styles.zludaStatusLabel}>Status:</span>
                    <span className={zludaInfo.installed ? styles.zludaStatusInstalled : styles.zludaStatusNotInstalled}>
                        {zludaInfo.installed 
                            ? "✓ " + t("config_page.advanced_settings.zluda_info.status_installed", { path: zludaInfo.path })
                            : "✗ " + t("config_page.advanced_settings.zluda_info.status_not_installed")
                        }
                    </span>
                </div>

                {/* Version */}
                {zludaInfo.installed && (
                    <div className={styles.zludaInfoRow}>
                        {t("config_page.advanced_settings.zluda_info.version", { version: zludaInfo.version })}
                    </div>
                )}

                {/* AMD GPU Count */}
                {zludaInfo.installed && (
                    <div className={styles.zludaInfoRow}>
                        {t("config_page.advanced_settings.zluda_info.devices", { count: zludaInfo.devices_available })}
                    </div>
                )}

                {/* Help Text */}
                <div className={styles.zludaHelpText}>
                    {t("config_page.advanced_settings.zluda_info.help_text")}
                </div>

                {/* Manual Install Instructions */}
                {!zludaInfo.installed && (
                    <div className={styles.zludaManualInstall}>
                        ⓘ {t("config_page.advanced_settings.zluda_info.manual_install")}
                    </div>
                )}

                {/* Help Link Button */}
                <button 
                    className={styles.zludaHelpButton}
                    onClick={openHelpLink}
                >
                    🔗 {t("config_page.advanced_settings.zluda_info.help_link")}
                </button>
            </div>
        </div>
    );
};
