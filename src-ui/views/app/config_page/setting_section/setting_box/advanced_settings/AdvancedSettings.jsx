import { useI18n } from "@useI18n";
import styles from "./AdvancedSettings.module.scss";

import { useCopyToClipboard, useOpenFolder } from "@logics_common";
import {
    useAdvancedSettings,
    useSaveButtonLogic,
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
import CopyThinSvg from "@images/copy_thin.svg?react";
import CheckMarkSvg from "@images/check_mark.svg?react";

export const AdvancedSettings = () => {
    return (
        <div className={styles.container}>
            <div>
                <OscIpAddressContainer />
                <OscPortContainer />
                <OpenConfigFolderContainer />
            </div>
            <WebsocketContainer />
            <ObsBrowserSourceContainer />
        </div>
    );
};

const OscIpAddressContainer = () => {
    const { t } = useI18n();
    const { currentOscIpAddress, setOscIpAddress } = useAdvancedSettings();

    const { variable, onChangeFunction, saveFunction } = useSaveButtonLogic({
        variable: currentOscIpAddress.data,
        state: currentOscIpAddress.state,
        setFunction: setOscIpAddress,
    });

    return (
        <EntryWithSaveButtonContainer
            label={t("config_page.advanced_settings.osc_ip_address.label")}
            variable={variable}
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

    const { variable, onChangeFunction: rawOnChange, saveFunction } = useSaveButtonLogic({
        variable: currentOscPort.data,
        state: currentOscPort.state,
        setFunction: setOscPort,
    });

    const onChangeFunction = (value) => {
        rawOnChange(value.replace(/[^0-9]/g, ""));
    };

    return (
        <EntryWithSaveButtonContainer
            label={t("config_page.advanced_settings.osc_port.label")}
            variable={variable}
            saveFunction={saveFunction}
            onChangeFunction={onChangeFunction}
            state={currentOscPort.state}
            width="10rem"
            type="number"
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
                ClickedIconComponent={CheckMarkSvg}
                clicked_duration={1000}
                onclickFunction={openFolder_ConfigFile}
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
            <WebsocketUrlContainer />
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

    const { variable, onChangeFunction, saveFunction } = useSaveButtonLogic({
        variable: currentWebsocketHost.data,
        state: currentWebsocketHost.state,
        setFunction: setWebsocketHost,
    });

    return (
        <EntryWithSaveButtonContainer
            label={t("config_page.advanced_settings.websocket_host.label")}
            variable={variable}
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

    const { variable, onChangeFunction: rawOnChange, saveFunction } = useSaveButtonLogic({
        variable: currentWebsocketPort.data,
        state: currentWebsocketPort.state,
        setFunction: setWebsocketPort,
    });

    const onChangeFunction = (value) => {
        rawOnChange(value.replace(/[^0-9]/g, ""));
    };

    return (
        <EntryWithSaveButtonContainer
            label={t("config_page.advanced_settings.websocket_port.label")}
            variable={variable}
            saveFunction={saveFunction}
            onChangeFunction={onChangeFunction}
            state={currentWebsocketPort.state}
            width="10rem"
            type="number"
        />
    );
};


const WebsocketUrlContainer = () => {
    const { t } = useI18n();
    const { copyToClipboard } = useCopyToClipboard();
    const { currentWebsocketHost, currentWebsocketPort, currentWebsocketAuthToken } = useAdvancedSettings();

    const host = currentWebsocketHost.data === "0.0.0.0" ? "127.0.0.1" : currentWebsocketHost.data;
    const token = currentWebsocketAuthToken.data;
    const url = token
        ? `ws://${host}:${currentWebsocketPort.data}/?token=${encodeURIComponent(token)}`
        : `ws://${host}:${currentWebsocketPort.data}`;

    return (
        <ActionButtonContainer
            label={t("config_page.advanced_settings.websocket_url.label")}
            desc={url}
            IconComponent={CopyThinSvg}
            ClickedIconComponent={CheckMarkSvg}
            clicked_duration={1000}
            onclickFunction={() => copyToClipboard(url)}
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
    const { copyToClipboard } = useCopyToClipboard();
    const { currentWebsocketHost, currentObsBrowserSourcePort } = useAdvancedSettings();

    const host = currentWebsocketHost.data === "0.0.0.0" ? "127.0.0.1" : currentWebsocketHost.data;
    const url = `http://${host}:${currentObsBrowserSourcePort.data}/obs`;

    return (
        <ActionButtonContainer
            label={t("config_page.advanced_settings.obs_browser_source_url.label")}
            desc={url}
            IconComponent={CopyThinSvg}
            ClickedIconComponent={CheckMarkSvg}
            clicked_duration={1000}
            onclickFunction={() => copyToClipboard(url)}
        />
    );
};

const ObsBrowserSourcePortContainer = () => {
    const { t } = useI18n();
    const { currentObsBrowserSourcePort, setObsBrowserSourcePort } = useAdvancedSettings();

    const { variable, onChangeFunction: rawOnChange, saveFunction } = useSaveButtonLogic({
        variable: currentObsBrowserSourcePort.data,
        state: currentObsBrowserSourcePort.state,
        setFunction: setObsBrowserSourcePort,
    });

    const onChangeFunction = (value) => {
        rawOnChange(value.replace(/[^0-9]/g, ""));
    };

    return (
        <EntryWithSaveButtonContainer
            label={t("config_page.advanced_settings.obs_browser_source_port.label")}
            variable={variable}
            saveFunction={saveFunction}
            onChangeFunction={onChangeFunction}
            state={currentObsBrowserSourcePort.state}
            width="10rem"
            type="number"
        />
    );
};

const ObsBrowserSourceMaxMessagesContainer = () => {
    const { t } = useI18n();
    const { currentObsBrowserSourceMaxMessages, setObsBrowserSourceMaxMessages } = useAdvancedSettings();

    const { variable, onChangeFunction: rawOnChange, saveFunction } = useSaveButtonLogic({
        variable: currentObsBrowserSourceMaxMessages.data,
        state: currentObsBrowserSourceMaxMessages.state,
        setFunction: setObsBrowserSourceMaxMessages,
    });

    const onChangeFunction = (value) => {
        rawOnChange(value.replace(/[^0-9]/g, ""));
    };

    return (
        <EntryWithSaveButtonContainer
            label={t("config_page.advanced_settings.obs_browser_source_max_messages.label")}
            variable={variable}
            saveFunction={saveFunction}
            onChangeFunction={onChangeFunction}
            state={currentObsBrowserSourceMaxMessages.state}
            width="10rem"
            type="number"
        />
    );
};

const ObsBrowserSourceDisplayDurationContainer = () => {
    const { t } = useI18n();
    const { currentObsBrowserSourceDisplayDuration, setObsBrowserSourceDisplayDuration } = useAdvancedSettings();

    const { variable, onChangeFunction: rawOnChange, saveFunction } = useSaveButtonLogic({
        variable: currentObsBrowserSourceDisplayDuration.data,
        state: currentObsBrowserSourceDisplayDuration.state,
        setFunction: setObsBrowserSourceDisplayDuration,
    });

    const onChangeFunction = (value) => {
        rawOnChange(value.replace(/[^0-9]/g, ""));
    };

    return (
        <EntryWithSaveButtonContainer
            label={t("config_page.advanced_settings.obs_browser_source_display_duration.label")}
            variable={variable}
            saveFunction={saveFunction}
            onChangeFunction={onChangeFunction}
            state={currentObsBrowserSourceDisplayDuration.state}
            width="10rem"
            type="number"
        />
    );
};

const ObsBrowserSourceFadeoutDurationContainer = () => {
    const { t } = useI18n();
    const { currentObsBrowserSourceFadeoutDuration, setObsBrowserSourceFadeoutDuration } = useAdvancedSettings();

    const { variable, onChangeFunction: rawOnChange, saveFunction } = useSaveButtonLogic({
        variable: currentObsBrowserSourceFadeoutDuration.data,
        state: currentObsBrowserSourceFadeoutDuration.state,
        setFunction: setObsBrowserSourceFadeoutDuration,
    });

    const onChangeFunction = (value) => {
        rawOnChange(value.replace(/[^0-9]/g, ""));
    };

    return (
        <EntryWithSaveButtonContainer
            label={t("config_page.advanced_settings.obs_browser_source_fadeout_duration.label")}
            variable={variable}
            saveFunction={saveFunction}
            onChangeFunction={onChangeFunction}
            state={currentObsBrowserSourceFadeoutDuration.state}
            width="10rem"
            type="number"
        />
    );
};

const ObsBrowserSourceFontSizeContainer = () => {
    const { t } = useI18n();
    const { currentObsBrowserSourceFontSize, setObsBrowserSourceFontSize } = useAdvancedSettings();

    const { variable, onChangeFunction: rawOnChange, saveFunction } = useSaveButtonLogic({
        variable: currentObsBrowserSourceFontSize.data,
        state: currentObsBrowserSourceFontSize.state,
        setFunction: setObsBrowserSourceFontSize,
    });

    const onChangeFunction = (value) => {
        rawOnChange(value.replace(/[^0-9]/g, ""));
    };

    return (
        <EntryWithSaveButtonContainer
            label={t("config_page.advanced_settings.obs_browser_source_font_size.label")}
            variable={variable}
            saveFunction={saveFunction}
            onChangeFunction={onChangeFunction}
            state={currentObsBrowserSourceFontSize.state}
            width="10rem"
            type="number"
        />
    );
};

const ObsBrowserSourceFontColorContainer = () => {
    const { t } = useI18n();
    const { currentObsBrowserSourceFontColor, setObsBrowserSourceFontColor } = useAdvancedSettings();

    const { variable, onChangeFunction, saveFunction } = useSaveButtonLogic({
        variable: currentObsBrowserSourceFontColor.data,
        state: currentObsBrowserSourceFontColor.state,
        setFunction: setObsBrowserSourceFontColor,
    });

    return (
        <ColorEntryWithSaveButtonContainer
            label={t("config_page.advanced_settings.obs_browser_source_font_color.label")}
            variable={variable}
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

    const { variable, onChangeFunction: rawOnChange, saveFunction } = useSaveButtonLogic({
        variable: currentObsBrowserSourceFontOutlineThickness.data,
        state: currentObsBrowserSourceFontOutlineThickness.state,
        setFunction: setObsBrowserSourceFontOutlineThickness,
    });

    const onChangeFunction = (value) => {
        rawOnChange(value.replace(/[^0-9]/g, ""));
    };

    return (
        <EntryWithSaveButtonContainer
            label={t("config_page.advanced_settings.obs_browser_source_font_outline_thickness.label")}
            variable={variable}
            saveFunction={saveFunction}
            onChangeFunction={onChangeFunction}
            state={currentObsBrowserSourceFontOutlineThickness.state}
            width="10rem"
            type="number"
        />
    );
};

const ObsBrowserSourceFontOutlineColorContainer = () => {
    const { t } = useI18n();
    const { currentObsBrowserSourceFontOutlineColor, setObsBrowserSourceFontOutlineColor } = useAdvancedSettings();

    const { variable, onChangeFunction, saveFunction } = useSaveButtonLogic({
        variable: currentObsBrowserSourceFontOutlineColor.data,
        state: currentObsBrowserSourceFontOutlineColor.state,
        setFunction: setObsBrowserSourceFontOutlineColor,
    });

    return (
        <ColorEntryWithSaveButtonContainer
            label={t("config_page.advanced_settings.obs_browser_source_font_outline_color.label")}
            variable={variable}
            saveFunction={saveFunction}
            onChangeFunction={onChangeFunction}
            state={currentObsBrowserSourceFontOutlineColor.state}
            width="10rem"
        />
    );
};
