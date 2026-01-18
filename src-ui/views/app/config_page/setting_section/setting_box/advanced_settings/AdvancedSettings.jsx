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
    ColorEntryWithSaveButtonContainer,
} from "../_templates/Templates";

import {
    SectionLabelComponent,
} from "../_components";

import OpenFolderSvg from "@images/open_folder.svg?react";
import HelpSvg from "@images/help.svg?react";
import CopySvg from "@images/copy.svg?react";

export const AdvancedSettings = () => {
    return (
        <div className={styles.container}>
            <div>
                <OscIpAddressContainer />
                <OscPortContainer />
                <OpenConfigFolderContainer />
                <OpenSwitchComputeDeviceModalContainer />
            </div>
            <WebsocketContainer />
            <ObsBrowserSourceContainer />
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
    const { currentEnableWebsocket, toggleEnableWebsocket, currentEnableObsBrowserSource } = useAdvancedSettings();

    const is_locked = currentEnableObsBrowserSource.data === true;
    const add_warnings = [];
    if (is_locked) {
        add_warnings.push({ label: t("config_page.advanced_settings.enable_websocket.locked_by_obs_browser_source") });
    }

    return (
        <CheckboxContainer
            label={t("config_page.advanced_settings.enable_websocket.label")}
            variable={currentEnableWebsocket}
            toggleFunction={toggleEnableWebsocket}
            is_available={!is_locked}
            add_warnings={add_warnings}
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


const ObsBrowserSourceContainer = () => {
    const { t } = useI18n();

    return (
        <div>
            <SectionLabelComponent label={t("config_page.advanced_settings.obs_browser_source.section_label")} />
            <EnableObsBrowserSourceContainer />
            <ObsBrowserSourceUrlContainer />
            <ObsBrowserSourcePortContainer />
            <ObsBrowserSourceMaxMessagesContainer />
            <ObsBrowserSourceDisplayDurationContainer />
            <ObsBrowserSourceFadeoutDurationContainer />
            <ObsBrowserSourceFontSizeContainer />
            <ObsBrowserSourceFontColorContainer />
            <ObsBrowserSourceFontOutlineThicknessContainer />
            <ObsBrowserSourceFontOutlineColorContainer />
        </div>
    );
};

const EnableObsBrowserSourceContainer = () => {
    const { t } = useI18n();
    const { currentEnableObsBrowserSource, toggleEnableObsBrowserSource } = useAdvancedSettings();

    return (
        <CheckboxContainer
            label={t("config_page.advanced_settings.enable_obs_browser_source.label")}
            desc={t("config_page.advanced_settings.enable_obs_browser_source.desc")}
            variable={currentEnableObsBrowserSource}
            toggleFunction={toggleEnableObsBrowserSource}
        />
    );
};

const ObsBrowserSourceUrlContainer = () => {
    const { t } = useI18n();
    const { currentWebsocketHost, currentObsBrowserSourcePort } = useAdvancedSettings();

    const host = currentWebsocketHost.data === "0.0.0.0" ? "127.0.0.1" : currentWebsocketHost.data;
    const url = `http://${host}:${currentObsBrowserSourcePort.data}/obs`;

    const copyUrlToClipboard = async () => {
        try {
            await navigator.clipboard.writeText(url);
        } catch (e) {
            // ignore
        }
    };

    return (
        <ActionButtonContainer
            label={t("config_page.advanced_settings.obs_browser_source_url.label")}
            desc={url}
            IconComponent={CopySvg}
            onclickFunction={copyUrlToClipboard}
        />
    );
};

const ObsBrowserSourcePortContainer = () => {
    const { t } = useI18n();
    const { currentObsBrowserSourcePort, setObsBrowserSourcePort } = useAdvancedSettings();
    const [input_value, setInputValue] = useState(`${currentObsBrowserSourcePort.data}`);

    const onChangeFunction = (value) => {
        value = value.replace(/[^0-9]/g, "");
        setInputValue(value);
    };

    const saveFunction = () => {
        setObsBrowserSourcePort(input_value);
    };

    useEffect(() => {
        if (currentObsBrowserSourcePort.state === "pending") return;
        setInputValue(`${currentObsBrowserSourcePort.data}`);
    }, [currentObsBrowserSourcePort]);

    return (
        <EntryWithSaveButtonContainer
            label={t("config_page.advanced_settings.obs_browser_source_port.label")}
            variable={input_value}
            saveFunction={saveFunction}
            onChangeFunction={onChangeFunction}
            state={currentObsBrowserSourcePort.state}
            width="10rem"
        />
    );
};

const ObsBrowserSourceMaxMessagesContainer = () => {
    const { t } = useI18n();
    const { currentObsBrowserSourceMaxMessages, setObsBrowserSourceMaxMessages } = useAdvancedSettings();
    const [input_value, setInputValue] = useState(`${currentObsBrowserSourceMaxMessages.data}`);

    const onChangeFunction = (value) => {
        value = value.replace(/[^0-9]/g, "");
        setInputValue(value);
    };

    const saveFunction = () => {
        setObsBrowserSourceMaxMessages(input_value);
    };

    useEffect(() => {
        if (currentObsBrowserSourceMaxMessages.state === "pending") return;
        setInputValue(`${currentObsBrowserSourceMaxMessages.data}`);
    }, [currentObsBrowserSourceMaxMessages]);

    return (
        <EntryWithSaveButtonContainer
            label={t("config_page.advanced_settings.obs_browser_source_max_messages.label")}
            variable={input_value}
            saveFunction={saveFunction}
            onChangeFunction={onChangeFunction}
            state={currentObsBrowserSourceMaxMessages.state}
            width="10rem"
        />
    );
};

const ObsBrowserSourceDisplayDurationContainer = () => {
    const { t } = useI18n();
    const { currentObsBrowserSourceDisplayDuration, setObsBrowserSourceDisplayDuration } = useAdvancedSettings();
    const [input_value, setInputValue] = useState(`${currentObsBrowserSourceDisplayDuration.data}`);

    const onChangeFunction = (value) => {
        value = value.replace(/[^0-9]/g, "");
        setInputValue(value);
    };

    const saveFunction = () => {
        setObsBrowserSourceDisplayDuration(input_value);
    };

    useEffect(() => {
        if (currentObsBrowserSourceDisplayDuration.state === "pending") return;
        setInputValue(`${currentObsBrowserSourceDisplayDuration.data}`);
    }, [currentObsBrowserSourceDisplayDuration]);

    return (
        <EntryWithSaveButtonContainer
            label={t("config_page.advanced_settings.obs_browser_source_display_duration.label")}
            variable={input_value}
            saveFunction={saveFunction}
            onChangeFunction={onChangeFunction}
            state={currentObsBrowserSourceDisplayDuration.state}
            width="10rem"
        />
    );
};

const ObsBrowserSourceFadeoutDurationContainer = () => {
    const { t } = useI18n();
    const { currentObsBrowserSourceFadeoutDuration, setObsBrowserSourceFadeoutDuration } = useAdvancedSettings();
    const [input_value, setInputValue] = useState(`${currentObsBrowserSourceFadeoutDuration.data}`);

    const onChangeFunction = (value) => {
        value = value.replace(/[^0-9]/g, "");
        setInputValue(value);
    };

    const saveFunction = () => {
        setObsBrowserSourceFadeoutDuration(input_value);
    };

    useEffect(() => {
        if (currentObsBrowserSourceFadeoutDuration.state === "pending") return;
        setInputValue(`${currentObsBrowserSourceFadeoutDuration.data}`);
    }, [currentObsBrowserSourceFadeoutDuration]);

    return (
        <EntryWithSaveButtonContainer
            label={t("config_page.advanced_settings.obs_browser_source_fadeout_duration.label")}
            variable={input_value}
            saveFunction={saveFunction}
            onChangeFunction={onChangeFunction}
            state={currentObsBrowserSourceFadeoutDuration.state}
            width="10rem"
        />
    );
};

const ObsBrowserSourceFontSizeContainer = () => {
    const { t } = useI18n();
    const { currentObsBrowserSourceFontSize, setObsBrowserSourceFontSize } = useAdvancedSettings();
    const [input_value, setInputValue] = useState(`${currentObsBrowserSourceFontSize.data}`);

    const onChangeFunction = (value) => {
        value = value.replace(/[^0-9]/g, "");
        setInputValue(value);
    };

    const saveFunction = () => {
        setObsBrowserSourceFontSize(input_value);
    };

    useEffect(() => {
        if (currentObsBrowserSourceFontSize.state === "pending") return;
        setInputValue(`${currentObsBrowserSourceFontSize.data}`);
    }, [currentObsBrowserSourceFontSize]);

    return (
        <EntryWithSaveButtonContainer
            label={t("config_page.advanced_settings.obs_browser_source_font_size.label")}
            variable={input_value}
            saveFunction={saveFunction}
            onChangeFunction={onChangeFunction}
            state={currentObsBrowserSourceFontSize.state}
            width="10rem"
        />
    );
};

const ObsBrowserSourceFontColorContainer = () => {
    const { t } = useI18n();
    const { currentObsBrowserSourceFontColor, setObsBrowserSourceFontColor } = useAdvancedSettings();
    const [input_value, setInputValue] = useState(`${currentObsBrowserSourceFontColor.data}`);

    const onChangeFunction = (value) => {
        setInputValue(value);
    };

    const saveFunction = () => {
        setObsBrowserSourceFontColor(input_value);
    };

    useEffect(() => {
        if (currentObsBrowserSourceFontColor.state === "pending") return;
        setInputValue(`${currentObsBrowserSourceFontColor.data}`);
    }, [currentObsBrowserSourceFontColor]);

    return (
        <ColorEntryWithSaveButtonContainer
            label={t("config_page.advanced_settings.obs_browser_source_font_color.label")}
            variable={input_value}
            saveFunction={saveFunction}
            onChangeFunction={onChangeFunction}
            state={currentObsBrowserSourceFontColor.state}
            width="10rem"
        />
    );
};

const ObsBrowserSourceFontOutlineThicknessContainer = () => {
    const { t } = useI18n();
    const { currentObsBrowserSourceFontOutlineThickness, setObsBrowserSourceFontOutlineThickness } = useAdvancedSettings();
    const [input_value, setInputValue] = useState(`${currentObsBrowserSourceFontOutlineThickness.data}`);

    const onChangeFunction = (value) => {
        value = value.replace(/[^0-9]/g, "");
        setInputValue(value);
    };

    const saveFunction = () => {
        setObsBrowserSourceFontOutlineThickness(input_value);
    };

    useEffect(() => {
        if (currentObsBrowserSourceFontOutlineThickness.state === "pending") return;
        setInputValue(`${currentObsBrowserSourceFontOutlineThickness.data}`);
    }, [currentObsBrowserSourceFontOutlineThickness]);

    return (
        <EntryWithSaveButtonContainer
            label={t("config_page.advanced_settings.obs_browser_source_font_outline_thickness.label")}
            variable={input_value}
            saveFunction={saveFunction}
            onChangeFunction={onChangeFunction}
            state={currentObsBrowserSourceFontOutlineThickness.state}
            width="10rem"
        />
    );
};

const ObsBrowserSourceFontOutlineColorContainer = () => {
    const { t } = useI18n();
    const { currentObsBrowserSourceFontOutlineColor, setObsBrowserSourceFontOutlineColor } = useAdvancedSettings();
    const [input_value, setInputValue] = useState(`${currentObsBrowserSourceFontOutlineColor.data}`);

    const onChangeFunction = (value) => {
        setInputValue(value);
    };

    const saveFunction = () => {
        setObsBrowserSourceFontOutlineColor(input_value);
    };

    useEffect(() => {
        if (currentObsBrowserSourceFontOutlineColor.state === "pending") return;
        setInputValue(`${currentObsBrowserSourceFontOutlineColor.data}`);
    }, [currentObsBrowserSourceFontOutlineColor]);

    return (
        <ColorEntryWithSaveButtonContainer
            label={t("config_page.advanced_settings.obs_browser_source_font_outline_color.label")}
            variable={input_value}
            saveFunction={saveFunction}
            onChangeFunction={onChangeFunction}
            state={currentObsBrowserSourceFontOutlineColor.state}
            width="10rem"
        />
    );
};
